use crate::Directory;
use crate::File;
use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use walkdir::WalkDir;

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
}

/// Helper functions
impl DirectoryManager {
    /// Resolves the provided root path.
    /// If `root_path` is `None`, it defaults to the current working directory.
    /// This is a helper function to simplify the initialization of `DirectoryManager`.
    ///
    /// # Arguments
    /// * `root_path` - An `Option<String>` representing the provided root path.
    ///
    /// # Returns
    /// A `String` representing the resolved root path.
    fn resolve_root_path(root_path: Option<String>) -> String {
        root_path.unwrap_or_else(|| {
            // Attempt to get the current working directory. If it fails, default to "."
            env::current_dir()
                .map(|path| path.to_string_lossy().into_owned())
                .unwrap_or_else(|_| ".".to_string())
        })
    }

    /// Canonicalizes the given path, converting it to an absolute path.
    /// On Windows, this function also removes the '\\?\' prefix if present.
    /// This is a helper function to handle path conversion and normalization.
    ///
    /// # Arguments
    /// * `path` - A `String` representing the path to be canonicalized.
    ///
    /// # Returns
    /// A `PyResult<String>` which is Ok containing the canonicalized path string,
    /// or an Err in case of any error during path resolution.
    fn canonicalize_path(path: String) -> PyResult<String> {
        let canonical_path =
            fs::canonicalize(PathBuf::from(path)).map_err(|e| PyIOError::new_err(e.to_string()))?;

        let mut path_str = canonical_path.to_string_lossy().into_owned();

        // Special handling for Windows paths to remove the '\\?\' prefix
        if cfg!(target_os = "windows") {
            path_str = path_str.trim_start_matches(r"\\?\").to_string();
        }

        Ok(path_str)
    }
}

#[pymethods]
impl DirectoryManager {
    #[new]
    fn new(root_path: Option<String>) -> PyResult<Self> {
        // Determine the root path and convert to absolute path
        let root_path_str = Self::resolve_root_path(root_path);
        let absolute_path_str = Self::canonicalize_path(root_path_str)?;

        // Initialize the DirectoryManager
        let mut manager = DirectoryManager {
            directories: vec![],
            files: vec![],
            extensions: vec![],
            root_path: absolute_path_str,
        };

        // Populate directories, files, and extensions
        manager.gather()?;

        Ok(manager)
    }

    /// Gathers and refreshes the lists of directories, files, and extensions.
    /// This function clears existing entries and repopulates them based on the current state
    /// of the file system starting from `root_path`.
    fn gather(&mut self) -> PyResult<()> {
        // Clear existing entries
        self.directories.clear();
        self.files.clear();
        self.extensions.clear();

        // Walk through the directory structure starting from root_path
        for entry in WalkDir::new(&self.root_path) {
            let entry = entry.map_err(|e| PyIOError::new_err(e.to_string()))?;
            let path = entry.path().to_path_buf();

            // Check if the path is a directory or a file
            if path.is_dir() {
                self.directories
                    .push(Directory::new(path.to_string_lossy().to_string()));
            } else if path.is_file() {
                match File::new(path.to_string_lossy().to_string()) {
                    Ok(file) => {
                        // Add unique extensions to the list
                        if !self.extensions.contains(&file.extension) {
                            self.extensions.push(file.extension.clone());
                        }
                        // Add the file to the list
                        self.files.push(file);
                    }
                    Err(e) => {
                        eprintln!("Error creating file: {:?}", e);
                    }
                }
            }
        }
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

        for file in &self.files {
            let name_match = match name {
                Some(n) => file.name == n,
                None => true,
            };

            let sub_path_match = match sub_path {
                Some(sp) => file.path.contains(sp),
                None => true,
            };

            let extension_match = match extension {
                Some(ext) => file.extension == ext,
                None => true,
            };

            if name_match && sub_path_match && extension_match {
                matched_files.push(file.clone());
                if return_first_found.unwrap_or(false) {
                    break;
                }
            }
        }

        Ok(matched_files)
    }


    fn find_text(&self, sub_string: &str) -> PyResult<Vec<File>> {
        let mut matched_files = Vec::new();

        for file in &self.files {
            // Use the read method from the File class to get file content
            let content = file.read()?;
            
            // Perform exact substring search
            if content.contains(sub_string) {
                matched_files.push(file.clone());
            }
        }

        Ok(matched_files)
    }


    /// Finds a single file based on name, sub-path, and extension criteria.
    /// Returns the first file that matches the criteria.
    /// If no match is found, returns an error.
    fn find_file(
        &self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
    ) -> PyResult<File> {
        let files = self.find_files(name, sub_path, extension, Some(true))?;

        // Check if a file was found and return it, or return an error if not
        files
            .into_iter()
            .next()
            .ok_or_else(|| PyValueError::new_err("No matching file found"))
    }

