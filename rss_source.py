"""
rss_source.py — Fetches jobs via RSS feeds (no API key, no scraping).

Sources included:
  - Indeed          (strong NL support)
  - LinkedIn        (via unofficial RSS-style URL)
  - IT Jobs Watch   (tech-focused)
  - Jobsite         (EU listings)

These are all standard RSS/XML endpoints — no auth needed.
"""
from __future__ import annotations
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Feed templates — {query} and {location} are substituted at runtime
FEEDS = [
    {
        "name": "indeed",
        "url": "https://www.indeed.com/rss?q={query}&l={location}&sort=date&fromage={days}",
    },
    {
        "name": "indeed_nl",
        "url": "https://nl.indeed.com/rss?q={query}&l={location}&sort=date&fromage={days}",
    },
    {
        "name": "linkedin",
        # LinkedIn's public job search page exposes an undocumented feed
        "url": (
            "https://www.linkedin.com/jobs/search/?keywords={query}"
            "&location={location}&f_TPR=r{seconds}&count={count}&start=0"
            "&format=json"  # we'll handle HTML parsing fallback
        ),
        "skip": True,  # LinkedIn blocks RSS — disabled by default
    },
]


def fetch(keywords: list[str], location: str, max_results: int,
          remote_ok: bool, max_age_days: int) -> list[dict]:
    all_jobs: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    active_feeds = [f for f in FEEDS if not f.get("skip")]

    for feed in active_feeds:
        for keyword in keywords:
            url = feed["url"].format(
                query=quote_plus(keyword),
                location=quote_plus(location),
                days=max_age_days,
                seconds=max_age_days * 86400,
                count=max_results,
            )
            logger.info(f"[RSS:{feed['name']}] '{keyword}' in '{location}'")
            jobs = _parse_feed(url, feed["name"], keyword, cutoff, max_results)
            logger.info(f"[RSS:{feed['name']}] Got {len(jobs)} results")
            all_jobs += jobs

    return all_jobs


def _parse_feed(url: str, source: str, keyword: str,
                cutoff: datetime, max_results: int) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[RSS:{source}] Request failed: {e}")
        return []

    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.error(f"[RSS:{source}] XML parse error: {e}")
        return []

    # Handle both RSS <channel><item> and Atom <entry> formats
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    jobs = []
    for item in items[:max_results]:
        title = _text(item, ["title"])
        url_ = _text(item, ["link", "guid"]) or _text(item, ["atom:link"], ns)
        company = _text(item, ["source", "author", "dc:creator"])
        location_ = _text(item, ["location", "georss:point"])
        description = _clean(_text(item, ["description", "summary", "content"]))
        date_str = _text(item, ["pubDate", "published", "updated", "dc:date"])

        # Parse and filter by date
        pub_dt = _parse_date(date_str)
        if pub_dt and pub_dt < cutoff:
            continue

        jobs.append({
            "source": source,
            "title": title or "",
            "company": company or "",
            "location": location_ or "",
            "url": url_ or "",
            "description": description[:500] if description else "",
            "salary": "",
            "date_posted": pub_dt.strftime("%Y-%m-%d") if pub_dt else date_str or "",
            "keyword": keyword,
        })

    return jobs


def _text(el: ET.Element, tags: list[str], ns: dict | None = None) -> str:
    for tag in tags:
        child = el.find(tag, ns or {})
        if child is not None and child.text:
            return child.text.strip()
    return ""


def _parse_date(s: str) -> datetime | None:
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).replace(tzinfo=None)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def _clean(text: str) -> str:
    """Strip HTML tags from description."""
    import re
    return re.sub(r"<[^>]+>", " ", text or "").strip()
