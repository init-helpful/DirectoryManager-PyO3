import unittest
import dirman

class TestDirectoryManager(unittest.TestCase):
    def setUp(self):
        self.dir_manager = dirman.DirectoryManager()

    def test_create_instance(self):
        self.assertIsNotNone(self.dir_manager)

    def test_print_tree(self):
        # Test that print_tree does not raise any errors
        try:
            self.dir_manager.print_tree(self.dir_manager.root_path)
        except Exception as e:
            self.fail(f"print_tree raised an exception {e}")

    # Tests for find_files
    def test_find_files_by_name(self):
        name = "example"
        files = self.dir_manager.find_files(name=name, sub_path=None, extension=None)
        self.assertIsInstance(files, list)
        # Add more assertions as needed, e.g., checking if all files have the correct name

    def test_find_files_by_sub_path(self):
        sub_path = "subfolder"
        files = self.dir_manager.find_files(name=None, sub_path=sub_path, extension=None)
        self.assertIsInstance(files, list)
        # Add more assertions as needed

    def test_find_files_by_extension(self):
        extension = "txt"
        files = self.dir_manager.find_files(name=None, sub_path=None, extension=extension)
        self.assertIsInstance(files, list)
        # Add more assertions as needed

    def test_find_files_by_combination(self):
        name = "example"
        sub_path = "subfolder"
        extension = "txt"
        files = self.dir_manager.find_files(name=name, sub_path=sub_path, extension=extension)
        self.assertIsInstance(files, list)
        # Add more assertions as needed


    def test_find_directoies_by_name(self):
        name = "example_dir"
        directories = self.dir_manager.find_directories(name=name, sub_path=None)
        self.assertIsInstance(directories, list)
        # Additional assertions can be made based on expected results

    def test_find_directoies_by_sub_path(self):
        sub_path = "subfolder"
        directories = self.dir_manager.find_directories(name=None, sub_path=sub_path)
        self.assertIsInstance(directories, list)
        # Additional assertions can be made based on expected results

    def test_find_directoies_by_combination(self):
        name = "example_dir"
        sub_path = "subfolder"
        directories = self.dir_manager.find_directories(name=name, sub_path=sub_path)
        self.assertIsInstance(directories, list)
        # Additional assertions can be made based on expected results


if __name__ == '__main__':
    unittest.main()
