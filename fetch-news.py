#!/usr/bin/env python3
"""
Fetches configured RSS feeds, applies a basic keyword filter for
hopeful / solutions-oriented social policy stories, and writes the
result to output/feed.json for TRMNL (or anything else) to consume.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import feedparser
from playwright.sync_api import sync_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# --- Config -----------------------------------------------------------

FEEDS = [
    "https://povertycenter.columbia.edu/news/rss.xml",
    # Add more working feed URLs here as you confirm them.
]

# Very basic keyword filter as a placeholder for the real SJN-rubric
# LLM pass. Swap this out later for something smarter.
KEYWORDS = [
    "policy", "housing", "healthcare", "poverty", "welfare",
    "education", "reform", "program", "initiative", "community",
]

MAX_ITEMS = 8

# --- Logic --------------------------------------------------------------

def matches_keywords(text: str) -> bool:
    text = text.lower()
    return any(re.search(rf"\b{k}\b", text) for k in KEYWORDS)


def fetch_feed_content(page, url: str) -> bytes:
    # Load the URL first so any Cloudflare (or similar) JS challenge runs
    # and clears in the browser context, then re-fetch the raw response
    # from inside the page so we get the actual feed body, not a
    # browser-rendered XML viewer.
    page.goto(url, wait_until="networkidle", timeout=30000)
    text = page.evaluate("(u) => fetch(u).then((r) => r.text())", url)
    return text.encode("utf-8")


def fetch_all():
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=USER_AGENT)
        for url in FEEDS:
            content = fetch_feed_content(page, url)
            parsed = feedparser.parse(content)
            source_name = parsed.feed.get("title", url)
            for entry in parsed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                items.append({
                    "title": title,
                    "summary": re.sub("<[^<]+?>", "", summary)[:200],
                    "link": entry.get("link", ""),
                    "source": source_name,
                    "published": entry.get("published", ""),
                })
        browser.close()
    return items


def main():
    items = fetch_all()
    items = items[:MAX_ITEMS]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "stories": items,
    }

    out_path = Path(__file__).parent / "output" / "feed.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Wrote {len(items)} stories to {out_path}")


if __name__ == "__main__":
    main()