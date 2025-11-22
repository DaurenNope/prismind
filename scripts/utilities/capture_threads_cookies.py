import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async as stealth

OUTPUT_PATH = Path(
    os.getenv(
        "THREADS_COOKIES_FILE",
        "/Users/mac/Documents/Development/beyondlines/config/threads_cookies.json",
    )
)


async def _wait_for_user_confirmation(
    prompt: str = "\nWhen you finish logging in (profile visible), press Enter here... ",
) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input, prompt)


async def capture_cookies(username: str, password: str, output: Path) -> None:
    async with async_playwright() as p:
        proxy = (
            os.getenv("THREADS_PROXY")
            or os.getenv("HTTPS_PROXY")
            or os.getenv("HTTP_PROXY")
        )
        launch_kwargs = {
            "headless": False,
            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--lang=en-US"],
        }
        if proxy:
            launch_kwargs["proxy"] = {"server": proxy}
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        )
        page = await context.new_page()
        await stealth(page)

        print("Opening Instagram login window for Threads session...")
        try:
            await page.goto(
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
            )
        except Exception:
            pass
        # Give time for manual login (captcha/2FA)
        await page.wait_for_timeout(90000)

        # Bind session to Threads
        try:
            await page.goto("https://www.threads.net/", wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
        except Exception:
            try:
                await page.goto(
                    "https://www.threads.com/", wait_until="domcontentloaded"
                )
                await page.wait_for_timeout(5000)
            except Exception:
                pass

        cookies = await context.cookies()
        normalized = []
        for c in cookies:
            c2 = dict(c)
            domain = c2.get("domain") or ".threads.net"
            if isinstance(domain, str) and domain.endswith("threads.com"):
                domain = ".threads.net"
            c2["domain"] = domain
            c2["path"] = c2.get("path") or "/"
            if "url" in c2:
                c2.pop("url", None)
            normalized.append(c2)

        output.parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w") as f:
            json.dump(normalized, f, indent=2)

        await context.close()
        await browser.close()


def main() -> None:
    load_dotenv()
    username: Optional[str] = os.getenv("THREADS_USERNAME")
    password: Optional[str] = os.getenv("THREADS_PASSWORD")
    if not username or not password:
        raise SystemExit(
            "THREADS_USERNAME and THREADS_PASSWORD must be set in env/.env"
        )
    asyncio.run(capture_cookies(username, password, OUTPUT_PATH))


if __name__ == "__main__":
    main()
