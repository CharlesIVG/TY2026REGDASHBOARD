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
import html as _html
import json
import os
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
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

# Logo for the HTML email. It MUST be an absolute https URL - email clients
# cannot read a file out of the repo, only fetch over the web, and most block
# images until the reader clicks "show images", so nothing critical depends on
# it loading. Drop ty-logo.png at the repo root (served by GitHub Pages) to
# make this resolve; until then the alt text shows instead.
LOGO_URL = "https://charlesivg.github.io/TY2026REGDASHBOARD/ty-logo.png"

# HTML email palette. Kept close to the dashboard, but on a light card because
# dark backgrounds render unpredictably across mail clients (Outlook strips
# them, some dark-mode clients invert them). RAG colours match the dashboard.
HEX = {
    "GREEN": "#2FB673", "YELLOW": "#E0A100", "RED": "#E5484D", "PENDING": "#8A94A6",
    "ink": "#1F2933", "muted": "#6B7280", "line": "#E5E7EB", "track": "#EDEFF2",
    "accent": "#0E8C7F", "headbg": "#0C1A1C", "cardbg": "#FFFFFF", "pagebg": "#F4F5F7",
}
RAG_DOT = {"GREEN": "\U0001F7E2", "YELLOW": "\U0001F7E1", "RED": "\U0001F534", "PENDING": "⚪"}

# Course fill-bar colours, matching the dashboard's Full / Half / Half-a-Half
# scheme so the email reads the same as the live gauges.
COURSE_HEX = {"full": "#9ACD32", "half": "#F89825", "quarter": "#7EB7E4"}

# Fixed wording that opens and closes every report. Edit the strings here -
# nothing else in the file needs to change. Blank strings produce blank lines.
GREETING = "Good Morning Community Impact Rockstars \U0001F918 - I've got your \U0001FAF5 daily progress report for the TEAMS IN for 2026!"
# "YamaGo" is the sign-off name. In plain text it prints as a word; in the
# HTML email it is replaced by yamago.png (drop that file at the repo root,
# served by GitHub Pages). If the image is missing, the alt text shows.
SIGNOFF_NAME = "YamaGo"
SIGNOFF = [
    "Have a great day and - keep on truckin!",
    "Let's Go!",
    SIGNOFF_NAME,
]
SIGNOFF_IMG_URL = "https://charlesivg.github.io/TY2026REGDASHBOARD/yamago.png"


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
    L.append(f"TOKYO YAMATHON - DAILY TEAM ENTRY REPORT")
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
            L.append("ENTRY TYPE")
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
        L.append(f"  {'People':<12} {ts['people']}")
        # A mean team size is meaningless here - you cannot have a third of
        # a person, and nobody can act on "3.38". The actual tally of team
        # sizes is what you'd use to order bibs, shirts or bus seats.
        # Largest teams first; sizes come from the data rather than being
        # hardcoded, so a 5-person team would appear on its own if allowed.
        dist = ts.get("distribution") or {}
        for size in sorted(dist, key=lambda s: int(s), reverse=True):
            count = dist[size]
            if count:
                L.append(f"  {size + '-person':<12} {count} teams")
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


def _bar(pct_val, color) -> str:
    """A progress bar built from two coloured table cells. No image, so it
    renders in every client including Outlook, which blocks images by default
    and ignores CSS width on divs. Width lives on the <td> as a percentage."""
    p = max(0, min(100, int(round(pct_val))))
    fill = (
        f'<td bgcolor="{color}" width="{p}%" '
        f'style="width:{p}%;height:10px;background:{color};font-size:0;line-height:0;'
        f'border-radius:5px 0 0 5px;">&nbsp;</td>'
    ) if p > 0 else ""
    rest = (
        f'<td bgcolor="{HEX["track"]}" width="{100 - p}%" '
        f'style="width:{100 - p}%;height:10px;background:{HEX["track"]};font-size:0;'
        f'line-height:0;border-radius:0 5px 5px 0;">&nbsp;</td>'
    ) if p < 100 else ""
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="border-collapse:collapse;table-layout:fixed;"><tr>{fill}{rest}</tr></table>'
    )


def _metric(icon, label, value, sub="", bar_html="") -> str:
    """One labelled metric block: icon + label on the left, big value on the
    right, optional progress bar and sub-line beneath."""
    e = _html.escape
    return f"""
      <tr><td style="padding:14px 22px 0 22px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="font:600 12px/1.3 Arial,Helvetica,sans-serif;color:{HEX['muted']};
                letter-spacing:.04em;text-transform:uppercase;">{icon}&nbsp; {e(label)}</td>
            <td align="right" style="font:700 20px/1 Arial,Helvetica,sans-serif;
                color:{HEX['ink']};white-space:nowrap;">{value}</td>
          </tr>
        </table>
        {('<div style="height:7px;"></div>' + bar_html) if bar_html else ''}
        {(f'<div style="font:400 12px/1.4 Arial,Helvetica,sans-serif;color:{HEX["muted"]};padding-top:6px;">{sub}</div>') if sub else ''}
      </td></tr>"""


