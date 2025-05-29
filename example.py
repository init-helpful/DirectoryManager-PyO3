import os
import shutil
import time
from dirman import DirectoryManager, File, Directory


EXAMPLE_ROOT_DIR = "dirman_example_usage_root"

def setup_example_env():
    """Creates a clean root directory for the example."""
    if os.path.exists(EXAMPLE_ROOT_DIR):
        # Add a small delay for OS to release file locks, especially on Windows
        time.sleep(0.1)
        shutil.rmtree(EXAMPLE_ROOT_DIR)
    os.makedirs(EXAMPLE_ROOT_DIR)
    print(f"Created example root directory: {os.path.abspath(EXAMPLE_ROOT_DIR)}")

def cleanup_example_env():
    """Removes the example root directory."""
    if os.path.exists(EXAMPLE_ROOT_DIR):
        time.sleep(0.1) # Brief pause before cleanup
        try:
            shutil.rmtree(EXAMPLE_ROOT_DIR)
            print(f"Cleaned up example root directory: {EXAMPLE_ROOT_DIR}")
        except Exception as e:
            print(f"Error during cleanup of {EXAMPLE_ROOT_DIR}: {e}")


def demonstrate_initialization_and_properties(dm):
    print("\n--- 1. Initialization and Basic Properties ---")
    print(f"Initialized DirectoryManager with root_path: {dm.root_path}")
    # __new__ calls gather(), so these might be populated if root_path wasn't empty initially
    print(f"Initial directories in manager: {[d.path for d in dm.directories]}")
    print(f"Initial files in manager: {[f.path for f in dm.files]}")
    print(f"Initial extensions found: {dm.extensions}")

def demonstrate_directory_creation(dm):
    print("\n--- 2. Directory Creation (create_directory) ---")
    dm.create_directory("docs")
    dm.create_directory("src/python_code")
    dm.create_directory("data/raw_data")
    print("Created directories: docs, src/python_code, data/raw_data")
    
    dm.gather() # Explicitly gather to update manager's state
    print("Directories after creation and gather:")
    for d in dm.directories:
        print(f"  - Path: {d.path}, Name: {d.name}")

def demonstrate_file_creation(dm):
    print("\n--- 3. File Creation (create_file) ---")
    dm.create_file("docs", "readme", "md", "# Project Readme\nThis is a test project.")
    dm.create_file("src", "main_app", "py", "print('Hello from main_app.py')")
    dm.create_file("src/python_code", "utils", "py", "# Utility functions here")
    dm.create_file("data", "config_settings", "json", '{"theme": "dark", "version": 1.0}')
    dm.create_file("docs", "notes_no_ext", file_content="These are some notes.") # No extension
    print("Created files: docs/readme.md, src/main_app.py, src/python_code/utils.py, data/config_settings.json, docs/notes_no_ext")

    dm.gather() # Update manager's state
    print("Files after creation and gather:")
    for f in dm.files:
        print(f"  - Path: {f.path}, Name: {f.name}, Ext: {f.extension}, Size: {f.size}")
    print(f"Current extensions in manager: {dm.extensions}")

def demonstrate_print_tree(dm):
    print("\n--- 4. Directory Tree (print_tree) ---")
    dm.print_tree()

