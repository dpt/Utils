# Utils

A collection of Python utilities for file and directory management.

## Scripts

### remove-duplicates.py

Recursively scans a directory and removes duplicate files based on size and MD5
hash comparison.

**Usage:** `python remove-duplicates.py DIRECTORY`

### rerename.py

Batch renames files and directories using regular expressions. Includes preset
patterns for common transformations (spaces to dots, comma removal, etc.).

**Usage:** `python rerename.py [OPTIONS] <from_regex> <to_regex> DIRECTORY`

**Options:**

- `-d` Use default patterns
- `-l` Convert to lowercase
- `-p` Preview mode (no changes)
- `-r` Recurse subdirectories

### resetjpegdpi.py

Resets the DPI metadata in JPEG files to standard values (version: 0x102, units:
0, density: 100x100).

**Usage:** `python resetjpegdpi.py DIRECTORY`

### pmt.py (Poor Man's Tagging)

Organizes directories by analyzing token-based naming patterns. Extracts tokens
from directory names (separated by '+' by default), sorts them by frequency, and
renames directories using the most common tokens first.

**Usage:** `python pmt.py <target_directory> [options]`

## Requirements

- Python 2.7+ (some scripts may need updating for Python 3)
- Standard library modules only

## Author

Copyright (c) David Thomas, 2007-2016. <dave@davespace.co.uk>
