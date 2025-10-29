#!/usr/bin/env python3
"""
Poor Man's Tagging

This script reads a specified directory containing subdirectories whose
names are built of tokens separated by a configurable separator (default
'+'). It extracts all tokens, sorts them by frequency, and renames the
directories to use the tokens ordered by frequency.

Created with assistance from Claude Sonnet 4.

Usage:
    python pmt.py <target_directory> [options]
"""

import argparse
import os
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path


def emit(message, quiet=False, level="info"):
    """
    Emit a message unless quiet mode is enabled and it's a normal info
    message.

    Args:
        message (str): Message to print
        quiet (bool): If True, suppress info messages but show warnings
                     and errors
        level (str): Message level - "info", "warning", or "error"
    """
    if not quiet or level in ("warning", "error"):
        print(message)


def extract_tokens_from_directories(directory_path, separator="+"):
    """
    Extract all tokens from directory names in the given path.

    Args:
        directory_path (Path): Path to the directory containing
                              subdirectories
        separator (str): Token separator character (default '+')

    Returns:
        tuple: (list of directory names, Counter of tokens)
    """
    directory_names = []
    all_tokens = []

    try:
        for item in directory_path.iterdir():
            if item.is_dir():
                dir_name = item.name
                directory_names.append(dir_name)

                # Split by separator and extract tokens
                tokens = [
                    token.strip()
                    for token in dir_name.split(separator)
                    if token.strip()
                ]
                all_tokens.extend(tokens)

    except (OSError, PermissionError) as e:
        print(f"Error reading directory {directory_path}: {e}")
        return [], Counter()

    return directory_names, Counter(all_tokens)


def sort_tokens_by_frequency(token_counter, sort_method="freq"):
    """
    Sort tokens by various methods.

    Args:
        token_counter (Counter): Counter object with token frequencies
        sort_method (str): Sorting method - "freq", "random", "alpha",
                          "length", "reverse"

    Returns:
        list: Sorted tokens according to the specified method
    """
    if sort_method == "random":
        tokens = list(token_counter.keys())
        random.shuffle(tokens)
        return tokens
    elif sort_method == "alpha":
        # Sort alphabetically (case-insensitive)
        return sorted(token_counter.keys(), key=lambda x: x.lower())
    elif sort_method == "length":
        # Sort by token length (shortest first), then alphabetically for
        # ties
        return sorted(token_counter.keys(), key=lambda x: (len(x), x.lower()))
    elif sort_method == "reverse":
        # Sort by frequency (ascending), then alphabetically for ties
        return sorted(token_counter.keys(), key=lambda x: (token_counter[x], x.lower()))
    else:
        # Default: sort by frequency (descending), then alphabetically
        # for ties
        return sorted(
            token_counter.keys(), key=lambda x: (-token_counter[x], x.lower())
        )


def create_new_directory_name(
    original_name, token_order, separator="+", transform=None
):
    """
    Create new directory name with tokens sorted by frequency.

    Args:
        original_name (str): Original directory name
        token_order (list): List of tokens sorted by frequency
        separator (str): Token separator character (default '+')
        transform (str): Token transformation - "lower", "upper", "title",
                        or None

    Returns:
        str: New directory name with sorted tokens
    """
    # Extract tokens from original name
    tokens = [
        token.strip() for token in original_name.split(separator) if token.strip()
    ]

    # Create a mapping of token to its frequency rank
    token_rank = {token: idx for idx, token in enumerate(token_order)}

    # Sort tokens in this directory by their frequency rank
    sorted_tokens = sorted(tokens, key=lambda x: token_rank.get(x, float("inf")))

    # Apply token transformation if specified
    if transform == "lower":
        sorted_tokens = [token.lower() for token in sorted_tokens]
    elif transform == "upper":
        sorted_tokens = [token.upper() for token in sorted_tokens]
    elif transform == "title":
        sorted_tokens = [token.title() for token in sorted_tokens]

    return separator.join(sorted_tokens)


