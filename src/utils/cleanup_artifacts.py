#!/usr/bin/env python

"""
Utility script to clean up test artifacts
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
import time
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parents[2].absolute()
sys.path.append(str(project_root))

ARTIFACTS_DIR = project_root / "artifacts"
TEST_RESULTS_DIR = ARTIFACTS_DIR / "test_results"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
HTML_DIR = ARTIFACTS_DIR / "html"
DEBUG_INFO_DIR = ARTIFACTS_DIR / "debug_info"

def get_dir_size(path):
    """Get the size of a directory in bytes"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp):  # Some files might be symlinks that no longer exist
                total_size += os.path.getsize(fp)
    return total_size

def format_size(size_bytes):
    """Format size in bytes to human-readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def list_artifact_directories(category=None, older_than=None):
    """List artifact directories with their sizes
    
    Args:
        category: Optional category to filter (test_results, screenshots, html)
        older_than: Optional age filter in days
    """
    dirs_to_check = []
    
    if category is None or category == 'test_results':
        if TEST_RESULTS_DIR.exists():
            dirs_to_check.append(("test_results", TEST_RESULTS_DIR))
    
    if category is None or category == 'screenshots':
        if SCREENSHOTS_DIR.exists():
            dirs_to_check.append(("screenshots", SCREENSHOTS_DIR))
    
    if category is None or category == 'html':
        if HTML_DIR.exists():
            dirs_to_check.append(("html", HTML_DIR))
    
    if category is None or category == 'debug_info':
        if DEBUG_INFO_DIR.exists():
            dirs_to_check.append(("debug_info", DEBUG_INFO_DIR))
    
    results = []
    age_cutoff = None
    if older_than:
        age_cutoff = datetime.now() - timedelta(days=older_than)
    
    total_size = 0
    
    # Print header
    print("\n{:<5} {:<15} {:<30} {:<15} {:<20}".format("#", "Category", "Directory", "Size", "Modified"))
    print("-" * 90)
    
    item_num = 1
    for cat, dir_path in dirs_to_check:
        try:
            # For test_results, list individual test runs
            if cat == "test_results" and dir_path.exists():
                for test_dir in dir_path.iterdir():
                    if test_dir.is_dir():
                        size = get_dir_size(test_dir)
                        mod_time = datetime.fromtimestamp(test_dir.stat().st_mtime)
                        
                        # Skip if not old enough
                        if age_cutoff and mod_time > age_cutoff:
                            continue
                            
                        size_str = format_size(size)
                        mod_time_str = mod_time.strftime('%Y-%m-%d %H:%M')
                        
                        print("{:<5} {:<15} {:<30} {:<15} {:<20}".format(
                            item_num, cat, test_dir.name, size_str, mod_time_str))
                        
                        results.append({
                            'num': item_num,
                            'category': cat,
                            'path': test_dir,
                            'size': size,
                            'mod_time': mod_time
                        })
                        
                        total_size += size
                        item_num += 1
            else:
                # For screenshots and html, just list the whole directory
                if dir_path.exists():
                    size = get_dir_size(dir_path)
                    if size > 0:  # Only show non-empty directories
                        mod_time = datetime.fromtimestamp(dir_path.stat().st_mtime)
                        
                        # Skip if not old enough
                        if age_cutoff and mod_time > age_cutoff:
                            continue
                            
                        size_str = format_size(size)
                        mod_time_str = mod_time.strftime('%Y-%m-%d %H:%M')
                        
                        print("{:<5} {:<15} {:<30} {:<15} {:<20}".format(
                            item_num, cat, cat, size_str, mod_time_str))
                        
                        results.append({
                            'num': item_num,
                            'category': cat,
                            'path': dir_path,
                            'size': size,
                            'mod_time': mod_time
                        })
                        
                        total_size += size
                        item_num += 1
        except Exception as e:
            print(f"Error processing {cat}: {str(e)}")
    
    print("-" * 90)
    print(f"Total size: {format_size(total_size)}\n")
    
    return results

def delete_artifacts(dirs_to_delete):
    """Delete specified artifact directories"""
    deleted_size = 0
    
    for dir_info in dirs_to_delete:
        path = dir_info['path']
        try:
            if path.exists():
                size = dir_info['size']
                
                if path.is_file():
                    os.remove(path)
                    print(f"Deleted file: {path.name} ({format_size(size)})")
                else:
                    shutil.rmtree(path)
                    print(f"Deleted directory: {path.name} ({format_size(size)})")
                    
                deleted_size += size
        except Exception as e:
            print(f"Error deleting {path}: {str(e)}")
    
    print(f"\nTotal space freed: {format_size(deleted_size)}")

def delete_all_by_category(category, older_than=None):
    """Delete all artifacts in a category"""
    if category not in ["test_results", "screenshots", "html", "debug_info", "all"]:
        print(f"Invalid category: {category}")
        return
        
    categories = [category] if category != "all" else ["test_results", "screenshots", "html", "debug_info"]
    all_dirs = []
    
    for cat in categories:
        all_dirs.extend(list_artifact_directories(cat, older_than))
    
    if not all_dirs:
        print(f"No artifacts found{'.' if not older_than else f' older than {older_than} days.'}")
        return
        
    total_size = sum(d['size'] for d in all_dirs)
    
    print(f"\nAbout to delete {len(all_dirs)} directories or files, totaling {format_size(total_size)}.")
    confirmation = input("Are you sure? (y/n): ").lower()
    
    if confirmation == 'y':
        delete_artifacts(all_dirs)
    else:
        print("Operation cancelled.")

def interactive_cleanup():
    """Interactive cleanup mode"""
    print("\nTeatime Artifact Cleanup Utility\n")
    
    # List all artifact directories
    all_dirs = list_artifact_directories()
    
    if not all_dirs:
        print("No artifacts found.")
        return
    
    # Ask user what to delete
    print("\nEnter the numbers of directories to delete (comma-separated), or:")
    print("  'all' to delete everything")
    print("  'screenshots' to delete all screenshots")
    print("  'html' to delete all HTML files")
    print("  'test_results' to delete all test results")
    print("  'debug_info' to delete all debug information")
    print("  'none' or empty to cancel")
    
    choice = input("\nYour choice: ").strip().lower()
    
    if not choice or choice == 'none':
        print("Operation cancelled.")
        return
        
    if choice == 'all':
        delete_all_by_category('all')
        return
        
    if choice in ['screenshots', 'html', 'test_results', 'debug_info']:
        delete_all_by_category(choice)
        return
    
    # Process individual selections
    try:
        selected_nums = [int(x.strip()) for x in choice.split(',') if x.strip().isdigit()]
        if not selected_nums:
            print("No valid selections. Operation cancelled.")
            return
            
        dirs_to_delete = [d for d in all_dirs if d['num'] in selected_nums]
        
        if not dirs_to_delete:
            print("No valid selections. Operation cancelled.")
            return
            
        total_size = sum(d['size'] for d in dirs_to_delete)
        
        print(f"\nAbout to delete {len(dirs_to_delete)} directories or files, totaling {format_size(total_size)}.")
        confirmation = input("Are you sure? (y/n): ").lower()
        
        if confirmation == 'y':
            delete_artifacts(dirs_to_delete)
        else:
            print("Operation cancelled.")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        print("Operation cancelled.")

def main():
    parser = argparse.ArgumentParser(description="Clean up test artifacts")
    parser.add_argument("--category", choices=["test_results", "screenshots", "html", "debug_info", "all"], 
                        help="Category to clean up (default: interactive mode)")
    parser.add_argument("--older-than", type=int, help="Only clean up artifacts older than X days")
    parser.add_argument("--list", action="store_true", help="Only list artifacts, don't delete anything")
    
    args = parser.parse_args()
    
    if args.list:
        list_artifact_directories(args.category, args.older_than)
        return
        
    if args.category:
        delete_all_by_category(args.category, args.older_than)
    else:
        interactive_cleanup()

if __name__ == "__main__":
    main()