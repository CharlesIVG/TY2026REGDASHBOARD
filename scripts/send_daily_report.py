#!/usr/bin/env python3
"""
Tokyo Yamathon 2026 - Registration Dashboard
------------------------------------------------------------------
Developed by SxS Partners for the International Volunteer Group-Japan
and Tokyo Yamathon.

This code is the intellectual property of SxS Partners. All rights
remain the property of SxS Partners and the project developer,
C. Stewart.

(c) SxS Partners - All rights reserved.
------------------------------------------------------------------
Builds and emails the daily Tokyo Yamathon registration report.

Reads data/history.csv (built by scripts/collect_snapshot.py, run on a
schedule throughout the day) and summarizes:
  - new teams registered "yesterday" (the day that just ended in JST),
    broken down by Full / Half / Half-a-Half
  - roughly when during the day those registrations landed (hourly)
  - running cumulative totals and % of slots filled per course

NOTE ON DATA LIMITS: history.csv stores aggregate counts only. Even
when sourced from the Webscorer API, the collector deliberately keeps
nothing but totals - participant-level records are never written to
this (public) repo, so "members per team" cannot be computed here. That
limit is stated explicitly in the email rather than silently omitted.

Run via .github/workflows/daily-report.yml, scheduled for 00:05 JST.
"""
import csv
import json
import os
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

JST = timezone(timedelta(hours=9))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(REPO_ROOT, "data", "history.csv")

# Slot capacities - keep in sync with index.html
FULL_SLOTS = 700
HALF_SLOTS = 250
QUARTER_SLOTS = 150
EVENT_GOAL = 1100

# Fundraising - derived, not reported. Webscorer exposes no donation or fee
# data via its API (verified), so funds are calculated as teams x entry fee.
FEE_PER_TEAM = 16000
FUNDS_GOAL = 17600000        # = 1,100 teams x Y16,000

CATEGORY_LABELS = {"full": "Full Course", "half": "Half Course", "quarter": "Half-a-Half"}
DASHBOARD_URL = "https://charlesivg.github.io/TY2026REGDASHBOARD/"

# Fixed wording that opens and closes every report. Edit the strings here -
# nothing else in the file needs to change. Blank strings produce blank lines.
GREETING = "Good Morning Rockstars - I've got your daily progress report for the teams in for 2026!"
SIGNOFF = [
    "Have a great day and - keep on truckin!",
    "Let's Go!",
    "YamaGo",
]


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in ("full", "half", "quarter", "total"):
            r[k] = int(r[k])
    return rows


def report_date_jst() -> str:
    """Defaults to 'the day that just ended' - i.e. yesterday in JST,
    since this is meant to run just after midnight JST. Override with
    REPORT_DATE=YYYY-MM-DD for manual/testing runs."""
    override = os.environ.get("REPORT_DATE")
    if override:
        return override
    now_jst = datetime.now(timezone.utc).astimezone(JST)
    yesterday = now_jst - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


def build_summary(rows, date_str):
    day_rows = [r for r in rows if r["date_jst"] == date_str]
    prior_rows = [r for r in rows if r["date_jst"] < date_str]
    later_rows = [r for r in rows if r["date_jst"] > date_str]

    baseline = prior_rows[-1] if prior_rows else (day_rows[0] if day_rows else None)
    closing = day_rows[-1] if day_rows else (later_rows[0] if later_rows else baseline)
    latest_overall = rows[-1] if rows else None

    # Only report a daily figure when the day AND the day before it were both
    # actually sampled. Without that, the subtraction sweeps up every
    # registration since the last snapshot and reports it as one day's work -
    # which is how "68 teams today" was produced from a six-day gap.
    prev_day = (
        datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=1)
    ).strftime("%Y-%m-%d")
    sampled_dates = {r["date_jst"] for r in rows}
    measured = date_str in sampled_dates and prev_day in sampled_dates

    if measured and baseline and closing:
        deltas = {
            k: max(0, closing[k] - baseline[k])
            for k in ("full", "half", "quarter", "total")
        }
    else:
        deltas = {"full": None, "half": None, "quarter": None, "total": None}

    # Hourly pattern: last snapshot per hour bucket on this date, diffed
    # against the previous bucket (or baseline for the first bucket).
    hourly = []
    if day_rows:
        buckets = {}
        for r in day_rows:
            hour = r["time_jst"][:2]
            buckets[hour] = r  # keep the last one seen per hour
        prev = baseline
        for hour in sorted(buckets):
            cur = buckets[hour]
            if prev:
                added = max(0, cur["total"] - prev["total"])
            else:
                added = 0
            if added > 0:
                hourly.append((f"{hour}:00", added))
            prev = cur

    return {
        "date": date_str,
        "have_data": bool(day_rows),
        "baseline": baseline,
        "closing": closing,
        "deltas": deltas,
        "hourly": hourly,
        "latest_overall": latest_overall,
        "snapshot_count": len(day_rows),
    }


def pct(n, d):
    return f"{(n / d * 100):.1f}%" if d else "n/a"