def merge_directories(source_path, target_path, dry_run=False, quiet=False):
    """
    Merge contents of source directory into target directory.

    Args:
        source_path (Path): Source directory to merge from
        target_path (Path): Target directory to merge into
        dry_run (bool): If True, only show what would be merged without
                       actually merging
        quiet (bool): If True, suppress normal output but show warnings
                     and errors

    Returns:
        bool: True if merge was successful (or would be in dry run),
              False otherwise
    """
    if dry_run:
        emit(
            f"    [DRY RUN] Would merge contents of '{source_path.name}' "
            f"into '{target_path.name}'",
            quiet,
        )
        return True

    try:
        # Create target directory if it doesn't exist
        target_path.mkdir(exist_ok=True)

        # Move all contents from source to target
        for item in source_path.iterdir():
            target_item = target_path / item.name

            if target_item.exists():
                if item.is_dir() and target_item.is_dir():
                    # Recursively merge subdirectories
                    if not merge_directories(
                        item, target_item, dry_run=False, quiet=quiet
                    ):
                        return False
                    # Remove the now-empty source subdirectory
                    item.rmdir()
                else:
                    # Handle file conflicts by adding a suffix
                    counter = 1
                    original_name = target_item.name
                    name_parts = (
                        original_name.rsplit(".", 1)
                        if "." in original_name
                        else [original_name, ""]
                    )

                    while target_item.exists():
                        if len(name_parts) == 2:
                            new_name = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                        else:
                            new_name = f"{name_parts[0]}_{counter}"
                        target_item = target_path / new_name
                        counter += 1

                    shutil.move(str(item), str(target_item))
                    emit(
                        f"      Moved '{item.name}' to '{target_item.name}' "
                        f"(renamed to avoid conflict)",
                        quiet,
                    )
            else:
                shutil.move(str(item), str(target_item))
                emit(f"      Moved '{item.name}'", quiet)

        # Remove the now-empty source directory
        source_path.rmdir()
        emit(f"    ✓ Merged '{source_path.name}' into '{target_path.name}'", quiet)
        return True

    except (OSError, shutil.Error) as e:
        emit(f"    ✗ Error merging directories: {e}", quiet, "error")
        return False


def remove_empty_directories(directory_path, dry_run=False, quiet=False):
    """
    Remove empty directories recursively.

    Args:
        directory_path (Path): Path to check for empty directories
        dry_run (bool): If True, only show what would be removed without
                       actually removing
        quiet (bool): If True, suppress normal output but show warnings
                     and errors

    Returns:
        int: Number of directories removed (or would be removed in dry run)
    """
    removed_count = 0

    try:
        for item in directory_path.iterdir():
            if item.is_dir():
                # First recursively check subdirectories
                removed_count += remove_empty_directories(item, dry_run, quiet)

                # Check if this directory is now empty
                try:
                    if not any(item.iterdir()):
                        if dry_run:
                            emit(
                                f"  [DRY RUN] Would remove empty directory: "
                                f"'{item.name}'",
                                quiet,
                            )
                        else:
                            item.rmdir()
                            emit(f"  Removed empty directory: '{item.name}'", quiet)
                        removed_count += 1
                except OSError:
                    # Directory not empty or other error
                    pass
    except (OSError, PermissionError):
        # Can't read directory
        pass

    return removed_count


def count_files_in_directory(directory_path):
    """
    Count the total number of files in a directory recursively.

    Args:
        directory_path (Path): Path to the directory to count files in

    Returns:
        int: Total number of files in the directory and all subdirectories
    """
    file_count = 0
    try:
        for item in directory_path.rglob("*"):
            if item.is_file():
                file_count += 1
    except (OSError, PermissionError):
        # Can't read directory or permission denied
        pass
    return file_count