def demonstrate_finding_items(dm):
    print("\n--- 5. Finding Files and Directories ---")
    
    print("\nFinding all '.py' files (find_files):")
    py_files = dm.find_files(extension="py")
    for f in py_files:
        print(f"  Found .py: {f.path} (Name: {f.name}, Size: {f.size})")

    print("\nFinding file 'readme.md' in 'docs' (find_file):")
    readme_file = dm.find_file(name="readme", sub_path="docs", extension="md")
    if readme_file:
        print(f"  Found: {readme_file} (type: {type(readme_file)})")
    else:
        print("  'readme.md' not found in 'docs'.")

    print("\nFinding first file named 'utils' (find_file, any extension):")
    utils_file = dm.find_file(name="utils")
    if utils_file:
        print(f"  Found: {utils_file.path}")
    
    print("\nFinding directory 'src' (find_directories):")
    src_dirs = dm.find_directories(name="src")
    for d_obj in src_dirs:
        print(f"  Found directory: {d_obj.path} (Name: {d_obj.name}, type: {type(d_obj)})")
        if d_obj.contains("main_app.py"): # Check relative to this directory
            print(f"    Directory '{d_obj.name}' contains 'main_app.py'")
        if not d_obj.contains("non_existent_file.txt"):
            print(f"    Directory '{d_obj.name}' does not contain 'non_existent_file.txt' (correctly)")


    print("\nFinding directories with 'data' in path (first one only) (find_directories):")
    data_dir_list = dm.find_directories(sub_path="data", return_first_found=True)
    if data_dir_list:
        print(f"  Found: {data_dir_list[0].path}")

def demonstrate_file_operations_and_content(dm):
    print("\n--- 6. File Operations (read, write, metadata) and Content Search (find_text) ---")
    
    print("\nFinding files containing 'Hello' (find_text):")
    hello_files = dm.find_text(sub_string="Hello")
    for f_obj in hello_files:
        print(f"  Found '{f_obj.path}' containing 'Hello'.")
        
        # Demonstrate File methods
        print(f"    Content of {f_obj.name}.{f_obj.extension}:")
        try:
            content = f_obj.read()
            print(f"      Read: '{content.strip()[:30]}...'")
            
            f_obj.write("\n# Appended line by dirman example.", overwrite=False)
            print(f"      Appended to. New content snippet: '{f_obj.read().strip()[:50]}...'")
            
            f_obj.write("# Overwritten by dirman example.", overwrite=True)
            print(f"      Overwritten. New content: '{f_obj.read().strip()}'")

            # Note: f_obj.size is stale here. DM needs to gather for its cache to update.
            # The File object itself does not update its own size field on write.
            
            print(f"    Metadata for {f_obj.path}: {f_obj.get_metadata()}")
            print(f"    Is read-only: {f_obj.is_read_only()}")

        except Exception as e:
            print(f"    Error during file operations for {f_obj.path}: {e}")

    # To show updated size from manager's perspective:
    dm.gather()
    print("\nAfter dm.gather(), checking updated file sizes for previously modified files:")
    # Re-fetch the file (e.g., main_app.py if it contained 'Hello' and was modified)
    # Assuming 'main_app.py' was the one:
    main_app_file_updated = dm.find_file(name="main_app", extension="py", sub_path="src")
    if main_app_file_updated:
        print(f"  Size of 'src/main_app.py' from manager: {main_app_file_updated.size}")
    else:
        print("  Could not re-find 'src/main_app.py' to check updated size (it might not have contained 'Hello').")


def demonstrate_renaming(dm):
    print("\n--- 7. Renaming a File (rename_file) ---")
    original_stem = "utils"
    original_sub_path = "src/python_code"
    original_ext = "py"
    new_full_filename = "helpers.py"

    print(f"Attempting to rename '{original_sub_path}/{original_stem}.{original_ext}' to '{new_full_filename}'")
    
    # Ensure it exists before trying to rename
    file_to_rename = dm.find_file(name=original_stem, sub_path=original_sub_path, extension=original_ext)
    if not file_to_rename:
        print(f"  ERROR: File '{original_stem}.{original_ext}' not found in '{original_sub_path}'. Skipping rename.")
        return

    try:
        dm.rename_file(
            new_full_name=new_full_filename,
            current_name_stem=original_stem,
            current_sub_path=original_sub_path,
            current_extension=original_ext
        )
        print(f"  Successfully called rename_file.")
        dm.gather() # Refresh manager's state

        if dm.find_file(name=original_stem, sub_path=original_sub_path, extension=original_ext):
            print(f"  VERIFICATION FAILED: Old file name still exists.")
        elif dm.find_file(name="helpers", sub_path=original_sub_path, extension="py"):
            print(f"  VERIFICATION SUCCESS: New file 'helpers.py' found in '{original_sub_path}'.")
        else:
            print(f"  VERIFICATION FAILED: New file name not found or old name check failed.")
            
    except Exception as e:
        print(f"  Error renaming file: {e}")
    dm.print_tree()


