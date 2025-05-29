"""
================================================================================
Project Code Aggregator & Snapshot Tool
================================================================================

Purpose:
--------
This script is designed to scan a specified project directory, identify relevant
source code files and other specified file types, and aggregate their content
into a single output text file. It can also generate a textual representation
of the project's directory structure.

The primary goal is to create a comprehensive "snapshot" of a project's
text-based assets, which can be useful for various purposes, such as:
- Providing context to Large Language Models (LLMs) for code analysis,
  documentation, or generation tasks.
- Archiving a project's state at a specific point in time.
- Facilitating code reviews by providing a consolidated view of changes.
- Creating a searchable document of all relevant project code.

Key Features:
-------------
1.  **Directory Tree Generation**: Optionally creates a visual tree structure of
    the project, showing directories and files that meet the filtering criteria.
    This tree is placed at the top of the output file.

2.  **File Content Aggregation**: Reads the content of selected files and appends
    it to the output file, with clear separators indicating each file's path.

3.  **Language Presets**: Comes with predefined configurations (file types to
    include, common files/directories to ignore) for various programming
    languages and environments (e.g., Python, JavaScript, Java, generic web).
    This allows for quick setup for common project types.

4.  **Customizable Filtering**:
    *   **File Types/Names**: Users can specify exact filenames (e.g., "Makefile")
      and file extensions (e.g., ".py", ".ts") to include.
    *   **Ignore Path Components**: Specific directory names (e.g., "node_modules",
      ".git", "build") can be blacklisted, causing the script to skip them and
      their contents.
    *   **Ignore Filename Substrings**: Files whose names contain certain
      substrings (e.g., ".test.", ".spec.", "generated_") can be excluded.
    *   **Whitelist Filename Substrings**: Optionally, users can specify
      substrings that *must* be present in a filename for it to be included,
      acting as a positive filter.

5.  **Flexible Configuration**: Users can easily modify settings in the `main()`
    function to:
    *   Specify the root directory to scan (defaults to current working dir).
    *   Define the output file name.
    *   Choose a language preset.
    *   Add custom file types, ignore rules, and whitelist rules that augment
      or override the presets.
    *   Toggle directory tree generation.
    *   Configure encoding and separator characters.

How it Works (General Flow):
---------------------------
1.  **Configuration Loading**: The script starts by loading configuration settings.
    This involves:
    a.  Reading user-defined settings from the `main()` function (root directory,
        output file, language preset choice, additional filters, etc.).
    b.  If a language preset is selected, its default file types and ignore
        rules are loaded.
    c.  These presets are then merged with any additional custom rules provided
        by the user. Sets are used internally to handle duplicates gracefully.

2.  **Root Directory Validation**: The specified root directory is validated to
    ensure it exists and is indeed a directory.

3.  **Configuration Summary**: A summary of the effective configuration (what
    files will be targeted, what will be ignored, etc.) is printed to the console.

4.  **Directory Tree Generation (Optional)**: If enabled, the script traverses
    the directory structure (respecting ignore rules) starting from the root
    and builds a list of lines representing the tree. This uses a recursive
    approach. The same filtering logic applied to file content collection
    is used here to ensure consistency.

5.  **File Scanning and Collection**:
    a.  The script uses `os.walk()` to traverse the directory tree.
    b.  For each directory and file encountered, it applies the `_should_include_entry`
        filter. This function checks:
        i.  If any part of the entry's path matches `ignore_path_components`.
        ii. (For files) If the file's type/name matches `target_file_types`.
        iii.(For files) If the filename matches `whitelist_fname_substrings` (if any).
        iv. (For files) If the filename matches `ignore_fname_substrings`.
    c.  Directories that are not ignored are traversed further.
    d.  Files that pass all filters are added to a list of `FileToProcess`.
    e.  This list is then sorted.

6.  **Output File Writing**:
    a.  The output file is opened in write mode.
    b.  If the directory tree was generated, it's written first, preceded by a
        header and separators.
    c.  The script then iterates through the sorted list of `FileToProcess`. For
        each file:
        i.  A separator line and the file's relative path are written.
        ii. The file's content is read (with specified encoding, replacing
            errors) and written to the output file.
    d.  If no files are found or if the tree generation fails, appropriate
        messages are written to the output file or console.

7.  **Summary and Completion**: Finally, a summary of the operation (how many
    files processed, any errors) is printed to the console.

Customization:
--------------
The easiest way to customize the script is by modifying the variables within
the "User Configuration" section of the `main()` function. This allows you to
point the script at your project, choose a suitable language preset, and then
fine-tune the included/excluded files and directories using the `additional_`
lists. For more advanced changes, the `LANGUAGE_DEFAULTS` dictionary or the
core logic functions can be modified.
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple, Callable, NamedTuple

# --- Configuration Constants ---
DEFAULT_SEPARATOR_CHAR = "-"
DEFAULT_SEPARATOR_LINE_LENGTH = 80
DEFAULT_ENCODING = "utf-8"
TREE_HEADER_TEXT = "Project File Structure"

# --- Language Specific Default Configurations ---
LANGUAGE_DEFAULTS = {
    "generic": {
        "file_types": [],
        "ignore_filename_substrings": [
            ".spec.", ".test.", "_fixture.", "generated_", "example_", ".log",
            ".lock", ".min.", ".map", "package-lock.json", "yarn.lock",
            "changelog",
        ],
        "ignore_path_components": [
            ".git", ".hg", ".svn", ".idea", ".vscode", ".vs",
            "__pycache__", ".pytest_cache", ".tox", "venv", "env", ".env",
            "node_modules", "bower_components", "target", "build", "dist", "out",
            "bin", "obj", "docs", "doc", "examples", "samples", "tests", "test",
            "test_data", "fixtures", "coverage", "temp", "tmp", "logs", "vendor",
            "site-packages", ".angular", ".next", ".nuxt",
        ]
    },
    "python": {
        "file_types": [
            ".py", ".pyw", ".ipynb", "requirements.txt", "setup.py",
            "pyproject.toml", "Pipfile", "Pipfile.lock", "Makefile", "manage.py"
        ],
        "ignore_filename_substrings": [".pyc"],
        "ignore_path_components": [
            "__pycache__", ".pytest_cache", ".tox", "venv", "env", ".env",
            "build", "dist", ".eggs", "site-packages", "htmlcov",
            "docs", "examples", "tests", "test",
        ],
    },
    "javascript": {
        "file_types": [
            ".js", ".jsx", ".mjs", ".cjs", ".json", ".html", ".css", ".scss", ".less", ".vue", ".svelte",
            "package.json", "webpack.config.js", "babel.config.js", "vite.config.js",
            ".eslintrc.json", ".prettierrc.json"
        ],
        "ignore_filename_substrings": [
            ".log", ".lock", ".map", "package-lock.json", "yarn.lock", ".min."
        ],
        "ignore_path_components": [
            "node_modules", "build", "dist", "out", "coverage", "public",
            "docs", "examples", "test", "tests", "e2e", "__tests__",
        ],
    },
    "typescript": {
        "file_types": [
            ".ts", ".tsx", ".json", "tsconfig.json", "tslint.json",
            ".html", ".css", ".scss", ".less", "package.json",
            "webpack.config.ts", "babel.config.js", "vite.config.ts",
            ".eslintrc.json", ".prettierrc.json"
        ],
        "ignore_filename_substrings": [
            ".js", ".js.map", ".d.ts", ".log", ".lock", ".map",
            "package-lock.json", "yarn.lock", ".min."
        ],
        "ignore_path_components": [
            "node_modules", "build", "dist", "out", "coverage", "public",
            ".next", ".nuxt", "docs", "examples", "test", "tests", "e2e", "__tests__",
        ],
    },
    "java": {
        "file_types": [".java", ".kt", ".scala", ".groovy", ".xml", ".properties", "pom.xml", "build.gradle", "settings.gradle"],
        "ignore_filename_substrings": [".class", ".jar", ".war", ".ear"],
        "ignore_path_components": [
            "target", "build", "out", ".gradle", ".ideaTarget",
            "docs", "examples", "test", "tests", "src/test",
        ],
    },
    "csharp": {
        "file_types": [".cs", ".csproj", ".sln", ".json", ".xml", ".config", ".cshtml", ".razor"],
        "ignore_filename_substrings": [],
        "ignore_path_components": [
            "bin", "obj", "Properties", "packages", ".vs", "TestResults",
            "docs", "examples", "test", "tests",
        ],
    },
    "go": {
        "file_types": [".go", "go.mod", "go.sum", "Makefile"],
        "ignore_filename_substrings": [],
        "ignore_path_components": [
            "vendor", "bin", "docs", "examples", "test", "tests",
        ],
    },
    "rust": {
        "file_types": [".rs", "Cargo.toml", "Cargo.lock", "build.rs", "Makefile"],
        "ignore_filename_substrings": [],
        "ignore_path_components": [
            "target", "docs", "examples", "test", "tests",
        ],
    },
    "ruby": {
        "file_types": [".rb", "Gemfile", "Rakefile", ".gemspec", "config.ru", ".yml", ".yaml"],
        "ignore_filename_substrings": [],
        "ignore_path_components": [
            "vendor/bundle", "tmp", "log", ".bundle", "coverage",
            "doc", "test", "spec", "features",
        ],
    },
    "php": {
        "file_types": [".php", "composer.json", "composer.lock", ".phtml", ".blade.php", ".xml"],
        "ignore_filename_substrings": [],
        "ignore_path_components": [
            "vendor", "public/build", "storage/framework", "storage/logs", "bootstrap/cache",
            "docs", "examples", "test", "tests", "spec",
        ],
    },
    "web_frontend": {
        "file_types": [
            ".html", ".htm", ".css", ".scss", ".less", ".sass", ".styl",
            ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte",
            ".json", ".svg", ".md", "package.json", "tsconfig.json",
            "webpack.config.js", "vite.config.js", "postcss.config.js"
        ],
        "ignore_filename_substrings": [".min.", ".map", "bundle.", "chunk."],
        "ignore_path_components": [
            "node_modules", "bower_components", "dist", "build", "public", "static", "assets",
            ".cache", ".parcel-cache", ".next", ".nuxt", ".svelte-kit",
            "docs", "examples", "test", "tests", "__tests__", "coverage"
        ]
    }
}


# --- Helper Data Structures ---

@dataclass
class FilterCriteria:
    """Holds normalized filter criteria for files and directories."""
    file_extensions: Set[str] = field(default_factory=set)
    exact_filenames: Set[str] = field(default_factory=set)
    whitelist_fname_substrings: Set[str] = field(default_factory=set)
    ignore_fname_substrings: Set[str] = field(default_factory=set)
    ignore_path_components: Set[str] = field(default_factory=set)

    @classmethod
    def normalize_inputs(
        cls,
        file_types: Optional[List[str]],
        whitelist_substrings: Optional[List[str]],
        ignore_filename_substrings: Optional[List[str]],
        ignore_path_components_list: Optional[List[str]],
    ) -> 'FilterCriteria':
        norm_exts = set()
        norm_exact_fnames = set()
        if file_types:
            for ft in file_types:
                ft_lower = ft.lower().strip()
                if not ft_lower:
                    continue
                if ft_lower.startswith("."):
                    norm_exts.add(ft_lower)
                else:
                    norm_exact_fnames.add(ft_lower)

        norm_whitelist = set(s.lower() for s in whitelist_substrings if s.strip()) if whitelist_substrings else set()
        norm_ignore_fname = set(s.lower() for s in ignore_filename_substrings if s.strip()) if ignore_filename_substrings else set()
        norm_ignore_path_components = set(d.lower() for d in ignore_path_components_list if d.strip()) if ignore_path_components_list else set()

        return cls(
            file_extensions=norm_exts,
            exact_filenames=norm_exact_fnames,
            whitelist_fname_substrings=norm_whitelist,
            ignore_fname_substrings=norm_ignore_fname,
            ignore_path_components=norm_ignore_path_components
        )

class FileToProcess(NamedTuple):
    absolute_path: Path
    relative_path_posix: str

class EffectiveConfig(NamedTuple):
    target_file_types: List[str]
    whitelist_fname_substrings: List[str]
    ignore_fname_substrings: List[str]
    ignore_path_components: List[str]
    active_preset_name: str

# --- Core Logic Functions ---

def validate_root_directory(root_dir_param: Optional[str]) -> Optional[Path]:
    original_param_for_messaging = root_dir_param if root_dir_param else "current working directory"
    try:
        base_path = Path(root_dir_param or Path.cwd())
        resolved_path = base_path.resolve(strict=True)
    except FileNotFoundError:
        print(f"Error: Root directory '{original_param_for_messaging}' does not exist.")
        return None
    except Exception as e:
        print(f"Error: Could not resolve root directory '{original_param_for_messaging}': {e}")
        return None

    if not resolved_path.is_dir():
        print(f"Error: Root path '{resolved_path}' is not a directory.")
        return None

    if not root_dir_param:
        print(f"No root directory specified, using current working directory: {resolved_path}")
    return resolved_path


def _should_include_entry(
    entry_path: Path,
    root_dir: Path,
    criteria: FilterCriteria,
    is_dir: bool,
    log_func: Optional[Callable[[str], None]] = None
) -> bool:
    try:
        relative_path = entry_path.relative_to(root_dir)
    except ValueError:
        if log_func:
            log_func(f"  Warning: Could not make '{entry_path}' relative to '{root_dir}'. Skipping.")
        return False

    entry_name_lower = entry_path.name.lower()

    if criteria.ignore_path_components:
        for part_str in relative_path.parts:
            if part_str.lower() in criteria.ignore_path_components:
                if log_func:
                    log_func(f"  Skipping '{relative_path.as_posix()}' (path component '{part_str}' in ignored components list)")
                return False

    if is_dir:
        return True

    file_ext_lower = entry_path.suffix.lower()
    matched_type = False
    if criteria.file_extensions or criteria.exact_filenames:
        if file_ext_lower in criteria.file_extensions:
            matched_type = True
        elif entry_name_lower in criteria.exact_filenames:
            matched_type = True
        if not matched_type:
            return False
    else: # No specific file types/extensions given, so consider all files (subject to other filters)
        matched_type = True


    if criteria.whitelist_fname_substrings:
        if not any(sub in entry_name_lower for sub in criteria.whitelist_fname_substrings):
            if log_func:
                log_func(f"  Skipping '{relative_path.as_posix()}' (filename not in whitelist: '{entry_path.name}')")
            return False

    if criteria.ignore_fname_substrings:
        for sub in criteria.ignore_fname_substrings:
            if sub in entry_name_lower:
                if log_func:
                    log_func(f"  Skipping '{relative_path.as_posix()}' (filename substring '{sub}' in ignore list: '{entry_path.name}')")
                return False

    return True


def _generate_tree_lines(
    root_dir: Path,
    criteria: FilterCriteria,
) -> List[str]:
    tree_lines: List[str] = [root_dir.name]

    def _recursive_build(current_path: Path, prefix_parts: List[str]):
        try:
            entries = sorted(
                current_path.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except OSError as e:
            error_prefix = "".join(prefix_parts) + ("└── " if not prefix_parts or prefix_parts[-1] != "│   " else "├── ")
            tree_lines.append(error_prefix + f"[Error accessing: {current_path.name} - {e.strerror}]")
            return

        displayable_children: List[Tuple[Path, bool]] = []
        for entry in entries:
            try:
                is_dir = entry.is_dir()
            except OSError:
                continue
            if _should_include_entry(entry, root_dir, criteria, is_dir=is_dir, log_func=None):
                 displayable_children.append((entry, is_dir))

        num_children = len(displayable_children)
        for i, (child_path, child_is_dir) in enumerate(displayable_children):
            is_last = (i == num_children - 1)
            connector = "└── " if is_last else "├── "

            tree_lines.append("".join(prefix_parts) + connector + child_path.name)

            if child_is_dir:
                new_prefix_parts = prefix_parts + ["    " if is_last else "│   "]
                _recursive_build(child_path, new_prefix_parts)

    _recursive_build(root_dir, [])
    return tree_lines

def _scan_for_processable_files(
    root_dir: Path,
    criteria: FilterCriteria,
    log_func: Callable[[str], None]
) -> List[FileToProcess]:
    """Scans the directory for files matching criteria and returns a sorted list."""
    files_to_process: List[FileToProcess] = []
    print(f"\nScanning directory for file content: {root_dir}")

    for dirpath_str, dirnames, filenames in os.walk(str(root_dir), topdown=True, onerror=lambda e: print(f"Warning: Cannot access {e.filename}: {e.strerror}")):
        current_dir_path = Path(dirpath_str)

        # Filter directories in-place for os.walk
        orig_dirnames = list(dirnames)
        dirnames[:] = []
        for d_name in orig_dirnames:
            dir_abs_path = current_dir_path / d_name
            if _should_include_entry(dir_abs_path, root_dir, criteria, is_dir=True, log_func=log_func):
                dirnames.append(d_name)

        # Process files in the current directory
        for filename in filenames:
            file_abs_path = current_dir_path / filename
            if _should_include_entry(file_abs_path, root_dir, criteria, is_dir=False, log_func=log_func):
                try:
                    relative_path_posix = file_abs_path.relative_to(root_dir).as_posix()
                    files_to_process.append(FileToProcess(file_abs_path, relative_path_posix))
                except ValueError: # Should be rare due to how os.walk provides paths
                    log_func(f"  Warning: Could not make '{file_abs_path}' relative to '{root_dir}'. Skipping.")
    
    files_to_process.sort(key=lambda f_info: f_info.relative_path_posix.lower())
    print(f"\nFound {len(files_to_process)} files matching criteria to process for content.")
    return files_to_process

def _write_aggregated_content_to_file(
    output_file_path: Path,
    tree_content_lines: Optional[List[str]],
    files_to_process: List[FileToProcess],
    encoding: str,
    separator_char: str,
    separator_line_len: int,
    tree_header_text: str
) -> int:
    """Writes the tree (if any) and file contents to the output file."""
    collected_files_count = 0
    separator_line = separator_char * separator_line_len

    if files_to_process or tree_content_lines:
        print(f"Output will be written to: {output_file_path}")

    try:
        with open(output_file_path, "w", encoding=encoding) as outfile:
            if tree_content_lines:
                outfile.write(f"{tree_header_text}\n")
                outfile.write(f"{separator_line}\n\n")
                for line in tree_content_lines:
                    outfile.write(line + "\n")
                outfile.write(f"\n{separator_line}\n\n")

            if not files_to_process:
                if not tree_content_lines: # No tree and no files
                    outfile.write("No files found matching the specified criteria for content aggregation.\n")
                # If tree was written but no files, that's fine, no extra message here.
            else:
                for file_info in files_to_process:
                    print(f"  Processing content of: {file_info.relative_path_posix}")
                    outfile.write(f"{separator_line}\n")
                    outfile.write(f"FILE: {file_info.relative_path_posix}\n")
                    outfile.write(f"{separator_line}\n\n")
                    try:
                        with open(file_info.absolute_path, "r", encoding=encoding, errors="replace") as infile:
                            content = infile.read()
                            outfile.write(content)
                        outfile.write("\n\n")
                        collected_files_count += 1
                    except Exception as e:
                        print(f"    Warning: Could not read file '{file_info.absolute_path}': {e}")
                        outfile.write(f"Error: Could not read file '{file_info.relative_path_posix}'. Issue: {e}\n\n")
    except IOError as e:
        print(f"Error: Could not write to output file '{output_file_path}': {e}")
        # Allow summary to still print, but collected_files_count will reflect the issue if it happened early.
    except Exception as e:
        print(f"Error: An unexpected error occurred during file content processing: {e}")
    
    return collected_files_count

def _print_processing_summary(
    collected_files_count: int,
    num_files_selected: int,
    output_file_path: Path,
    generate_tree_flag: bool,
    tree_content_lines: Optional[List[str]], # Pass this to check if tree was actually generated
    tree_header_text: str
) -> None:
    """Prints the summary of the file collection and writing process."""
    if collected_files_count > 0:
        summary_msg = (
            f"\nProcess complete. Appended content of {collected_files_count} files "
            f"to '{output_file_path}'."
        )
        if collected_files_count == num_files_selected:
            summary_msg += f" (All {num_files_selected} selected files were processed successfully)."
        else:
            failed_to_read_count = num_files_selected - collected_files_count
            summary_msg += (
                f" ({failed_to_read_count} of {num_files_selected} selected "
                f"files could not be read)."
            )
        print(summary_msg)
    else: # No files successfully collected
        if num_files_selected > 0: # Files were selected, but none read
             print(
                f"\nProcess complete. Output file '{output_file_path}' created/updated. "
                f"{num_files_selected} files were selected, but none could be successfully read."
            )
        elif not (generate_tree_flag and tree_content_lines): # No files selected AND no (successful) tree
            print(
                f"\nProcess complete. Output file '{output_file_path}' created/updated. "
                "No files matched criteria for content aggregation."
            )
        else: # Tree might have been written, but no files selected/processed
             print(f"\nProcess complete. Output file '{output_file_path}' created/updated.")

    if generate_tree_flag:
        if tree_content_lines is not None and len(tree_content_lines) > 1: # Check if tree has content beyond root
            print(f"Directory tree under header '{tree_header_text}' was included at the top of '{output_file_path}'.")
        else:
            print(f"Directory tree generation was attempted but failed or produced no usable content beyond the root; it was not meaningfully added to '{output_file_path}'.")


def collect_and_append_files(
    root_dir: Path,
    file_types: List[str],
    output_file_path_str: str,
    whitelist_substrings_in_filename: Optional[List[str]] = None,
    ignore_substrings_in_filename: Optional[List[str]] = None,
    ignore_dirs_in_path: Optional[List[str]] = None,
    encoding: str = DEFAULT_ENCODING,
    separator_char: str = DEFAULT_SEPARATOR_CHAR,
    separator_line_len: int = DEFAULT_SEPARATOR_LINE_LENGTH,
    generate_tree: bool = False,
) -> None:
    """Orchestrates the collection of files and aggregation of their content."""
    criteria = FilterCriteria.normalize_inputs(
        file_types,
        whitelist_substrings_in_filename,
        ignore_substrings_in_filename,
        ignore_dirs_in_path
    )

    tree_content_lines: Optional[List[str]] = None
    if generate_tree:
        print(f"\nGenerating directory tree for: {root_dir}")
        try:
            tree_content_lines = _generate_tree_lines(root_dir, criteria) # Pass full criteria
            if tree_content_lines:
                 print(f"Directory tree will be included at the top of '{output_file_path_str}' under header '{TREE_HEADER_TEXT}'.")
            else:
                print("Directory tree generation resulted in no content.")
        except Exception as e:
            print(f"Error: An unexpected error occurred during tree generation: {e}")
        print("-" * 30) # Separator after tree generation attempt info

    def log_skip_for_collection(message: str): # Logger for file scanning
        print(message)

    files_to_process = _scan_for_processable_files(root_dir, criteria, log_skip_for_collection)

    output_file_path = Path(output_file_path_str).resolve()
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    collected_files_count = _write_aggregated_content_to_file(
        output_file_path,
        tree_content_lines,
        files_to_process,
        encoding,
        separator_char,
        separator_line_len,
        TREE_HEADER_TEXT
    )

    _print_processing_summary(
        collected_files_count,
        len(files_to_process),
        output_file_path,
        generate_tree,
        tree_content_lines,
        TREE_HEADER_TEXT
    )


# --- Main Execution Helper Functions ---

def load_and_merge_configurations(
    language_preset_name: Optional[str],
    additional_target_file_types: Optional[List[str]],
    additional_whitelist_fname_substrings: Optional[List[str]],
    additional_ignore_fname_substrings: Optional[List[str]],
    additional_ignore_path_components: Optional[List[str]],
) -> EffectiveConfig:
    """Loads language preset and merges with additional configurations."""
    effective_target_file_types = set(additional_target_file_types or [])
    effective_whitelist_fname_substrings = set(additional_whitelist_fname_substrings or [])
    effective_ignore_fname_substrings = set(additional_ignore_fname_substrings or [])
    effective_ignore_path_components = set(additional_ignore_path_components or [])

    active_preset_name = "generic"  # Default to generic
    preset_settings = {}

    if language_preset_name:
        language_preset_name_lower = language_preset_name.lower()
        if language_preset_name_lower in LANGUAGE_DEFAULTS:
            active_preset_name = language_preset_name_lower
            preset_settings = LANGUAGE_DEFAULTS[active_preset_name]
            print(f"Loading settings from '{active_preset_name}' language preset.")
        else:
            print(f"Warning: Language preset '{language_preset_name}' not found. Falling back to 'generic' defaults for preset part.")
            preset_settings = LANGUAGE_DEFAULTS.get("generic", {})
    else:
        print("No language preset specified. Using 'generic' defaults for preset part.")
        preset_settings = LANGUAGE_DEFAULTS.get("generic", {})

    effective_target_file_types.update(preset_settings.get("file_types", []))
    effective_ignore_fname_substrings.update(preset_settings.get("ignore_filename_substrings", []))
    effective_ignore_path_components.update(preset_settings.get("ignore_path_components", []))

    return EffectiveConfig(
        target_file_types=sorted(list(effective_target_file_types)),
        whitelist_fname_substrings=sorted(list(effective_whitelist_fname_substrings)),
        ignore_fname_substrings=sorted(list(effective_ignore_fname_substrings)),
        ignore_path_components=sorted(list(effective_ignore_path_components)),
        active_preset_name=active_preset_name
    )

def print_configuration_summary(
    root_dir: Path,
    output_file: Path,
    config: EffectiveConfig,
    generate_tree: bool,
    tree_header: str,
) -> None:
    """Prints a summary of the effective configuration."""
    print(f"\n--- Configuration Summary ---")
    print(f"Root Directory: {root_dir}")
    print(f"Output Content File: {output_file}")
    print(f"Language Preset Active: '{config.active_preset_name}' (plus any 'additional_' configurations)")

    if generate_tree:
        print(f"Directory Tree Generation: Enabled ('{tree_header}')")

    if config.target_file_types:
        print(f"Effective Target File Types/Names: {', '.join(config.target_file_types)}")
    else:
        print("Effective Target File Types/Names: (None specified)")
        if not generate_tree and not config.whitelist_fname_substrings:
             print("Warning: No target file types specified and not generating a tree or using whitelist. Output might be empty for file content.")

    if config.whitelist_fname_substrings:
        print(f"Effective Whitelist Filename Substrings: {', '.join(config.whitelist_fname_substrings)}")
    if config.ignore_fname_substrings:
        print(f"Effective Ignored Filename Substrings: {', '.join(config.ignore_fname_substrings)}")
    if config.ignore_path_components:
        print(f"Effective Ignored Path Components: {', '.join(config.ignore_path_components)}")
    print("--- End Configuration Summary ---")


# --- Main Execution Block ---
def main():
    # --- User Configuration ---
    #   Modify these settings to customize the script's behavior.
    # --------------------------

    root_directory_to_scan_param: Optional[str] = ""
    output_file_name: str = "project_code_snapshot.txt"
    language_preset_name: Optional[str] = "rust"

    additional_target_file_types: List[str] = [".py"]
    additional_whitelist_filename_substrings: Optional[List[str]] = []
    additional_ignore_filename_substrings: Optional[List[str]] = ["Cargo.lock"]
    additional_ignore_path_components: Optional[List[str]] = ["objects",".git",".github"]

    file_encoding: str = DEFAULT_ENCODING
    separator_char_config: str = DEFAULT_SEPARATOR_CHAR
    separator_len_config: int = DEFAULT_SEPARATOR_LINE_LENGTH
    generate_tree_flag: bool = True
    
    # --- End User Configuration ---

    print("--- Starting File Collection Script ---")

    effective_config = load_and_merge_configurations(
        language_preset_name,
        additional_target_file_types,
        additional_whitelist_filename_substrings,
        additional_ignore_filename_substrings,
        additional_ignore_path_components
    )

    actual_root_dir = validate_root_directory(root_directory_to_scan_param)
    if actual_root_dir is None:
        print("--- Script Execution Failed: Invalid root directory ---")
        sys.exit(1)

    abs_output_content_file = Path(output_file_name).resolve()

    print_configuration_summary(
        actual_root_dir,
        abs_output_content_file,
        effective_config,
        generate_tree_flag,
        TREE_HEADER_TEXT
    )

    collect_and_append_files(
        actual_root_dir,
        effective_config.target_file_types,
        str(abs_output_content_file),
        whitelist_substrings_in_filename=effective_config.whitelist_fname_substrings,
        ignore_substrings_in_filename=effective_config.ignore_fname_substrings,
        ignore_dirs_in_path=effective_config.ignore_path_components,
        encoding=file_encoding,
        separator_char=separator_char_config,
        separator_line_len=separator_len_config,
        generate_tree=generate_tree_flag,
    )
    print("\n--- Script Execution Finished ---")

if __name__ == "__main__":
    main()