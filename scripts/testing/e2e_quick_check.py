#!/usr/bin/env python3
"""
Quick end-to-end check:
- Collect from enabled platforms
- Analyze a small batch
- Build digest and print brief report
"""

import asyncio

from src.application.automation.orchestrator import get_orchestrator


async def main():
    orch = get_orchestrator()

    print("🔄 Collecting...")
    results = await orch.collect_all()
    print("Collection:")
    for k, v in results.items():
        if k != "errors":
            print(f"  {k}: {v}")
    if results.get("errors"):
        print(f"Errors: {results['errors']}")

    print("\n🧠 Analyzing (up to 10)...")
    analyzed = await orch.analyze_batch(limit=10)
    print(f"Analyzed: {analyzed}")

    print("\n🗞️ Building digest (10 items)...")
    feed = await orch.build_news_feed(limit=10)
    for i, item in enumerate(feed, start=1):
        t = item.get("title") or "Untitled"
        u = item.get("url") or ""
        print(f"  {i:02d}. {t} — {u}")


if __name__ == "__main__":
    asyncio.run(main())


