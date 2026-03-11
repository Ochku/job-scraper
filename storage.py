"""
storage.py — SQLite-backed seen-job tracking.
Ensures we never alert on the same job twice.
"""
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "seen_jobs.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            id          TEXT PRIMARY KEY,
            title       TEXT,
            company     TEXT,
            source      TEXT,
            first_seen  TEXT
        )
    """)
    conn.commit()
    return conn


def make_job_id(title: str, company: str, url: str) -> str:
    """Stable fingerprint so duplicate listings don't sneak through."""
    raw = f"{title.lower().strip()}|{company.lower().strip()}|{url.strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def filter_new_jobs(jobs: list[dict]) -> list[dict]:
    """Return only jobs not previously seen; persist the new ones."""
    if not jobs:
        return []

    conn = _connect()
    new_jobs = []
    now = datetime.utcnow().isoformat()

    for job in jobs:
        jid = job.get("id") or make_job_id(
            job.get("title", ""), job.get("company", ""), job.get("url", "")
        )
        row = conn.execute("SELECT id FROM seen_jobs WHERE id = ?", (jid,)).fetchone()
        if row is None:
            new_jobs.append({**job, "id": jid})
            conn.execute(
                "INSERT INTO seen_jobs (id, title, company, source, first_seen) VALUES (?,?,?,?,?)",
                (jid, job.get("title", ""), job.get("company", ""), job.get("source", ""), now),
            )

    conn.commit()
    conn.close()
    return new_jobs


def seen_count() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
    conn.close()
    return n