def find_largest_directory(directory_path, quiet=False):
    """
    Find and report the directory containing the largest number of files.

    Args:
        directory_path (Path): Path to search for directories
        quiet (bool): If True, suppress normal output but show warnings
                     and errors
    """
    largest_dir = None
    largest_count = 0

    try:
        for item in directory_path.iterdir():
            if item.is_dir():
                file_count = count_files_in_directory(item)
                if file_count > largest_count:
                    largest_count = file_count
                    largest_dir = item.name
    except (OSError, PermissionError):
        emit(
            f"Error reading directory for file counting: {directory_path}",
            quiet,
            "error",
        )
        return

    if largest_dir:
        emit(
            f"\nDirectory with most files: '{largest_dir}' ({largest_count} files)",
            quiet,
        )
    else:
        emit("\nNo directories found for file counting.", quiet)


def rename_directories(
    directory_path,
    dry_run=False,
    sort_method="freq",
    separator="+",
    quiet=False,
    transform=None,
):
    """
    Rename directories with tokens sorted by frequency or other methods,
    merging directories with colliding names.

    Args:
        directory_path (Path): Path to the directory containing
                              subdirectories
        dry_run (bool): If True, only show what would be renamed without
                       actually renaming
        sort_method (str): "freq" for frequency sorting, "random" for
                          random sorting
        separator (str): Token separator character (default '+')
        quiet (bool): If True, suppress normal output but show warnings
                     and errors
        transform (str): Token transformation - "lower", "upper", "title",
                        or None
    """
    emit(f"Processing directory: {directory_path}", quiet)
    emit("-" * 50, quiet)

    # Extract tokens and count frequencies
    directory_names, token_counter = extract_tokens_from_directories(
        directory_path, separator
    )

    if not directory_names:
        emit("No subdirectories found or unable to read directory.", quiet)
        return

    # Sort tokens by frequency or randomly
    sorted_tokens = sort_tokens_by_frequency(token_counter, sort_method)

    emit(
        f"Found {len(directory_names)} directories and "
        f"{len(sorted_tokens)} unique tokens.",
        quiet,
    )
    if sort_method == "random":
        emit("\nTokens (randomly ordered):", quiet)
    elif sort_method == "alpha":
        emit("\nTokens (alphabetically ordered):", quiet)
    elif sort_method == "length":
        emit("\nTokens (sorted by length):", quiet)
    elif sort_method == "reverse":
        emit("\nToken frequencies (sorted by frequency - ascending):", quiet)
    else:
        emit("\nToken frequencies (sorted by frequency - descending):", quiet)

    for token in sorted_tokens:
        emit(f"  {token}: {token_counter[token]}", quiet)

    # Build mapping of new names to original directories
    rename_map = defaultdict(list)
    for original_name in directory_names:
        new_name = create_new_directory_name(
            original_name, sorted_tokens, separator, transform
        )
        rename_map[new_name].append(original_name)

    emit(f"\n{'DRY RUN - ' if dry_run else ''}Directory processing:", quiet)
    emit("-" * 30, quiet)

    renamed_count = 0
    merged_count = 0

    # Process each target name and its associated directories
    for new_name, original_names in rename_map.items():
        if len(original_names) == 1:
            # Simple rename case
            original_name = original_names[0]
            if original_name != new_name:
                old_path = directory_path / original_name
                new_path = directory_path / new_name

                emit(f"'{original_name}' -> '{new_name}'", quiet)

                if not dry_run:
                    try:
                        old_path.rename(new_path)
                        renamed_count += 1
                        emit(f"  ✓ Renamed successfully", quiet)
                    except OSError as e:
                        emit(f"  ✗ Error renaming: {e}", quiet, "error")
                else:
                    renamed_count += 1
        else:
            # Collision case - need to merge directories
            emit(f"COLLISION: Multiple directories map to '{new_name}':", quiet)
            for orig in original_names:
                emit(f"  - '{orig}'", quiet)

            if not dry_run:
                # Choose the first directory as the target, merge others
                # into it
                target_name = original_names[0]
                target_path = directory_path / target_name

                # First rename target to final name if needed
                if target_name != new_name:
                    new_target_path = directory_path / new_name
                    try:
                        target_path.rename(new_target_path)
                        target_path = new_target_path
                        emit(
                            f"  ✓ Renamed '{target_name}' to '{new_name}' "
                            f"(merge target)",
                            quiet,
                        )
                    except OSError as e:
                        emit(f"  ✗ Error renaming merge target: {e}", quiet, "error")
                        continue

                # Merge remaining directories into the target
                merge_success = True
                for source_name in original_names[1:]:
                    source_path = directory_path / source_name
                    emit(f"  Merging '{source_name}' into '{new_name}':", quiet)
                    if not merge_directories(source_path, target_path, dry_run, quiet):
                        merge_success = False
                        break

                if merge_success:
                    merged_count += len(original_names) - 1
                    renamed_count += 1
                    emit(
                        f"  ✓ Successfully merged {len(original_names)} "
                        f"directories into '{new_name}'",
                        quiet,
                    )
                else:
                    emit(
                        f"  ✗ Failed to merge directories for '{new_name}'",
                        quiet,
                        "error",
                    )
            else:
                # Dry run - just show what would happen
                emit(
                    f"  [DRY RUN] Would merge {len(original_names)} "
                    f"directories into '{new_name}'",
                    quiet,
                )
                merged_count += len(original_names) - 1
                renamed_count += 1

    emit(
        f"\n{renamed_count} directories {'would be' if dry_run else 'were'} processed.",
        quiet,
    )
    if merged_count > 0:
        emit(
            f"{merged_count} directories "
            f"{'would be' if dry_run else 'were'} merged due to name "
            f"collisions.",
            quiet,
        )

    # Remove empty directories
    emit(f"\n{'DRY RUN - ' if dry_run else ''}Cleaning up empty directories:", quiet)
    emit("-" * 30, quiet)
    empty_removed = remove_empty_directories(directory_path, dry_run, quiet)
    if empty_removed > 0:
        emit(
            f"{empty_removed} empty directories "
            f"{'would be' if dry_run else 'were'} removed.",
            quiet,
        )
    else:
        emit("No empty directories found.", quiet)

    # Find and report directory with most files
    find_largest_directory(directory_path, quiet)