def demonstrate_moving_items(dm):
    print("\n--- 8. Moving Files and Directories (move_file, move_files, move_directories) ---")
    archive_dir_name = "archive" # Relative to root
    dm.create_directory(archive_dir_name)
    dm.gather()
    print(f"Created '{archive_dir_name}' directory for moving items.")

    # Move a single file (e.g., docs/readme.md to archive/)
    print("\nMoving 'docs/readme.md' to 'archive' (move_file):")
    if dm.find_file(name="readme", sub_path="docs", extension="md"):
        try:
            dm.move_file(name="readme", sub_path="docs", extension="md", dest_directory_name=archive_dir_name)
            print("  Moved 'docs/readme.md'.")
            dm.gather()
            if not dm.find_file(name="readme", sub_path="docs", extension="md") and \
               dm.find_file(name="readme", sub_path=archive_dir_name, extension="md"):
                print("  Single file move successful.")
            else:
                print("  Single file move verification failed.")
        except Exception as e:
            print(f"  Error moving single file: {e}")
    else:
        print("  'docs/readme.md' not found. Skipping move_file demo for it.")
    dm.print_tree()

    # Move multiple files (e.g., all files from 'src' to 'archive')
    # Note: 'src' might contain 'python_code' subdir. move_files moves *files*.
    print("\nMoving all files (not subdirs) from 'src' to 'archive' (move_files):")
    files_in_src = [f for f in dm.files if os.path.dirname(os.path.relpath(f.path, dm.root_path)) == "src"]
    if files_in_src:
        try:
            dm.move_files(sub_path="src", dest_directory_name=archive_dir_name) # Will only move files directly in 'src'
            print(f"  Moved {len(files_in_src)} file(s) from 'src'.")
            dm.gather()
            # Verification is a bit more complex here, check counts
            # This check is simplified:
            if not [f for f in dm.files if os.path.dirname(os.path.relpath(f.path, dm.root_path)) == "src"]:
                 print("  Multiple files move from 'src' seems successful (src is empty of files).")
            else:
                 print("  Multiple files move from 'src' verification failed (src still has files).")
        except Exception as e:
            print(f"  Error moving multiple files: {e}")
    else:
        print("  No files found directly in 'src' to move. Skipping.")
    dm.print_tree()

    # Move a directory (e.g., 'data/raw_data' into 'archive')
    print("\nMoving directory 'data/raw_data' into 'archive' (move_directories):")
    if dm.find_directories(name="raw_data", sub_path="data"):
        try:
            # dest_dir_name_filter refers to the name of an existing directory where 'raw_data' will be moved into.
            dm.move_directories(name="raw_data", sub_path="data", dest_dir_name_filter=archive_dir_name)
            print("  Moved 'data/raw_data' directory.")
            dm.gather()
            expected_new_subpath = os.path.join(archive_dir_name, "raw_data")
            if not dm.find_directories(name="raw_data", sub_path="data") and \
               dm.find_directories(name="raw_data", sub_path=archive_dir_name): # Check it's inside archive
                print("  Directory move successful.")
            else:
                print("  Directory move verification failed.")
        except Exception as e:
            print(f"  Error moving directory: {e}")
    else:
        print("  Directory 'data/raw_data' not found for moving. Skipping.")
    dm.print_tree()


