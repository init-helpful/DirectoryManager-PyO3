import unittest
import os
import tempfile
import dirman


class TestDirectoryManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.directory_manager = dirman.DirectoryManager(self.temp_dir)

    def tearDown(self):
        os.rmdir(self.temp_dir)

    def test_new(self):
        self.assertEqual(self.directory_manager.root_path, self.temp_dir)

    def test_create_file(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        files = self.directory_manager.get_files("")
        new_file = next((file for file in files if file.name == "test_file.txt"), None)
        self.assertIsNotNone(new_file)

    def test_rename_file(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        self.directory_manager.rename_file("new_file", "test_file", None, ".txt")
        files = self.directory_manager.get_files("")
        renamed_file = next(
            (file for file in files if file.name == "new_file.txt"), None
        )
        self.assertIsNotNone(renamed_file)

    def test_gather(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        self.directory_manager.gather()
        files = self.directory_manager.get_files("")
        new_file = next((file for file in files if file.name == "test_file.txt"), None)
        self.assertIsNotNone(new_file)

    def test_find_files(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        files = self.directory_manager.find_files(None, "", ".txt")
        new_file = next((file for file in files if file.name == "test_file.txt"), None)
        self.assertIsNotNone(new_file)

    def test_find_directories(self):
        self.directory_manager.create_directory("", "test_directory")
        directories = self.directory_manager.find_directories(None, "")
        new_directory = next(
            (
                directory
                for directory in directories
                if directory.name == "test_directory"
            ),
            None,
        )
        self.assertIsNotNone(new_directory)

    def test_delete_files(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        self.directory_manager.delete_files(None, "", ".txt")
        files = self.directory_manager.get_files("")
        new_file = next((file for file in files if file.name == "test_file.txt"), None)
        self.assertIsNone(new_file)

    def test_delete_directories(self):
        self.directory_manager.create_directory("", "test_directory")
        self.directory_manager.delete_directories(None, "")
        directories = self.directory_manager.get_directories("")
        new_directory = next(
            (
                directory
                for directory in directories
                if directory.name == "test_directory"
            ),
            None,
        )
        self.assertIsNone(new_directory)

    def test_move_files(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        self.directory_manager.create_directory("", "test_directory")
        self.directory_manager.move_files(None, "", ".txt", None, "", None)
        files = self.directory_manager.get_files("test_directory")
        moved_file = next(
            (file for file in files if file.name == "test_file.txt"), None
        )
        self.assertIsNotNone(moved_file)

    def test_move_directories(self):
        self.directory_manager.create_directory("", "test_directory")
        self.directory_manager.create_directory("", "test_directory_2")
        self.directory_manager.move_directories(
            None, "test_directory", None, "test_directory_2"
        )
        directories = self.directory_manager.get_directories("test_directory_2")
        moved_directory = next(
            (
                directory
                for directory in directories
                if directory.name == "test_directory"
            ),
            None,
        )
        self.assertIsNotNone(moved_directory)

    def test_compare_to(self):
        self.directory_manager.create_file("", "test_file", ".txt", "test content")
        other_directory_manager = dirman.DirectoryManager(self.temp_dir)
        self.directory_manager.create_file(
            "", "another_test_file", ".txt", "another test content"
        )
        differences = self.directory_manager.compare_to(other_directory_manager)
        self.assertEqual(len(differences), 1)


if __name__ == "__main__":
    unittest.main()