def main():
    """Main function to handle command line arguments and execute the script."""
    parser = argparse.ArgumentParser(
        description="""
Poor Man's Tagging - Rename directories with tokens sorted by frequency

This script reads a specified directory containing subdirectories whose
names are built of tokens separated by a configurable separator (default
'+'). It extracts all tokens, sorts them by frequency, and renames the
directories to use the tokens ordered by frequency.
        """.strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Created with assistance from Claude Sonnet 4.",
    )

    parser.add_argument(
        "target_directory", help="Directory containing subdirectories to process"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be renamed without actually renaming",
    )

    parser.add_argument(
        "--sort",
        choices=["freq", "random", "alpha", "length", "reverse"],
        default="freq",
        help="Sort method: freq (default), random, alpha, length, or reverse",
    )

    parser.add_argument(
        "--separator", default="+", help="Token separator character (default: '+')"
    )

    parser.add_argument(
        "--transform",
        choices=["lower", "upper", "title"],
        help="Transform token case: lower, upper, or title",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress normal output but show warnings and errors",
    )

    args = parser.parse_args()

    target_dir = args.target_directory
    dry_run = args.dry_run
    quiet = args.quiet
    sort_method = args.sort
    separator = args.separator
    transform = args.transform

    # Convert to Path object
    directory_path = Path(target_dir)

    # Validate directory exists
    if not directory_path.exists():
        print(f"Error: Directory '{target_dir}' does not exist.")
        sys.exit(1)

    if not directory_path.is_dir():
        print(f"Error: '{target_dir}' is not a directory.")
        sys.exit(1)

    # Execute the renaming
    try:
        rename_directories(
            directory_path, dry_run, sort_method, separator, quiet, transform
        )
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
