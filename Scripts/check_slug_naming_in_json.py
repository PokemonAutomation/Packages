#!/usr/bin/env python3
"""
Check JSON files for non-compliant attribute names (keys).
Only lowercase letters, digits, and hyphens are allowed for object keys.

Special case: If the entire JSON file is an array of strings (slug list),
those strings are also validated. Otherwise, string values (like display text)
are NOT validated since they may contain any characters.
"""

import json
import os
import sys
import re
from pathlib import Path

# Pattern: only lowercase letters, digits, and hyphens
VALID_PATTERN = re.compile(r'^[a-z0-9\-]+$')

# Exceptions: specific attribute names that are allowed despite not matching the pattern
ALLOWED_EXCEPTIONS = {
    # Language codes
    'chi_sim',      # Chinese Simplified
    'chi_tra',      # Chinese Traditional
    # Sprite metadata
    'spriteHeight',
    'spriteWidth',
    'spriteLocations',
}


def is_valid_name(name):
    """
    Check if a name is valid.
    Valid names either:
    1. Match the pattern (lowercase letters, digits, hyphens), OR
    2. Are in the allowed exceptions list
    """
    return name in ALLOWED_EXCEPTIONS or bool(VALID_PATTERN.match(name))


def check_object(obj, file_path, line_offset=0, path="", is_top_level_array=False):
    """
    Recursively check JSON object for invalid attribute names.
    Only checks object keys, not values (which may be display strings).
    Special case: if the top-level JSON is an array of strings (slugs), check those.
    Returns list of (file_path, issue_description) tuples.
    """
    issues = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key

            # Check if the key itself is valid
            if not is_valid_name(key):
                issues.append((file_path, f"Invalid key '{key}' at {current_path}"))

            # Recursively check the value (only for nested objects/arrays)
            issues.extend(check_object(value, file_path, line_offset, current_path, is_top_level_array=False))

    elif isinstance(obj, list):
        # Only check strings in the list if this is the top-level array
        # (i.e., the entire JSON file is a list of slug strings)
        for idx, item in enumerate(obj):
            current_path = f"{path}[{idx}]" if path else f"[{idx}]"

            if isinstance(item, str):
                # Only validate strings if this is a top-level array (list of slugs)
                if is_top_level_array:
                    if not is_valid_name(item):
                        issues.append((file_path, f"Invalid string '{item}' at {current_path}"))
            else:
                # Recursively check non-string items (nested objects/arrays)
                issues.extend(check_object(item, file_path, line_offset, current_path, is_top_level_array=False))

    return issues


def check_json_file(file_path):
    """Check a single JSON file for naming violations."""
    issues = []

    try:
        # Use utf-8-sig to automatically handle UTF-8 BOM if present
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            data = json.loads(content)

        # Check the parsed JSON structure
        # Only validate array strings if the top-level is an array (list of slugs)
        is_top_level_array = isinstance(data, list)
        issues = check_object(data, file_path, is_top_level_array=is_top_level_array)

    except json.JSONDecodeError as e:
        issues.append((file_path, f"JSON parse error: {e}"))
    except Exception as e:
        issues.append((file_path, f"Error reading file: {e}"))

    return issues


def find_json_files(folder_path):
    """Find all .json files in the given folder and subfolders."""
    json_files = []
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist", file=sys.stderr)
        return []

    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory", file=sys.stderr)
        return []

    # Recursively find all .json files
    for json_file in folder.rglob('*.json'):
        json_files.append(json_file)

    return json_files


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_json_naming.py <folder_path>")
        print("\nChecks all JSON files in the folder for invalid object keys (attribute names).")
        print("Only lowercase letters, digits, and hyphens (-) are allowed for keys.")
        print("\nNote: String values (like display text) are NOT checked.")
        print("Exception: If the JSON file is a top-level array of strings, those are validated.")
        sys.exit(1)

    folder_path = sys.argv[1]

    print(f"Scanning for JSON files in: {folder_path}")
    json_files = find_json_files(folder_path)

    if not json_files:
        print("No JSON files found.")
        return

    print(f"Found {len(json_files)} JSON file(s)\n")

    total_issues = 0
    files_with_issues = 0

    for json_file in sorted(json_files):
        issues = check_json_file(json_file)

        if issues:
            files_with_issues += 1
            total_issues += len(issues)

            print(f"\n{json_file}:")
            for file_path, issue in issues:
                print(f"  - {issue}")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Total files scanned: {len(json_files)}")
    print(f"  Files with issues: {files_with_issues}")
    print(f"  Total issues found: {total_issues}")

    if total_issues > 0:
        sys.exit(1)
    else:
        print("\n✓ All JSON files passed validation!")


if __name__ == "__main__":
    main()
