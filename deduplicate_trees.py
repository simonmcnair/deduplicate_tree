#!/usr/bin/env python3
"""
Directory Tree Deduplication Script

This script compares two directory trees and removes files from the second tree
that are identical to files in the first tree (based on SHA256 checksums).

Usage:
    python deduplicate_trees.py <safe_tree> <tree_to_clean> [--dry-run] [--verbose]

Arguments:
    safe_tree       : The reference directory tree (will NOT be modified)
    tree_to_clean   : The directory tree to remove duplicates from
    --dry-run       : Show what would be deleted without actually deleting
    --verbose       : Show detailed progress information
"""

import os
import sys
import hashlib
import argparse
from pathlib import Path
from datetime import datetime


def calculate_sha256(filepath):
    """Calculate SHA256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            # Read in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None


def scan_directory_tree(root_path, verbose=False):
    """
    Scan a directory tree and create a mapping of relative paths to checksums.
    
    Returns:
        dict: {relative_path: (absolute_path, checksum)}
    """
    file_map = {}
    root = Path(root_path).resolve()
    
    if verbose:
        print(f"\nScanning {root}...")
    
    file_count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        print(f" scanning {dirpath}")
        for filename in filenames:
            filepath = Path(dirpath) / filename
            relative_path = filepath.relative_to(root)
            
            if verbose print(f"Scanning: {filepath}")
            checksum = calculate_sha256(filepath)
            if verbose print(f"{filename} checksum is {checksum}")
            if checksum:
                file_map[str(relative_path)] = (str(filepath), checksum)
                file_count += 1
                if verbose and file_count % 100 == 0:
                    print(f"  Scanned {file_count} files...")
    
    if verbose:
        print(f"  Total: {file_count} files")
    
    return file_map


def find_duplicates(safe_map, clean_map, verbose=False):
    """
    Find files in clean_map that are identical to files in safe_map.
    
    Returns:
        list: List of (filepath, relative_path) tuples to delete
    """
    to_delete = []
    
    for rel_path, (clean_filepath, clean_checksum) in clean_map.items():
        if rel_path in safe_map:
            safe_filepath, safe_checksum = safe_map[rel_path]
            
            if clean_checksum == safe_checksum:
                #to_delete.append((clean_filepath, rel_path))
                to_delete.append((clean_filepath, safe_filepath, clean_checksum))
                if verbose:
                    print(f"  Match found: {rel_path}")
    
    return to_delete


def format_size(size_bytes):
    """Format bytes into human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def delete_files(to_delete, dry_run=True):
    """
    Delete files from the list.
    
    Args:
        to_delete: List of (filepath, relative_path) tuples
        dry_run: If True, only show what would be deleted
    """
    total_size = 0
    deleted_count = 0
    
    print(f"\n{'=' * 70}")
    if dry_run:
        print("DRY RUN - No files will actually be deleted")
    else:
        print("DELETING FILES")
    print(f"{'=' * 70}\n")

  # for filepath, rel_path in to_delete:
    for clean_path, safe_path, checksum in to_delete:
        try:
            file_size = os.path.getsize(clean_path)
            total_size += file_size
            
            # Display sequential information for ease of reading
            print(f"  [REFERENCE]    {safe_path}")
            print(f"  {'[WOULD DELETE]' if dry_run else '[DELETING]'} {clean_path}")
            print(f"  [SHA256]:{checksum}  [SIZE]:{format_size(file_size)}\n")
         
            if not dry_run:
                os.remove(clean_path)
                deleted_count += 1
        except Exception as e:
            print(f"  ERROR with {rel_path}: {e}")
    
    print(f"\n{'=' * 70}")
    print(f"Summary:")
    print(f"  Files {'that would be' if dry_run else ''} deleted: {len(to_delete)}")
    print(f"  Total size {'that would be' if dry_run else ''} freed: {format_size(total_size)}")
    if not dry_run:
        print(f"  Successfully deleted: {deleted_count}")
    print(f"{'=' * 70}\n")


