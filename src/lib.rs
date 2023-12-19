use pyo3::PyResult;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat};
use pyo3::exceptions::PyIOError;
use pyo3::exceptions::PyValueError;

/// UNIX_EPOCH is a reference point (January 1, 1970, at 00:00 UTC)
use std::time::UNIX_EPOCH;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::Path;
use std::path::PathBuf;
use std::fs::OpenOptions;
use std::io::Write;
use walkdir::WalkDir;

#[pyclass]
#[derive(Clone)]
struct File {
    #[pyo3(get)]
    path: String,
    #[pyo3(get)]
    name: String,
    #[pyo3(get)]
    extension: String,
    #[pyo3(get)]
    size: u64,
}

impl PartialEq for File {
    fn eq(&self, other: &Self) -> bool {
        self.path == other.path
    }
}

#[pymethods]
impl File {
    #[new]
    fn new(path: String) -> PyResult<Self> {
        let path_obj = Path::new(&path);

        let name = path_obj
            .file_stem()
            .map_or_else(|| "".to_string(), |n| n.to_string_lossy().to_string());

        let extension = path_obj
            .extension()
            .map_or_else(|| "".to_string(), |e| e.to_string_lossy().to_string());

        let size = fs::metadata(&path)
            .map_err(|e| PyValueError::new_err(e.to_string()))?
            .len();

        Ok(File {
            path,
            name,
            extension,
            size,
        })
    }

    fn read(&self) -> PyResult<String> {
        let content =
            fs::read_to_string(&self.path).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(content)
    }

    /// Overwrites the file with the given text.
    fn write_over(&self, text: String) -> PyResult<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .truncate(true)
            .open(&self.path)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;

        write!(file, "{}", text)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;

        Ok(())
    }

    /// Appends the given text to the end of the file, on a new line.
    fn concat(&self, text: String) -> PyResult<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .append(true)
            .open(&self.path)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;

        writeln!(file, "{}", text)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;

        Ok(())
    }

    fn get_metadata(&self, py: Python) -> PyResult<PyObject> {
        let metadata = fs::metadata(&self.path)
            .map_err(|e| PyValueError::new_err(e.to_string()))?;

        let dict = PyDict::new(py);

        if let Ok(last_modified) = metadata.modified() {
            if let Ok(duration_since_epoch) = last_modified.duration_since(UNIX_EPOCH) {
                dict.set_item("last_modified", PyFloat::new(py, duration_since_epoch.as_secs_f64()))?;
            }
        }

        if let Ok(creation_time) = metadata.created() {
            if let Ok(duration_since_epoch) = creation_time.duration_since(UNIX_EPOCH) {
                dict.set_item("creation_time", PyFloat::new(py, duration_since_epoch.as_secs_f64()))?;
            }
        }

        dict.set_item("is_read_only", metadata.permissions().readonly())?;
        dict.set_item("size", metadata.len())?;

        // Convert the dictionary to a PyObject and return
        Ok(dict.to_object(py))
    }

    fn is_read_only(&self) -> PyResult<bool> {
        let metadata =
            fs::metadata(&self.path).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(metadata.permissions().readonly())
    }

    fn __repr__(&self) -> PyResult<&String> {
        Ok(&self.name)
    }

    fn __eq__(&self, other: &File) -> PyResult<bool> {
        Ok(self.path == other.path
            && self.name == other.name
            && self.extension == other.extension
            && self.size == other.size)
    }
}

#[pyclass]
#[derive(Clone)]
struct Directory {
    #[pyo3(get)]
    path: String,
    #[pyo3(get)]
    name: String,
}

#[pymethods]
impl Directory {
    #[new]
    fn new(path: String) -> Self {
        let name = Path::new(&path)
            .file_name()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();

        Directory { path, name }
    }

    fn contains(&self, target_path: String) -> PyResult<bool> {
        Ok(Path::new(&self.path).join(&target_path).exists())
    }

    fn __repr__(&self) -> PyResult<&String> {
        Ok(&self.path)
    }

    fn __eq__(&self, other: &Directory) -> PyResult<bool> {
        Ok(self.path == other.path && self.name == other.name)
    }
}

#[pyclass]
struct DirectoryManager {
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
        return_first_found: Option<bool>, // New optional parameter
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

    fn print_tree(&self, level: Option<usize>) -> PyResult<()> {
        self.print_sub_tree(&self.root_path, level.unwrap_or(0))
    }

    fn print_sub_tree(&self, current_path: &str, level: usize) -> PyResult<()> {
        let padding = " ".repeat(level * 2);

        // Print the name of the current directory
        if let Some(name) = Path::new(current_path).file_name().and_then(|n| n.to_str()) {
            println!("{}{}/", padding, name);
        }

        // Print sub-directories within the current directory
        for directory in &self.directories {
            if Path::new(&directory.path)
                .parent()
                .and_then(|p| p.to_str())
                .map_or(false, |p| p == current_path)
            {
                self.print_sub_tree(&directory.path, level + 1)?;
            }
        }

        // Print files within the current directory, with an extra indent
        let file_padding = " ".repeat((level + 1) * 2);
        for file in &self.files {
            if Path::new(&file.path)
                .parent()
                .and_then(|p| p.to_str())
                .map_or(false, |p| p == current_path)
            {
                let display_name = format!("{}.{}", file.name, file.extension);
                println!("{}{}", file_padding, display_name);
            }
        }

        Ok(())
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
    ) -> PyResult<()> {
        let files_to_move = self.find_files(name, sub_path, extension, Some(false))?;
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

        // Collect indices of files to be moved
        let indices_to_move: Vec<usize> = self
            .files
            .iter()
            .enumerate()
            .filter_map(|(index, file)| {
                if files_to_move.iter().any(|f| f.path == file.path) {
                    Some(index)
                } else {
                    None
                }
            })
            .collect();

        // Move files and update their paths in the vector
        for index in indices_to_move {
            if let Some(file) = self.files.get_mut(index) {
                let new_file_path = dest_path.join(&file.name);
                fs::rename(&file.path, &new_file_path)
                    .map_err(|e| PyIOError::new_err(e.to_string()))?;
                file.path = new_file_path.to_string_lossy().into_owned();
            }
        }

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

#[pymodule]
fn dirman(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<File>()?;
    m.add_class::<Directory>()?;
    m.add_class::<DirectoryManager>()?;
    Ok(())
}
