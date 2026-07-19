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
Polls the Tokyo Yamathon team-count endpoint and records a snapshot.

Writes/updates:
  data/latest.json   - single latest snapshot (served to the dashboard, same-origin on GitHub Pages)
  data/history.csv   - one row appended per run (powers the daily report)
  data/feed.json     - rolling log of registration bumps (powers the dashboard's
                        "Registration Activity" feed panel). A new entry is added
                        whenever a course's count increases versus the previous run.
  data/daily.json    - new registrations per calendar day (JST), rebuilt from
                        history.csv on every run. Powers the daily report card
                        and the last-7-days bar chart.
  data/weekly.json   - actuals vs the weekly operating plan in data/plan.json,
                        with a green/amber/red status per campaign week. Powers
                        the week-on-week campaign tracker.

Run on a schedule via .github/workflows/collect.yml.
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

LIVE_DATA_URL = os.environ.get(
    "LIVE_DATA_URL", "https://www.tokyo-yamathon.com/_functions/counts"
)
JST = timezone(timedelta(hours=9))
FEED_MAX = 150

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
LATEST_PATH = os.path.join(DATA_DIR, "latest.json")
HISTORY_PATH = os.path.join(DATA_DIR, "history.csv")
FEED_PATH = os.path.join(DATA_DIR, "feed.json")
DAILY_PATH = os.path.join(DATA_DIR, "daily.json")
PLAN_PATH = os.path.join(DATA_DIR, "plan.json")
WEEKLY_PATH = os.path.join(DATA_DIR, "weekly.json")
DAILY_DAYS = 21  # days of history to keep in daily.json (chart shows the last 7)

HISTORY_FIELDS = [
    "fetched_at_utc",
    "fetched_at_jst",
    "date_jst",
    "time_jst",
    "full",
    "half",
    "quarter",
    "total",
    "source_updated_utc",
    "source",  # "webscorer" | "wix" for collected rows, "report" for seeded points
    "general",  # channel split - blank when sourced from the Wix aggregate endpoint
    "sponsor",
]


