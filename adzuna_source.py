"""
sources/adzuna_source.py
Uses the free Adzuna Jobs API.
Sign up at https://developer.adzuna.com — free tier: 250 req/day.
Set ADZUNA_APP_ID and ADZUNA_API_KEY in your .env file.
"""
from __future__ import annotations
import logging
import os
import requests
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Adzuna country codes → https://api.adzuna.com/v1/api/jobs/{country}/search/1
COUNTRY_CODE = "nl"   # nl=Netherlands, gb=UK, us=US, de=Germany, etc.


def fetch(keywords: list[str], location: str, max_results: int,
          remote_ok: bool, max_age_days: int) -> list[dict]:
    app_id = os.getenv("ADZUNA_APP_ID")
    api_key = os.getenv("ADZUNA_API_KEY")

    if not app_id or not api_key:
        logger.warning("[Adzuna] ADZUNA_APP_ID / ADZUNA_API_KEY not set — skipping.")
        return []

    all_jobs: list[dict] = []

    for keyword in keywords:
        logger.info(f"[Adzuna] Searching: '{keyword}' in '{location}'")
        try:
            params = {
                "app_id": app_id,
                "app_key": api_key,
                "results_per_page": min(max_results, 50),
                "what": keyword,
                "where": location,
                "max_days_old": max_age_days,
                "content-type": "application/json",
            }
            url = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY_CODE}/search/1"
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("results", []):
                job = {
                    "source": "adzuna",
                    "title": item.get("title", ""),
                    "company": item.get("company", {}).get("display_name", ""),
                    "location": item.get("location", {}).get("display_name", ""),
                    "url": item.get("redirect_url", ""),
                    "description": item.get("description", "")[:500],
                    "salary": _fmt_salary(item),
                    "date_posted": item.get("created", ""),
                    "keyword": keyword,
                }
                all_jobs.append(job)

        except Exception as exc:
            logger.error(f"[Adzuna] Error for keyword '{keyword}': {exc}")

    return all_jobs


def _fmt_salary(item: dict) -> str:
    low = item.get("salary_min")
    high = item.get("salary_max")
    if low and high:
        return f"€ {low:,.0f} – {high:,.0f}"
    if low:
        return f"€ {low:,.0f}+"
    return ""
