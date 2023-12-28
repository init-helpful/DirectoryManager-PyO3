# Directory Manager Project

## Overview

The Directory Manager Project is a Python extension written in Rust using PyO3. It facilitates efficient interaction with the filesystem, offering capabilities to handle files and directories. The project is cross-platform, compatible with both Unix-like and Windows systems.

## Features

- **File and Directory Operations**: Manage files and directories with functions for reading, writing, moving, and deleting.
- **Metadata Retrieval**: Fetch file metadata such as last modified time, creation time, size, and read-only status.
- **Content Manipulation**: Overwrite or append content in files.
- **Directory Traversal**: Traverse, list, and perform batch operations on directories.
- **Custom Python Classes**: Includes `File`, `Directory`, and `DirectoryManager` classes, each with specific functionalities.

## How to Use (Python)

After installing the Directory Manager, you can use it in Python as follows:

1. **Create a Directory Manager Instance**:
   ```python
   from dirman import DirectoryManager
   dm = DirectoryManager('/path/to/directory')
   ```
   
2. **File Operations**:
   - Reading a file:
     ```python
     file = dm.find_file(name="example.txt")
     content = file.read()
     ```
   - Writing (overwriting) to a file:
     ```python
     file.write_over("New content")
     ```
   - Appending to a file:
     ```python
     file.concat("Additional content")
     ```

3. **Get Metadata**:
   ```python
   metadata = file.get_metadata()
   print(metadata['last_modified'], metadata['size'])
   ```

4. **Directory Operations**:
   - Moving files:
     ```python
     dm.move_files(name="example.txt",dest_directory_name="another_folder")
     ```
   - Deleting directories:
     ```python
     dm.delete_directories(name="old_folder")
     ```

## Building with Maturin (Rust Source)

Maturin is a build system to build and publish Rust-based Python packages with minimal configuration.

