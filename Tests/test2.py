import pytest
import os
import tempfile
import dirman


def test_file_creation():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        assert file.name == os.path.basename(tmp.name)
        assert file.extension == ".txt"
        assert file.size > 0


def test_file_renaming():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        new_name = "new_file.txt"
        file.rename(new_name)
        assert file.name == new_name
        assert file.path == os.path.splitext(tmp.name)[0] + "_new_file.txt"


def test_directory_manager_gather():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            assert len(manager.files) > 0
            assert len(manager.directories) > 0


def test_directory_manager_find_files():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            files = manager.find_files(name=os.path.basename(file.name))
            assert len(files) > 0
            assert files[0].name == os.path.basename(file.name)


def test_directory_manager_find_directories():
    with tempfile.TemporaryDirectory() as tmp:
        manager = dirman.DirectoryManager(tmp)
        manager.gather()
        directories = manager.find_directories(name=os.path.basename(tmp))
        assert len(directories) > 0
        assert directories[0].name == os.path.basename(tmp)


def test_directory_manager_create_file():
    with tempfile.TemporaryDirectory() as tmp:
        manager = dirman.DirectoryManager(tmp)
        file_name = "new_file.txt"
        manager.create_file(tmp, file_name, None, None)
        files = manager.find_files(name=file_name)
        assert len(files) > 0
        assert files[0].name == file_name


def test_directory_manager_rename_file():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            new_name = "new_name.txt"
            manager.rename_file(
                new_name,
                name=os.path.basename(file.name),
                sub_path=tmp,
                extension=".txt",
            )
            files = manager.find_files(name=new_name)
            assert len(files) > 0
            assert files[0].name == new_name


def test_directory_manager_create_directory():
    with tempfile.TemporaryDirectory() as tmp:
        manager = dirman.DirectoryManager(tmp)
        dir_name = "new_dir"
        manager.create_directory(dir_name)
        directories = manager.find_directories(name=dir_name)
        assert len(directories) > 0
        assert directories[0].name == dir_name


def test_file_read():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        assert file.read() == ""


def test_file_write():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        content = "Hello, World!"
        file.write(content, False)
        assert file.read() == content


def test_directory_contains():
    with tempfile.TemporaryDirectory() as tmp:
        directory = dirman.Directory(tmp)
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            assert directory.contains(os.path.basename(file.name))


def test_directory_manager_delete_files():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            manager.delete_files(
                name=os.path.basename(file.name), sub_path=tmp, extension=".txt"
            )
            assert len(manager.find_files(name=os.path.basename(file.name))) == 0


def test_directory_manager_delete_directories():
    with tempfile.TemporaryDirectory() as tmp:
        manager = dirman.DirectoryManager(tmp)
        manager.gather()
        manager.delete_directories(name=os.path.basename(tmp))
        assert len(manager.find_directories(name=os.path.basename(tmp))) == 0


def test_directory_manager_compare_to():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager1 = dirman.DirectoryManager(tmp)
            manager1.gather()
            manager2 = dirman.DirectoryManager(tmp)
            manager2.gather()
            assert len(manager1.compare_to(manager2)) == 0


def test_directory_manager_print_tree():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory(dir=tmp) as subdir:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            try:
                manager.print_tree()
            except Exception as e:
                pytest.fail(f"print_tree raised an exception: {e}")


def test_directory_manager_move_files():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.NamedTemporaryFile(dir=tmp, suffix=".txt") as file:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            manager.move_files(
                name=os.path.basename(file.name),
                sub_path=tmp,
                extension=".txt",
                dest_directory_name="new_dir",
                dest_sub_path=tmp,
            )
            files = manager.find_files(
                name=os.path.basename(file.name),
                sub_path=os.path.join(tmp, "new_dir"),
                extension=".txt",
            )
            assert len(files) > 0
            assert files[0].name == os.path.basename(file.name)


def test_directory_manager_move_directories():
    with tempfile.TemporaryDirectory() as tmp:
        with tempfile.TemporaryDirectory(dir=tmp) as subdir:
            manager = dirman.DirectoryManager(tmp)
            manager.gather()
            manager.move_directories(
                name=os.path.basename(subdir),
                sub_path=tmp,
                dest_name="new_dir",
                dest_sub_path=tmp,
            )
            directories = manager.find_directories(name="new_dir", sub_path=tmp)
            assert len(directories) > 0
            assert directories[0].name == "new_dir"


def test_file_equality():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file1 = dirman.File(tmp.name)
        file2 = dirman.File(tmp.name)
        assert file1 == file2


def test_directory_equality():
    with tempfile.TemporaryDirectory() as tmp:
        directory1 = dirman.Directory(tmp)
        directory2 = dirman.Directory(tmp)
        assert directory1 == directory2


def test_file_is_read_only():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        assert file.is_read_only() == os.access(tmp.name, os.R_OK)


def test_file_get_metadata():
    with tempfile.NamedTemporaryFile(suffix=".txt") as tmp:
        file = dirman.File(tmp.name)
        metadata = file.get_metadata()
        assert "last_modified" in metadata
        assert "creation_time" in metadata
        assert "is_read_only" in metadata
        assert "size" in metadata


def test_directory_manager_canonicalize_path():
    manager = dirman.DirectoryManager(".")
    assert manager.canonicalize_path(".") == os.getcwd()


def test_directory_manager_resolve_root_path():
    manager = dirman.DirectoryManager(".")
    assert manager.resolve_root_path(None) == os.getcwd()
