#!/usr/bin/env python3
"""
Convert Twitter cookies from old format (list) to storage_state format (dict)

Old format: [{"name": "...", "value": "...", ...}, ...]
New format: {"cookies": [...], "origins": [...]}
"""

import json
import sys
from pathlib import Path


def convert_cookies(old_file: Path, new_file: Path = None):
    """Convert cookies from old format to storage_state format"""

    if not old_file.exists():
        print(f"❌ Cookie file not found: {old_file}")
        return False

    # Load old format
    with open(old_file, "r") as f:
        old_data = json.load(f)

    # Check if already in new format
    if isinstance(old_data, dict) and "cookies" in old_data:
        print(f"✅ Cookie file is already in storage_state format")
        return True

    # Convert from list to storage_state format
    if isinstance(old_data, list):
        print(
            f"📝 Converting {len(old_data)} cookies from list format to storage_state format..."
        )

        # Convert each cookie to Playwright format
        cookies = []
        for cookie in old_data:
            if isinstance(cookie, dict):
                # Map old format to Playwright storage_state format
                playwright_cookie = {
                    "name": cookie.get("name", ""),
                    "value": cookie.get("value", ""),
                    "domain": cookie.get("domain", ""),
                    "path": cookie.get("path", "/"),
                    "expires": cookie.get("expirationDate", -1),
                    "httpOnly": cookie.get("httpOnly", False),
                    "secure": cookie.get("secure", True),
                    "sameSite": cookie.get("sameSite", "None"),
                }
                cookies.append(playwright_cookie)

        # Create storage_state format
        new_data = {"cookies": cookies, "origins": []}

        # Save to new file (or overwrite old file)
        output_file = new_file or old_file
        with open(output_file, "w") as f:
            json.dump(new_data, f, indent=2)

        print(f"✅ Converted {len(cookies)} cookies to storage_state format")
        print(f"   Saved to: {output_file}")
        return True
    else:
        print(f"❌ Unknown cookie format: {type(old_data)}")
        return False


if __name__ == "__main__":
    import os

    # Get cookie file from env or default
    username = os.getenv("TWITTER_USERNAME", "cryptoniard")
    cookie_file = Path(f"config/twitter_cookies_{username}.json")

    if len(sys.argv) > 1:
        cookie_file = Path(sys.argv[1])

    if not cookie_file.exists():
        print(f"❌ Cookie file not found: {cookie_file}")
        print(f"   Usage: python scripts/convert_twitter_cookies.py [cookie_file_path]")
        sys.exit(1)

    success = convert_cookies(cookie_file)
    sys.exit(0 if success else 1)
