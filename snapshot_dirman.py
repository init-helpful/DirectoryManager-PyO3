import os
import sys
from pathlib import Path
from typing import List, Optional, Set, Tuple, Callable, NamedTuple, Dict 

try:
    from dirman import DirectoryManager, File as DirmanFile, Directory as DirmanDirectory
except ImportError:
    print("Error: dirman module not found. Make sure it's compiled and in PYTHONPATH.")
    print("You might need to run 'maturin develop' in the DirMan project root.")
    sys.exit(1)

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

def _generate_tree_lines_dirman(
    root_path_obj: Path,
    filtered_dirs: List[DirmanDirectory],
    filtered_files: List[DirmanFile]
) -> List[str]:
    tree_lines: List[str] = [root_path_obj.name]
    parent_to_children_map: Dict[str, List[Tuple[DirmanFile | DirmanDirectory, bool, str]]] = {}
    all_filtered_entries: List[Tuple[DirmanFile | DirmanDirectory, bool]] = \
        [(d, True) for d in filtered_dirs] + [(f, False) for f in filtered_files]

    for entry_obj, is_dir_flag in all_filtered_entries:
        entry_abs_path = Path(entry_obj.path)
        parent_path_str = str(entry_abs_path.parent)
        display_name = entry_abs_path.name
        parent_to_children_map.setdefault(parent_path_str, []).append((entry_obj, is_dir_flag, display_name))

    for parent_path_str in parent_to_children_map:
        parent_to_children_map[parent_path_str].sort(
            key=lambda x: (not x[1], x[2].lower())
        )

    def _recursive_build(current_parent_path_str: str, prefix_parts: List[str]):
        children = parent_to_children_map.get(current_parent_path_str, [])
        num_children = len(children)
        for i, (child_obj, child_is_dir, child_display_name) in enumerate(children):
            is_last = (i == num_children - 1)
            connector = "└── " if is_last else "├── "
            tree_lines.append("".join(prefix_parts) + connector + child_display_name)
            if child_is_dir:
                new_prefix_parts = prefix_parts + ["    " if is_last else "│   "]
                _recursive_build(child_obj.path, new_prefix_parts)

    _recursive_build(str(root_path_obj), [])
    return tree_lines

def _prepare_files_to_process_dirman(
    dm_root_path: Path,
    filtered_dm_files: List[DirmanFile]
) -> List[FileToProcess]:
    files_to_process: List[FileToProcess] = []
    for dm_file in filtered_dm_files:
        abs_path = Path(dm_file.path)
        try:
            relative_path_posix = abs_path.relative_to(dm_root_path).as_posix()
            files_to_process.append(FileToProcess(abs_path, relative_path_posix))
        except ValueError:
             print(f"  Warning: Could not make DirmanFile path '{abs_path}' relative to '{dm_root_path}'. Skipping.")
    files_to_process.sort(key=lambda f_info: f_info.relative_path_posix.lower())
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
                if not tree_content_lines:
                    outfile.write("No files found matching the specified criteria for content aggregation.\n")
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
    except Exception as e:
        print(f"Error: An unexpected error occurred during file content processing: {e}")
    return collected_files_count

def _print_processing_summary(
    collected_files_count: int,
    num_files_selected: int,
    output_file_path: Path,
    generate_tree_flag: bool,
    tree_content_lines: Optional[List[str]], 
    tree_header_text: str
) -> None:
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
    else: 
        if num_files_selected > 0:
             print(
                f"\nProcess complete. Output file '{output_file_path}' created/updated. "
                f"{num_files_selected} files were selected, but none could be successfully read."
            )
        elif not (generate_tree_flag and tree_content_lines): 
            print(
                f"\nProcess complete. Output file '{output_file_path}' created/updated. "
                "No files matched criteria for content aggregation."
            )
        else: 
             print(f"\nProcess complete. Output file '{output_file_path}' created/updated.")
    if generate_tree_flag:
        if tree_content_lines is not None and len(tree_content_lines) > 1: 
            print(f"Directory tree under header '{tree_header_text}' was included at the top of '{output_file_path}'.")
        else:
            print(f"Directory tree generation was attempted but failed or produced no usable content beyond the root; it was not meaningfully added to '{output_file_path}'.")

