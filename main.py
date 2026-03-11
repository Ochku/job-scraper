#!/usr/bin/env python3
"""
main.py — Job Alert entry point.

Usage:
  python main.py               # run with config.yaml
  python main.py --dry-run     # fetch & print, don't send email
  python main.py --reset       # clear seen-jobs DB (re-alerts everything)
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from storage import filter_new_jobs, seen_count
from notifier import send_alert
from jobspy_source import fetch as fetch_jobspy
from adzuna_source import fetch as fetch_adzuna
from remotive_source import fetch as fetch_remotive

# ── Bootstrap ────────────────────────────────────────────────────────────────

load_dotenv()  # loads .env from current directory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


# ── Filters ───────────────────────────────────────────────────────────────────

def apply_filters(jobs: list[dict], config: dict) -> list[dict]:
    filters = config.get("filters", {})
    exclude_kw = [k.lower() for k in filters.get("exclude_title_keywords", [])]
    require_salary = filters.get("require_salary", False)

    result = []
    for job in jobs:
        title_lower = job.get("title", "").lower()
        if any(k in title_lower for k in exclude_kw):
            continue
        if require_salary and not job.get("salary"):
            continue
        result.append(job)
    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def run(config: dict, dry_run: bool = False) -> None:
    search = config.get("search", {})
    keywords: list[str] = search.get("keywords", [])
    location: str = search.get("location", "")
    max_results: int = search.get("max_results_per_source", 25)
    remote_ok: bool = search.get("remote_ok", True)
    max_age_days: int = config.get("filters", {}).get("max_age_days", 7)
    sources_cfg: dict = config.get("sources", {})

    if not keywords:
        logger.error("No keywords defined in config.yaml — nothing to do.")
        sys.exit(1)

    logger.info(f"Starting job search | keywords={keywords} | location='{location}'")
    logger.info(f"Jobs already seen in DB: {seen_count()}")

    # ── Fetch from all enabled sources ───────────────────────────────────────
    all_jobs: list[dict] = []

    if sources_cfg.get("jobspy", True):
        all_jobs += fetch_jobspy(keywords, location, max_results, remote_ok, max_age_days)

    if sources_cfg.get("adzuna", True):
        all_jobs += fetch_adzuna(keywords, location, max_results, remote_ok, max_age_days)

    if sources_cfg.get("remotive", True):
        all_jobs += fetch_remotive(keywords, location, max_results, remote_ok, max_age_days)

    logger.info(f"Total fetched (before dedup): {len(all_jobs)}")

    # ── Apply content filters ─────────────────────────────────────────────────
    all_jobs = apply_filters(all_jobs, config)
    logger.info(f"After content filters: {len(all_jobs)}")

    # ── Deduplicate against DB ────────────────────────────────────────────────
    if not dry_run:
        new_jobs = filter_new_jobs(all_jobs)
    else:
        # In dry-run mode don't persist, just show everything
        new_jobs = all_jobs

    logger.info(f"New (not seen before): {len(new_jobs)}")

    if not new_jobs:
        logger.info("No new jobs found — no email sent.")
        return

    # ── Print summary ─────────────────────────────────────────────────────────
    for job in new_jobs:
        logger.info(
            f"  [{job.get('source','?'):20s}] {job.get('title','')[:50]:50s}  |  {job.get('company','')}"
        )

    # ── Send email ────────────────────────────────────────────────────────────
    min_jobs = config.get("email", {}).get("min_jobs_to_send", 1)
    if len(new_jobs) < min_jobs:
        logger.info(f"Only {len(new_jobs)} new job(s), below min_jobs_to_send={min_jobs}. Skipping email.")
        return

    if dry_run:
        logger.info("[DRY RUN] Would send email — skipping actual send.")
    else:
        send_alert(new_jobs, config)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Alert Monitor")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Fetch & print without sending email")
    parser.add_argument("--reset", action="store_true", help="Clear the seen-jobs database")
    args = parser.parse_args()

    if args.reset:
        db = Path("seen_jobs.db")
        if db.exists():
            db.unlink()
            logger.info("seen_jobs.db deleted — fresh start.")
        sys.exit(0)

    cfg = load_config(args.config)
    run(cfg, dry_run=args.dry_run)