    fn find_directories(
        &self,
        name: Option<&str>,
        sub_path: Option<&str>,
        return_first_found: Option<bool>, // New optional parameter
    ) -> PyResult<Vec<Directory>> {
        let mut matched_directories = Vec::new();

        for directory in &self.directories {
            let name_match = match name {
                Some(n) => directory.name == n,
                None => true,
            };

            let sub_path_match = match sub_path {
                Some(sp) => directory.path.contains(sp),
                None => true,
            };

            if name_match && sub_path_match {
                matched_directories.push(directory.clone());
                if return_first_found.unwrap_or(false) {
                    break;
                }
            }
        }

        Ok(matched_directories)
    }

    fn create_file(
        &mut self,
        directory_sub_path: &str,
        file_name: &str,
        file_extension: Option<&str>,
        file_content: Option<&str>,
    ) -> PyResult<()> {
        // Construct the full path of the file
        let full_path = Path::new(&self.root_path).join(directory_sub_path);

        // Join the file name and the file extension if provided
        let file_name_with_extension = match file_extension {
            Some(ext) => format!("{}.{}", file_name, ext),
            None => file_name.to_string(),
        };

        // Create the file
        let _ = fs::File::create(full_path.join(&file_name_with_extension))?;

        // Create a new File object
        let new_file = File::new(
            full_path
                .join(&file_name_with_extension)
                .to_string_lossy()
                .into_owned(),
        )?;

        // Write content to the file if provided
        if let Some(content) = file_content {
            new_file.write(content.to_string(), true)?;
        }

        // Add the new file to the files vector
        self.files.push(new_file);

        Ok(())
    }

    fn rename_file(
        &mut self,
        new_name: &str,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
    ) -> PyResult<()> {
        // Find the file to rename
        let old_file = self.find_file(name, sub_path, extension)?;

        // Rename the file
        let mut renamed_file = old_file.clone();
        renamed_file.rename(new_name);

        // Update the file in the files list
        for file in &mut self.files {
            if file.path == old_file.path {
                *file = renamed_file.clone();
                break;
            }
        }

        Ok(())
    }

    fn print_tree(&self) -> PyResult<()> {
        let tree_string = self.get_sub_tree_string(None, None);
        println!("{}", tree_string);
        Ok(())
    }
    

    fn get_sub_tree_string(&self, current_path: Option<&str>, level: Option<usize>) -> String {
        let current_path = current_path.unwrap_or(&self.root_path);
        let level = level.unwrap_or(0);
        
        let mut result = String::new();
        let padding = " ".repeat(level * 2);

        // Add the name of the current directory to the result
        if let Some(name) = Path::new(current_path).file_name().and_then(|n| n.to_str()) {
            result.push_str(&format!("{}{}/\n", padding, name));
        }

        // Process sub-directories within the current directory
        for directory in &self.directories {
            if Path::new(&directory.path)
                .parent()
                .and_then(|p| p.to_str())
                .map_or(false, |p| p == current_path)
            {
                result.push_str(&self.get_sub_tree_string(Some(&directory.path), Some(level + 1)));
            }
        }

        // Add files within the current directory, with an extra indent
        let file_padding = " ".repeat((level + 1) * 2);
        for file in &self.files {
            if Path::new(&file.path)
                .parent()
                .and_then(|p| p.to_str())
                .map_or(false, |p| p == current_path)
            {
                let display_name = format!("{}.{}", file.name, file.extension);
                result.push_str(&format!("{}{}\n", file_padding, display_name));
            }
        }

        result
    }
    

    fn compare_to(&self, other: &DirectoryManager) -> PyResult<Vec<String>> {
        let self_files: HashSet<_> = self.files.iter().map(|f| &f.path).collect();
        let other_files: HashSet<_> = other.files.iter().map(|f| &f.path).collect();

        let diff: Vec<String> = self_files
            .symmetric_difference(&other_files)
            .map(|s| s.to_string())
            .collect();

        Ok(diff)
    }

    fn delete_files(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        files_to_delete: Option<Vec<File>>,
    ) -> PyResult<()> {
        let files_to_delete = if let Some(override_files) = files_to_delete {
            // Directly use the provided list of directories
            override_files
        } else {
            // Find directories based on provided criteria. (return all - not return first found)
            self.find_files(name, sub_path, extension, Some(false))?
        };

        if files_to_delete.is_empty() {
            return Err(PyIOError::new_err("No matching files found to delete"));
        }

        for file in &files_to_delete {
            fs::remove_file(&file.path).map_err(|e| PyIOError::new_err(e.to_string()))?;
        }

        // Remove the deleted files from the files vector
        self.files.retain(|f| !files_to_delete.contains(f));

        Ok(())
    }