def load_plan():
    path = os.path.join(REPO_ROOT, "data", "weekly.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_teamsize():
    path = os.path.join(REPO_ROOT, "data", "teamsize.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def render_text(summary) -> str:
    """Plain numbers. No graphics, no tables, no decoration - a straight
    status read for the team, short enough to take in on a phone."""
    d = summary["deltas"]
    latest = summary["latest_overall"]
    wk = load_plan()

    L = []
    L.append(f"TOKYO YAMATHON - REGISTRATION REPORT")
    L.append(f"{summary['date']} (JST)")
    L.append("")
    if GREETING:
        L.append(GREETING)
        L.append("")

    # --- are we on target ---
    if wk:
        # weekly.json stores "amber" as its status value; the team asked for
        # red/yellow/green language, so translate on display only.
        status = (wk.get("status") or "pending").upper()
        if status == "AMBER":
            status = "YELLOW"
        cum = wk.get("cumulative", 0)
        target = wk.get("targetNow")
        goal = wk.get("goal", EVENT_GOAL)
        days = wk.get("daysRemaining")
        L.append(f"STATUS: {status}")
        if target:
            diff = round(cum - target)
            word = "ahead of" if diff >= 0 else "behind"
            L.append(f"  {cum} teams vs {round(target)} planned by now ({abs(diff)} {word} plan)")
        L.append(f"  {cum} of {goal} goal ({pct(cum, goal)})")
        if days is not None:
            L.append(f"  {days} days until registration closes")
        L.append("")

    # --- yesterday ---
    if d.get("total") is None:
        L.append("NEW TEAMS YESTERDAY: not measured")
        L.append("  (needs a full day of tracking either side to be accurate)")
    else:
        L.append(f"NEW TEAMS YESTERDAY: {d['total']}")
        L.append(f"  Full         {d['full']}")
        L.append(f"  Half         {d['half']}")
        L.append(f"  Half-a-Half  {d['quarter']}")
    L.append("")

    # --- totals ---
    if latest:
        L.append("RUNNING TOTALS")
        L.append(f"  Full         {latest['full']:>4} / {FULL_SLOTS}   {pct(latest['full'], FULL_SLOTS)}")
        L.append(f"  Half         {latest['half']:>4} / {HALF_SLOTS}   {pct(latest['half'], HALF_SLOTS)}")
        L.append(f"  Half-a-Half  {latest['quarter']:>4} / {QUARTER_SLOTS}   {pct(latest['quarter'], QUARTER_SLOTS)}")
        L.append(f"  TOTAL        {latest['total']:>4} / {EVENT_GOAL}  {pct(latest['total'], EVENT_GOAL)}")
        gen, spo = latest.get("general"), latest.get("sponsor")
        if gen not in (None, "") or spo not in (None, ""):
            L.append("")
            L.append("BY CHANNEL")
            L.append(f"  General      {gen}")
            L.append(f"  Sponsor      {spo}")
    # --- fundraising ---
    if latest:
        raised = latest["total"] * FEE_PER_TEAM
        gap = max(0, FUNDS_GOAL - raised)
        p = raised / FUNDS_GOAL * 100 if FUNDS_GOAL else 0
        status = "GREEN" if p >= 85 else "YELLOW" if p >= 50 else "RED"
        L.append("")
        L.append(f"FUNDS RAISED: \u00a5{raised:,}   [{status}]")
        L.append(f"  Goal         \u00a5{FUNDS_GOAL:,}")
        L.append(f"  Progress     {p:.1f}%")
        L.append(f"  Still needed \u00a5{gap:,}  ({gap // FEE_PER_TEAM} more teams)")

    # --- participants (from periodic export; API has no roster) ---
    ts = load_teamsize()
    if ts and ts.get("people"):
        L.append("")
        L.append("PARTICIPANTS")
        L.append(f"  People       {ts['people']}")
        L.append(f"  Avg per team {ts['avgTeamSize']}")
        L.append(f"  (from registration export {ts['asOf']} - not live)")
    L.append("")

    # --- this week vs plan ---
    if wk:
        cur = [w for w in wk.get("weeks", []) if w.get("started") and not w.get("baseline")]
        if cur:
            w = cur[-1]
            L.append(f"THIS WEEK ({w['label']}, {w['start']} to {w['end']})")
            L.append(f"  Target this week   {w['targetNew']}")
            L.append(f"  Actual so far      {w['actualNew'] if w['actualNew'] is not None else '-'}")
            L.append(f"  Cumulative target  {w['targetCum']}")
            L.append("")

    L.append(f"Dashboard: {DASHBOARD_URL}")
    if SIGNOFF:
        L.append("")
        L.extend(SIGNOFF)
    return "\n".join(L)


def send_email(subject: str, text_body: str) -> None:
    host = os.environ.get("SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER")
    password = os.environ.get("SMTP_PASS")
    mail_from = os.environ.get("MAIL_FROM", user or "")
    mail_to = os.environ.get("MAIL_TO", "allivg@ivgjapan.org")

    if not host or not user or not password:
        print("SMTP_HOST/SMTP_USER/SMTP_PASS not set - printing report instead of sending.\n")
        print(text_body)
        return

    # Plain text only - the team asked for straight numbers, no graphics.
    msg = MIMEText(text_body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = mail_to

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        if port != 465:
            server.starttls()
            server.ehlo()
        server.login(user, password)
        server.sendmail(mail_from, [mail_to], msg.as_string())
    print(f"Sent report to {mail_to} via {host}:{port}")


def main() -> int:
    rows = load_history()
    date_str = report_date_jst()
    summary = build_summary(rows, date_str)
    text_body = render_text(summary)
    subject = f"Tokyo Yamathon - Daily Registration Report ({date_str})"
    try:
        send_email(subject, text_body)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR sending email: {exc}", file=sys.stderr)
        print(text_body)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
