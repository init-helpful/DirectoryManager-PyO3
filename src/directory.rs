use pyo3::prelude::*;
use std::path::Path;
#[pyclass]
#[derive(Clone)]
pub struct Directory {
    #[pyo3(get)]
    pub path: String,
    #[pyo3(get)]
    pub name: String,
}

#[pymethods]
impl Directory {
    #[new]
    pub fn new(path: String) -> Self {
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
