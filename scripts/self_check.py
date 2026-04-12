#!/usr/bin/env python3
"""Self check script for competition."""

import sys
import argparse
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def check_directory_structure():
    """Check directory structure."""
    print("Checking directory structure...")
    
    required_dirs = [
        "configs",
        "src",
        "experiments",
        "tests",
        "results/runs",
        "results/comparisons",
        "results/finals",
        "results/tests",
        "scripts"
    ]
    
    all_exist = True
    for directory in required_dirs:
        path = Path(directory)
        if not path.exists():
            print(f"Missing directory: {directory}")
            all_exist = False
        else:
            print(f"Directory exists: {directory}")
    
    return all_exist

def check_required_files():
    """Check required files."""
    print("\nChecking required files...")
    
    required_files = [
        "main.py",
        "README.md",
        "requirements.txt",
        "experiments/run_demo.py",
        "experiments/compare_strategies.py",
        "scripts/self_check.py",
        "scripts/export_final_package.py"
    ]
    
    all_exist = True
    for file in required_files:
        path = Path(file)
        if not path.exists():
            print(f"Missing file: {file}")
            all_exist = False
        else:
            print(f"File exists: {file}")
    
    return all_exist

def check_communication_module():
    """Check communication module."""
    print("\nChecking communication module...")
    
    communication_files = [
        "src/communication/__init__.py",
        "src/communication/network_manager.py",
        "src/communication/message_dispatch.py",
        "src/communication/communication_logger.py"
    ]
    
    all_exist = True
    for file in communication_files:
        path = Path(file)
        if not path.exists():
            print(f"Missing file: {file}")
            all_exist = False
        else:
            print(f"File exists: {file}")
    
    return all_exist

def main():
    """Run self check."""
    parser = argparse.ArgumentParser(description="Self check script for competition")
    args = parser.parse_args()
    
    print("=== Self Check for Competition ===")
    
    checks = [
        check_directory_structure(),
        check_required_files(),
        check_communication_module()
    ]
    
    print("\n=== Self Check Results ===")
    if all(checks):
        print("All checks passed! The system is ready for competition.")
    else:
        print("Some checks failed. Please fix the issues above.")

if __name__ == "__main__":
    main()
