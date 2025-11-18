#!/usr/bin/env python3
"""
Fix bare except clauses that hide errors
"""

import os
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def fix_bare_except_clauses(file_path):
    """Fix bare except clauses in a file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        changes_made = []

        # Find bare except clauses
        # Pattern 1: except: (on its own line)
        bare_except_pattern1 = r"(\s*)except:\s*"
        matches1 = re.findall(bare_except_pattern1, content)

        # Pattern 2: except: followed by code on same line
        bare_except_pattern2 = r"except:\s*(.*)"
        matches2 = re.findall(bare_except_pattern2, content)

        # Process Pattern 1 (multi-line except)
        for indent in matches1:
            # Replace bare except with except Exception as e
            old_except = f"{indent}except:"
            new_except = f"{indent}except Exception as e:"

            if old_except in content:
                content = content.replace(old_except, new_except, 1)
                changes_made.append((old_except, new_except, "multi-line"))

        # Process Pattern 2 (single-line except)
        for except_code in matches2:
            # Skip if it already has proper exception handling
            if "as " in except_code or "except " in except_code:
                continue

            # Replace bare except with proper exception handling
            old_except = f"except: {except_code}"
            new_except = f"except Exception as e: {except_code}"

            if old_except in content:
                content = content.replace(old_except, new_except, 1)
                changes_made.append((old_except, new_except, "single-line"))

        # Add logging import if needed and changes were made
        if changes_made and "import logging" not in content:
            lines = content.split("\n")
            insert_line = 0

            # Find a good place to add the import
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


def add_error_logging(content):
    """Add error logging to except blocks that don't have it"""
    # Find except blocks and check if they log the error
    lines = content.split("\n")
    changes_made = []

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for except lines
        if re.match(r"\s*except\s+\w+", line) or re.match(
            r"\s*except\s+Exception", line
        ):
            # Check if the except block already has error logging
            has_logging = False
            j = i + 1
            indent = len(line) - len(line.lstrip())

            # Look through the except block content
            while j < len(lines):
                next_line = lines[j]
                if next_line.strip() == "":
                    j += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent and next_line.strip():
                    break  # End of except block
                if (
                    "logger." in next_line
                    or "print(" in next_line
                    or "logging." in next_line
                ):
                    has_logging = True
                    break
                j += 1

            # If no logging found, add it
            if not has_logging:
                # Find the end of the except line and insert logging
                except_end = line.rstrip()
                logging_line = f"{' ' * (indent + 4)}logger.error(f\"Error in {Path(__file__).name}: {{e}}\")"

                # Insert after the except line
                lines.insert(i + 1, logging_line)
                changes_made.append((i, line, logging_line))
                i += 1  # Skip the line we just added

        i += 1

    return "\n".join(lines), len(changes_made)


def main():
    """Main function to fix bare except clauses"""
    print("🔧 Fixing bare except clauses that hide errors...")
    print("=" * 60)

    # Find all Python files in src
    src_path = Path("src")
    python_files = list(src_path.rglob("*.py"))

    total_files = 0
    total_changes = 0

    for file_path in python_files:
        # First fix bare except clauses
        bare_changes = fix_bare_except_clauses(file_path)

        # Then add error logging to existing except blocks
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated_content, logging_changes = add_error_logging(content)

            if logging_changes > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)

            total_changes = bare_changes + logging_changes

            if total_changes > 0:
                print(
                    f"✅ {file_path}: {bare_changes} bare except fixed, {logging_changes} added error logging"
                )

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")

        if total_changes > 0:
            total_files += 1

    print(f"\n📊 SUMMARY:")
    print(f"   Files processed: {total_files}")
    print(f"   Bare except clauses fixed: {total_changes}")

    if total_changes > 0:
        print(f"\n🎉 Error handling improved significantly!")
        print(f"   Errors will now be properly logged for debugging")
    else:
        print(f"\n✅ All files already have proper exception handling")


if __name__ == "__main__":
    main()
