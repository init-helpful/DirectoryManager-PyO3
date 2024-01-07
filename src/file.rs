use pyo3::exceptions::PyIOError;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFloat};
use pyo3::PyResult;
use std::ffi::OsStr;
use std::fs;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::Path;
use std::time::UNIX_EPOCH;
impl PartialEq for File {
    fn eq(&self, other: &Self) -> bool {
        self.path == other.path
    }
}

#[pyclass]
#[derive(Clone)]
pub struct File {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub extension: String,
    #[pyo3(get)]
    pub size: u64,
}

#[pymethods]
impl File {
    #[new]
    pub fn new(path: String) -> PyResult<Self> {
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

    pub fn rename(&mut self, new_name: &str) {
        // Construct the new path
        let old_path = Path::new(&self.path);
        let parent = old_path.parent().expect("Failed to get parent directory");

        // Extract the extension from the old file name
        let extension = old_path.extension().and_then(OsStr::to_str).unwrap_or("");

        // Append the extension to the new file name
        let new_name_with_extension = format!("{}.{}", new_name, extension);

        let new_path = parent.join(&new_name_with_extension);

        // Rename the file
        fs::rename(&old_path, &new_path).expect("Failed to rename file");

        // Update the name and path of the File object
        self.name = new_name.to_string();
        self.path = new_path.to_string_lossy().into_owned();
    }

    fn read(&self) -> PyResult<String> {
        let content =
            fs::read_to_string(&self.path).map_err(|e| PyValueError::new_err(e.to_string()))?;
        Ok(content)
    }

    pub fn write(&self, text: String, overwrite: bool) -> PyResult<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .truncate(!overwrite)
            .append(overwrite)
            .open(&self.path)
            .map_err(|e| PyIOError::new_err(e.to_string()))?;

        if overwrite {
            write!(file, "{}", text).map_err(|e| PyIOError::new_err(e.to_string()))?;
        } else {
            writeln!(file, "{}", text).map_err(|e| PyIOError::new_err(e.to_string()))?;
        }

        Ok(())
    }

    fn get_metadata(&self, py: Python) -> PyResult<PyObject> {
        let metadata =
            fs::metadata(&self.path).map_err(|e| PyValueError::new_err(e.to_string()))?;

        let dict = PyDict::new(py);

        if let Ok(last_modified) = metadata.modified() {
            if let Ok(duration_since_epoch) = last_modified.duration_since(UNIX_EPOCH) {
                dict.set_item(
                    "last_modified",
                    PyFloat::new(py, duration_since_epoch.as_secs_f64()),
                )?;
            }
        }

        if let Ok(creation_time) = metadata.created() {
            if let Ok(duration_since_epoch) = creation_time.duration_since(UNIX_EPOCH) {
                dict.set_item(
                    "creation_time",
                    PyFloat::new(py, duration_since_epoch.as_secs_f64()),
                )?;
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
