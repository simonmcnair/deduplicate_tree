# Directory Tree Deduplication Script

This script compares two directory trees and removes files from the second tree that are identical to files in the first tree.

## How It Works

1. **Scans both directory trees** - Creates a map of all files with their relative paths and SHA256 checksums
2. **Compares files** - Finds files in the "tree to clean" that have matching paths AND matching checksums in the "safe tree"
3. **Removes duplicates** - Deletes the duplicate files from the "tree to clean" (leaving the safe tree untouched)
4. **Cleans up** - Optionally removes empty directories left behind

## Safety Features

- **Dry run mode** (enabled by default with `--dry-run`) - Shows what would be deleted without actually deleting anything
- **Confirmation prompt** - Asks for confirmation before deleting in live mode
- **SHA256 checksums** - Verifies files are truly identical, not just same name
- **Detailed logging** - Shows exactly what's happening
- **Read-only safe tree** - The reference tree is never modified

## Installation

No installation needed! Just requires Python 3.6 or later (which is standard on most systems).

## Usage

### Basic Syntax

```bash
python deduplicate_trees.py <safe_tree> <tree_to_clean> [options]
```

### Arguments

- `safe_tree` - The reference directory (will NOT be modified)
- `tree_to_clean` - The directory to remove duplicates from
- `--dry-run` - Show what would be deleted without actually deleting (HIGHLY RECOMMENDED FIRST!)
- `--verbose` or `-v` - Show detailed progress information

### Examples

#### 1. First, always do a dry run:
```bash
python deduplicate_trees.py /path/to/safe/folder /path/to/folder/to/clean --dry-run
```

This shows you exactly what would be deleted without actually deleting anything.

#### 2. Dry run with verbose output:
```bash
python deduplicate_trees.py /path/to/safe/folder /path/to/folder/to/clean --dry-run --verbose
```

Shows detailed progress as it scans and compares files.

#### 3. Actually delete the duplicates:
```bash
python deduplicate_trees.py /path/to/safe/folder /path/to/folder/to/clean
```

This will prompt for confirmation before deleting.

#### 4. Real-world example:
```bash
# Dry run first
python deduplicate_trees.py ~/Documents/master_backup ~/Documents/working_copy --dry-run

# If it looks good, run for real
python deduplicate_trees.py ~/Documents/master_backup ~/Documents/working_copy
```

## What Gets Deleted?

A file is deleted from the "tree to clean" if:
1. A file with the **same relative path** exists in the "safe tree"
2. The files have **identical SHA256 checksums** (meaning identical content)

## What Doesn't Get Deleted?

Files in the "tree to clean" are preserved if:
- They don't exist in the "safe tree" (different filename or location)
- They have different content (even with the same name)
- They're in a different directory structure

## Example Output

```
======================================================================
Directory Tree Deduplication
======================================================================
Safe tree (reference):  /home/user/backup
Tree to clean:          /home/user/working
Mode:                   DRY RUN
======================================================================

Step 1: Scanning safe tree...
  Total: 1523 files

Step 2: Scanning tree to clean...
  Total: 1687 files

Step 3: Finding duplicate files...

Found 1205 duplicate files

Step 4: Processing files...

======================================================================
DRY RUN - No files will actually be deleted
======================================================================

  [WOULD DELETE] documents/report.pdf (2.34 MB)
  [WOULD DELETE] images/photo1.jpg (1.12 MB)
  [WOULD DELETE] data/spreadsheet.xlsx (456.78 KB)
  ...

======================================================================
Summary:
  Files that would be deleted: 1205
  Total size that would be freed: 3.45 GB
======================================================================
```

## Use Cases

- **Backup management** - Remove files from a working copy that already exist in your backup
- **Version control** - Keep only modified files in a development folder
- **Storage optimization** - Free up space by removing redundant files
- **Archive cleanup** - Remove duplicates before archiving

## Safety Tips

1. **Always run with --dry-run first** to see what would happen
2. **Verify the output** before running without --dry-run
3. **Have backups** of important data (just in case!)
4. **Test with small directories first** to understand how it works
5. **Use absolute paths** to avoid confusion about which directories you're comparing

## Troubleshooting

### "Permission denied" errors
Make sure you have read permissions on the safe tree and read+write permissions on the tree to clean.

### Script is slow
Large directories with many files can take time to scan and checksum. Use `--verbose` to see progress.

### No duplicates found
- Check that the relative paths match between trees
- Verify that the directory structures are similar
- Files must have identical content (same checksum), not just the same name

## Technical Details

- **Checksum algorithm**: SHA256 (very reliable, cryptographically secure)
- **File reading**: Reads files in 4KB chunks (memory efficient for large files)
- **Path matching**: Uses relative paths from each tree's root
- **Empty directories**: Automatically removed after file deletion (in live mode only)

## License

Free to use and modify as needed!
