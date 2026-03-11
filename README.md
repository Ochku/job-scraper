# 🔔 Job Alert Monitor

A Python job alert system that scrapes **Indeed, Glassdoor, LinkedIn** (via JobSpy), **Adzuna API**, and **Remotive**, deduplicates results, and emails you a daily digest of new postings.

---

## 📦 Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your search
Edit **`config.yaml`**:
```yaml
search:
  keywords:
    - "machine learning engineer"
    - "data scientist"
  location: "Amsterdam, Netherlands"
  remote_ok: true
```

### 3. Set credentials
```bash
cp .env.example .env
```
Then edit `.env`:
```
EMAIL_PASSWORD=your_gmail_app_password
ADZUNA_APP_ID=your_id
ADZUNA_API_KEY=your_key
```

> **Gmail tip**: Use an [App Password](https://support.google.com/accounts/answer/185833) (not your real password). Go to Google Account → Security → 2-Step Verification → App passwords.

> **Adzuna tip**: Free tier available at [developer.adzuna.com](https://developer.adzuna.com) — 250 requests/day is more than enough.

---

## 🚀 Usage

```bash
# Test run — fetches jobs and prints them, no email sent
python main.py --dry-run

# Normal run — fetches, deduplicates, sends email if new jobs found
python main.py

# Use a different config file
python main.py --config my_other_search.yaml

# Clear the seen-jobs database (forces re-alerting of all jobs)
python main.py --reset
```

---

## ⏰ Schedule daily runs

### macOS / Linux (cron)
```bash
crontab -e
```
Add this line to run at 8:00 AM every day:
```
0 8 * * * cd /path/to/job-alert && python main.py >> logs/job_alert.log 2>&1
```

### Windows (Task Scheduler)
Create a basic task → trigger: daily → action: `python C:\path\to\job-alert\main.py`

---

## 🗂 Project structure

```
job-alert/
├── main.py              # Entry point & orchestration
├── config.yaml          # Your search config (edit this!)
├── .env                 # Secrets (never commit this)
├── .env.example         # Template for .env
├── requirements.txt
├── storage.py           # SQLite deduplication
├── notifier.py          # Email formatting & sending
├── seen_jobs.db         # Auto-created; tracks seen jobs
└── sources/
    ├── jobspy_source.py  # Indeed, Glassdoor, LinkedIn, ZipRecruiter
    ├── adzuna_source.py  # Adzuna Jobs API
    └── remotive_source.py # Remotive (remote jobs, free, no key)
```

---

## 🔧 Tips

| Goal | How |
|---|---|
| Search multiple cities | Create separate `config_berlin.yaml`, `config_amsterdam.yaml` etc. |
| Only remote jobs | Set `remote_ok: true` and disable `jobspy`/`adzuna` |
| Add more keywords | Append to the `keywords` list in `config.yaml` |
| Stop getting old jobs | Run `python main.py --reset` then re-run |
| Filter seniority | Add terms like `"staff"`, `"principal"` to `exclude_title_keywords` |

---

## ⚠️ Notes on scraping

- **Indeed / Glassdoor**: These sites actively fight scraping and may block requests over time. JobSpy uses rotating user-agents but results may occasionally be empty. This is normal.
- **LinkedIn**: LinkedIn Jobs are included via JobSpy but rate-limits apply. For heavy usage, consider the official [LinkedIn Jobs API](https://developer.linkedin.com/).
- **Adzuna & Remotive**: These are official APIs and are reliable.