def fetch_counts(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "yamathon-tracker-bot/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_source() -> tuple:
    """Get current counts, preferring the Webscorer API when credentials are
    present and falling back to the Wix aggregate endpoint otherwise.

    Webscorer is preferred because it exposes the general/sponsor split that
    the Wix endpoint sums away. The fallback means a missing/expired token
    degrades to the previous behaviour instead of breaking collection.

    Returns (data, source_name).
    """
    cfg_path = os.path.join(DATA_DIR, "webscorer_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, encoding="utf-8") as f:
                ws_cfg = json.load(f)
        except (json.JSONDecodeError, OSError):
            ws_cfg = {}
        if ws_cfg.get("enabled"):
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            try:
                import webscorer  # noqa: PLC0415
            except ImportError:
                webscorer = None
            if webscorer and webscorer.configured():
                try:
                    data = webscorer.fetch_all(ws_cfg)
                    data.pop("_diagnostics", None)
                    return data, "webscorer"
                except Exception as exc:  # noqa: BLE001
                    # webscorer.py redacts credentials before raising
                    print(f"WARN: Webscorer fetch failed, falling back to Wix: {exc}", file=sys.stderr)

    return fetch_counts(LIVE_DATA_URL), "wix"


def migrate_history_header() -> None:
    """Bring an existing history.csv up to the current column set.

    Columns have been added over time (source, then general/sponsor). Appending
    new-style rows to a file with an older header silently misaligns every
    column, so rewrite the file with the full header and blanks for the
    columns that didn't exist when those rows were written.
    """
    if not os.path.exists(HISTORY_PATH):
        return
    try:
        with open(HISTORY_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing = reader.fieldnames or []
            if existing == HISTORY_FIELDS:
                return
            rows = list(reader)
    except OSError:
        return

    with open(HISTORY_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        writer.writeheader()
        for r in rows:
            r.pop(None, None)  # drop values orphaned by a short header
            writer.writerow({k: r.get(k, "") for k in HISTORY_FIELDS})
    print(f"Migrated history.csv header: {existing} -> {HISTORY_FIELDS}", file=sys.stderr)


def load_previous_counts() -> dict:
    """Best-effort read of the counts written by the last run, so we can
    detect increases and log them to the feed. Missing/corrupt file just
    means no feed entries get generated this run (nothing to diff against)."""
    if not os.path.exists(LATEST_PATH):
        return {}
    try:
        with open(LATEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def update_feed(prev: dict, full: int, half: int, quarter: int, now_ms: int) -> None:
    feed = []
    if os.path.exists(FEED_PATH):
        try:
            with open(FEED_PATH, encoding="utf-8") as f:
                feed = json.load(f)
            if not isinstance(feed, list):
                feed = []
        except (json.JSONDecodeError, OSError):
            feed = []

    new_entries = []
    for course, new_val in (("full", full), ("half", half), ("quarter", quarter)):
        old_val = int(prev.get(course, 0) or 0) if prev else None
        if old_val is None:
            continue  # first run ever - nothing to diff against
        delta = new_val - old_val
        if delta > 0:
            new_entries.append(
                {"ts": now_ms, "course": course, "delta": delta, "totalAfter": new_val}
            )

    if new_entries:
        feed = new_entries + feed  # newest first
        feed = feed[:FEED_MAX]
        with open(FEED_PATH, "w", encoding="utf-8") as f:
            json.dump(feed, f, indent=2)
            f.write("\n")
    elif not os.path.exists(FEED_PATH):
        # seed an empty file so the dashboard's fetch() doesn't 404 on first run
        with open(FEED_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def rebuild_daily(now_jst: datetime) -> None:
    """Recompute new-registrations-per-day from history.csv.

    The counts endpoint only ever reports running totals, so "how many
    teams registered on day X" is derived: take the last snapshot of each
    day (that day's closing total) and subtract the previous day's closing
    total.

    Days with no snapshots at all carry the last known totals forward and
    report 0. Note the consequence: if collection is down for a day, any
    registrations that happened during the outage get attributed to the day
    collection resumes, because the endpoint gives us no way to split them.
    The `hasData` flag marks which days actually had snapshots, so a gap is
    distinguishable from a genuinely quiet day.
    """
    if not os.path.exists(HISTORY_PATH):
        return

    try:
        with open(HISTORY_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return

    closing = {}  # date_jst -> dict of closing totals (last row of that day wins)
    for r in rows:
        try:
            closing[r["date_jst"]] = {
                "full": int(r["full"]),
                "half": int(r["half"]),
                "quarter": int(r["quarter"]),
                "total": int(r["total"]),
            }
        except (KeyError, ValueError):
            continue

    if not closing:
        return

    first_date = datetime.strptime(min(closing), "%Y-%m-%d").date()
    today = now_jst.date()
    window_start = max(first_date, today - timedelta(days=DAILY_DAYS - 1))

    days = []
    carried = None  # last known closing totals at or before the day being processed

    # Walk from the very first day we have data for, so the carry-forward
    # baseline is correct even for days before the output window.
    day = first_date
    while day <= today:
        key = day.strftime("%Y-%m-%d")
        prev_close = carried
        if key in closing:
            carried = closing[key]
        cur_close = carried

        if prev_close is None or cur_close is None:
            deltas = {"full": 0, "half": 0, "quarter": 0, "total": 0}
        else:
            deltas = {
                k: max(0, cur_close[k] - prev_close[k])
                for k in ("full", "half", "quarter", "total")
            }

        if day >= window_start:
            days.append(
                {
                    "date": key,
                    "dow": int(day.strftime("%w")),  # 0=Sunday
                    "full": deltas["full"],
                    "half": deltas["half"],
                    "quarter": deltas["quarter"],
                    "total": deltas["total"],
                    "cumulative": cur_close["total"] if cur_close else 0,
                    "hasData": key in closing,
                }
            )
        day += timedelta(days=1)

    payload = {"generated_at": now_jst.isoformat(), "days": days}
    with open(DAILY_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def closing_series():
    """date (str) -> closing totals for that day, plus a sorted list of dates."""
    if not os.path.exists(HISTORY_PATH):
        return {}, []
    try:
        with open(HISTORY_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except OSError:
        return {}, []

    closing = {}
    for r in rows:
        try:
            closing[r["date_jst"]] = {
                "full": int(r["full"]),
                "half": int(r["half"]),
                "quarter": int(r["quarter"]),
                "total": int(r["total"]),
            }
        except (KeyError, ValueError):
            continue
    return closing, sorted(closing)


def total_on_or_before(closing, dates, day):
    """Cumulative total as of `day`, carrying the last known value forward.
    Returns None if we have no data at or before that date."""
    key = day.strftime("%Y-%m-%d")
    best = None
    for d in dates:
        if d <= key:
            best = d
        else:
            break
    return closing[best]["total"] if best else None


def rebuild_weekly(now_jst: datetime) -> None:
    """Compare actual registrations against the weekly operating plan and
    assign each week a green / amber / red status.

    Status rules come from section 6 of the 2026 Registration Outlook and are
    driven by the CUMULATIVE position (not the weekly figure alone), because a
    single soft week is expected noise in a back-loaded curve:

      green  cumulative at or above the week's cumulative target
      amber  cumulative below target by up to 10%, OR the week's new teams
             came in under 90% of that week's plan
      red    cumulative more than 10% below target, OR two weak weeks in a row

    The report defines amber as "5-10% below" and green as "at or above
    target", which leaves 0-5% below undefined. That gap is folded into amber
    so a shortfall is never painted green.

    The in-flight week is pro-rated by days elapsed, so a week that is two days
    old is judged against two days' worth of its target rather than the whole.
    """
    if not os.path.exists(PLAN_PATH):
        return
    try:
        with open(PLAN_PATH, encoding="utf-8") as f:
            plan = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    closing, dates = closing_series()
    if not closing:
        return

    th = plan.get("thresholds", {})
    amber_max = float(th.get("amberMaxShortfallPct", 10))
    weak_pct = float(th.get("weakWeekPct", 90))
    weak_for_red = int(th.get("weakWeeksForRed", 2))
    today = now_jst.date()

    out_weeks = []
    consecutive_weak = 0

    for w in plan.get("weeks", []):
        start = datetime.strptime(w["start"], "%Y-%m-%d").date()
        end = datetime.strptime(w["end"], "%Y-%m-%d").date()
        days_total = (end - start).days + 1

        started = today >= start
        finished = today > end
        in_progress = started and not finished

        # cumulative at the day before this week began = the week's opening line
        opening = total_on_or_before(closing, dates, start - timedelta(days=1))
        if opening is None:
            opening = 0
        as_of = min(today, end)
        current = total_on_or_before(closing, dates, as_of) if started else None

        days_elapsed = 0 if not started else min((today - start).days + 1, days_total)

        target_new = w.get("newTeams") or 0
        target_cum = w.get("cumulative") or 0
        is_baseline = bool(w.get("baseline"))

        entry = {
            "n": w["n"],
            "label": w.get("label", "W" + str(w["n"])),
            "start": w["start"],
            "end": w["end"],
            "daysTotal": days_total,
            "daysElapsed": days_elapsed,
            "targetNew": target_new,
            "targetCum": target_cum,
            "pattern2025": w.get("pattern2025"),
            "baseline": is_baseline,
            "started": started,
            "inProgress": in_progress,
            "actualNew": None,
            "actualCum": None,
            "proRatedTargetCum": None,
            "shortfallPct": None,
            "status": "pending",
            "weak": False,
        }

        if started and current is not None:
            actual_new = max(0, current - opening)
            entry["actualNew"] = actual_new
            entry["actualCum"] = current

            # pro-rate the cumulative target across the week for an in-flight week
            if in_progress and days_total:
                frac = days_elapsed / days_total
                pro_rated = opening_target(plan, w) + (target_cum - opening_target(plan, w)) * frac
            else:
                pro_rated = float(target_cum)
            entry["proRatedTargetCum"] = round(pro_rated, 1)

            if is_baseline:
                # opening week has no plan target - it IS the baseline
                entry["status"] = "green"
                entry["shortfallPct"] = 0.0
                entry["reason"] = "baseline"
            else:
                shortfall = ((pro_rated - current) / pro_rated * 100) if pro_rated > 0 else 0.0
                entry["shortfallPct"] = round(shortfall, 1)

                # Weak week = new teams under `weak_pct`% of plan (pro-rated while
                # in flight). Suppressed for the first 2 days of a live week: with
                # so little of the week elapsed there isn't enough signal, and a
                # quiet Monday would otherwise raise a false alarm.
                expected_new = target_new * (days_elapsed / days_total) if in_progress else target_new
                too_early = in_progress and days_elapsed < 3
                entry["weak"] = bool(
                    not too_early and expected_new > 0 and actual_new < expected_new * (weak_pct / 100)
                )

                if finished:
                    consecutive_weak = consecutive_weak + 1 if entry["weak"] else 0

                if shortfall <= 0:
                    status, reason = "green", "at_or_above_target"
                elif shortfall <= amber_max:
                    status, reason = "amber", "below_target"
                else:
                    status, reason = "red", "below_target"

                # trend escalations from report section 6
                if status == "green" and entry["weak"]:
                    status, reason = "amber", "weak_week"
                if consecutive_weak >= weak_for_red:
                    status, reason = "red", "two_weak_weeks"

                entry["status"] = status
                entry["reason"] = reason
                entry["consecutiveWeak"] = consecutive_weak

        out_weeks.append(entry)

    latest_total = closing[dates[-1]]["total"] if dates else 0
    closes = datetime.strptime(plan["closes"], "%Y-%m-%d").date()
    live = [w for w in out_weeks if w["started"] and not w["baseline"]]
    current_week = live[-1] if live else None

    # Overall status = where we stand right now: latest cumulative against
    # today's pro-rated cumulative target, plus the report's trend triggers.
    # (Deliberately not just "the current week's status" - on the first day of
    # a week that reads as a shortfall purely because the week just started.)
    if current_week and current_week["proRatedTargetCum"]:
        overall_short = round(
            (current_week["proRatedTargetCum"] - latest_total)
            / current_week["proRatedTargetCum"] * 100, 1
        )
        if overall_short <= 0:
            overall, overall_reason = "green", "at_or_above_target"
        elif overall_short <= amber_max:
            overall, overall_reason = "amber", "below_target"
        else:
            overall, overall_reason = "red", "below_target"
        if consecutive_weak >= weak_for_red:
            overall, overall_reason = "red", "two_weak_weeks"
    else:
        overall, overall_reason, overall_short = "pending", "not_started", None

    payload = {
        "generated_at": now_jst.isoformat(),
        "goal": plan.get("goal"),
        "closes": plan.get("closes"),
        "daysRemaining": max(0, (closes - today).days),
        "cumulative": latest_total,
        "status": overall,
        "reason": overall_reason,
        "shortfallPct": overall_short,
        "targetNow": current_week["proRatedTargetCum"] if current_week else None,
        "currentWeek": current_week["label"] if current_week else None,
        "consecutiveWeak": consecutive_weak,
        "weeks": out_weeks,
    }
    with open(WEEKLY_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def opening_target(plan, week):
    """Cumulative target at the START of `week` (i.e. the previous week's
    cumulative target), used as the floor when pro-rating an in-flight week."""
    prev_cum = 0
    for w in plan.get("weeks", []):
        if w["n"] == week["n"]:
            break
        prev_cum = w.get("cumulative") or prev_cum
    return float(prev_cum)


def main() -> int:
    prev = load_previous_counts()

    try:
        data, source = fetch_source()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: could not fetch counts: {exc}", file=sys.stderr)
        return 1

    full = int(data.get("full", 0) or 0)
    half = int(data.get("half", 0) or 0)
    quarter = int(data.get("quarter", 0) or 0)
    total = int(data.get("total", full + half + quarter) or (full + half + quarter))
    source_updated = data.get("updated", "")
    # present only when sourced from Webscorer; None means "not tracked"
    general = data.get("general")
    sponsor = data.get("sponsor")

    now_utc = datetime.now(timezone.utc)
    now_jst = now_utc.astimezone(JST)

    os.makedirs(DATA_DIR, exist_ok=True)
    update_feed(prev, full, half, quarter, int(now_utc.timestamp() * 1000))

    latest = {
        "full": full,
        "half": half,
        "quarter": quarter,
        "total": total,
        "updated": source_updated,
        "fetched_at": now_utc.isoformat(),
        "source": source,
    }
    if general is not None:
        latest["general"] = int(general)
    if sponsor is not None:
        latest["sponsor"] = int(sponsor)
    if data.get("byChannel"):
        latest["byChannel"] = data["byChannel"]
    with open(LATEST_PATH, "w", encoding="utf-8") as f:
        json.dump(latest, f, indent=2)
        f.write("\n")

    migrate_history_header()

    write_header = not os.path.exists(HISTORY_PATH)
    with open(HISTORY_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HISTORY_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "fetched_at_utc": now_utc.isoformat(),
                "fetched_at_jst": now_jst.isoformat(),
                "date_jst": now_jst.strftime("%Y-%m-%d"),
                "time_jst": now_jst.strftime("%H:%M:%S"),
                "full": full,
                "half": half,
                "quarter": quarter,
                "total": total,
                "source_updated_utc": source_updated,
                "source": source,
                "general": "" if general is None else int(general),
                "sponsor": "" if sponsor is None else int(sponsor),
            }
        )

    rebuild_daily(now_jst)
    rebuild_weekly(now_jst)

    chan = ""
    if general is not None or sponsor is not None:
        chan = f" general={general} sponsor={sponsor}"
    print(
        f"OK [{source}]: {now_jst.isoformat()} "
        f"full={full} half={half} quarter={quarter} total={total}{chan}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
