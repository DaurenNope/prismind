#!/usr/bin/env python3
"""Import Twitter cookies from a curl command"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


def parse_curl_cookies(curl_command: str) -> dict:
    """Extract cookies from curl command"""
    # Extract cookie string from -b flag (handle both single and multi-line)
    # Remove newlines and extra spaces first
    curl_command = re.sub(r"\s+", " ", curl_command)

    cookie_match = re.search(r"-b\s+'([^']+)'", curl_command)
    if not cookie_match:
        # Try with escaped quotes
        cookie_match = re.search(r"-b\s+['\"]([^'\"]+)['\"]", curl_command)

    if not cookie_match:
        raise ValueError("Could not find cookies in curl command (looking for -b flag)")

    cookie_string = cookie_match.group(1)

    # Parse cookies
    cookies = []
    for cookie_pair in cookie_string.split("; "):
        if "=" in cookie_pair:
            name, value = cookie_pair.split("=", 1)
            name = name.strip()
            value = unquote(value.strip())

            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".x.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": name in ["auth_token", "ct0", "kdt"],
                    "sameSite": "None",
                }
            )

    return cookies


def create_storage_state(cookies: list) -> dict:
    """Create Playwright storage_state format"""
    return {"cookies": cookies, "origins": []}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/import_twitter_cookies_from_curl.py <curl_command>"
        )
        print("\nOr paste the curl command when prompted:")
        curl_command = input("Paste curl command: ")
    else:
        curl_command = sys.argv[1]

    try:
        cookies = parse_curl_cookies(curl_command)
        print(f"✅ Extracted {len(cookies)} cookies")

        # Check for critical cookies
        cookie_names = [c["name"] for c in cookies]
        if "auth_token" not in cookie_names:
            print("⚠️  Warning: auth_token not found")
        if "ct0" not in cookie_names:
            print("⚠️  Warning: ct0 (CSRF token) not found")

        storage_state = create_storage_state(cookies)

        # Save to cookie file
        username = input("Enter Twitter username: ").strip()
        cookie_file = Path(f"cookies/twitter_cookies_{username}.json")
        cookie_file.parent.mkdir(parents=True, exist_ok=True)

        with open(cookie_file, "w") as f:
            json.dump(storage_state, f, indent=2)

        print(f"✅ Saved cookies to: {cookie_file}")
        print(f"   Contains {len(cookies)} cookies")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
