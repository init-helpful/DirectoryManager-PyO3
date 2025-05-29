import unittest
import os
import shutil
import time
from dirman import DirectoryManager, File 

RENAMED_FILE_STEM = "File_Has_Been_Renamed"
RENAMED_FILE_EXTENSION = "md" 
DEFAULT_BASE_DIR_NAME = "test_dir" 
DEFAULT_FILE_STEM = "test_file"
DEFAULT_FILE_EXTENSION = "txt"
MOVE_TEST_DIR_NAME = "move_destination"
TEST_DATA_ROOT = ".//Tests//TestData" 
INTER_TEST_PAUSE_SECONDS = 0.1 # Adjust as needed, e.g., 0.1 or 0.05

def get_test_file_name(index_char):
    return f"{DEFAULT_FILE_STEM}_{index_char}" 

def get_test_file_full_name(index_char):
    return f"{DEFAULT_FILE_STEM}_{index_char}.{DEFAULT_FILE_EXTENSION}"

def generate_test_environment(
    dm,
    num_files_per_dir=2,
    num_directories=1,
    base_dir_name=DEFAULT_BASE_DIR_NAME,
):
    for dir_index in range(num_directories):
        dir_sub_path = f"{base_dir_name}_{dir_index + 1}"
        dm.create_directory(dir_sub_path)

        for file_char_index in range(num_files_per_dir):
            file_char = chr(ord("a") + file_char_index)
            file_stem = get_test_file_name(file_char) 
            file_content = f"Content for {file_stem}.{DEFAULT_FILE_EXTENSION} in {dir_sub_path}"
            dm.create_file(dir_sub_path, file_stem, DEFAULT_FILE_EXTENSION, file_content)

def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Function {func.__name__} took {elapsed_time:.4f} seconds to run.")
        return result
    return wrapper

