use pyo3::prelude::*;

mod directory;
mod directory_manager;
mod file;

use directory::Directory;
use directory_manager::DirectoryManager;
use file::File;

#[pymodule]
fn dirman(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<File>()?;
    m.add_class::<Directory>()?;
    m.add_class::<DirectoryManager>()?;
    Ok(())
}
