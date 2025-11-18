#!/usr/bin/env python3
import re
from typing import Optional

from src.database.manager import SupabaseManager


def sanitize_threads_content(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return raw
    thread_part = None
    thread_total = None
    text = raw
    # Remove short time markers like 1d/2h
    text = re.sub(r"\b\d+\s*[dhm]\b", " ", text, flags=re.I)
    # Split to segments and filter
    segs = re.split(r"[\n\r]+|\s{2,}", text)
    cleaned = []
    seen = set()
    footer_phrases = (
        "log in to see more replies",
        "log in or sign up for threads",
        "see what people are talking about",
        "join the conversation",
        "continue with instagram",
        "log in with username instead",
        "threads terms",
        "privacy policy",
        "cookies policy",
        "report a problem",
    )
    thread_pattern = re.compile(r"(.*?)(?:\s+|\n|\r)(\d+)\s*/\s*(\d+)\s*$", re.DOTALL)
    for s in segs:
        t = s.strip()
        if not t:
            continue
        # Drop very short noise
        if len(t) < 6:
            continue
        lowered = t.lower()
        if any(phrase in lowered for phrase in footer_phrases):
            continue
        if lowered in ("log in", "learn more", "terms"):
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
    # Build thread content from sequential Translate markers
    translate_sequence = re.compile(
        r"(?i)(.*?)(?:Translate\s+(\d+)\s*/\s*(\d+))", re.DOTALL
    )
    segments = []
    current_total = None
    expected_part = 1

    for match in translate_sequence.finditer(main):
        segment = match.group(1).strip()
        part = int(match.group(2))
        total = int(match.group(3))

        if current_total is None:
            current_total = total
        elif total != current_total:
            break

        if part < expected_part:
            continue

        if segment:
            first_token = segment.split()[0] if segment.split() else ""
            if not first_token.startswith("@") and not re.match(
                r"^[\w\.-]+__", first_token
            ):
                segments.append(segment)

        expected_part = part + 1
        if part >= total:
            break

    if segments:
        main = " ".join(segments).strip()
    else:
        translate_marker = re.search(r"Translate\s+\d+\s*/\s*\d+", main, re.IGNORECASE)
        if translate_marker:
            main = main[: translate_marker.start()].rstrip()

    main = re.sub(r"\s+", " ", main).strip()
    main = re.sub(r"\bTranslate\b", "", main, flags=re.IGNORECASE).strip()
    marker_match = thread_pattern.match(main)
    if marker_match:
        base = marker_match.group(1).rstrip()
        part = int(marker_match.group(2))
        total = int(marker_match.group(3))
        if 0 < part <= total <= 50:
            main = base
    main = re.sub(r"\s+", " ", main).strip()
    return main[:4000] if main else main


def run(limit: int = 5000) -> dict:
    sm = SupabaseManager()
    client = sm.client
    # Scan all Threads posts (limit applied) to ensure cleanup after UI changes
    rows = (
        client.table("posts")
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
            client.table("posts").update({"content": cleaned}).eq(
                "post_id", pid
            ).execute()
            fixed += 1
        except Exception:
            skipped += 1
    return {"scanned": len(data), "fixed": fixed, "skipped": skipped}


if __name__ == "__main__":
    res = run()
    print(res)
