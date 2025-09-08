#!/usr/bin/env python3
"""
Export site cookies/localStorage via Playwright after a manual login.

Usage:
  python scripts/export_cookies.py --site reddit
  python scripts/export_cookies.py --site twitter

Flow:
- Launches a headed Chromium window
- Opens the login page
- You sign in manually
- Press Enter in the terminal
- Script saves cookies+storage to ./cookies/<site>_storage_state.json and prints cookie JSON
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, Any


def get_targets(site: str) -> Dict[str, str]:
    if site == "reddit":
        return {
            "name": "reddit",
            "login_url": "https://www.reddit.com/login",
            "domain_filter": "reddit.com",
        }
    if site == "twitter":
        return {
            "name": "twitter",
            "login_url": "https://twitter.com/login",
            "domain_filter": "twitter.com",
        }
    raise ValueError("site must be 'reddit' or 'twitter'")


def export_storage_state(site: str, auto: bool = False, no_wait: bool = False) -> Dict[str, Any]:
    from playwright.sync_api import sync_playwright

    target = get_targets(site)
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    out_path = cookies_dir / f"{target['name']}_storage_state.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])  # headed
        context = browser.new_context()
        page = context.new_page()

        print(f"\n➡️  Opening {target['login_url']}")
        page.goto(target["login_url"], timeout=60000, wait_until="domcontentloaded")

        if auto:
            import os as _os
            username = _os.getenv('REDDIT_USERNAME') if site == 'reddit' else _os.getenv('TWITTER_USERNAME')
            password = _os.getenv('REDDIT_PASSWORD') if site == 'reddit' else _os.getenv('TWITTER_PASSWORD')
            if not (username and password):
                print("⚠️ Missing username/password in env; falling back to manual login.")
            else:
                try:
                    if site == 'reddit':
                        page.fill('input[name="username"]', username, timeout=30000)
                        page.fill('input[name="password"]', password, timeout=30000)
                        page.click('button[type="submit"]', timeout=30000)
                        page.wait_for_timeout(4000)
                        page.goto(f'https://www.reddit.com/user/{username}/', timeout=60000)
                    else:  # twitter
                        page.fill('input[name="text"]', username, timeout=30000)
                        page.keyboard.press('Enter')
                        page.wait_for_timeout(2000)
                        try:
                            page.fill('input[name="password"]', password, timeout=30000)
                        except Exception:
                            # Sometimes Twitter asks for username again
                            pass
                        page.keyboard.press('Enter')
                        page.wait_for_timeout(5000)
                except Exception as _e:
                    print(f"⚠️ Auto-login encountered an issue: {_e}. You can complete login manually in the window.")

        if not no_wait:
            print("   If not already logged in, complete login in the window. Once you see your feed/home, press Enter here...")
            try:
                input("\nPress Enter AFTER login is complete...")
            except KeyboardInterrupt:
                browser.close()
                raise SystemExit(1)
        else:
            # Give a few seconds for redirects/session to settle
            page.wait_for_timeout(5000)

        # Save full storage state (cookies + localStorage)
        context.storage_state(path=str(out_path))
        state = context.storage_state()

        browser.close()

    return state


def filter_domain_cookies(state: Dict[str, Any], domain_filter: str) -> Any:
    cookies = state.get("cookies", [])
    filtered = [c for c in cookies if domain_filter in (c.get("domain") or "")]
    return filtered


def main():
    parser = argparse.ArgumentParser(description="Export cookies/localStorage via Playwright after login")
    parser.add_argument("--site", choices=["reddit", "twitter"], required=True)
    parser.add_argument("--auto", action="store_true", help="Attempt auto-login using env credentials")
    parser.add_argument("--no-wait", action="store_true", help="Do not wait for manual Enter; proceed automatically")
    args = parser.parse_args()

    try:
        state = export_storage_state(args.site, auto=args.auto, no_wait=args.no_wait)
    except Exception as e:
        print(f"❌ Failed to export storage state: {e}")
        return

    target = get_targets(args.site)
    cookies = filter_domain_cookies(state, target["domain_filter"])

    # Write a clean cookies json next to storage_state for convenience
    cookies_dir = Path("cookies")
    cookies_json_path = cookies_dir / f"{target['name']}_cookies.json"
    with open(cookies_json_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved storage state: cookies/{target['name']}_storage_state.json")
    print(f"✅ Saved cookies JSON:    cookies/{target['name']}_cookies.json")

    # Also print the cookies JSON so you can copy into GitHub Secrets
    print("\nCopy this into your GitHub Secret (e.g., REDDIT_COOKIES_JSON / TWITTER_COOKIES_JSON):\n")
    print(json.dumps(cookies, ensure_ascii=False))


if __name__ == "__main__":
    main()


