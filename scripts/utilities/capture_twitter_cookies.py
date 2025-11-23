from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async as stealth

DEFAULT_OUTPUT = Path("config/cookies/twitter_cookies_cryptoniard.json")


async def _wait_for_user(
    prompt: str = "\nWhen the X home feed is fully loaded, press Enter here... ",
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input, prompt)


async def capture_twitter_cookies(output_path: Path, proxy: str | None = None) -> None:
    playwright = None
    browser = None
    context = None
    try:
        playwright = await async_playwright().start()

        # Remove automation flags and add realistic browser args
        launch_kwargs = {
            "headless": False,
            "args": [
                "--lang=en-US",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-site-isolation-trials",
            ],
        }
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}

        browser = await playwright.chromium.launch(**launch_kwargs)

        # More realistic browser context with permissions and locale
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation", "notifications"],
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        # Add script to hide webdriver property before any page loads
        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.navigator.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """
        )

        page = await context.new_page()
        await stealth(page)

        # Additional JavaScript to mask automation after page load
        await page.add_init_script(
            """
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
            delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        """
        )

        print("Opening https://x.com/home in a headed browser window...")
        try:
            await page.goto(
                "https://x.com/home", wait_until="domcontentloaded", timeout=30000
            )
        except Exception as e:
            print(f"⚠️  Navigation warning: {e}")

        # Give user time to see the browser and start login
        print("\n⚠️  Browser window should be open now.")
        print("    Please complete the login flow manually in the opened browser.")
        print(
            "    Once you see the authenticated home timeline, come back to this terminal."
        )
        print("\n    Waiting 5 seconds for you to see the browser...")
        await asyncio.sleep(5)

        # Keep browser open and wait for user confirmation
        print(
            "\n    Browser will stay open. Press Enter here when login is complete..."
        )
        try:
            await _wait_for_user()
        except (EOFError, KeyboardInterrupt):
            print("\n⚠️  Input interrupted. Saving current state anyway...")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(output_path))
        print(f"\n✅ Saved Playwright storage_state to {output_path}")
    except Exception as e:
        print(f"\n❌ Error during capture: {e}")
        import traceback

        traceback.print_exc()
        if context:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(output_path))
                print(f"⚠️  Saved partial state to {output_path} anyway")
            except Exception:
                pass
    finally:
        # Keep browser open for a moment so user can see it
        print("\nClosing browser in 2 seconds...")
        await asyncio.sleep(2)
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()


def main() -> None:
    load_dotenv()
    output_file = Path(os.getenv("TWITTER_COOKIES_FILE", DEFAULT_OUTPUT))
    proxy = (
        os.getenv("TWITTER_PROXY")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
    )
    asyncio.run(capture_twitter_cookies(output_file, proxy))


if __name__ == "__main__":
    main()