class TestDirman(unittest.TestCase):
    @classmethod
    @time_it
    def setUpClass(cls):
        if os.path.exists(TEST_DATA_ROOT):
            shutil.rmtree(TEST_DATA_ROOT)
        os.makedirs(TEST_DATA_ROOT)
        
        cls.dm = DirectoryManager(TEST_DATA_ROOT)
        generate_test_environment(cls.dm, num_files_per_dir=3, num_directories=2)
        cls.dm.gather() 

    @classmethod
    @time_it
    def tearDownClass(cls):
        if os.path.exists(TEST_DATA_ROOT):
            time.sleep(0.1) # Brief pause before final cleanup
            try:
                shutil.rmtree(TEST_DATA_ROOT)
                print(f"Cleaned up test directory: {TEST_DATA_ROOT}")
            except PermissionError as e:
                print(f"Warning: Could not remove test directory {TEST_DATA_ROOT} due to PermissionError: {e}")
            except Exception as e:
                print(f"Warning: Error during cleanup of {TEST_DATA_ROOT}: {e}")

    def tearDown(self):
        """This method is called after each test method."""
        time.sleep(INTER_TEST_PAUSE_SECONDS)
        # You could also add a dm.gather() here if you want each test to start
        # with a manager perfectly synced to the state left by the previous test,
        # but that might hide issues if tests are not truly independent.
        # For now, just a pause.
        # print(f"--- Paused for {INTER_TEST_PAUSE_SECONDS}s after {self._testMethodName} ---")


    @time_it
    def test_01_initial_directory_and_file_creation(self):
        num_dirs_expected = 2 
        num_files_per_dir = 3
        
        self.assertEqual(len(self.dm.directories), num_dirs_expected, 
                         f"Expected {num_dirs_expected} dirs, found {len(self.dm.directories)}")
        self.assertEqual(len(self.dm.files), num_files_per_dir * num_dirs_expected)
        
        self.assertIn(DEFAULT_FILE_EXTENSION, self.dm.extensions)

    @time_it
    def test_02_find_files_by_stem_and_extension(self):
        found_files = self.dm.find_files(name=get_test_file_name("a"), extension=DEFAULT_FILE_EXTENSION)
        self.assertEqual(len(found_files), 2) 
        for f in found_files:
            self.assertTrue(isinstance(f, File))
            self.assertEqual(f.name, get_test_file_name("a"))
            self.assertEqual(f.extension, DEFAULT_FILE_EXTENSION)

    @time_it
    def test_03_find_single_file(self):
        target_sub_path = f"{DEFAULT_BASE_DIR_NAME}_1" 
        target_file_stem = get_test_file_name("b")    

        found_file = self.dm.find_file(name=target_file_stem, sub_path=target_sub_path, extension=DEFAULT_FILE_EXTENSION)
        self.assertIsNotNone(found_file)
        self.assertEqual(found_file.name, target_file_stem)
        self.assertTrue(target_sub_path in found_file.path)
        
        with self.assertRaises(ValueError): 
            self.dm.find_file(name="non_existent_file_stem")

    @time_it
    def test_04_rename_file(self):
        dir_to_test_in = f"{DEFAULT_BASE_DIR_NAME}_1"
        original_file_stem = get_test_file_name("c")

        self.dm.gather()
        files_before_rename = self.dm.find_files(name=original_file_stem, sub_path=dir_to_test_in, extension=DEFAULT_FILE_EXTENSION)
        self.assertEqual(len(files_before_rename), 1, f"Should find exactly one file named '{original_file_stem}.{DEFAULT_FILE_EXTENSION}' in '{dir_to_test_in}' to rename")

        new_full_filename = f"{RENAMED_FILE_STEM}.{RENAMED_FILE_EXTENSION}"

        # Modified call: new_full_filename is now positional
        self.dm.rename_file(
            new_full_name=new_full_filename,       # Keyword
            current_name_stem=original_file_stem,  # Keyword
            current_sub_path=dir_to_test_in,       # Keyword
            current_extension=DEFAULT_FILE_EXTENSION # Keyword
        )

        files_after_rename_old_name = self.dm.find_files(name=original_file_stem, sub_path=dir_to_test_in, extension=DEFAULT_FILE_EXTENSION)
        self.assertEqual(len(files_after_rename_old_name), 0)

        renamed_files_found = self.dm.find_files(name=RENAMED_FILE_STEM, sub_path=dir_to_test_in, extension=RENAMED_FILE_EXTENSION)
        self.assertEqual(len(renamed_files_found), 1)
        if renamed_files_found:
            self.assertEqual(renamed_files_found[0].name, RENAMED_FILE_STEM)
            self.assertEqual(renamed_files_found[0].extension, RENAMED_FILE_EXTENSION)
            
    @time_it
    def test_05_move_files(self):
        # Ensure the environment is as expected from setUpClass + any prior test modifications
        self.dm.gather() # Good practice to gather if state from prior tests might affect this one's setup

        source_dir_sub_path = f"{DEFAULT_BASE_DIR_NAME}_2" 
        
        # Check if move_destination already exists (e.g. from a previous failed run or another test)
        # If so, we might want to clean it or use a more unique name for this test.
        # For simplicity now, we assume setUpClass provides a clean slate for these.
        self.dm.create_directory(MOVE_TEST_DIR_NAME)
        self.dm.gather() # Gather after creating the destination directory

        dest_dir_obj_list = self.dm.find_directories(name=MOVE_TEST_DIR_NAME, return_first_found=True)
        self.assertEqual(len(dest_dir_obj_list),1, f"Destination directory {MOVE_TEST_DIR_NAME} not found or not unique by manager")

        files_in_source_before = self.dm.find_files(sub_path=source_dir_sub_path)
        self.assertGreater(len(files_in_source_before), 0, f"Source directory '{source_dir_sub_path}' should have files to move")
        num_files_to_move = len(files_in_source_before)

        files_in_dest_before = self.dm.find_files(sub_path=MOVE_TEST_DIR_NAME)
        
        self.dm.move_files(
            sub_path=source_dir_sub_path, 
            dest_directory_name=MOVE_TEST_DIR_NAME 
        )
        self.dm.gather() # Gather after moving files

        files_in_source_after = self.dm.find_files(sub_path=source_dir_sub_path)
        self.assertEqual(len(files_in_source_after), 0, "Files should be removed from source directory")

        files_in_dest_after = self.dm.find_files(sub_path=MOVE_TEST_DIR_NAME)
        self.assertEqual(len(files_in_dest_after), len(files_in_dest_before) + num_files_to_move, "Files not moved to destination directory correctly")

    @time_it
    def test_06_delete_file(self):
        temp_dir = "temp_delete_dir_test06" # Unique name for this test
        temp_file_stem = "deletable_file"
        temp_file_ext = "tmp"
        
        self.dm.create_directory(temp_dir)
        self.dm.create_file(temp_dir, temp_file_stem, temp_file_ext, "content")
        self.dm.gather() # Ensure manager sees newly created file/dir

        files_before_delete = self.dm.find_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)
        self.assertEqual(len(files_before_delete), 1, "File to be deleted should exist")

        self.dm.delete_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)
        self.dm.gather() # Ensure manager updates after delete

        files_after_delete = self.dm.find_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)
        self.assertEqual(len(files_after_delete), 0, "File should be deleted")
        
        self.dm.delete_directories(name=temp_dir) 
        self.dm.gather()


    @time_it
    def test_07_print_tree(self):
        print("\n--- Test Tree Output ---")
        try:
            self.dm.gather() 
            self.dm.print_tree()
            print("----------------------")
        except Exception as e:
            self.fail(f"dm.print_tree() raised an exception: {e}")
            
    @time_it
    def test_08_find_text_in_files(self):
        self.dm.gather() # Ensure we're looking at the current state of FS

        search_string_unique_to_one_file = f"Content for {get_test_file_name('a')}.{DEFAULT_FILE_EXTENSION} in {DEFAULT_BASE_DIR_NAME}_1"
        search_string_common = "Content for" 

        found_specific = self.dm.find_text(search_string_unique_to_one_file)
        self.assertEqual(len(found_specific), 1, f"Should find specific text: '{search_string_unique_to_one_file}'")
        if found_specific:
            self.assertTrue(get_test_file_name("a") in found_specific[0].name)
            self.assertTrue(f"{DEFAULT_BASE_DIR_NAME}_1" in found_specific[0].path)

        # Re-count files that should have the common text based on current manager state
        # This is more robust than assuming a fixed number from setUpClass if other tests modify files.
        expected_common_count = 0
        for f in self.dm.files:
            try:
                if search_string_common in f.read():
                    expected_common_count +=1
            except Exception: # Skip files that might be unreadable for some reason
                pass
        
        found_common = self.dm.find_text(search_string_common)
        self.assertEqual(len(found_common), expected_common_count, f"Mismatch in files found containing '{search_string_common}'")

        found_none = self.dm.find_text("gibberish_text_not_in_any_file_qwerty_123_xyz")
        self.assertEqual(len(found_none), 0)

    @time_it
    def test_09_delete_directories(self):
        dir_to_delete_base = "dir_for_deletion_test09" 
        
        self.dm.create_directory(f"{dir_to_delete_base}_1")
        self.dm.create_file(f"{dir_to_delete_base}_1", "file1_in_del_dir", "txt", "content")
        self.dm.create_directory(f"{dir_to_delete_base}_2")
        self.dm.gather() 

        dirs_before = self.dm.find_directories(sub_path=dir_to_delete_base)
        self.assertEqual(len(dirs_before), 2, "Should find 2 directories to delete")
        
        files_in_dir1_before = self.dm.find_files(sub_path=f"{dir_to_delete_base}_1")
        self.assertEqual(len(files_in_dir1_before), 1, "Should find 1 file in the first directory to be deleted")

        self.dm.delete_directories(sub_path=dir_to_delete_base)
        self.dm.gather() # Crucial to gather after deletion to reflect FS changes and cache pruning

        dirs_after = self.dm.find_directories(sub_path=dir_to_delete_base)
        self.assertEqual(len(dirs_after), 0, "Directories should be deleted from manager")
        
        files_after_dir_delete = self.dm.find_files(sub_path=f"{dir_to_delete_base}_1")
        self.assertEqual(len(files_after_dir_delete), 0, "Files in deleted directory should be gone from manager")

if __name__ == "__main__":
    print(f"Running tests. Test data will be created in: {os.path.abspath(TEST_DATA_ROOT)}")
    print("Make sure your compiled Rust library is accessible to Python (e.g., via maturin develop or build).")
    unittest.main()