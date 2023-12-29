from dirman import DirectoryManager

# Create a new DirectoryManager instance
test_directory = DirectoryManager(".//Tests//Data")


def generate_directories(
    num_files=10,
    num_directories=5,
    base_dir_name="dir",
    base_file_name="test_{}.txt",
):
    # Create the directories
    for directory_index in range(num_directories):
        dir_name = f"{base_dir_name}{directory_index+1}"
        test_directory.create_directory(dir_name)

        # Create and fill the files in the directories
        for i in range(num_files):
            file_name = base_file_name.format(chr(ord("a") + i))
            file_content = f"Default text for {file_name}"
            test_directory.create_file(dir_name, file_name, None, file_content)


generate_directories()
