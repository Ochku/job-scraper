"""
notifier.py — Sends a nicely formatted HTML email digest of new jobs.
"""
from __future__ import annotations
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

logger = logging.getLogger(__name__)


def send_alert(jobs: list[dict], config: dict) -> bool:
    """
    Send an HTML email with the list of new jobs.
    Returns True on success.
    """
    email_cfg = config.get("email", {})
    smtp_host = email_cfg.get("smtp_host", "smtp.gmail.com")
    smtp_port = int(email_cfg.get("smtp_port", 587))
    use_tls = email_cfg.get("use_tls", True)
    sender = email_cfg.get("sender", "")
    recipients = email_cfg.get("recipients", [])
    subject_prefix = email_cfg.get("subject_prefix", "[Job Alert]")
    password = os.getenv("EMAIL_PASSWORD", "")

    if not sender or not recipients:
        logger.error("[Email] sender or recipients not configured.")
        return False
    if not password:
        logger.error("[Email] EMAIL_PASSWORD not set in .env")
        return False

    subject = f"{subject_prefix} {len(jobs)} new job{'s' if len(jobs) != 1 else ''} found — {datetime.now().strftime('%b %d, %Y')}"
    html = _build_html(jobs, config)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(_build_plain(jobs), "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(sender, password)
            server.sendmail(sender, recipients, msg.as_string())
        logger.info(f"[Email] Alert sent to {recipients} ({len(jobs)} jobs)")
        return True
    except Exception as exc:
        logger.error(f"[Email] Failed to send: {exc}")
        return False


# ── HTML template ────────────────────────────────────────────────────────────

def _build_html(jobs: list[dict], config: dict) -> str:
    search_cfg = config.get("search", {})
    location = search_cfg.get("location", "")

    cards = ""
    # Group by source for a cleaner layout
    sources_seen: dict[str, int] = {}
    for job in jobs:
        src = job.get("source", "unknown")
        sources_seen[src] = sources_seen.get(src, 0) + 1

    for job in jobs:
        salary_html = (
            f'<span style="color:#16a34a;font-weight:600">{job["salary"]}</span>'
            if job.get("salary")
            else '<span style="color:#9ca3af">Not specified</span>'
        )
        date_html = f'<span style="color:#6b7280">{job.get("date_posted","")}</span>' if job.get("date_posted") else ""
        cards += f"""
        <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:18px 22px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:6px;">
            <div>
              <a href="{job.get('url','#')}" style="font-size:17px;font-weight:700;color:#1d4ed8;text-decoration:none;">
                {job.get('title','')}
              </a>
              <div style="color:#374151;margin-top:3px;font-size:14px;">
                🏢 {job.get('company','')} &nbsp;·&nbsp; 📍 {job.get('location','')}
              </div>
            </div>
            <span style="font-size:11px;background:#f3f4f6;color:#6b7280;padding:3px 9px;border-radius:99px;">
              {job.get('source','').split('/')[0].upper()}
            </span>
          </div>
          <div style="margin-top:10px;font-size:13px;color:#4b5563;line-height:1.6;">
            {job.get('description','')[:300]}{'…' if len(job.get('description','')) > 300 else ''}
          </div>
          <div style="margin-top:10px;font-size:13px;display:flex;gap:18px;flex-wrap:wrap;">
            <span>💰 {salary_html}</span>
            {f'<span>📅 {date_html}</span>' if job.get('date_posted') else ''}
          </div>
          <a href="{job.get('url','#')}" style="display:inline-block;margin-top:12px;background:#1d4ed8;color:#fff;
             text-decoration:none;padding:7px 16px;border-radius:6px;font-size:13px;font-weight:600;">
            View Job →
          </a>
        </div>
        """

    source_pills = " ".join(
        f'<span style="background:#dbeafe;color:#1d4ed8;padding:2px 10px;border-radius:99px;font-size:12px;">'
        f'{s} ({n})</span>'
        for s, n in sources_seen.items()
    )

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
    <body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <div style="max-width:660px;margin:32px auto;padding:0 16px;">

        <!-- Header -->
        <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);border-radius:12px;padding:28px 32px;margin-bottom:24px;">
          <h1 style="margin:0;color:#fff;font-size:22px;">🔔 Job Alert Digest</h1>
          <p style="margin:6px 0 0;color:#bfdbfe;font-size:14px;">
            {len(jobs)} new position{'s' if len(jobs)!=1 else ''} matching your search &nbsp;·&nbsp; {datetime.now().strftime('%B %d, %Y')}
          </p>
          <p style="margin:8px 0 0;color:#bfdbfe;font-size:13px;">📍 {location}</p>
          <div style="margin-top:12px;">{source_pills}</div>
        </div>

        <!-- Job cards -->
        {cards}

        <!-- Footer -->
        <div style="text-align:center;color:#9ca3af;font-size:12px;margin-top:24px;padding-bottom:32px;">
          Sent by your Job Alert bot · Edit <code>config.yaml</code> to change keywords or filters
        </div>
      </div>
    </body>
    </html>
    """


def _build_plain(jobs: list[dict]) -> str:
    lines = [f"Job Alert — {len(jobs)} new job(s) found\n" + "=" * 50]
    for job in jobs:
        lines.append(
            f"\n{job.get('title','')} @ {job.get('company','')}\n"
            f"Location : {job.get('location','')}\n"
            f"Salary   : {job.get('salary') or 'N/A'}\n"
            f"Source   : {job.get('source','')}\n"
            f"Link     : {job.get('url','')}\n"
            + "-" * 40
        )
    return "\n".join(lines)
