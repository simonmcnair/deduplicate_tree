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
            print(f"  {msg or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  {msg or 'Assertion failed'}")
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

        # Define paths using forward slashes (Path handles the conversion)
        expected_paths = {
            Path("file1.txt"),
            Path("file2.txt"),
            Path("subdir/file3.txt"),
            Path("subdir/nested/file4.txt")
        }

        #expected_paths = {"file1.txt", "file2.txt", "subdir/file3.txt", "subdir/nested/file4.txt"}
        #actual_paths = set(file_map.keys())
        actual_paths = {Path(p) for p in file_map.keys()}
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
            #deleted_rel_path = to_delete[0][1]
            #test.assert_equal(deleted_rel_path, "file1.txt", "file1.txt marked for deletion")
            #test.assert_equal(Path(deleted_rel_path), Path("file1.txt"), "file1.txt marked for deletion")
            clean_path, safe_path, checksum = to_delete[0]
            test.assert_true("file1.txt" in clean_path, "file1.txt marked for deletion")#!/usr/bin/env python3
"""
Black-box test suite for deduplicate_trees.py

Tests the script as users would run it - via command line only.
No imports from the script itself.

Run with: python test_deduplicate_trees.py
"""

import os
import sys
import tempfile
import subprocess
import hashlib
from pathlib import Path


class TestCase:
    """Simple test case class"""
    def __init__(self, name):
        self.name = name
        self.passed = 0
        self.failed = 0
    
    def assert_equal(self, actual, expected, msg=""):
        if actual == expected:
            self.passed += 1
            print(f"  [PASS] {msg or 'Assertion passed'}")
        else:
            self.failed += 1
            print(f"  [FAIL] {msg or 'Assertion failed'}")
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


def run_script(*args, input_text=None):
    """Helper to run the deduplicate script"""
    result = subprocess.run(
        [sys.executable, "deduplicate_trees.py"] + list(args),
        input=input_text,
        capture_output=True,
        text=True
    )
    return result


def test_help_and_version():
    """Test that --help works"""
    test = TestCase("test_help_and_version")
    
    result = run_script("--help")
    test.assert_equal(result.returncode, 0, "Help exits with code 0")
    test.assert_true("usage:" in result.stdout.lower(), "Help shows usage")
    test.assert_true("--dry-run" in result.stdout, "Help mentions --dry-run")
    test.assert_true("--verbose" in result.stdout, "Help mentions --verbose")
    
    return test.summary()


def test_missing_arguments():
    """Test error handling for missing arguments"""
    test = TestCase("test_missing_arguments")
    
    # No arguments
    result = run_script()
    test.assert_true(result.returncode != 0, "Exits with error when no args")
    
    # Only one argument
    result = run_script("/some/path")
    test.assert_true(result.returncode != 0, "Exits with error with only one arg")
    
    return test.summary()


def test_nonexistent_paths():
    """Test error handling for non-existent paths"""
    test = TestCase("test_nonexistent_paths")
    
    result = run_script("/nonexistent/path1", "/nonexistent/path2", "--dry-run")
    test.assert_true(result.returncode != 0, "Exits with error for non-existent paths")
    test.assert_true("does not exist" in result.stdout.lower(), "Error message mentions path doesn't exist")
    
    return test.summary()


def test_same_directory_error():
    """Test that using same directory for both args is rejected"""
    test = TestCase("test_same_directory_error")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = run_script(tmpdir, tmpdir, "--dry-run")
        test.assert_true(result.returncode != 0, "Exits with error for same directory")
        test.assert_true("same directory" in result.stdout.lower(), "Error mentions same directory")
    
    return test.summary()


def test_empty_directories():
    """Test with empty directories"""
    test = TestCase("test_empty_directories")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        safe_dir.mkdir()
        clean_dir.mkdir()
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        test.assert_equal(result.returncode, 0, "Handles empty directories")
        test.assert_true(
            "0 duplicate" in result.stdout.lower() or "no duplicates" in result.stdout.lower(),
            "Reports no duplicates for empty dirs"
        )
    
    return test.summary()


def test_no_duplicates():
    """Test when there are no duplicates"""
    test = TestCase("test_no_duplicates")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create different files
        create_test_file(safe_dir / "file1.txt", b"content A")
        create_test_file(clean_dir / "file2.txt", b"content B")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        test.assert_equal(result.returncode, 0, "Exits successfully")
        test.assert_true(
            "0 duplicate" in result.stdout.lower() or "no duplicates" in result.stdout.lower(),
            "Reports no duplicates"
        )
        
        # Files should still exist
        test.assert_true((safe_dir / "file1.txt").exists(), "Safe file still exists")
        test.assert_true((clean_dir / "file2.txt").exists(), "Clean file still exists")
    
    return test.summary()