def cleanup_empty_directories(root_path, dry_run=True, verbose=False):
    """
    Remove empty directories after file deletion.
    """
    if dry_run:
        return
    
    removed_dirs = []
    root = Path(root_path).resolve()
    
    # Walk bottom-up so we can remove empty child directories first
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        # Skip the root directory itself
        if dirpath == str(root):
            continue
        
        # Check if directory is empty
        try:
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
                removed_dirs.append(dirpath)
                if verbose:
                    print(f"  Removed empty directory: {Path(dirpath).relative_to(root)}")
        except Exception as e:
            if verbose:
                print(f"  Could not remove {dirpath}: {e}")
    
    if removed_dirs:
        print(f"\nRemoved {len(removed_dirs)} empty directories")


def main():
    parser = argparse.ArgumentParser(
        description='Compare two directory trees and remove duplicate files from the second tree.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run (safe, shows what would happen):
  python deduplicate_trees.py /path/to/safe /path/to/clean --dry-run

  # Actually delete duplicates:
  python deduplicate_trees.py /path/to/safe /path/to/clean

  # Verbose mode to see detailed progress:
  python deduplicate_trees.py /path/to/safe /path/to/clean --dry-run --verbose
        """
    )
    
    parser.add_argument('safe_tree', help='Reference directory tree (will NOT be modified)')
    parser.add_argument('tree_to_clean', help='Directory tree to remove duplicates from')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting (RECOMMENDED FIRST)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed progress information')
    
    args = parser.parse_args()
    
    # Validate paths
    safe_path = Path(args.safe_tree)
    clean_path = Path(args.tree_to_clean)
    
    if not safe_path.exists():
        print(f"Error: Safe tree path does not exist: {safe_path}")
        sys.exit(1)
    
    if not clean_path.exists():
        print(f"Error: Tree to clean path does not exist: {clean_path}")
        sys.exit(1)
    
    if not safe_path.is_dir():
        print(f"Error: Safe tree path is not a directory: {safe_path}")
        sys.exit(1)
    
    if not clean_path.is_dir():
        print(f"Error: Tree to clean path is not a directory: {clean_path}")
        sys.exit(1)
    
    # Check if paths are the same
    if safe_path.resolve() == clean_path.resolve():
        print("Error: Both paths point to the same directory!")
        sys.exit(1)
    
    print(f"\n{'=' * 70}")
    print("Directory Tree Deduplication")
    print(f"{'=' * 70}")
    print(f"Safe tree (reference):  {safe_path.resolve()}")
    print(f"Tree to clean:          {clean_path.resolve()}")
    print(f"Mode:                   {'DRY RUN' if args.dry_run else 'LIVE DELETE'}")
    print(f"{'=' * 70}\n")
    
    if not args.dry_run:
        response = input("WARNING: This will DELETE files. Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    # Scan both trees
    print("Step 1: Scanning safe tree...")
    safe_map = scan_directory_tree(safe_path, args.verbose)
    
    print("\nStep 2: Scanning tree to clean...")
    clean_map = scan_directory_tree(clean_path, args.verbose)
    
    # Find duplicates
    print("\nStep 3: Finding duplicate files...")
    to_delete = find_duplicates(safe_map, clean_map, args.verbose)
    
    print(f"\nFound {len(to_delete)} duplicate files")
    
    if not to_delete:
        print("No duplicates found. Nothing to do.")
        sys.exit(0)
    
    # Delete files
    print("\nStep 4: Processing files...")
    delete_files(to_delete, args.dry_run)
    
    # Clean up empty directories
    if not args.dry_run:
        print("\nStep 5: Cleaning up empty directories...")
        cleanup_empty_directories(clean_path, args.dry_run, args.verbose)
    
    if args.dry_run:
        print("\n" + "=" * 70)
        print("This was a DRY RUN. No files were actually deleted.")
        print("To actually delete files, run again without --dry-run")
        print("=" * 70)


if __name__ == "__main__":
    main()
