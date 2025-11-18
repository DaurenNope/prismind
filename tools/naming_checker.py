#!/usr/bin/env python3
"""
Naming Convention Checker for BEYONDLINES
Ensures consistent naming conventions across the codebase
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple


class NamingConventionChecker:
    """Checks Python files for naming convention violations"""

    def __init__(self):
        self.violations = []
        self.stats = {
            "files_checked": 0,
            "classes_found": 0,
            "functions_found": 0,
            "variables_found": 0,
            "violations_found": 0,
        }

    def check_directory(self, directory: str) -> List[Dict]:
        """Check all Python files in a directory"""
        violations = []
        directory_path = Path(directory)

        if not directory_path.exists():
            print(f"❌ Directory {directory} does not exist")
            return violations

        for py_file in directory_path.rglob("*.py"):
            # Skip specific directories
            if any(skip in str(py_file) for skip in [".venv", "__pycache__", ".git"]):
                continue

            file_violations = self.check_file(py_file)
            if file_violations:
                violations.extend(file_violations)

        return violations

    def check_file(self, filepath: Path) -> List[Dict]:
        """Check a single Python file for naming convention violations"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            file_violations = []
            self.stats["files_checked"] += 1

            # Check classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.stats["classes_found"] += 1
                    if not self._is_pascal_case(node.name):
                        violation = {
                            "type": "class",
                            "name": node.name,
                            "line": node.lineno,
                            "file": str(filepath),
                            "message": f"Class '{node.name}' should use PascalCase",
                        }
                        file_violations.append(violation)

                elif isinstance(node, ast.FunctionDef):
                    self.stats["functions_found"] += 1
                    if not self._is_snake_case(node.name):
                        violation = {
                            "type": "function",
                            "name": node.name,
                            "line": node.lineno,
                            "file": str(filepath),
                            "message": f"Function '{node.name}' should use snake_case",
                        }
                        file_violations.append(violation)

                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            if var_name.isupper():
                                # Constants are allowed to be UPPER_SNAKE_CASE
                                continue
                            elif var_name.startswith("_"):
                                # Private variables - check if they follow snake_case
                                if not self._is_snake_case(var_name.lstrip("_")):
                                    violation = {
                                        "type": "variable",
                                        "name": var_name,
                                        "line": node.lineno,
                                        "file": str(filepath),
                                        "message": f"Variable '{var_name}' should use snake_case",
                                    }
                                    file_violations.append(violation)
                            else:
                                self.stats["variables_found"] += 1
                                if not self._is_snake_case(var_name):
                                    violation = {
                                        "type": "variable",
                                        "name": var_name,
                                        "line": node.lineno,
                                        "file": str(filepath),
                                        "message": f"Variable '{var_name}' should use snake_case",
                                    }
                                    file_violations.append(violation)

            self.stats["violations_found"] += len(file_violations)
            return file_violations

        except Exception as e:
            print(f"❌ Error parsing {filepath}: {e}")
            return []

    def _is_pascal_case(self, name: str) -> bool:
        """Check if a string follows PascalCase"""
        if not name:
            return False

        # Remove common prefixes/suffixes that might contain underscores
        clean_name = name

        # Check if it's a valid identifier
        if not clean_name.replace("_", "").isalnum():
            return False

        # PascalCase: starts with uppercase, contains only letters and numbers
        return clean_name[0].isupper() and "_" not in clean_name

    def _is_snake_case(self, name: str) -> bool:
        """Check if a string follows snake_case"""
        if not name:
            return False

        # Check if it's a valid identifier
        if not name.isidentifier():
            return False

        # Check if it's all lowercase with underscores
        return name.lower() == name

    def print_summary(self):
        """Print a summary of the checking results"""
        print("\n" + "=" * 60)
        print("📊 Naming Convention Check Summary")
        print("=" * 60)
        print(f"Files checked: {self.stats['files_checked']}")
        print(f"Classes found: {self.stats['classes_found']}")
        print(f"Functions found: {self.stats['functions_found']}")
        print(f"Variables found: {self.stats['variables_found']}")
        print(f"Violations found: {self.stats['violations_found']}")
        print("=" * 60)

    def print_violations(self, violations: List[Dict], max_shown: int = 20):
        """Print violations in a readable format"""
        if not violations:
            print("✅ No naming convention violations found!")
            return

        print(f"\n❌ Found {len(violations)} naming convention violations:")
        print("-" * 60)

        # Sort violations by file and line
        violations.sort(key=lambda x: (x["file"], x["line"]))

        shown = 0
        for violation in violations:
            if shown >= max_shown:
                print(f"\n... and {len(violations) - max_shown} more violations")
                break

            relative_path = violation["file"].replace("./", "")
            print(f"{relative_path}:{violation['line']} - {violation['message']}")
            shown += 1

    def generate_report(self, violations: List[Dict]) -> str:
        """Generate a detailed report of violations"""
        report = []
        report.append("# Naming Convention Violations Report\n")

        # Group violations by type
        by_type = {}
        for violation in violations:
            violation_type = violation["type"]
            if violation_type not in by_type:
                by_type[violation_type] = []
            by_type[violation_type].append(violation)

        for violation_type, items in by_type.items():
            report.append(f"## {violation_type.title()} Violations ({len(items)})\n")

            for item in items:
                relative_path = item["file"].replace("./", "")
                report.append(f"- {relative_path}:{item['line']} - `{item['name']}`")

            report.append("")

        return "\n".join(report)


def main():
    """Main function to run the naming convention checker"""
    if len(sys.argv) < 2:
        print("Usage: python naming_checker.py <directory>")
        print("Example: python naming_checker.py src")
        sys.exit(1)

    directory = sys.argv[1]
    checker = NamingConventionChecker()

    print(f"🔍 Checking naming conventions in {directory}...")
    violations = checker.check_directory(directory)

    # Print summary
    checker.print_summary()

    # Print violations
    checker.print_violations(violations)

    # Generate report if violations found
    if violations:
        report = checker.generate_report(violations)
        report_file = "naming_violations_report.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"\n📄 Detailed report saved to {report_file}")

        # Exit with error code if violations found
        sys.exit(1)
    else:
        print("\n✅ All naming conventions are correct!")
        sys.exit(0)


if __name__ == "__main__":
    main()
