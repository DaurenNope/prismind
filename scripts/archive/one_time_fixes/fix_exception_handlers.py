#!/usr/bin/env python3
"""
Fix all exception handlers that use undefined variable 'e'
"""
import re
from pathlib import Path
from typing import List, Tuple


def fix_exception_handlers(content: str) -> Tuple[str, int]:
    """Fix exception handlers that use undefined 'e' variable"""
    fixes = 0
    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is "except Exception:" without "as e"
        except_match = re.match(r"^(\s*)(except\s+Exception)\s*:\s*$", line)
        if except_match and "as e" not in line:
            indent = except_match.group(1)
            # Look ahead up to 5 lines for logger call with {e}
            found_logger_with_e = False
            for j in range(i + 1, min(i + 6, len(lines))):
                next_line = lines[j]
                if "{e}" in next_line and "logger." in next_line:
                    found_logger_with_e = True
                    break
                # Stop if we hit another except or def or class
                if re.match(r"^\s*(except|def|class|if|for|while|try|with)", next_line):
                    break

            if found_logger_with_e:
                # Fix: add "as e"
                new_lines.append(f"{indent}except Exception as e:")
                fixes += 1
                i += 1
                continue

        # Also check for "Error in fix_bare_except" pattern
        if "Error in fix_bare_except" in line and "{e}" in line:
            # Find the except line above it
            for j in range(max(0, i - 5), i):
                prev_line = lines[j]
                except_match = re.match(
                    r"^(\s*)(except\s+Exception)\s*:\s*$", prev_line
                )
                if except_match and "as e" not in prev_line:
                    # Fix the except line
                    indent = except_match.group(1)
                    new_lines[j] = f"{indent}except Exception as e:"
                    fixes += 1
                    # Also fix the error message
                    line = line.replace(
                        "Error in fix_bare_except.py: {e}", "Error: {e}"
                    )
                    break

        new_lines.append(line)
        i += 1

    return "\n".join(new_lines), fixes


def main():
    """Fix all Python files in src/"""
    src_dir = Path("src")
    total_fixes = 0
    files_fixed = []

    for py_file in sorted(src_dir.rglob("*.py")):
        try:
            content = py_file.read_text(encoding="utf-8")

            # Skip if file doesn't have the problematic pattern
            if "Error in fix_bare_except" not in content:
                # Check for except Exception: with {e} reference nearby
                if not (
                    re.search(r"except\s+Exception\s*:", content) and "{e}" in content
                ):
                    continue

            fixed_content, fixes = fix_exception_handlers(content)

            if fixes > 0:
                py_file.write_text(fixed_content, encoding="utf-8")
                files_fixed.append((str(py_file), fixes))
                total_fixes += fixes
                print(f"✅ Fixed {fixes} issue(s) in {py_file}")
        except Exception as e:
            print(f"❌ Error processing {py_file}: {e}")

    print(f"\n{'='*80}")
    print(f"✅ Fixed {total_fixes} exception handler(s) in {len(files_fixed)} file(s)")
    print(f"{'='*80}")

    if files_fixed:
        print("\nTop 20 files fixed:")
        for filepath, count in sorted(files_fixed, key=lambda x: x[1], reverse=True)[
            :20
        ]:
            print(f"  {filepath}: {count} fix(es)")


if __name__ == "__main__":
    main()