def test_dry_run_preserves_files():
    """Test that dry-run doesn't actually delete files"""
    test = TestCase("test_dry_run_preserves_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create identical files
        create_test_file(safe_dir / "dup1.txt", b"duplicate content")
        create_test_file(clean_dir / "dup1.txt", b"duplicate content")
        create_test_file(safe_dir / "dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "dup2.txt", b"another duplicate")
        create_test_file(clean_dir / "unique.txt", b"unique content")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Exits successfully")
        test.assert_true("DRY RUN" in result.stdout, "Output mentions DRY RUN")
        test.assert_true("2" in result.stdout, "Output mentions 2 duplicates")
        
        # All files should still exist after dry run
        test.assert_true((clean_dir / "dup1.txt").exists(), "dup1.txt still exists")
        test.assert_true((clean_dir / "dup2.txt").exists(), "dup2.txt still exists")
        test.assert_true((clean_dir / "unique.txt").exists(), "unique.txt still exists")
        
        # Safe directory untouched
        test.assert_true((safe_dir / "dup1.txt").exists(), "Safe dup1.txt exists")
        test.assert_true((safe_dir / "dup2.txt").exists(), "Safe dup2.txt exists")
    
    return test.summary()


def test_actual_deletion():
    """Test that actual deletion works correctly"""
    test = TestCase("test_actual_deletion")
    
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
        
        # Run with actual deletion (auto-confirm with 'yes')
        result = run_script(str(safe_dir), str(clean_dir), input_text="yes\n")
        
        test.assert_equal(result.returncode, 0, "Exits successfully")
        test.assert_false("DRY RUN" in result.stdout, "Not a dry run")
        
        # Duplicate files should be deleted
        test.assert_false((clean_dir / "dup1.txt").exists(), "dup1.txt deleted")
        test.assert_false((clean_dir / "subdir/dup2.txt").exists(), "dup2.txt deleted")
        
        # Unique file should be preserved
        test.assert_true((clean_dir / "unique.txt").exists(), "unique.txt preserved")
        
        # Safe directory completely untouched
        test.assert_true((safe_dir / "dup1.txt").exists(), "Safe dup1.txt preserved")
        test.assert_true((safe_dir / "subdir/dup2.txt").exists(), "Safe dup2.txt preserved")
        test.assert_true((safe_dir / "safe_only.txt").exists(), "Safe only file preserved")
        
        # Empty subdirectory should be removed
        test.assert_false((clean_dir / "subdir").exists(), "Empty subdir removed")
    
    return test.summary()


def test_deletion_abort():
    """Test that answering 'no' to confirmation aborts deletion"""
    test = TestCase("test_deletion_abort")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create identical files
        create_test_file(safe_dir / "dup.txt", b"duplicate")
        create_test_file(clean_dir / "dup.txt", b"duplicate")
        
        # Run and answer 'no' to confirmation
        result = run_script(str(safe_dir), str(clean_dir), input_text="no\n")
        
        test.assert_equal(result.returncode, 0, "Exits successfully when aborted")
        test.assert_true("Aborted" in result.stdout or "aborted" in result.stdout, "Shows abort message")
        
        # File should still exist
        test.assert_true((clean_dir / "dup.txt").exists(), "File not deleted after abort")
    
    return test.summary()


def test_different_content_same_name():
    """Test that files with same name but different content are not deleted"""
    test = TestCase("test_different_content_same_name")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create files with same name but different content
        create_test_file(safe_dir / "file.txt", b"original content")
        create_test_file(clean_dir / "file.txt", b"modified content")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Exits successfully")
        test.assert_true(
            "0 duplicate" in result.stdout.lower() or "no duplicates" in result.stdout.lower(),
            "Reports no duplicates for different content"
        )
        test.assert_true((clean_dir / "file.txt").exists(), "Modified file preserved")
    
    return test.summary()


def test_nested_directories():
    """Test handling of nested directory structures"""
    test = TestCase("test_nested_directories")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create nested structure with duplicates
        create_test_file(safe_dir / "a/b/c/deep.txt", b"deep file")
        create_test_file(clean_dir / "a/b/c/deep.txt", b"deep file")
        create_test_file(safe_dir / "x/y/file.txt", b"another")
        create_test_file(clean_dir / "x/y/file.txt", b"another")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles nested directories")
        test.assert_true("2" in result.stdout, "Finds 2 duplicates in nested structure")
    
    return test.summary()


def test_verbose_mode():
    """Test that verbose mode produces more output"""
    test = TestCase("test_verbose_mode")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        create_test_file(safe_dir / "file.txt", b"content")
        create_test_file(clean_dir / "file.txt", b"content")
        
        # Run without verbose
        result_normal = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        # Run with verbose
        result_verbose = run_script(str(safe_dir), str(clean_dir), "--dry-run", "--verbose")
        
        test.assert_equal(result_verbose.returncode, 0, "Verbose mode exits successfully")
        test.assert_true(
            len(result_verbose.stdout) > len(result_normal.stdout),
            "Verbose mode produces more output"
        )
    
    return test.summary()


def test_special_characters_in_filenames():
    """Test handling of filenames with spaces and special characters"""
    test = TestCase("test_special_characters_in_filenames")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create files with special characters (Windows-compatible)
        create_test_file(safe_dir / "file with spaces.txt", b"content")
        create_test_file(clean_dir / "file with spaces.txt", b"content")
        create_test_file(safe_dir / "file-with-dashes.txt", b"more content")
        create_test_file(clean_dir / "file-with-dashes.txt", b"more content")
        create_test_file(safe_dir / "file_underscores_123.txt", b"numbers")
        create_test_file(clean_dir / "file_underscores_123.txt", b"numbers")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles special characters in filenames")
        test.assert_true("3" in result.stdout, "Finds 3 duplicates with special chars")
    
    return test.summary()


def test_binary_files():
    """Test handling of binary files (images, executables, etc.)"""
    test = TestCase("test_binary_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create binary files with non-text content
        binary_data1 = bytes([0x00, 0xFF, 0x42, 0x13, 0x37] * 100)
        binary_data2 = bytes(range(256)) * 10
        
        create_test_file(safe_dir / "binary1.bin", binary_data1)
        create_test_file(clean_dir / "binary1.bin", binary_data1)
        create_test_file(safe_dir / "binary2.dat", binary_data2)
        create_test_file(clean_dir / "binary2.dat", binary_data2)
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles binary files")
        test.assert_true("2" in result.stdout, "Finds 2 duplicate binary files")
    
    return test.summary()


def test_zero_byte_files():
    """Test handling of empty (zero-byte) files"""
    test = TestCase("test_zero_byte_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create multiple empty files
        create_test_file(safe_dir / "empty1.txt", b"")
        create_test_file(clean_dir / "empty1.txt", b"")
        create_test_file(safe_dir / "empty2.txt", b"")
        create_test_file(clean_dir / "empty2.txt", b"")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles zero-byte files")
        test.assert_true("2" in result.stdout, "Finds 2 duplicate empty files")
    
    return test.summary()


def test_large_files():
    """Test handling of larger files (10MB+)"""
    test = TestCase("test_large_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create 10MB files
        large_data = b"x" * (10 * 1024 * 1024)
        
        create_test_file(safe_dir / "large.bin", large_data)
        create_test_file(clean_dir / "large.bin", large_data)
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles large files")
        test.assert_true("1" in result.stdout, "Finds 1 duplicate large file")
        test.assert_true("10" in result.stdout or "MB" in result.stdout, "Shows file size")
    
    return test.summary()


def test_different_paths_same_content():
    """Test that files in different relative paths are NOT deleted even if content matches"""
    test = TestCase("test_different_paths_same_content")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Same content but different paths
        create_test_file(safe_dir / "dirA/file.txt", b"same content")
        create_test_file(clean_dir / "dirB/file.txt", b"same content")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Exits successfully")
        test.assert_true(
            "0 duplicate" in result.stdout.lower() or "no duplicates" in result.stdout.lower(),
            "Does not delete files in different paths"
        )
        test.assert_true((clean_dir / "dirB/file.txt").exists(), "File in different path preserved")
    
    return test.summary()


def test_partial_directory_overlap():
    """Test when directories partially overlap (some files match, some don't)"""
    test = TestCase("test_partial_directory_overlap")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create partial overlap
        create_test_file(safe_dir / "subdir/file1.txt", b"content1")
        create_test_file(clean_dir / "subdir/file1.txt", b"content1")  # duplicate
        create_test_file(safe_dir / "subdir/file2.txt", b"content2")
        create_test_file(clean_dir / "subdir/file2.txt", b"modified2")  # different
        create_test_file(clean_dir / "subdir/file3.txt", b"content3")  # only in clean
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles partial overlap")
        test.assert_true("1" in result.stdout, "Finds 1 duplicate in partial overlap")
        
        # Verify files still exist (dry run)
        test.assert_true((clean_dir / "subdir/file1.txt").exists(), "Duplicate still exists in dry run")
        test.assert_true((clean_dir / "subdir/file2.txt").exists(), "Modified file exists")
        test.assert_true((clean_dir / "subdir/file3.txt").exists(), "Unique file exists")
    
    return test.summary()


def test_files_only_in_safe_directory():
    """Test that files only in safe directory are ignored"""
    test = TestCase("test_files_only_in_safe_directory")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Files only in safe
        create_test_file(safe_dir / "safe_only1.txt", b"content1")
        create_test_file(safe_dir / "safe_only2.txt", b"content2")
        create_test_file(safe_dir / "subdir/safe_only3.txt", b"content3")
        
        # One file in both
        create_test_file(safe_dir / "both.txt", b"shared")
        create_test_file(clean_dir / "both.txt", b"shared")
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles safe-only files")
        test.assert_true("1" in result.stdout, "Finds only 1 duplicate (shared file)")
        
        # Safe directory should be completely untouched
        test.assert_true((safe_dir / "safe_only1.txt").exists(), "Safe-only file 1 exists")
        test.assert_true((safe_dir / "safe_only2.txt").exists(), "Safe-only file 2 exists")
        test.assert_true((safe_dir / "subdir/safe_only3.txt").exists(), "Safe-only file 3 exists")
    
    return test.summary()


def test_many_files():
    """Test with a larger number of files (performance/scalability check)"""
    test = TestCase("test_many_files")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create 100 duplicate files
        num_files = 100
        for i in range(num_files):
            content = f"file content {i}".encode()
            create_test_file(safe_dir / f"file_{i}.txt", content)
            create_test_file(clean_dir / f"file_{i}.txt", content)
        
        result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
        
        test.assert_equal(result.returncode, 0, "Handles many files")
        test.assert_true(str(num_files) in result.stdout, f"Finds {num_files} duplicates")
    
    return test.summary()


def test_readonly_file_in_safe():
    """Test that read-only files in safe directory work correctly"""
    test = TestCase("test_readonly_file_in_safe")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        safe_dir = tmpdir / "safe"
        clean_dir = tmpdir / "clean"
        
        # Create files
        safe_file = safe_dir / "readonly.txt"
        create_test_file(safe_file, b"content")
        create_test_file(clean_dir / "readonly.txt", b"content")
        
        # Make safe file read-only
        safe_file.chmod(0o444)
        
        try:
            result = run_script(str(safe_dir), str(clean_dir), "--dry-run")
            
            test.assert_equal(result.returncode, 0, "Handles read-only files in safe dir")
            test.assert_true("1" in result.stdout, "Finds duplicate with read-only safe file")
        finally:
            # Restore permissions for cleanup
            safe_file.chmod(0o644)
    
    return test.summary()


def main():
    print("=" * 70)
    print("Running Black-Box Test Suite for deduplicate_trees.py")
    print("=" * 70)
    print()
    
    all_passed = True
    
    all_passed &= test_help_and_version()
    print()
    
    all_passed &= test_missing_arguments()
    print()
    
    all_passed &= test_nonexistent_paths()
    print()
    
    all_passed &= test_same_directory_error()
    print()
    
    all_passed &= test_empty_directories()
    print()
    
    all_passed &= test_no_duplicates()
    print()
    
    all_passed &= test_dry_run_preserves_files()
    print()
    
    all_passed &= test_actual_deletion()
    print()
    
    all_passed &= test_deletion_abort()
    print()
    
    all_passed &= test_different_content_same_name()
    print()
    
    all_passed &= test_nested_directories()
    print()
    
    all_passed &= test_verbose_mode()
    print()
    
    all_passed &= test_special_characters_in_filenames()
    print()
    
    all_passed &= test_binary_files()
    print()
    
    all_passed &= test_zero_byte_files()
    print()
    
    all_passed &= test_large_files()
    print()
    
    all_passed &= test_different_paths_same_content()
    print()
    
    all_passed &= test_partial_directory_overlap()
    print()
    
    all_passed &= test_files_only_in_safe_directory()
    print()
    
    all_passed &= test_many_files()
    print()
    
    all_passed &= test_readonly_file_in_safe()
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
    test.assert_true(checksum is not None, "Checksum is present")
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
