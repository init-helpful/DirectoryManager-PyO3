
import os
import sys
import shutil
import time
import subprocess
from pathlib import Path
import filecmp

sys.path.append(os.path.dirname(__file__))



PYTHON_EXE = sys.executable
ORIGINAL_SCRIPT_NAME = "snapshot.py"
DIRMAN_SCRIPT_NAME = "snapshot_dirman.py"

TEST_ENV_DIR = "snapshot_test_environment"
OUTPUT_ORIGINAL = "project_snapshot_original_test.txt"
OUTPUT_DIRMAN = "project_snapshot_dirman_test.txt"


def create_test_project_structure(base_path: Path):
    """Creates a more complex test project structure."""
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)

    structure = [
        ("src", True, None),
        ("src/app.py", False, "print('Hello from app.py')\n# python code\nimport os"),
        ("src/utils.py", False, "# Utility functions\n# Another line for utils.py"),
        ("src/components", True, None),
        ("src/components/button.js", False, "// Button component\n// javascript code here"),
        ("src/components/style.css", False, "/* CSS for button */\nbody { font-family: Arial; }"),
        ("docs", True, None),
        ("docs/readme.md", False, "# Project Documentation\nMarkdown content."),
        ("docs/api.rst", False, ".. API Docs\n   More reStructuredText."),
        ("tests", True, None),
        ("tests/test_app.py", False, "# Test for app.py\n# python test code"),
        ("tests/data", True, None),
        ("tests/data/fixture.json", False, '{"key": "value_fixture"}'),
        (".git", True, None),
        (".git/config", False, "[core]\nrepositoryformatversion = 0"),
        ("node_modules", True, None),
        ("node_modules/lib_a/index.js", False, "// lib_a content"),
        ("README.md", False, "Main project README."),
        ("Makefile", False, "build:\n\techo Building..."),
        ("project.toml", False, "[tool.poetry]\nname = \"testproject\""),
        ("src/generated_code.py", False, "# This should be ignored by substring filter"),
        ("data", True, None),
        ("data/input.csv", False, "col1,col2\nval1,val2"),
        ("data/archive.zip", False, "binarydata"),
        ("data/logs", True, None),
        ("data/logs/app.log", False, "Log entry 1\nLog entry 2"),
    ]

    for rel_path_str, is_dir, content in structure:
        full_path = base_path / rel_path_str
        if is_dir:
            full_path.mkdir(parents=True, exist_ok=True)
        else:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content or f"Content for {rel_path_str}")
    
    for i in range(3):
        deep_dir = base_path / f"deep_module_{i}"
        deep_dir.mkdir()
        for j in range(5):
            sub_dir = deep_dir / f"sub_pkg_{j}"
            sub_dir.mkdir()
            for k in range(10):
                with open(sub_dir / f"file_{k}.py", "w") as f:
                    f.write(f"# Content for deep/sub/file_{i}_{j}_{k}.py")
                if k % 2 == 0:
                     with open(sub_dir / f"data_file_{k}.txt", "w") as f:
                        f.write(f"Some text data {i}_{j}_{k}")

    print(f"Test project structure created at: {base_path.resolve()}")


def run_script_and_time(script_name: str, cwd: Path, output_filename: str, num_runs: int = 3) -> float:
    """Runs a script via subprocess and returns average execution time."""
    print(f"\n--- Testing {script_name} ---")
    total_time = 0
    



    script_path = Path(__file__).parent / script_name

    expected_script_output_name = "project_code_snapshot.txt"
    if "dirman" in script_name.lower():
        expected_script_output_name = "project_code_snapshot_dirman.txt"

    for i in range(num_runs):
        default_output_in_cwd = cwd / expected_script_output_name
        if default_output_in_cwd.exists():
            default_output_in_cwd.unlink()

        start_time = time.perf_counter()
        process = subprocess.Popen(
            [PYTHON_EXE, str(script_path)],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        end_time = time.perf_counter()

        if process.returncode != 0:
            print(f"Error running {script_name} (run {i+1}):")
            print("STDOUT:\n", stdout)
            print("STDERR:\n", stderr)
        else:
            print(f"Run {i+1}/{num_runs} of {script_name} completed in {end_time - start_time:.4f}s")
        
        total_time += (end_time - start_time)

        final_output_path = cwd / output_filename
        if default_output_in_cwd.exists():
            if final_output_path.exists():
                final_output_path.unlink()
            default_output_in_cwd.rename(final_output_path)
        else:
            print(f"Warning: Expected output '{default_output_in_cwd}' not found after running {script_name}.")


    avg_time = total_time / num_runs
    print(f"Average time for {script_name} over {num_runs} runs: {avg_time:.4f}s")
    return avg_time

def compare_outputs(file1: Path, file2: Path) -> bool:
    """Compares two files for equality."""
    if not file1.exists():
        print(f"Error: Output file {file1} does not exist for comparison.")
        return False
    if not file2.exists():
        print(f"Error: Output file {file2} does not exist for comparison.")
        return False
    
    print(f"\nComparing output files: {file1.name} and {file2.name}")
    are_identical = filecmp.cmp(str(file1), str(file2), shallow=False)
    if are_identical:
        print("Output files are identical.")
    else:
        print("Output files differ.")
    return are_identical


def main_test():
    test_project_root = Path(__file__).parent / TEST_ENV_DIR
    
    original_script_path = Path(__file__).parent / ORIGINAL_SCRIPT_NAME
    dirman_script_path = Path(__file__).parent / DIRMAN_SCRIPT_NAME

    if not original_script_path.exists():
        print(f"Error: Original script '{ORIGINAL_SCRIPT_NAME}' not found at {original_script_path}")
        return
    if not dirman_script_path.exists():
        print(f"Error: Dirman script '{DIRMAN_SCRIPT_NAME}' not found at {dirman_script_path}")
        return

    try:
        print("Setting up test environment...")
        create_test_project_structure(test_project_root)

        output_original_path = test_project_root / OUTPUT_ORIGINAL
        output_dirman_path = test_project_root / OUTPUT_DIRMAN

        time_original = run_script_and_time(ORIGINAL_SCRIPT_NAME, cwd=test_project_root, output_filename=OUTPUT_ORIGINAL)

        time_dirman = run_script_and_time(DIRMAN_SCRIPT_NAME, cwd=test_project_root, output_filename=OUTPUT_DIRMAN)

        print("\n--- Speed Comparison Summary ---")
        print(f"Average time for Original (os.walk): {time_original:.4f}s")
        print(f"Average time for Dirman version:     {time_dirman:.4f}s")

        if time_original > 0 and time_dirman > 0 :
            if time_dirman < time_original:
                print(f"Dirman version was {time_original / time_dirman:.2f}x faster.")
            elif time_original < time_dirman:
                print(f"Original (os.walk) version was {time_dirman / time_original:.2f}x faster.")
            else:
                print("Both versions had similar performance.")
        
        compare_outputs(output_original_path, output_dirman_path)

    except Exception as e:
        print(f"An error occurred during the test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nCleaning up test environment...")
        if test_project_root.exists():
            try:
                shutil.rmtree(test_project_root)
                print(f"Removed test environment: {test_project_root}")
            except Exception as e:
                print(f"Error cleaning up test environment: {e}")


if __name__ == "__main__":
    
    main_test()