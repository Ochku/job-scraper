"""
sources/remotive_source.py
Remotive is a free remote-job board with a public API — no key needed.
Great for finding remote-friendly roles in tech.
API docs: https://remotive.com/api-documentation
"""
from __future__ import annotations
import logging
import requests
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def fetch(keywords: list[str], location: str, max_results: int,
          remote_ok: bool, max_age_days: int) -> list[dict]:
    if not remote_ok:
        logger.info("[Remotive] remote_ok=false — skipping remote-only source.")
        return []

    all_jobs: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=max_age_days)

    for keyword in keywords:
        logger.info(f"[Remotive] Searching: '{keyword}'")
        try:
            resp = requests.get(
                "https://remotive.com/api/remote-jobs",
                params={"search": keyword, "limit": max_results},
                timeout=15,
            )
            resp.raise_for_status()
            jobs = resp.json().get("jobs", [])

            for item in jobs:
                # Filter by age
                pub_str = item.get("publication_date", "")
                if pub_str:
                    try:
                        pub_dt = datetime.strptime(pub_str[:10], "%Y-%m-%d")
                        if pub_dt < cutoff:
                            continue
                    except ValueError:
                        pass

                job = {
                    "source": "remotive",
                    "title": item.get("title", ""),
                    "company": item.get("company_name", ""),
                    "location": item.get("candidate_required_location", "Remote"),
                    "url": item.get("url", ""),
                    "description": _strip_html(item.get("description", ""))[:500],
                    "salary": item.get("salary", ""),
                    "date_posted": pub_str[:10] if pub_str else "",
                    "keyword": keyword,
                }
                all_jobs.append(job)

        except Exception as exc:
            logger.error(f"[Remotive] Error for keyword '{keyword}': {exc}")

    return all_jobs


def _strip_html(text: str) -> str:
    """Very lightweight HTML tag remover."""
    import re
    return re.sub(r"<[^>]+>", " ", text).strip()
