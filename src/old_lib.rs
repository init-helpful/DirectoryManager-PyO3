use pyo3::prelude::*;
// use pyo3::wrap_pyfunction;
use std::fs;
use std::path::{Path, PathBuf};

#[pyclass]
#[derive(Clone)]
struct File {
    name: String,
    path: PathBuf,
}

#[pymethods]
impl File {
    #[new]
    fn new(name: String, path: PathBuf) -> Self {
        File { name, path }
    }

    fn get_path(&self) -> &PathBuf {
        &self.path
    }

    fn file_name_without_extension(&self) -> Option<String> {
        Path::new(&self.name)
            .file_stem()
            .and_then(|s| s.to_str())
            .map(|s| s.to_string())
    }

    fn extension(&self) -> Option<String> {
        Path::new(&self.name)
            .extension()
            .and_then(|s| s.to_str())
            .map(|s| s.to_string())
    }
}

#[pyclass]
struct Directory {
    files: Vec<File>,
    path: PathBuf,
}

#[pymethods]
impl Directory {
    #[new]
    fn new(files: Vec<File>, path: PathBuf) -> Self {
        Directory { files, path }
    }

    fn find_files_by_name(&self, name: &str) -> Vec<File> {
        self.files.iter().filter(|f| f.name == name).cloned().collect()
    }

    fn get_path(&self) -> &PathBuf {
        &self.path
    }

    fn find_files_by_extension(&self, extension: &str) -> Vec<File> {
        self.files.iter().filter(|f| {
            f.extension()
                .map(|ext| ext == extension)
                .unwrap_or(false)
        }).cloned().collect()
    }

    pub fn load_files(&mut self) -> Result<(), std::io::Error> {
        if !self.is_loaded {
            let entries = fs::read_dir(&self.path)?;

            for entry in entries {
                let entry = entry?;
                if entry.path().is_file() {
                    self.files.push(File::new(
                        entry.file_name().to_string_lossy().into_owned(),
                        entry.path(),
                    ));
                }
            }

            self.is_loaded = true;
        }

        Ok(())
    }
}

#[pyclass]
struct DirectoryManager {
    directories: Vec<Directory>,
    root_path: PathBuf,
}

#[pymethods]
impl DirectoryManager {
    #[new]
    fn new(root_path: Option<PathBuf>) -> Self {
        let path = match root_path {
            Some(p) if !p.as_os_str().is_empty() => p,
            _ => env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
        };

        DirectoryManager {
            directories: Vec::new(),
            root_path: path,
        }
    }

    fn get_path(&self) -> &PathBuf {
        &self.root_path
    }


    // fn gather_directories(&mut self) {
    //     let entries = fs::read_dir(&self.root_path).unwrap();
    //     for entry in entries {
    //         let entry = entry.unwrap();
    //         let path = entry.path();
    //         if path.is_dir() {
    //             let files = fs::read_dir(&path)
    //                 .unwrap()
    //                 .filter_map(|e| e.ok())
    //                 .filter(|e| e.path().is_file())
    //                 .map(|e| File::new(e.file_name().to_string_lossy().into_owned(), e.path()))
    //                 .collect();

    //             self.directories.push(Directory::new(files, path));
    //         }
    //     }
    // }

    fn gather_directories(&mut self) -> Result<(), std::io::Error> {
        let entries = fs::read_dir(&self.root_path)?;
    
        for entry in entries {
            let entry = entry?;
            let path = entry.path();
    
            if path.is_dir() {
                // Directory loading can be deferred
                self.directories.push(Directory::new(Vec::new(), path));
            }
        }
    
        Ok(())
    }

     // Function to find all files with a specific extension
     fn find_files_by_extension_a(&mut self, extension: &str) -> Vec<&File> {
        let mut extension_map = HashMap::new();
    
        for directory in &mut self.directories {
            if directory.files.is_empty() {
                // Lazy loading files in a directory
                directory.load_files()?;
            }
    
            for file in &directory.files {
                extension_map.entry(file.extension())
                    .or_insert_with(Vec::new)
                    .push(file);
            }
        }
    
        extension_map.get(extension).cloned().unwrap_or_default()
    }

    fn find_files_by_extension_b(&mut self, extension: &str) -> Vec<&File> {
        let mut matching_files = Vec::new();

        for directory in &mut self.directories {
            directory.load_files().unwrap();  // Handle this error appropriately

            for file in &directory.files {
                if let Some(file_ext) = file.extension() {
                    if file_ext == extension {
                        matching_files.push(file);
                    }
                }
            }
        }

        matching_files
    }
}

#[pymodule]
fn dirman(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<File>()?;
    m.add_class::<Directory>()?;
    m.add_class::<DirectoryManager>()?;
    Ok(())
}
