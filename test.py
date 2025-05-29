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
        dm.create_directory(dir_sub_path) # DM state updated

        for file_char_index in range(num_files_per_dir):
            file_char = chr(ord("a") + file_char_index)
            file_stem = get_test_file_name(file_char) 
            file_content = f"Content for {file_stem}.{DEFAULT_FILE_EXTENSION} in {dir_sub_path}"
            dm.create_file(dir_sub_path, file_stem, DEFAULT_FILE_EXTENSION, file_content) # DM state updated

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

        files_before_rename = self.dm.find_files(name=original_file_stem, sub_path=dir_to_test_in, extension=DEFAULT_FILE_EXTENSION)
        self.assertEqual(len(files_before_rename), 1, f"Should find exactly one file named '{original_file_stem}.{DEFAULT_FILE_EXTENSION}' in '{dir_to_test_in}' to rename")

        new_full_filename = f"{RENAMED_FILE_STEM}.{RENAMED_FILE_EXTENSION}"

        self.dm.rename_file(
            new_full_name=new_full_filename,       
            current_name_stem=original_file_stem,  
            current_sub_path=dir_to_test_in,       
            current_extension=DEFAULT_FILE_EXTENSION 
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
        source_dir_sub_path = f"{DEFAULT_BASE_DIR_NAME}_2" 
        
        self.dm.create_directory(MOVE_TEST_DIR_NAME)

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

        files_in_source_after = self.dm.find_files(sub_path=source_dir_sub_path)
        self.assertEqual(len(files_in_source_after), 0, "Files should be removed from source directory")

        files_in_dest_after = self.dm.find_files(sub_path=MOVE_TEST_DIR_NAME)
        self.assertEqual(len(files_in_dest_after), len(files_in_dest_before) + num_files_to_move, "Files not moved to destination directory correctly")

    @time_it
    def test_06_delete_file(self):
        temp_dir = "temp_delete_dir_test06" 
        temp_file_stem = "deletable_file"
        temp_file_ext = "tmp"
        
        self.dm.create_directory(temp_dir)
        self.dm.create_file(temp_dir, temp_file_stem, temp_file_ext, "content")


        files_before_delete = self.dm.find_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)
        self.assertEqual(len(files_before_delete), 1, "File to be deleted should exist")

        self.dm.delete_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)


        files_after_delete = self.dm.find_files(name=temp_file_stem, sub_path=temp_dir, extension=temp_file_ext)
        self.assertEqual(len(files_after_delete), 0, "File should be deleted")
        
        self.dm.delete_directories(name=temp_dir)



    @time_it
    def test_07_print_tree(self):
        print("\n--- Test Tree Output ---")
        try:

            self.dm.print_tree()
            print("----------------------")
        except Exception as e:
            self.fail(f"dm.print_tree() raised an exception: {e}")
            
    @time_it
    def test_08_find_text_in_files_and_file_write_size_update(self):
        search_string_unique_to_one_file = f"Content for {get_test_file_name('a')}.{DEFAULT_FILE_EXTENSION} in {DEFAULT_BASE_DIR_NAME}_1"
        search_string_common = "Content for" 

        found_specific = self.dm.find_text(search_string_unique_to_one_file)
        self.assertEqual(len(found_specific), 1, f"Should find specific text: '{search_string_unique_to_one_file}'")
        if found_specific:
            self.assertTrue(get_test_file_name("a") in found_specific[0].name)
            self.assertTrue(f"{DEFAULT_BASE_DIR_NAME}_1" in found_specific[0].path)

        expected_common_count = 0
        for f_obj_in_dm in self.dm.files:
            try:
                if search_string_common in f_obj_in_dm.read():
                    expected_common_count +=1
            except Exception:
                pass
        
        found_common = self.dm.find_text(search_string_common)
        self.assertEqual(len(found_common), expected_common_count, f"Mismatch in files found containing '{search_string_common}'")

        found_none = self.dm.find_text("gibberish_text_not_in_any_file_qwerty_123_xyz")
        self.assertEqual(len(found_none), 0)

        # Test File.write() and its size update on the File object instance
        if found_specific:
            file_to_write = found_specific[0] # This is a clone
            original_size = file_to_write.size
            new_content = "This is new, longer content."
            file_to_write.write(new_content, overwrite=True) # This updates file_to_write.size

            self.assertEqual(file_to_write.read(), new_content)
            self.assertEqual(file_to_write.size, len(new_content.encode('utf-8'))) # Assuming utf-8 for len
            self.assertNotEqual(file_to_write.size, original_size)

            # Verify the DM's internal cache for this file path might still have the old size
            # unless a gather() is called or the DM's File object was directly mutated (not possible here).
            # Re-fetch from DM to see its cached version.
            # This behavior is important to understand: modifications to cloned File objects
            # do not automatically update the DirectoryManager's internal list of File objects.
            dm_internal_file_version = self.dm.find_file(name=file_to_write.name, extension=file_to_write.extension, sub_path=os.path.dirname(os.path.relpath(file_to_write.path, self.dm.root_path)))
            if dm_internal_file_version:
                # This check depends on whether find_file returns a new clone or if DM state reflects the write.
                # With current changes, find_file returns a new clone based on current FS, so it SHOULD reflect the new size *if* find_file re-reads metadata.
                # Let's assume File.new() is called by find_file which re-reads metadata.
                # However, find_file in Rust currently searches self.files (the cached list). So it will return a clone of the cached (old size) file.
                # A gather() would be needed to make dm_internal_file_version.size reflect the new size from disk.

                self.dm.gather() # Explicitly gather to update DM's internal cache

                dm_refreshed_file_version = self.dm.find_file(name=file_to_write.name, extension=file_to_write.extension, sub_path=os.path.dirname(os.path.relpath(file_to_write.path, self.dm.root_path)))
                if dm_refreshed_file_version:
                    self.assertEqual(dm_refreshed_file_version.size, len(new_content.encode('utf-8')), "DM's size for file should be updated after gather()")


    @time_it
    def test_09_delete_directories(self):
        dir_to_delete_base = "dir_for_deletion_test09" 
        
        self.dm.create_directory(f"{dir_to_delete_base}_1")
        self.dm.create_file(f"{dir_to_delete_base}_1", "file1_in_del_dir", "txt", "content")
        self.dm.create_directory(f"{dir_to_delete_base}_2")

        dirs_before = self.dm.find_directories(sub_path=dir_to_delete_base)
        self.assertEqual(len(dirs_before), 2, "Should find 2 directories to delete")
        
        files_in_dir1_before = self.dm.find_files(sub_path=f"{dir_to_delete_base}_1")
        self.assertEqual(len(files_in_dir1_before), 1, "Should find 1 file in the first directory to be deleted")

        self.dm.delete_directories(sub_path=dir_to_delete_base)


        dirs_after = self.dm.find_directories(sub_path=dir_to_delete_base)
        self.assertEqual(len(dirs_after), 0, "Directories should be deleted from manager")
        
        files_after_dir_delete = self.dm.find_files(sub_path=f"{dir_to_delete_base}_1")
        self.assertEqual(len(files_after_dir_delete), 0, "Files in deleted directory should be gone from manager")

if __name__ == "__main__":
    print(f"Running tests. Test data will be created in: {os.path.abspath(TEST_DATA_ROOT)}")
    print("Make sure your compiled Rust library is accessible to Python (e.g., via maturin develop or build).")
    unittest.main()