def _section(title) -> str:
    return f"""
      <tr><td style="padding:22px 22px 0 22px;">
        <div style="font:700 11px/1 Arial,Helvetica,sans-serif;color:{HEX['accent']};
            letter-spacing:.12em;text-transform:uppercase;border-bottom:2px solid {HEX['line']};
            padding-bottom:8px;">{title}</div>
      </td></tr>"""


def render_html(summary) -> str:
    """Email-safe HTML: table layout, inline styles only, no web fonts, images
    optional. Mirrors the plain-text report section for section so both stay in
    step. The plain-text part is always sent alongside as the fallback."""
    e = _html.escape
    d = summary["deltas"]
    latest = summary["latest_overall"]
    wk = load_plan()
    ts = load_teamsize()

    rows = []

    # --- campaign status ---
    if wk:
        status = (wk.get("status") or "pending").upper()
        if status == "AMBER":
            status = "YELLOW"
        col = HEX.get(status, HEX["PENDING"])
        cum = wk.get("cumulative", 0)
        target = wk.get("targetNow")
        goal = wk.get("goal", EVENT_GOAL)
        days = wk.get("daysRemaining")
        line = ""
        if target:
            diff = round(cum - target)
            word = "ahead of plan" if diff >= 0 else "behind plan"
            line = f"{cum} teams vs {round(target)} planned by now &middot; {abs(diff)} {word}"
        if days is not None:
            line += (" &middot; " if line else "") + f"{days} days until close"
        rows.append(f"""
      <tr><td style="padding:22px 22px 0 22px;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
            style="border:1px solid {HEX['line']};border-radius:10px;">
          <tr><td style="padding:14px 16px;">
            <span style="display:inline-block;background:{col};color:#ffffff;
                font:700 12px/1 Arial,Helvetica,sans-serif;letter-spacing:.06em;
                padding:6px 12px;border-radius:14px;">{RAG_DOT.get(status,'')} STATUS: {status}</span>
            <div style="font:400 13px/1.5 Arial,Helvetica,sans-serif;color:{HEX['muted']};padding-top:10px;">{line}</div>
          </td></tr>
        </table>
      </td></tr>""")

    # --- new teams yesterday ---
    rows.append(_section("\U0001F195 New Teams Yesterday"))
    if d.get("total") is None:
        rows.append(_metric("", "Not measured", "&ndash;",
                            sub="Needs a full day of tracking either side to be accurate."))
    else:
        split = (f"Full <b>{d['full']}</b> &nbsp; Half <b>{d['half']}</b> &nbsp; "
                 f"Half-a-Half <b>{d['quarter']}</b>")
        rows.append(_metric("", "Teams registered", f"{d['total']}", sub=split))

    # --- running totals + funds ---
    if latest:
        rows.append(_section("\U0001F4CA Running Totals"))
        for key, cap, lab in (("full", FULL_SLOTS, "Full Trek"),
                              ("half", HALF_SLOTS, "Half Trek"),
                              ("quarter", QUARTER_SLOTS, "Half a Half Trek")):
            v = latest[key]
            p = (v / cap * 100) if cap else 0
            rows.append(_metric("", lab, f"{v} / {cap} &middot; {pct(v, cap)}",
                                bar_html=_bar(p, COURSE_HEX[key])))
        tp = (latest["total"] / EVENT_GOAL * 100) if EVENT_GOAL else 0
        # Total-vs-goal bar uses its own deeper green, distinct from the Full
        # Trek bar, so the summary line reads as a separate measure.
        rows.append(_metric("\U0001F3AF", "Total vs Goal",
                            f"{latest['total']} / {EVENT_GOAL} &middot; {pct(latest['total'], EVENT_GOAL)}",
                            bar_html=_bar(tp, "#238A01")))
        gen, spo = latest.get("general"), latest.get("sponsor")
        if gen not in (None, "") or spo not in (None, ""):
            rows.append(_metric("\U0001F4E9", "Entry Type",
                                f"General <b>{gen}</b> &nbsp; Sponsor <b>{spo}</b>"))

        raised = latest["total"] * FEE_PER_TEAM
        gap = max(0, FUNDS_GOAL - raised)
        fp = raised / FUNDS_GOAL * 100 if FUNDS_GOAL else 0
        fstatus = "GREEN" if fp >= 85 else "YELLOW" if fp >= 50 else "RED"
        rows.append(_section("\U0001F4B4 Funds Raised"))
        rows.append(_metric("", "Raised", f"&yen;{raised:,}",
                            bar_html=_bar(fp, HEX[fstatus]),
                            sub=(f"{RAG_DOT[fstatus]} {fp:.1f}% of &yen;{FUNDS_GOAL:,} goal &middot; "
                                 f"still needed &yen;{gap:,} ({gap // FEE_PER_TEAM} more teams)")))

    # --- participant breakdown ---
    if ts and ts.get("people"):
        rows.append(_section("\U0001F6B6‍➡️\U0001F6B6\U0001F3FB‍♀️‍➡️ Participant Breakdown"))
        dist = ts.get("distribution") or {}
        tally = " &nbsp; ".join(
            f"<b>{sz}</b>={dist[sz]}"
            for sz in sorted(dist, key=lambda s: int(s), reverse=True) if dist[sz]
        )
        rows.append(_metric("", "People", f"{ts['people']}"))
        rows.append(_metric("", "Team member composition", tally,
                            sub=f"{ts.get('teams','')} teams &middot; from Webscorer registration "
                                f"data import &middot; last import {ts['asOf']}"))

    body_rows = "".join(rows)
    greeting_html = (
        f'<tr><td style="padding:20px 22px 0 22px;font:400 15px/1.5 Arial,Helvetica,sans-serif;'
        f'color:{HEX["ink"]};">{e(GREETING)}</td></tr>' if GREETING else ""
    )
    # HTML sign-off: the text lines as-is, but the "YamaGo" name shown as
    # yamago.png instead of the word. Plain text keeps the word (no image).
    so_lines = [e(s) for s in SIGNOFF if s != SIGNOFF_NAME]
    so_parts = []
    if so_lines:
        so_parts.append(
            f'<div style="font:600 14px/1.6 Arial,Helvetica,sans-serif;color:{HEX["accent"]};">'
            f'{"<br>".join(so_lines)}</div>'
        )
    if SIGNOFF_IMG_URL:
        so_parts.append(
            f'<img src="{SIGNOFF_IMG_URL}" width="150" alt="{e(SIGNOFF_NAME)}" '
            f'style="display:block;border:0;outline:none;margin-top:12px;max-width:150px;height:auto;">'
        )
    signoff_html = (
        f'<tr><td style="padding:20px 22px 0 22px;">{"".join(so_parts)}</td></tr>'
        if so_parts else ""
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light only"></head>
<body style="margin:0;padding:0;background:{HEX['pagebg']};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{HEX['pagebg']};">
<tr><td align="center" style="padding:24px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0"
      style="width:600px;max-width:100%;background:{HEX['cardbg']};border-radius:14px;overflow:hidden;
      border:1px solid {HEX['line']};">
    <tr><td style="background:{HEX['cardbg']};padding:26px 22px 18px 22px;border-bottom:1px solid {HEX['line']};">
      <img src="{LOGO_URL}" width="270" alt="Tokyo Yamathon" style="display:block;border:0;outline:none;width:270px;max-width:78%;height:auto;">
      <div style="font:700 18px/1.2 Arial,Helvetica,sans-serif;color:{HEX['ink']};padding-top:16px;">
        Daily Team Entry Report</div>
      <div style="font:400 13px/1.2 Arial,Helvetica,sans-serif;color:{HEX['muted']};padding-top:4px;">
        \U0001F4C5 {e(summary['date'])} (JST)</div>
    </td></tr>
    {greeting_html}
    {body_rows}
    {signoff_html}
    <tr><td style="padding:24px 22px 22px 22px;">
      <a href="{DASHBOARD_URL}" style="display:inline-block;background:{HEX['accent']};color:#ffffff;
          font:700 13px/1 Arial,Helvetica,sans-serif;text-decoration:none;padding:12px 20px;
          border-radius:8px;">Open the live dashboard &rarr;</a>
    </td></tr>
    <tr><td style="padding:0 22px 22px 22px;font:400 11px/1.5 Arial,Helvetica,sans-serif;color:{HEX['muted']};
        border-top:1px solid {HEX['line']};padding-top:16px;">
      &copy; SxS Partners&#26666;&#24335;&#20250;&#31038; &mdash; provided to IVG-Japan on loan for
      Tokyo Yamathon 2026. Figures are counts, not adjusted for cancellations or unpaid entries.
    </td></tr>
  </table>
</td></tr></table>
</body></html>"""


def send_email(subject: str, text_body: str, html_body: str = "") -> None:
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

    # multipart/alternative: plain text first, HTML second. A mail client shows
    # the last part it can render, so graphical clients get the HTML and plain
    # readers (watches, notification previews, text-only clients) get the text.
    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    else:
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
    html_body = render_html(summary)
    subject = f"Tokyo Yamathon - Daily Team Entry Report ({date_str})"
    try:
        send_email(subject, text_body, html_body)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR sending email: {exc}", file=sys.stderr)
        print(text_body)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
