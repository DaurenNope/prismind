#!/usr/bin/env python3
"""
Fix print statements by converting them to proper logging
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def categorize_print_statement(line, print_content):
    """Categorize print statement and suggest appropriate logging level"""
    content = print_content.lower().strip()

    # Error patterns
    error_patterns = [
        r"❌",
        r"error",
        r"fail",
        r"exception",
        r"traceback",
        r"critical",
        r"fatal",
        r"crash",
        r"abort",
        r"panic",
    ]

    # Warning patterns
    warning_patterns = [
        r"⚠️",
        r"warning",
        r"warn",
        r"deprecated",
        r"timeout",
        r"retry",
        r"attempt",
        r"unable",
        r"cannot",
        r"missing",
    ]

    # Success patterns
    success_patterns = [
        r"✅",
        r"success",
        r"complete",
        r"done",
        r"finished",
        r"loaded",
        r"saved",
        r"created",
        r"updated",
        r"deleted",
    ]

    # Info patterns
    info_patterns = [
        r"ℹ️",
        r"starting",
        r"initializing",
        r"processing",
        r"collecting",
        r"scraping",
        r"fetching",
        r"analyzing",
        r"running",
        r"executing",
        r"performing",
    ]

    # Debug patterns
    debug_patterns = [
        r"🔍",
        r"debug",
        r"trace",
        r"detail",
        r"verbose",
        r"step",
        r"phase",
        r"stage",
        r"checkpoint",
    ]

    # Check patterns in order of priority
    if any(re.search(pattern, content, re.IGNORECASE) for pattern in error_patterns):
        return "error"
    elif any(
        re.search(pattern, content, re.IGNORECASE) for pattern in warning_patterns
    ):
        return "warning"
    elif any(
        re.search(pattern, content, re.IGNORECASE) for pattern in success_patterns
    ):
        return "info"
    elif any(re.search(pattern, content, re.IGNORECASE) for pattern in info_patterns):
        return "info"
    elif any(re.search(pattern, content, re.IGNORECASE) for pattern in debug_patterns):
        return "debug"
    else:
        return "info"  # Default to info


def convert_print_to_logging(file_path):
    """Convert print statements in a file to logging calls"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if logging is already imported
        has_logging_import = "import logging" in content or "from logging" in content

        original_content = content
        changes_made = []

        # Find print statements with regex
        print_pattern = r"(\s*)print\((.*?)\)"
        matches = re.findall(print_pattern, content, re.DOTALL)

        if not matches:
            return 0  # No print statements found

        # Process matches in reverse order to avoid shifting line numbers
        for indent, print_args in reversed(matches):
            # Clean up the print arguments
            print_args = print_args.strip()

            # Skip certain print statements
            if print_args.startswith("--") or "sys.stderr.write" in print_args:
                continue

            # Categorize the log level
            log_level = categorize_print_statement(file_path, print_args)

            # Create logger call
            if 'f"' in print_args or "f'" in print_args:
                # f-string
                logger_call = f"{indent}logger.{log_level}({print_args})"
            else:
                # Regular string or expression
                logger_call = f"{indent}logger.{log_level}({print_args})"

            # Replace the print statement
            old_print = f"{indent}print({print_args})"
            content = content.replace(old_print, logger_call, 1)

            changes_made.append((old_print, logger_call, log_level))

        # Add logging import if needed
        if changes_made and not has_logging_import:
            # Find a good place to add the import (after shebang or first import)
            lines = content.split("\n")
            insert_line = 0

            # Skip shebang and encoding
            for i, line in enumerate(lines):
                if line.strip().startswith("#!") or line.strip().startswith("# -*-"):
                    insert_line = i + 1
                elif line.strip().startswith("import") or line.strip().startswith(
                    "from"
                ):
                    insert_line = i
                    break
                elif line.strip():
                    insert_line = i
                    break

            # Insert logging import
            logging_import = "import logging"
            if insert_line == 0:
                lines.insert(0, logging_import)
            else:
                lines.insert(insert_line, logging_import)

            # Add logger setup if it doesn't exist
            logger_setup = "logger = logging.getLogger(__name__)"
            if "logger = logging.getLogger" not in "\n".join(lines):
                # Find end of imports section
                import_end = insert_line
                while import_end < len(lines) and (
                    lines[import_end].strip().startswith("import")
                    or lines[import_end].strip().startswith("from")
                    or lines[import_end].strip() == ""
                ):
                    import_end += 1

                lines.insert(import_end, "")
                lines.insert(import_end + 1, logger_setup)

            content = "\n".join(lines)

        # Write back the file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return len(changes_made)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0


def main():
    """Main function to fix print statements"""
    print("🔧 Fixing print statements to use proper logging...")
    print("=" * 60)

    # Find all Python files in src
    src_path = Path("src")
    python_files = list(src_path.rglob("*.py"))

    total_files = 0
    total_changes = 0

    for file_path in python_files:
        changes = convert_print_to_logging(file_path)
        if changes > 0:
            print(f"✅ {file_path}: {changes} print statements converted")
            total_changes += changes
        total_files += 1

    print(f"\n📊 SUMMARY:")
    print(f"   Files processed: {total_files}")
    print(f"   Print statements converted: {total_changes}")

    if total_changes > 0:
        print(f"\n🎉 Technical debt cleanup in progress!")
        print(
            f"   Run 'python -m pytest tests/test_collection_unit.py' to verify changes"
        )
    else:
        print(f"\n✅ All files already using proper logging")


if __name__ == "__main__":
    main()
