use crate::Directory;
use crate::File;
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::{DirEntry, WalkDir};

#[pyclass]
pub struct DirectoryManager {
    #[pyo3(get)]
    directories: Vec<Directory>,
    #[pyo3(get)]
    files: Vec<File>,
    #[pyo3(get)]
    extensions: Vec<String>,
    #[pyo3(get)]
    root_path: String,

    // Fields for storing filter criteria
    target_extensions: Option<HashSet<String>>,
    target_exact_filenames: Option<HashSet<String>>,
    ignore_path_components: Option<HashSet<String>>,
    ignore_filename_substrings: Option<HashSet<String>>,
    whitelist_filename_substrings: Option<HashSet<String>>,
}

/// Helper functions (not exposed to Python directly)
impl DirectoryManager {
    fn resolve_root_path(root_path: Option<String>) -> String {
        root_path.unwrap_or_else(|| {
            env::current_dir()
                .map(|path| path.to_string_lossy().into_owned())
                .unwrap_or_else(|_| ".".to_string())
        })
    }

    fn canonicalize_path(path_str: &str) -> PyResult<String> {
        let canonical_path = fs::canonicalize(PathBuf::from(path_str)).map_err(|e| {
            PyIOError::new_err(format!("Failed to canonicalize path {}: {}", path_str, e))
        })?;

        let mut path_str_owned = canonical_path.to_string_lossy().into_owned();

        if cfg!(target_os = "windows") && path_str_owned.starts_with(r"\\?\") {
            path_str_owned = path_str_owned[r"\\?\".len()..].to_string();
        }
        Ok(path_str_owned)
    }

    fn _should_include_entry_rust(&self, entry_path: &Path, is_dir: bool) -> bool {
        let root_path_obj = Path::new(&self.root_path);
        let relative_path = match entry_path.strip_prefix(root_path_obj) {
            Ok(p) => p,
            Err(_) => {
                // If entry_path is the root_path itself, strip_prefix results in an empty path.
                // This is fine for path component checks (it won't match any).
                // If it's truly outside, it's an issue, but WalkDir usually handles this.
                if entry_path == root_path_obj {
                    Path::new("") // Represent root as empty relative path for checks
                } else {
                    return true; // Or false, depending on desired strictness
                }
            }
        };

        let entry_name_osstr = entry_path.file_name().unwrap_or_default();
        let entry_name_lower = entry_name_osstr.to_string_lossy().to_lowercase();

        if let Some(ignore_components) = &self.ignore_path_components {
            if !ignore_components.is_empty() {
                for part in relative_path.components() {
                    if let Some(part_str) = part.as_os_str().to_str() {
                        if ignore_components.contains(&part_str.to_lowercase()) {
                            return false;
                        }
                    }
                }
            }
        }

        if is_dir {
            return true;
        }

        // File-specific checks
        let file_ext_lower = entry_path.extension().unwrap_or_default().to_string_lossy().to_lowercase();

        let mut matched_type = false;
        let mut has_target_criteria = false;

        if let Some(target_exts) = &self.target_extensions {
            if !target_exts.is_empty() {
                has_target_criteria = true;
                // target_exts contains ".py", file_ext_lower is "py"
                if target_exts.contains(&format!(".{}", file_ext_lower)) {
                    matched_type = true;
                }
            }
        }

        if !matched_type {
            if let Some(target_exact) = &self.target_exact_filenames {
                if !target_exact.is_empty() {
                    has_target_criteria = true;
                    // target_exact contains "makefile", entry_name_lower is "makefile" (full filename)
                    if target_exact.contains(&entry_name_lower) {
                        matched_type = true;
                    }
                }
            }
        }
        
        if has_target_criteria && !matched_type {
            return false;
        }
        // If no target criteria (extensions or exact names were specified or they were empty), all files pass this stage.

        if let Some(whitelist_subs) = &self.whitelist_filename_substrings {
            if !whitelist_subs.is_empty() {
                if !whitelist_subs.iter().any(|sub| entry_name_lower.contains(sub)) {
                    return false;
                }
            }
        }

        if let Some(ignore_subs) = &self.ignore_filename_substrings {
             if !ignore_subs.is_empty() {
                if ignore_subs.iter().any(|sub| entry_name_lower.contains(sub)) {
                    return false;
                }
            }
        }
        true
    }

    fn get_tree_string_recursive(&self, current_dir_path: &Path, level: usize) -> String {
        let mut result = String::new();
        let padding = "  ".repeat(level);

        let dir_display_name = if level == 0 {
            current_dir_path
                .file_name()
                .map(|name| name.to_string_lossy().into_owned())
                .unwrap_or_else(|| self.root_path.clone())
        } else {
            current_dir_path
                .file_name()
                .unwrap_or_default()
                .to_string_lossy()
                .into_owned()
        };
        result.push_str(&format!("{}{}/\n", padding, dir_display_name));

        let children_padding = "  ".repeat(level + 1);

        let mut sub_dirs_to_process: Vec<&Path> = self
            .directories
            .iter()
            .map(|d_obj| Path::new(&d_obj.path))
            .filter(|p| p.parent() == Some(current_dir_path))
            .collect();
        sub_dirs_to_process.sort();
        for sub_dir_path in sub_dirs_to_process {
            result.push_str(&self.get_tree_string_recursive(sub_dir_path, level + 1));
        }

        let mut files_in_current_dir: Vec<&File> = self
            .files
            .iter()
            .filter(|file_obj| Path::new(&file_obj.path).parent() == Some(current_dir_path))
            .collect();
        files_in_current_dir.sort_by_key(|f| &f.path);
        for file_entry in files_in_current_dir {
            let display_name = if file_entry.extension.is_empty() {
                file_entry.name.clone()
            } else {
                format!("{}.{}", file_entry.name, file_entry.extension)
            };
            result.push_str(&format!("{}{}\n", children_padding, display_name));
        }
        result
    }
}

#[pymethods]
impl DirectoryManager {
    #[new]
    #[pyo3(signature = (
        root_path=None,
        target_extensions=None,
        target_exact_filenames=None,
        ignore_path_components=None,
        ignore_filename_substrings=None,
        whitelist_filename_substrings=None
    ))]
    fn new(
        root_path: Option<String>,
        target_extensions: Option<Vec<String>>,
        target_exact_filenames: Option<Vec<String>>,
        ignore_path_components: Option<Vec<String>>,
        ignore_filename_substrings: Option<Vec<String>>,
        whitelist_filename_substrings: Option<Vec<String>>,
    ) -> PyResult<Self> {
        let root_path_str = Self::resolve_root_path(root_path);
        let absolute_path_str = Self::canonicalize_path(&root_path_str)?;

        let mut manager = DirectoryManager {
            directories: vec![],
            files: vec![],
            extensions: vec![],
            root_path: absolute_path_str,
            target_extensions: target_extensions.map(|v| v.into_iter().map(|s| s.to_lowercase()).collect()),
            target_exact_filenames: target_exact_filenames.map(|v| v.into_iter().map(|s| s.to_lowercase()).collect()),
            ignore_path_components: ignore_path_components.map(|v| v.into_iter().map(|s| s.to_lowercase()).collect()),
            ignore_filename_substrings: ignore_filename_substrings.map(|v| v.into_iter().map(|s| s.to_lowercase()).collect()),
            whitelist_filename_substrings: whitelist_filename_substrings.map(|v| v.into_iter().map(|s| s.to_lowercase()).collect()),
        };

        manager.gather()?;
        Ok(manager)
    }

    pub fn gather(&mut self) -> PyResult<()> {
        self.directories.clear();
        self.files.clear();
        self.extensions.clear();

        let root_path_obj = PathBuf::from(&self.root_path);

        // Temporary vectors to store paths that pass the filter
        let mut filtered_dir_paths: Vec<PathBuf> = Vec::new();
        let mut filtered_file_paths: Vec<PathBuf> = Vec::new();

        // Phase 1: Collect paths using WalkDir and filter_entry
        // The closure for filter_entry borrows `self` immutably.
        let walker = WalkDir::new(&root_path_obj)
            .min_depth(0) // Start from root itself to apply filters correctly to immediate children
            .into_iter()
            .filter_entry(|e: &DirEntry| {
                let path = e.path();
                // Always allow traversal from/into the root directory itself.
                // The actual decision to *list* the root's children is done by _should_include_entry_rust.
                if path == root_path_obj {
                    return true;
                }
                let is_dir = e.file_type().is_dir();
                self._should_include_entry_rust(path, is_dir)
            });

        for entry_result in walker {
            let entry = match entry_result {
                Ok(e) => e,
                Err(e) => {
                    // Log error or handle, e.g., for permission issues
                    eprintln!("Warning: Error walking directory entry: {}", e);
                    continue;
                }
            };
            
            let path = entry.path();

            // Skip adding the root path itself to the lists of collected sub-directories or files
            if path == root_path_obj {
                continue;
            }

            if entry.file_type().is_dir() {
                filtered_dir_paths.push(path.to_path_buf());
            } else if entry.file_type().is_file() {
                filtered_file_paths.push(path.to_path_buf());
            }
        }

        // Phase 2: Populate self.directories and self.files
        // The immutable borrow of `self` from the filter_entry closure has ended.
        // Now we can mutably borrow `self`.

        for dir_path in filtered_dir_paths {
            self.directories.push(Directory::new(&dir_path.to_string_lossy()));
        }

        let mut collected_extensions_set = HashSet::new();
        for file_path in filtered_file_paths {
            match File::new(&file_path.to_string_lossy()) {
                Ok(file_obj) => {
                    if !file_obj.extension.is_empty() {
                        collected_extensions_set.insert(file_obj.extension.clone());
                    }
                    self.files.push(file_obj);
                }
                Err(e) => {
                    eprintln!(
                        "Warning: Could not create File object for {}: {}",
                        file_path.display(),
                        e
                    );
                }
            }
        }

        self.extensions = collected_extensions_set.into_iter().collect();
        self.extensions.sort(); // Sort for consistent ordering

        // Sort directories and files for consistent ordering if desired
        self.directories.sort_by(|a, b| a.path.cmp(&b.path));
        self.files.sort_by(|a, b| a.path.cmp(&b.path));

        Ok(())
    }

    fn find_files(
        &self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        return_first_found: Option<bool>,
    ) -> PyResult<Vec<File>> {
        let mut matched_files = Vec::new();
        let first_only = return_first_found.unwrap_or(false);

        for file in &self.files {
            let name_match = name.map_or(true, |n| file.name == n);
            let sub_path_match = sub_path.map_or(true, |sp| file.path.contains(sp));
            let extension_match = extension.map_or(true, |ext| file.extension == ext);

            if name_match && sub_path_match && extension_match {
                matched_files.push(file.clone());
                if first_only {
                    break;
                }
            }
        }
        Ok(matched_files)
    }

    fn find_text(&self, sub_string: &str) -> PyResult<Vec<File>> {
        let mut matched_files = Vec::new();
        for file in &self.files {
            match file.read() {
                Ok(content) => {
                    if content.contains(sub_string) {
                        matched_files.push(file.clone());
                    }
                }
                Err(e) => {
                    eprintln!("Could not read file {} during find_text: {}", file.path, e);
                }
            }
        }
        Ok(matched_files)
    }

    fn find_file(
        &self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
    ) -> PyResult<File> {
        let files = self.find_files(name, sub_path, extension, Some(true))?;
        files
            .into_iter()
            .next()
            .ok_or_else(|| PyValueError::new_err("No matching file found"))
    }

    fn find_directories(
        &self,
        name: Option<&str>,
        sub_path: Option<&str>,
        return_first_found: Option<bool>,
    ) -> PyResult<Vec<Directory>> {
        let mut matched_directories = Vec::new();
        let first_only = return_first_found.unwrap_or(false);

        for directory in &self.directories {
            let name_match = name.map_or(true, |n| directory.name == n);
            let sub_path_match = sub_path.map_or(true, |sp| directory.path.contains(sp));

            if name_match && sub_path_match {
                matched_directories.push(directory.clone());
                if first_only {
                    break;
                }
            }
        }
        Ok(matched_directories)
    }

    fn create_file(
        &mut self,
        directory_sub_path: &str,
        file_stem: &str,
        file_extension: Option<&str>,
        file_content: Option<&str>,
    ) -> PyResult<()> {
        let target_dir_path = Path::new(&self.root_path).join(directory_sub_path);

        fs::create_dir_all(&target_dir_path).map_err(|e| {
            PyIOError::new_err(format!(
                "Failed to create directory {}: {}",
                target_dir_path.display(),
                e
            ))
        })?;

        let file_basename = match file_extension {
            Some(ext) if !ext.is_empty() => {
                format!("{}.{}", file_stem, ext.trim_start_matches('.'))
            }
            _ => file_stem.to_string(),
        };

        let new_file_path = target_dir_path.join(&file_basename);

        // Create the file first before instantiating File struct, which reads metadata
        fs::File::create(&new_file_path).map_err(|e| {
            PyIOError::new_err(format!(
                "Failed to create file {}: {}",
                new_file_path.display(),
                e
            ))
        })?;
        
        if let Some(content) = file_content {
            // Use fs::write for simplicity if creating and writing immediately
            fs::write(&new_file_path, content).map_err(|e| {
                 PyIOError::new_err(format!(
                    "Failed to write content to new file {}: {}",
                    new_file_path.display(),
                    e
                ))
            })?;
        }

        // Now create the File object, metadata will be fresh
        let new_file_obj = File::new(&new_file_path.to_string_lossy())?;


        if !new_file_obj.extension.is_empty() && !self.extensions.contains(&new_file_obj.extension)
        {
            self.extensions.push(new_file_obj.extension.clone());
            self.extensions.sort();
        }
        self.files.push(new_file_obj);

        Ok(())
    }
    
    #[pyo3(signature = (new_full_name, current_name_stem=None, current_sub_path=None, current_extension=None))]
    fn rename_file(
        &mut self,
        new_full_name: &str,            
        current_name_stem: Option<&str>, 
        current_sub_path: Option<&str>,  
        current_extension: Option<&str>, 
    ) -> PyResult<()> {
        let file_to_rename_info =
            self.find_file(current_name_stem, current_sub_path, current_extension)?;
        let old_path_key = file_to_rename_info.path.clone();

        let file_in_manager = self
            .files
            .iter_mut()
            .find(|f| f.path == old_path_key)
            .ok_or_else(|| {
                PyIOError::new_err(format!(
                    "File {} not found in manager cache for rename.",
                    old_path_key
                ))
            })?;

        file_in_manager.rename(new_full_name)?;
        Ok(())
    }

    fn print_tree(&self) -> PyResult<()> {
        let root_path_obj = Path::new(&self.root_path);
        let tree_string = self.get_tree_string_recursive(root_path_obj, 0);
        println!("{}", tree_string);
        Ok(())
    }

    fn compare_to(&self, other: &DirectoryManager) -> PyResult<Vec<String>> {
        let self_files_paths: HashSet<_> = self.files.iter().map(|f| f.path.as_str()).collect();
        let other_files_paths: HashSet<_> = other.files.iter().map(|f| f.path.as_str()).collect();

        let diff: Vec<String> = self_files_paths
            .symmetric_difference(&other_files_paths)
            .map(|s| s.to_string())
            .collect();
        Ok(diff)
    }

    fn delete_files(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        files_to_delete_override: Option<Vec<File>>,
    ) -> PyResult<()> {
        let files_found_for_deletion = if let Some(override_files) = files_to_delete_override {
            override_files
        } else {
            self.find_files(name, sub_path, extension, Some(false))?
        };

        if files_found_for_deletion.is_empty() {
            return Ok(());
        }

        let paths_to_delete: HashSet<_> = files_found_for_deletion
            .iter()
            .map(|f| f.path.as_str())
            .collect();

        for file_path_str in &paths_to_delete {
            fs::remove_file(file_path_str).map_err(|e| {
                PyIOError::new_err(format!("Failed to delete file {}: {}", file_path_str, e))
            })?;
        }

        self.files
            .retain(|f| !paths_to_delete.contains(f.path.as_str()));
        // Also update extensions list if needed, though not critical for this script
        Ok(())
    }

    fn move_files(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        dest_directory_name: Option<&str>,
        dest_sub_path: Option<&str>,
        files_to_move_override: Option<Vec<File>>,
    ) -> PyResult<()> {
        let actual_files_to_move_info = if let Some(override_files) = files_to_move_override {
            override_files
        } else {
            self.find_files(name, sub_path, extension, Some(false))?
        };

        if actual_files_to_move_info.is_empty() {
            return Ok(());
        }

        let destination_directories =
            self.find_directories(dest_directory_name, dest_sub_path, Some(true))?; // Ensure only one target dir

        if destination_directories.len() != 1 {
            return Err(PyIOError::new_err(
                "Destination directory not found or not unique.",
            ));
        }

        let dest_dir_path = PathBuf::from(&destination_directories[0].path);

        for file_info_clone in actual_files_to_move_info {
            let old_file_path_str = file_info_clone.path.clone();
            let file_name_osstr = Path::new(&old_file_path_str).file_name().ok_or_else(|| {
                PyValueError::new_err(format!("File has no name: {}", old_file_path_str))
            })?;

            let new_file_path = dest_dir_path.join(file_name_osstr);

            fs::rename(&old_file_path_str, &new_file_path).map_err(|e| {
                PyIOError::new_err(format!(
                    "Failed to move file {} to {}: {}",
                    old_file_path_str,
                    new_file_path.display(),
                    e
                ))
            })?;

            if let Some(f_in_manager) = self.files.iter_mut().find(|f| f.path == old_file_path_str)
            {
                f_in_manager.path = new_file_path.to_string_lossy().into_owned();
                 f_in_manager.name = new_file_path
                    .file_stem()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned();
                f_in_manager.extension = new_file_path
                    .extension()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .into_owned();
            }
        }
        Ok(())
    }
    
    fn move_file(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        dest_directory_name: Option<&str>,
        dest_sub_path: Option<&str>,
    ) -> PyResult<()> {
        let files_found = self.find_files(name, sub_path, extension, Some(true))?;
        if files_found.is_empty() {
            return Err(PyIOError::new_err("No matching file found to move."));
        }
        self.move_files(
            None, // Name, sub_path, extension are already used to find the specific file(s)
            None,
            None,
            dest_directory_name,
            dest_sub_path,
            Some(files_found), // Pass the found files directly
        )
    }

    fn create_directory(&mut self, directory_sub_path: &str) -> PyResult<()> {
        let full_path = Path::new(&self.root_path).join(directory_sub_path);
        fs::create_dir_all(&full_path).map_err(|e| {
            PyIOError::new_err(format!(
                "Failed to create directory {}: {}",
                full_path.display(),
                e
            ))
        })?;

        let new_directory = Directory::new(&full_path.to_string_lossy());
        // Avoid adding if it's already there (e.g., due to race or re-creation)
        if !self.directories.iter().any(|d| d.path == new_directory.path) {
            self.directories.push(new_directory);
        }
        Ok(())
    }

    fn delete_directories(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        directories_to_delete_override: Option<Vec<Directory>>,
    ) -> PyResult<()> {
        let actual_directories_to_delete =
            if let Some(override_dirs) = directories_to_delete_override {
                override_dirs
            } else {
                self.find_directories(name, sub_path, Some(false))?
            };

        if actual_directories_to_delete.is_empty() {
            return Ok(());
        }

        let dir_paths_to_delete_set: HashSet<PathBuf> = actual_directories_to_delete
            .iter()
            .map(|d| PathBuf::from(&d.path)) 
            .collect();

        for dir_path_to_delete in &dir_paths_to_delete_set {
            fs::remove_dir_all(dir_path_to_delete).map_err(|e| {
                PyIOError::new_err(format!(
                    "Failed to delete directory {}: {}",
                    dir_path_to_delete.display(),
                    e
                ))
            })?;
        }

        self.directories
            .retain(|d| !dir_paths_to_delete_set.contains(&PathBuf::from(&d.path)));

        // Also remove files that were within these deleted directories
        self.files.retain(|file_obj| {
            let file_path = Path::new(&file_obj.path);
            // Check if any ancestor of the file is one of the deleted directories
            !dir_paths_to_delete_set.iter().any(|deleted_dir_path| file_path.starts_with(deleted_dir_path))
        });
        Ok(())
    }

    fn move_directories(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        dest_dir_name_filter: Option<&str>, // This is the name of an existing directory to move INTO
        dest_dir_sub_path_filter: Option<&str>,
    ) -> PyResult<()> {
        let dirs_to_move_clones = self.find_directories(name, sub_path, Some(false))?;
        if dirs_to_move_clones.is_empty() {
            return Ok(());
        }

        let destination_parent_dirs =
            self.find_directories(dest_dir_name_filter, dest_dir_sub_path_filter, Some(true))?; // Ensure unique destination
        if destination_parent_dirs.len() != 1 {
            return Err(PyIOError::new_err(
                "Destination parent directory not found or not unique.",
            ));
        }
        let dest_parent_path = PathBuf::from(&destination_parent_dirs[0].path);

        for dir_to_move_clone in dirs_to_move_clones {
            let old_dir_path_str = &dir_to_move_clone.path;
            let dir_name_osstr = Path::new(old_dir_path_str).file_name().ok_or_else(|| {
                PyValueError::new_err(format!("Directory has no name: {}", old_dir_path_str))
            })?;

            let new_dir_path = dest_parent_path.join(dir_name_osstr);

            fs::rename(old_dir_path_str, &new_dir_path).map_err(|e| {
                PyIOError::new_err(format!(
                    "Failed to move directory {} to {}: {}",
                    old_dir_path_str,
                    new_dir_path.display(),
                    e
                ))
            })?;
            
            // Update paths for the moved directory and all files/subdirectories within it in the manager
            let old_dir_path_prefix = PathBuf::from(old_dir_path_str);

            if let Some(dir_in_manager) = self
                .directories
                .iter_mut()
                .find(|d| d.path == *old_dir_path_str)
            {
                dir_in_manager.path = new_dir_path.to_string_lossy().into_owned();
                dir_in_manager.name = dir_name_osstr.to_string_lossy().into_owned();
            }
            // Update paths for sub-directories
            for sub_dir_in_manager in self.directories.iter_mut() {
                let current_sub_dir_path = PathBuf::from(&sub_dir_in_manager.path);
                if current_sub_dir_path.starts_with(&old_dir_path_prefix) && current_sub_dir_path != old_dir_path_prefix {
                    if let Ok(path_suffix) = current_sub_dir_path.strip_prefix(&old_dir_path_prefix) {
                        let updated_path = new_dir_path.join(path_suffix);
                        sub_dir_in_manager.path = updated_path.to_string_lossy().into_owned();
                    }
                }
            }
            // Update paths for files
            for file_in_manager in self.files.iter_mut() {
                 let current_file_path = PathBuf::from(&file_in_manager.path);
                 if current_file_path.starts_with(&old_dir_path_prefix) {
                     if let Ok(path_suffix) = current_file_path.strip_prefix(&old_dir_path_prefix) {
                         let updated_path = new_dir_path.join(path_suffix);
                         file_in_manager.path = updated_path.to_string_lossy().into_owned();
                     }
                 }
            }
        }
        Ok(())
    }
}