def collect_and_append_files_dirman(
    root_dir: Path,
    effective_config: EffectiveConfig,
    output_file_path_str: str,
    encoding: str = DEFAULT_ENCODING,
    separator_char: str = DEFAULT_SEPARATOR_CHAR,
    separator_line_len: int = DEFAULT_SEPARATOR_LINE_LENGTH,
    generate_tree: bool = False,
) -> None:
    print(f"Initializing DirectoryManager for root: {root_dir} with filters.")
    
    target_extensions_for_dm = [ft for ft in effective_config.target_file_types if ft.startswith(".")]
    target_exact_filenames_for_dm = [ft for ft in effective_config.target_file_types if not ft.startswith(".")]


    dm = DirectoryManager(
        root_path=str(root_dir) if root_dir else None, # Explicitly pass None if root_dir is empty string from param
        target_extensions=target_extensions_for_dm if target_extensions_for_dm else None,
        target_exact_filenames=target_exact_filenames_for_dm if target_exact_filenames_for_dm else None,
        ignore_path_components=effective_config.ignore_path_components if effective_config.ignore_path_components else None,
        ignore_filename_substrings=effective_config.ignore_fname_substrings if effective_config.ignore_fname_substrings else None,
        whitelist_filename_substrings=effective_config.whitelist_fname_substrings if effective_config.whitelist_fname_substrings else None
    )
    
    print(f"DirectoryManager (pre-filtered in Rust) gathered {len(dm.directories)} directories and {len(dm.files)} files.")

    filtered_dm_dirs = dm.directories
    filtered_dm_files = dm.files
    
    tree_content_lines: Optional[List[str]] = None
    if generate_tree:
        print(f"\nGenerating directory tree for: {root_dir} (using pre-filtered entries from dm)")
        try:
            tree_content_lines = _generate_tree_lines_dirman(Path(dm.root_path), filtered_dm_dirs, filtered_dm_files)
            if tree_content_lines and len(tree_content_lines) > 1:
                 print(f"Directory tree will be included at the top of '{output_file_path_str}'.")
            else:
                print("Directory tree generation resulted in no significant content.")
                tree_content_lines = None
        except Exception as e:
            print(f"Error during dirman tree generation: {e}")
        print("-" * 30)

    files_to_process_list = _prepare_files_to_process_dirman(Path(dm.root_path), filtered_dm_files)
    print(f"\nPrepared {len(files_to_process_list)} files from DirmanFile list to process for content.")

    output_file_path = Path(output_file_path_str).resolve()
    output_file_path.parent.mkdir(parents=True, exist_ok=True)

    collected_files_count = _write_aggregated_content_to_file(
        output_file_path,
        tree_content_lines,
        files_to_process_list,
        encoding,
        separator_char,
        separator_line_len,
        TREE_HEADER_TEXT
    )

    _print_processing_summary(
        collected_files_count,
        len(files_to_process_list),
        output_file_path,
        generate_tree,
        tree_content_lines,
        TREE_HEADER_TEXT
    )

def load_and_merge_configurations(
    language_preset_name: Optional[str],
    additional_target_file_types: Optional[List[str]],
    additional_whitelist_fname_substrings: Optional[List[str]],
    additional_ignore_fname_substrings: Optional[List[str]],
    additional_ignore_path_components: Optional[List[str]],
) -> EffectiveConfig:
    effective_target_file_types = set(additional_target_file_types or [])
    effective_whitelist_fname_substrings = set(additional_whitelist_fname_substrings or [])
    effective_ignore_fname_substrings = set(additional_ignore_fname_substrings or [])
    effective_ignore_path_components = set(additional_ignore_path_components or [])
    active_preset_name = "generic" 
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

def main_dirman():
    root_directory_to_scan_param: Optional[str] = "" 
    output_file_name: str = "project_code_snapshot_dirman.txt" 
    language_preset_name: Optional[str] = "rust"
    additional_target_file_types: List[str] = [".py"]
    additional_whitelist_filename_substrings: Optional[List[str]] = []
    additional_ignore_filename_substrings: Optional[List[str]] = ["Cargo.lock", "snapshot_dirman.py", "snapshot_os_walk.py", "test_snapshot_speed.py"]
    additional_ignore_path_components: Optional[List[str]] = ["objects", ".git", ".github", "target/debug/deps", "target/release/deps", "target/rls"]
    file_encoding: str = DEFAULT_ENCODING
    separator_char_config: str = DEFAULT_SEPARATOR_CHAR
    separator_len_config: int = DEFAULT_SEPARATOR_LINE_LENGTH
    generate_tree_flag: bool = True

    print("--- Starting File Collection Script (Dirman Version with Rust Filtering) ---")
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
    collect_and_append_files_dirman(
        actual_root_dir,
        effective_config,
        str(abs_output_content_file),
        encoding=file_encoding,
        separator_char=separator_char_config,
        separator_line_len=separator_len_config,
        generate_tree=generate_tree_flag,
    )
    print("\n--- Script Execution Finished (Dirman Version with Rust Filtering) ---")

if __name__ == "__main__":
    main_dirman()