def demonstrate_comparison(dm):
    print("\n--- 9. Comparing Directory States (compare_to) ---")
    # Create two slightly different directory structures for comparison
    comp_A_path = os.path.join(EXAMPLE_ROOT_DIR, "compare_A")
    comp_B_path = os.path.join(EXAMPLE_ROOT_DIR, "compare_B")
    os.makedirs(comp_A_path, exist_ok=True)
    os.makedirs(comp_B_path, exist_ok=True)

    dm_A = DirectoryManager(comp_A_path)
    dm_A.create_file("", "file_A_only", "txt", "In A")
    dm_A.create_file("", "shared_file", "dat", "Shared content from A")
    dm_A.gather()

    dm_B = DirectoryManager(comp_B_path)
    dm_B.create_file("", "file_B_only", "txt", "In B")
    dm_B.create_file("", "shared_file", "dat", "Shared content from B") # Same path relative to root, but different DM root
    dm_B.gather()

    print(f"Comparing DM_A (root: {dm_A.root_path}) with DM_B (root: {dm_B.root_path})")
    # compare_to checks for differences in absolute file paths.
    differences = dm_A.compare_to(dm_B)
    print("Path differences found (symmetric difference):")
    if differences:
        for diff_path in sorted(differences): # Sort for consistent output
            print(f"  - {diff_path}")
    else:
        print("  No differences in file paths found.")
    
    # Cleanup comparison directories
    shutil.rmtree(comp_A_path)
    shutil.rmtree(comp_B_path)


def demonstrate_deletions(dm):
    print("\n--- 10. Deleting Files and Directories (delete_files, delete_directories) ---")
    
    # Delete specific files (e.g., 'notes_no_ext' from 'docs')
    print("\nAttempting to delete 'docs/notes_no_ext' (delete_files):")
    if dm.find_file(name="notes_no_ext", sub_path="docs"):
        try:
            dm.delete_files(name="notes_no_ext", sub_path="docs")
            print("  Called delete_files for 'docs/notes_no_ext'.")
            dm.gather()
            if not dm.find_file(name="notes_no_ext", sub_path="docs"):
                print("  File deletion successful.")
            else:
                print("  File deletion verification failed.")
        except Exception as e:
            print(f"  Error deleting file: {e}")
    else:
        print("  'docs/notes_no_ext' not found. Skipping its deletion.")
    dm.print_tree()

    # Delete a directory (e.g., 'docs' if it's empty or we want to remove all contents)
    # 'docs' might still have 'readme.md' if move failed or wasn't targeted.
    # Let's target 'archive' for deletion instead, which should have items.
    print("\nAttempting to delete directory 'archive' and its contents (delete_directories):")
    if dm.find_directories(name="archive"):
        try:
            dm.delete_directories(name="archive") 
            print("  Called delete_directories for 'archive'.")
            dm.gather()
            if not dm.find_directories(name="archive"):
                print("  Directory 'archive' deletion successful.")
            else:
                print("  Directory 'archive' deletion verification failed.")
        except Exception as e:
            print(f"  Error deleting directory 'archive': {e}")
    else:
        print("  Directory 'archive' not found. Skipping its deletion.")
    dm.print_tree()


def main():
    setup_example_env()
    
    # Initialize DirectoryManager for the example root
    # Using an absolute path for clarity in output, though relative works.
    abs_example_root_dir = os.path.abspath(EXAMPLE_ROOT_DIR)
    dm = DirectoryManager(abs_example_root_dir)

    try:
        demonstrate_initialization_and_properties(dm)
        
        demonstrate_directory_creation(dm)
        demonstrate_file_creation(dm)
        
        demonstrate_print_tree(dm)
        
        demonstrate_finding_items(dm)
        
        demonstrate_file_operations_and_content(dm)
        
        # demonstrate_renaming(dm)
        
        # demonstrate_moving_items(dm)
        
        demonstrate_comparison(dm) # Compares two separate DM instances/roots
        
        # demonstrate_deletions(dm)

        print("\n--- Final State of Managed Directory (after all operations) ---")
        dm.gather() # Final gather to reflect all changes
        dm.print_tree()
        print(f"Final directories in manager: {[d.path for d in dm.directories]}")
        print(f"Final files in manager: {[f.path for f in dm.files]}")
        print(f"Final extensions in manager: {dm.extensions}")

    except Exception as e:
        print(f"\nAN UNEXPECTED ERROR OCCURRED IN THE EXAMPLE SCRIPT: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup_example_env()

if __name__ == "__main__":
    main()