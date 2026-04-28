"""
AI News Daily — RSS aggregator.

Fetches a curated set of AI-focused RSS feeds, normalizes entries,
dedupes by title/url, categorizes them, and writes data/news.json
which the static frontend reads.

No external dependencies beyond `feedparser`. Designed to run once a day
from a GitHub Actions cron.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import feedparser  # type: ignore

# -----------------------------------------------------------------------------
# Feeds — curated AI-focused sources. All free, all RSS.
# -----------------------------------------------------------------------------
FEEDS: list[dict] = [
    # Major tech press — AI sections
    {"name": "TechCrunch AI",       "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "Industry"},
    {"name": "The Verge AI",        "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "category": "Industry"},
    {"name": "MIT Tech Review AI",  "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "category": "Research"},
    {"name": "Ars Technica AI",     "url": "https://arstechnica.com/ai/feed/", "category": "Industry"},
    {"name": "VentureBeat AI",      "url": "https://venturebeat.com/category/ai/feed/", "category": "Industry"},
    {"name": "Wired AI",            "url": "https://www.wired.com/feed/tag/ai/latest/rss", "category": "Industry"},

    # Lab / company blogs
    {"name": "OpenAI",              "url": "https://openai.com/blog/rss.xml", "category": "Labs"},
    {"name": "Google AI",           "url": "https://blog.google/technology/ai/rss/", "category": "Labs"},
    {"name": "DeepMind",            "url": "https://deepmind.google/blog/rss.xml", "category": "Labs"},
    {"name": "Hugging Face",        "url": "https://huggingface.co/blog/feed.xml", "category": "Open Source"},

    # Research firehose (high volume — capped per feed)
    {"name": "arXiv cs.AI",         "url": "https://export.arxiv.org/rss/cs.AI", "category": "Research"},
    {"name": "arXiv cs.LG",         "url": "https://export.arxiv.org/rss/cs.LG", "category": "Research"},

    # Aggregators / community
    {"name": "Hacker News (AI)",    "url": "https://hnrss.org/newest?q=AI+OR+LLM+OR+GPT&points=50", "category": "Community"},
]

# How many items to keep per feed when normalizing (prevents arXiv from drowning others)
PER_FEED_CAP = 12
# How many total items to keep in the final JSON
TOTAL_CAP = 120
# Drop entries older than this many days
MAX_AGE_DAYS = 14

ROOT = Path(__file__).parent
OUT_PATH = ROOT / "data" / "news.json"
OUT_JS_PATH = ROOT / "data" / "news.js"  # also written so file:// preview works


def clean_text(s: str | None, max_len: int = 280) -> str:
    """Strip HTML tags and collapse whitespace; truncate cleanly."""
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > max_len:
        s = s[: max_len - 1].rstrip() + "…"
    return s


def parse_published(entry) -> dt.datetime | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        v = getattr(entry, key, None) or (entry.get(key) if hasattr(entry, "get") else None)
        if v:
            try:
                return dt.datetime(*v[:6], tzinfo=dt.timezone.utc)
            except Exception:
                pass
    return None


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc
        return host.replace("www.", "")
    except Exception:
        return ""


def make_id(title: str, link: str) -> str:
    return hashlib.md5(f"{title}|{link}".encode("utf-8")).hexdigest()[:12]


def fetch_feed(feed_def: dict) -> list[dict]:
    print(f"  fetching: {feed_def['name']}")
    try:
        parsed = feedparser.parse(feed_def["url"])
    except Exception as e:
        print(f"    !! failed: {e}")
        return []

    items: list[dict] = []
    for entry in parsed.entries[:PER_FEED_CAP]:
        title = clean_text(entry.get("title"), 220)
        link = entry.get("link") or ""
        if not title or not link:
            continue
        summary = clean_text(entry.get("summary") or entry.get("description"), 320)
        published = parse_published(entry)

        # try to grab an image from media tags
        image = ""
        media = entry.get("media_content") or entry.get("media_thumbnail") or []
        if isinstance(media, list) and media:
            image = (media[0] or {}).get("url", "") or ""
        if not image:
            for link_obj in entry.get("links", []) or []:
                if "image" in (link_obj.get("type") or ""):
                    image = link_obj.get("href", "")
                    break

        items.append({
            "id": make_id(title, link),
            "title": title,
            "summary": summary,
            "url": link,
            "source": feed_def["name"],
            "domain": domain_of(link),
            "category": feed_def["category"],
            "image": image,
            "published": published.isoformat() if published else None,
        })
    return items


def main() -> int:
    print(f"AI News build — {dt.datetime.now(dt.timezone.utc).isoformat()}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_items: list[dict] = []
    for feed in FEEDS:
        all_items.extend(fetch_feed(feed))

    # Drop ancient items
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MAX_AGE_DAYS)
    fresh = [
        item for item in all_items
        if not item["published"] or dt.datetime.fromisoformat(item["published"]) >= cutoff
    ]

    # Dedupe by (title.lower(), domain) — different sources covering same story
    seen: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for item in fresh:
        key = (re.sub(r"\W+", "", item["title"].lower())[:80], item["domain"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    # Sort by published desc (None at the end)
    deduped.sort(
        key=lambda it: it["published"] or "0000",
        reverse=True,
    )

    final = deduped[:TOTAL_CAP]

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "count": len(final),
        "categories": sorted({it["category"] for it in final}),
        "items": final,
    }

    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    OUT_PATH.write_text(json_text, encoding="utf-8")
    # JS shim — lets the page render when opened via file:// (Chrome blocks fetch from file://)
    OUT_JS_PATH.write_text(f"window.NEWS_DATA = {json_text};\n", encoding="utf-8")
    print(f"  wrote {len(final)} items -> {OUT_PATH.relative_to(ROOT)} + news.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
