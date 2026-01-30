#!/usr/bin/env python3
"""
Test suite for deduplicate_trees.py

Run with: python test_deduplicate_trees.py
"""

import os
import sys
import tempfile
import shutil
import hashlib
from pathlib import Path
import subprocess

# Import the functions we want to test
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deduplicate_trees import (
    calculate_sha256,
    scan_directory_tree,
    find_duplicates,
    cleanup_empty_directories
)


class TestCase:
    """Simple test case class"""
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
    
    def assert_equal(self, actual, expected, msg=""):
        if actual == expected:
            self.passed += 1
            print(f"  ✓ {msg or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  ✗ {msg or 'Assertion failed'}")
            print(f"    Expected: {expected}")
            print(f"    Got: {actual}")
    
    def assert_true(self, condition, msg=""):
        self.assert_equal(condition, True, msg)
    
    def assert_false(self, condition, msg=""):
        self.assert_equal(condition, False, msg)
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{self.name}: {self.passed}/{total} passed")
        return self.failed == 0


def create_test_file(path, content):
    """Helper to create a test file with specific content"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'wb') as f:
        f.write(content)


def test_calculate_sha256():
    """Test SHA256 calculation"""
    test = TestCase("test_calculate_sha256")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Test 1: Empty file
        empty_file = tmpdir / "empty.txt"
        create_test_file(empty_file, b"")
        expected_hash = hashlib.sha256(b"").hexdigest()
        actual_hash = calculate_sha256(empty_file)
        test.assert_equal(actual_hash, expected_hash, "Empty file hash")
        
        # Test 2: Small file
        small_file = tmpdir / "small.txt"
        content = b"Hello, World!"
        create_test_file(small_file, content)
        expected_hash = hashlib.sha256(content).hexdigest()
        actual_hash = calculate_sha256(small_file)
        test.assert_equal(actual_hash, expected_hash, "Small file hash")
        
        # Test 3: Larger file (multiple chunks)
        large_file = tmpdir / "large.txt"
        content = b"x" * 10000  # 10KB
        create_test_file(large_file, content)
        expected_hash = hashlib.sha256(content).hexdigest()
        actual_hash = calculate_sha256(large_file)
        test.assert_equal(actual_hash, expected_hash, "Large file hash")
        
        # Test 4: Non-existent file
        nonexistent = tmpdir / "does_not_exist.txt"
        result = calculate_sha256(nonexistent)
        test.assert_equal(result, None, "Non-existent file returns None")
    
    return test.summary()


def test_scan_directory_tree():
    """Test directory tree scanning"""
    test = TestCase("test_scan_directory_tree")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test structure
        create_test_file(tmpdir / "file1.txt", b"content1")
        create_test_file(tmpdir / "file2.txt", b"content2")
        create_test_file(tmpdir / "subdir/file3.txt", b"content3")
        create_test_file(tmpdir / "subdir/nested/file4.txt", b"content4")
        
        # Scan the tree
        file_map = scan_directory_tree(tmpdir, verbose=False)
        
        # Test 1: Correct number of files
        test.assert_equal(len(file_map), 4, "Found 4 files")
        
        # Test 2: Relative paths are correct
        expected_paths = {"file1.txt", "file2.txt", "subdir/file3.txt", "subdir/nested/file4.txt"}
        actual_paths = set(file_map.keys())
        test.assert_equal(actual_paths, expected_paths, "Correct relative paths")
        
        # Test 3: Checksums are calculated
        for rel_path, (abs_path, checksum) in file_map.items():
            test.assert_true(checksum is not None, f"Checksum exists for {rel_path}")
            test.assert_equal(len(checksum), 64, f"Checksum is SHA256 length for {rel_path}")
    
    return test.summary()


def test_find_duplicates():
    """Test duplicate detection"""
    test = TestCase("test_find_duplicates")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create identical files
        create_test_file(safe_dir / "file1.txt", b"same content")
        create_test_file(clean_dir / "file1.txt", b"same content")
        
        # Create different files with same name
        create_test_file(safe_dir / "file2.txt", b"original")
        create_test_file(clean_dir / "file2.txt", b"modified")
        
        # Create file only in clean
        create_test_file(clean_dir / "file3.txt", b"unique")
        
        # Create file only in safe
        create_test_file(safe_dir / "file4.txt", b"reference")
        
        # Scan both trees
        safe_map = scan_directory_tree(safe_dir)
        clean_map = scan_directory_tree(clean_dir)
        
        # Find duplicates
        to_delete = find_duplicates(safe_map, clean_map)
        
        # Test 1: Only one duplicate (file1.txt)
        test.assert_equal(len(to_delete), 1, "Found exactly 1 duplicate")
        
        # Test 2: Correct file marked for deletion
        if to_delete:
            deleted_rel_path = to_delete[0][1]
            test.assert_equal(deleted_rel_path, "file1.txt", "file1.txt marked for deletion")
    
    return test.summary()


def test_integration_dry_run():
    """Integration test with dry run"""
    test = TestCase("test_integration_dry_run")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create test structure
        create_test_file(safe_dir / "dup1.txt", b"duplicate content")
        create_test_file(clean_dir / "dup1.txt", b"duplicate content")
        create_test_file(safe_dir / "dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "unique.txt", b"unique content")
        
        # Run the script in dry-run mode
        result = subprocess.run(
            [sys.executable, "deduplicate_trees.py", str(safe_dir), str(clean_dir), "--dry-run"],
            capture_output=True,
            text=True
        )
        
        # Test 1: Script exits successfully
        test.assert_equal(result.returncode, 0, "Script exits with code 0")
        
        # Test 2: Files still exist after dry run
        test.assert_true((clean_dir / "dup1.txt").exists(), "dup1.txt still exists")
        test.assert_true((clean_dir / "dup2.txt").exists(), "dup2.txt still exists")
        test.assert_true((clean_dir / "unique.txt").exists(), "unique.txt still exists")
        
        # Test 3: Output mentions dry run
        test.assert_true("DRY RUN" in result.stdout, "Output mentions DRY RUN")
        
        # Test 4: Output shows 2 duplicates would be deleted
        test.assert_true("2" in result.stdout, "Output mentions 2 files")
    
    return test.summary()


def test_integration_live_delete():
    """Integration test with actual deletion"""
    test = TestCase("test_integration_live_delete")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create test structure
        create_test_file(safe_dir / "dup1.txt", b"duplicate content")
        create_test_file(clean_dir / "dup1.txt", b"duplicate content")
        create_test_file(safe_dir / "subdir/dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "subdir/dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "unique.txt", b"unique content")
        create_test_file(safe_dir / "safe_only.txt", b"safe content")
        
        # Run the script with actual deletion (auto-confirm with 'yes')
        result = subprocess.run(
            [sys.executable, "deduplicate_trees.py", str(safe_dir), str(clean_dir)],
            input="yes\n",
            capture_output=True,
            text=True
        )
        
        # Test 1: Script exits successfully
        test.assert_equal(result.returncode, 0, "Script exits with code 0")
        
        # Test 2: Duplicate files are deleted
        test.assert_false((clean_dir / "dup1.txt").exists(), "dup1.txt deleted")
        test.assert_false((clean_dir / "subdir/dup2.txt").exists(), "dup2.txt deleted")
        
        # Test 3: Unique file still exists
        test.assert_true((clean_dir / "unique.txt").exists(), "unique.txt preserved")
        
        # Test 4: Safe directory untouched
        test.assert_true((safe_dir / "dup1.txt").exists(), "Safe dup1.txt preserved")
        test.assert_true((safe_dir / "subdir/dup2.txt").exists(), "Safe dup2.txt preserved")
        test.assert_true((safe_dir / "safe_only.txt").exists(), "Safe only file preserved")
        
        # Test 5: Empty subdirectory removed
        test.assert_false((clean_dir / "subdir").exists(), "Empty subdir removed")
    
    return test.summary()


def test_edge_cases():
    """Test edge cases and error conditions"""
    test = TestCase("test_edge_cases")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Test 1: Empty directories
        safe_dir = tmpdir / "empty_safe"
        clean_dir = tmpdir / "empty_clean"
        safe_dir.mkdir()
        clean_dir.mkdir()
        
        result = subprocess.run(
            [sys.executable, "deduplicate_trees.py", str(safe_dir), str(clean_dir), "--dry-run"],
            capture_output=True,
            text=True
        )
        test.assert_equal(result.returncode, 0, "Handles empty directories")
        test.assert_true("0 duplicate files" in result.stdout or "No duplicates found" in result.stdout, 
                        "Reports no duplicates for empty dirs")
        
        # Test 2: Non-existent directory
        result = subprocess.run(
            [sys.executable, "deduplicate_trees.py", "/nonexistent/path1", "/nonexistent/path2", "--dry-run"],
            capture_output=True,
            text=True
        )
        test.assert_true(result.returncode != 0, "Exits with error for non-existent path")
        
        # Test 3: Same directory for both args
        same_dir = tmpdir / "same"
        same_dir.mkdir()
        result = subprocess.run(
            [sys.executable, "deduplicate_trees.py", str(same_dir), str(same_dir), "--dry-run"],
            capture_output=True,
            text=True
        )
        test.assert_true(result.returncode != 0, "Exits with error for same directory")
    
    return test.summary()


def main():
    print("=" * 70)
    print("Running Test Suite for deduplicate_trees.py")
    print("=" * 70)
    print()
    
    all_passed = True
    
    all_passed &= test_calculate_sha256()
    print()
    
    all_passed &= test_scan_directory_tree()
    print()
    
    all_passed &= test_find_duplicates()
    print()
    
    all_passed &= test_integration_dry_run()
    print()
    
    all_passed &= test_integration_live_delete()
    print()
    
    all_passed &= test_edge_cases()
    print()
    
    print("=" * 70)
    if all_passed:
        print("ALL TESTS PASSED")
        print("=" * 70)
        return 0
    else:
        print("SOME TESTS FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
