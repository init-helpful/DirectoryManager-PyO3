use pyo3::prelude::*;
use std::path::Path;

#[pyclass]
#[derive(Clone, Debug)]
pub struct Directory {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub name: String,
}

#[pymethods]
impl Directory {
    #[new]
    pub fn new(path: &str) -> Self {
        let name = Path::new(path)
            .file_name()
            .unwrap_or_default() // Returns empty OsStr if no file_name (e.g. "/")
            .to_string_lossy()
            .into_owned();

        Directory {
            path: path.to_string(),
            name,
        }
    }

    pub fn contains(&self, target_path: &str) -> PyResult<bool> {
        Ok(Path::new(&self.path).join(target_path).exists())
    }

    fn __repr__(&self) -> PyResult<String> {
        Ok(format!("Directory(path='{}')", self.path))
    }

    fn __str__(&self) -> PyResult<String> {
        Ok(self.path.clone())
    }

    fn __eq__(&self, other: &Directory) -> PyResult<bool> {
        // Assuming paths are canonical and thus unique identifiers
        Ok(self.path == other.path)
    }

}
