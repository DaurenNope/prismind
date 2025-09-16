#!/usr/bin/env python3
"""
Script to update and manage project dependencies.

This script helps manage project dependencies by:
1. Updating requirements files
2. Checking for outdated packages
3. Generating dependency reports
"""

import subprocess
import sys
from pathlib import Path

def run_command(command: str, cwd: Path = None) -> tuple[bool, str]:
    """Run a shell command and return (success, output)."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            check=True,
            text=True,
            capture_output=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr}"

def check_outdated():
    """Check for outdated packages."""
    print("\nChecking for outdated packages...")
    success, output = run_command("pip list --outdated --format=freeze")
    if success:
        if output.strip():
            print("Outdated packages found:")
            print(output)
        else:
            print("All packages are up to date.")
    else:
        print(f"Failed to check for outdated packages: {output}")

def update_requirements():
    """Update requirements files."""
    print("\nUpdating requirements files...")
    
    # Update requirements.txt
    print("Updating requirements.txt...")
    success, _ = run_command(
        "pip freeze --exclude-editable | grep -v '^pkg-resources==' > requirements.txt"
    )
    if success:
        print("requirements.txt updated successfully.")
    else:
        print("Failed to update requirements.txt")
    
    # Update requirements-dev.txt
    print("\nUpdating requirements-dev.txt...")
    success, _ = run_command(
        "pip freeze --exclude-editable | grep -v '^pkg-resources==' > requirements-dev.txt"
    )
    if success:
        print("requirements-dev.txt updated successfully.")
    else:
        print("Failed to update requirements-dev.txt")

def generate_dependency_report():
    """Generate a dependency report."""
    print("\nGenerating dependency report...")
    success, output = run_command("pipdeptree")
    if success:
        with open("dependency-report.txt", "w") as f:
            f.write(output)
        print("Dependency report saved to dependency-report.txt")
    else:
        print(f"Failed to generate dependency report: {output}")

def main():
    """Main function."""
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    print("🚀 PrisMind Dependency Management")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Check for outdated packages")
        print("2. Update requirements files")
        print("3. Generate dependency report")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            check_outdated()
        elif choice == "2":
            update_requirements()
        elif choice == "3":
            generate_dependency_report()
        elif choice == "4":
            print("\nGoodbye! 👋")
            break
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    import os
    main()
