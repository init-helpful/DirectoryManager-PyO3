import unittest
from dirman import DirectoryManager
import time

RENAME_TEST_TEXT = "File_Has_Been_Renamed"
DEFAULT_BASE_PATH_NAME = "dir"
DEFAULT_FILE_NAME = "test_{}.txt"
MOVE_TEST_DIR = "move_to"


def generate_directories(
    dm,
    num_files=5,
    num_directories=1,
    base_dir_name=DEFAULT_BASE_PATH_NAME,
    base_file_name=DEFAULT_FILE_NAME,
):
    # Create the directories
    for directory_index in range(num_directories):
        dir_name = f"{base_dir_name}{directory_index+1}"
        dm.create_directory(dir_name)

        # Create and fill the files in the directories
        for i in range(num_files):
            file_name = base_file_name.format(chr(ord("a") + i))
            file_content = f"Default text for {file_name}"
            dm.create_file(dir_name, file_name, None, file_content)


def wait(_for=1):
    time.sleep(_for)


def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time} seconds to run.")
        return result

    return wrapper


class TestDirman(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = DirectoryManager(".//Tests//Data")

    @classmethod
    def tearDownClass(cls):
        cls.dm.delete_directories(sub_path=DEFAULT_BASE_PATH_NAME)
        cls.dm.delete_directories(sub_path=MOVE_TEST_DIR)

    def test_generate_directories(self):
        num_files = 5
        num_directories = 1
        generate_directories(num_files=num_files, num_directories=num_directories)
        self.assertEqual(len(self.dm.files), num_files * num_directories)

    def test_find_files(self):
        num_files = 5
        num_directories = 1
        generate_directories(num_files=num_files, num_directories=num_directories)
        found_file_by_name = self.dm.find_files(name="test_a")
        self.assertGreater(len(found_file_by_name), 0)

    def test_rename_file(self):
        generate_directories(self.dm)
        self.dm.rename_file(RENAME_TEST_TEXT, sub_path="dir1")
        self.assertGreater(len(self.dm.find_files(name=RENAME_TEST_TEXT)), 0)

    def test_move_files(self):
        num_files = 5
        num_directories = 1
        generate_directories(num_files=num_files, num_directories=num_directories)
        self.dm.create_directory(MOVE_TEST_DIR)
        self.dm.move_files(sub_path="dir1", dest_directory_name=MOVE_TEST_DIR)
        self.assertGreater(len(self.dm.find_directories(sub_path=MOVE_TEST_DIR)), 0)

    def test_delete_file(self):
        num_files = 5
        num_directories = 1
        generate_directories(num_files=num_files, num_directories=num_directories)
        self.dm.rename_file(RENAME_TEST_TEXT, sub_path="dir1")
        self.dm.delete_files(name=RENAME_TEST_TEXT)
        self.assertEqual(len(self.dm.find_files(name=RENAME_TEST_TEXT)), 0)


if __name__ == "__main__":
    unittest.main()