    fn move_files(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        extension: Option<&str>,
        dest_directory_name: Option<&str>,
        dest_sub_path: Option<&str>,
        files_to_move: Option<Vec<File>>,
    ) -> PyResult<()> {
        let files_to_move = if let Some(override_files) = files_to_move {
            override_files
        } else {
            self.find_files(name, sub_path, extension, Some(false))?
        };

        let destination_directories =
            self.find_directories(dest_directory_name, dest_sub_path, Some(false))?;

        if files_to_move.is_empty() {
            return Err(PyIOError::new_err("No matching files found to move"));
        }

        if destination_directories.len() != 1 {
            return Err(PyIOError::new_err(
                "Destination directory not found or not unique",
            ));
        }

        let dest_path = PathBuf::from(&destination_directories[0].path);

        for file in files_to_move {
            let new_file_path = dest_path.join(&file.name);
            fs::rename(&file.path, &new_file_path)
                .map_err(|e| PyIOError::new_err(e.to_string()))?;
            // Update file path in the original vector
            if let Some(f) = self.files.iter_mut().find(|f| f.path == file.path) {
                f.path = new_file_path.to_string_lossy().into_owned();
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
        // Find the first file that matches the criteria
        let files_to_move = self.find_files(name, sub_path, extension, Some(true))?;

        // Check if a file was found
        if files_to_move.is_empty() {
            return Err(PyIOError::new_err("No matching file found to move"));
        }

        // Call move_files with the first found file
        // Some parameters are not used since files_to_move_override is provided
        self.move_files(
            None,
            None,
            None,
            dest_directory_name,
            dest_sub_path,
            Some(vec![files_to_move[0].clone()]),
        )
    }

    fn create_directory(&mut self, directory_sub_path: &str) -> PyResult<()> {
        // Construct the full path of the directory
        let full_path = Path::new(&self.root_path).join(directory_sub_path);

        // Create the directory
        fs::create_dir_all(&full_path).map_err(|e| PyIOError::new_err(e.to_string()))?;

        // Create a new Directory object
        let new_directory = Directory::new(full_path.to_string_lossy().into_owned());

        // Add the new directory to the directories vector
        self.directories.push(new_directory);

        Ok(())
    }

    fn delete_directories(
        &mut self,
        name: Option<&str>,
        sub_path: Option<&str>,
        directories_to_delete: Option<Vec<Directory>>,
    ) -> PyResult<()> {
        let directories_to_delete = if let Some(override_directories) = directories_to_delete {
            // Directly use the provided list of directories
            override_directories
        } else {
            // Find directories based on provided criteria
            self.find_directories(name, sub_path, Some(false))?
        };

        if directories_to_delete.is_empty() {
            return Err(PyIOError::new_err(
                "No matching directories found to delete",
            ));
        }

        for directory in &directories_to_delete {
            fs::remove_dir_all(&directory.path).map_err(|e| PyIOError::new_err(e.to_string()))?;
        }

        // Remove the deleted directories from the directories vector
        self.directories
            .retain(|d| !directories_to_delete.iter().any(|x| x.path == d.path));

        Ok(())
    }

    fn move_directories(
        &mut self, // Changed to a mutable reference
        name: Option<&str>,
        sub_path: Option<&str>,
        dest_name: Option<&str>,
        dest_sub_path: Option<&str>,
    ) -> PyResult<()> {
        let directories_to_move = self.find_directories(name, sub_path, Some(false))?;
        let destination_directories =
            self.find_directories(dest_name, dest_sub_path, Some(false))?;

        if directories_to_move.is_empty() {
            return Err(PyIOError::new_err("No matching directories found to move"));
        }

        if destination_directories.len() != 1 {
            return Err(PyIOError::new_err(
                "Destination directory not found or not unique",
            ));
        }

        let dest_path = PathBuf::from(&destination_directories[0].path);

        // Collect indices of directories to be moved
        let indices_to_move: Vec<usize> = self
            .directories
            .iter()
            .enumerate()
            .filter_map(|(index, dir)| {
                if directories_to_move.iter().any(|d| d.path == dir.path) {
                    Some(index)
                } else {
                    None
                }
            })
            .collect();

        // Move directories and update their paths in the vector
        for index in indices_to_move {
            if let Some(dir) = self.directories.get_mut(index) {
                let new_directory_path = dest_path.join(&dir.name);
                fs::rename(&dir.path, &new_directory_path)
                    .map_err(|e| PyIOError::new_err(e.to_string()))?;
                dir.path = new_directory_path.to_string_lossy().into_owned();
            }
        }

        Ok(())
    }
}
