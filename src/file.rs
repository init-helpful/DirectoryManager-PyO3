use pyo3::exceptions::{PyIOError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;
use std::time::UNIX_EPOCH;

// PartialEq for Rust-side comparisons (e.g., Vec::contains)
// Made consistent with Python's __eq__
impl PartialEq for File {
    fn eq(&self, other: &Self) -> bool {
        self.path == other.path
    }
}
impl Eq for File {} // If PartialEq is defined, Eq is often useful

// use std::hash::{Hash, Hasher};
// impl Hash for File {
//     fn hash<H: Hasher>(&self, state: &mut H) {
//         self.path.hash(state);
//     }
// }


#[pyclass]
#[derive(Clone, Debug)]
pub struct File {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub name: String, // Base name of the file, without extension
    #[pyo3(get)]
    pub extension: String,
    #[pyo3(get, set)] // Allow size to be set if updated manually or by DirectoryManager
    pub size: u64,
}

#[pymethods]
impl File {
    #[new]
    pub fn new(path: &str) -> PyResult<Self> {
        let path_obj = Path::new(path);

        let name = path_obj
            .file_stem()
            .unwrap_or_default() // For files like ".bashrc", file_stem is ".bashrc"
            .to_string_lossy()
            .to_string();

        let extension = path_obj
            .extension()
            .unwrap_or_default()
            .to_string_lossy()
            .to_string();

        let metadata = fs::metadata(path_obj)
            .map_err(|e| PyValueError::new_err(format!("Failed to get metadata for {}: {}", path, e)))?;
        
        let size = metadata.len();

        Ok(File {
            path: path.to_string(),
            name,
            extension,
            size,
        })
    }

    /// Renames the file. The new name should be the full filename (e.g., "new_name.txt").
    pub fn rename(&mut self, new_full_name: &str) -> PyResult<()> {
        let old_path_obj = Path::new(&self.path);
        let parent_dir = old_path_obj.parent().ok_or_else(|| {
            PyIOError::new_err(format!(
                "File path '{}' has no parent directory.",
                self.path
            ))
        })?;

        let new_path_obj = parent_dir.join(new_full_name);

        fs::rename(old_path_obj, &new_path_obj).map_err(|e| {
            PyIOError::new_err(format!(
                "Failed to rename file from '{}' to '{}': {}",
                self.path,
                new_path_obj.display(),
                e
            ))
        })?;

        // Update fields after successful rename
        self.path = new_path_obj.to_string_lossy().into_owned();
        self.name = new_path_obj
            .file_stem()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        self.extension = new_path_obj
            .extension()
            .unwrap_or_default()
            .to_string_lossy()
            .into_owned();
        // Size typically doesn't change on rename, but if it could, refresh:
        // self.size = fs::metadata(&self.path)?.len();
        // If the OS guarantees size is preserved on rename within the same filesystem,
        // no need to update self.size. For cross-filesystem renames (which fs::rename might emulate),
        // size could change. Assume size is preserved by typical rename operation.
        Ok(())
    }

    pub fn read(&self) -> PyResult<String> {
        fs::read_to_string(&self.path)
            .map_err(|e| PyValueError::new_err(format!("Failed to read file {}: {}", self.path, e)))
    }

    /// Writes text to the file.
    /// If overwrite is true, the file is truncated before writing.
    /// If overwrite is false, the text is appended to the file.
    /// The file is created if it does not exist.
    pub fn write(&mut self, text: &str, overwrite: bool) -> PyResult<()> {
        let mut options = OpenOptions::new();
        options.create(true); // Create if it doesn't exist

        if overwrite {
            options.write(true).truncate(true);
        } else {
            options.append(true);
        }

        let mut file = options.open(&self.path).map_err(|e| {
            PyIOError::new_err(format!("Failed to open file {}: {}", self.path, e))
        })?;

        file.write_all(text.as_bytes()).map_err(|e| {
            PyIOError::new_err(format!("Failed to write to file {}: {}", self.path, e))
        })?;
        
        // Update self.size after writing
        let metadata = fs::metadata(&self.path)
            .map_err(|e| PyIOError::new_err(format!("Failed to get metadata for {}: {}", self.path, e)))?;
        self.size = metadata.len();

        Ok(())
    }

    fn get_metadata(&self, py: Python) -> PyResult<PyObject> {
        let metadata = fs::metadata(&self.path)
            .map_err(|e| PyValueError::new_err(format!("Failed to get metadata for {}: {}", self.path, e)))?;

        let dict = PyDict::new(py);

        if let Ok(modified_time) = metadata.modified() {
            if let Ok(duration_since_epoch) = modified_time.duration_since(UNIX_EPOCH) {
                dict.set_item("last_modified", PyFloat::new(py, duration_since_epoch.as_secs_f64()))?;
            }
        }

        if let Ok(created_time) = metadata.created() {
            if let Ok(duration_since_epoch) = created_time.duration_since(UNIX_EPOCH) {
                dict.set_item("creation_time", PyFloat::new(py, duration_since_epoch.as_secs_f64()))?;
            }
        }

        dict.set_item("is_read_only", metadata.permissions().readonly())?;
        dict.set_item("size", metadata.len())?; // Current size from FS

        Ok(dict.to_object(py))
    }

    fn is_read_only(&self) -> PyResult<bool> {
        let metadata = fs::metadata(&self.path)
            .map_err(|e| PyValueError::new_err(format!("Failed to get metadata for {}: {}", self.path, e)))?;
        Ok(metadata.permissions().readonly())
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok(format!(
            "File(path='{}', name='{}', extension='{}', size={})",
            self.path, self.name, self.extension, self.size
        ))
    }

    fn __str__(&self) -> PyResult<String> {
        Ok(self.path.clone())
    }
    
    fn __eq__(&self, other: &File) -> PyResult<bool> {
        // Compare by path, assuming paths are canonical and unique.
        Ok(self.path == other.path)
    }
}