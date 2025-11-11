#!/usr/bin/env python3
import re
from typing import Optional

from src.database.manager import SupabaseManager


def sanitize_threads_content(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return raw
    text = raw
    # Remove repeated 'Translate' tokens
    text = re.sub(r"\bTranslate\b", "", text)
    # Remove pagination like "1/3"
    text = re.sub(r"\b\d+\s*/\s*\d+\b", " ", text)
    # Remove short time markers like 1d/2h
    text = re.sub(r"\b\d+\s*[dhm]\b", " ", text, flags=re.I)
    # Split to segments and filter
    segs = re.split(r"[\n\r]+|\s{2,}", text)
    cleaned = []
    seen = set()
    for s in segs:
        t = s.strip()
        if not t:
            continue
        # Drop very short noise
        if len(t) < 6:
            continue
        # Drop pure usernames
        if re.fullmatch(r"@\w+", t):
            continue
        # Drop likely username/display blocks without @
        if re.fullmatch(r"[A-Za-z0-9._-]{3,32}", t):
            continue
        # Drop section labels
        if t.lower() in ("ai threads", "threads", "original", "more"):
            continue
        # Drop domain-only embeds
        if re.fullmatch(r"[\w.-]+\.(com|net|org|io|ai)(/.*)?", t, re.I):
            continue
        # Stop at obvious comment markers
        if t.startswith("=== ") or t.lower().startswith("top valuable comments"):
            break
        # De-duplicate
        if t in seen:
            continue
        seen.add(t)
        cleaned.append(t)
    main = " ".join(cleaned)
    # Sentence-level de-duplication
    sentences = re.split(r"(?<=[\.!?…])\s+", main)
    uniq_sent = []
    seen_sent = set()
    for sent in sentences:
        s = sent.strip()
        if not s:
            continue
        key = re.sub(r"\s+", " ", s.lower())
        if key in seen_sent:
            continue
        seen_sent.add(key)
        uniq_sent.append(s)
    main = " ".join(uniq_sent)
    # Trim after common noise cues
    for m in ["💬", "Comments:", "TOP VALUABLE COMMENTS", "http://", "https://"]:
        idx = main.find(m)
        if idx > 80:
            main = main[:idx]
            break
    main = re.sub(r"\s+", " ", main).strip()
    return main[:800] if main else main


def run(limit: int = 5000) -> dict:
    sm = SupabaseManager()
    client = sm.client
    # Scan all Threads posts (limit applied) to ensure cleanup after UI changes
    rows = (
        client
        .table("posts")
        .select("id,post_id,content")
        .eq("platform", "threads")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    data = getattr(rows, "data", []) or []
    fixed = 0
    skipped = 0
    for r in data:
        pid = r.get("post_id")
        content = r.get("content")
        cleaned = sanitize_threads_content(content)
        if not cleaned or cleaned == content:
            skipped += 1
            continue
        try:
            client.table("posts").update({"content": cleaned}).eq("post_id", pid).execute()
            fixed += 1
        except Exception:
            skipped += 1
    return {"scanned": len(data), "fixed": fixed, "skipped": skipped}


if __name__ == "__main__":
    res = run()
    print(res)


