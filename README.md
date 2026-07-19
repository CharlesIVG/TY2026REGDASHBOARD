# Tokyo Yamathon — Registration Dashboard

> **Developed by SxS Partners** for the International Volunteer
> Group-Japan and Tokyo Yamathon.
>
> This code is the intellectual property of SxS Partners. All rights
> remain the property of SxS Partners and the project developer,
> **C. Stewart**.
>
> © SxS Partners — All rights reserved.

---


Live team-registration dashboard, styled after the "Command Center"
design from [CharlesIVG/TokyoYamathon](https://github.com/CharlesIVG/TokyoYamathon)
(dark theme, radar gauges, KPI tiles, live activity feed — same fonts
and color system as `index.html`/`command-center.html` there), but
repointed at pre-race registration counts instead of race-day results,
since there's no finish-line data until race day itself. Plus a daily
email report. Runs entirely on GitHub — no server to maintain.

## How it works

- **`index.html`** — the dashboard, hosted via GitHub Pages. Instead of
  calling the Wix counts endpoint directly from the browser (risky —
  cross-origin requests from a `github.io` domain may be blocked by
  CORS on the Wix side), it reads three same-origin files in this repo:
  `data/latest.json` (current counts → KPI tiles and gauges),
  `data/daily.json` (per-day totals → the Daily Report card and the
  Last-7-Days bar chart), and `data/feed.json` (recent registration
  bumps → the activity feed). The `'Upper Clock'` font is embedded
  inline as base64 (same approach as the reference site — external font
  requests get blocked in some embed sandboxes).

### Daily report + weekly chart

Above the activity feed sit two panels:

- **Daily Report** — today's date (JST), the number of teams that
  registered today, split by Full / Half / Half-a-Half, plus the
  running cumulative total.
- **Last 7 Days** — a bar chart of daily registrations for the rolling
  7-day window ending today, with the weekday letter and date under
  each bar. The y-axis is fixed at **100 teams** as requested; if a
  single day ever exceeds 100 the scale grows in steps of 50 so a big
  day is never silently clipped. A day with no snapshots (collection
  outage) renders as a hatched bar with a `·` instead of a `0`, so an
  outage can't be misread as "nobody registered."

  A rolling window is used rather than a strict Sunday→Saturday
  calendar week because early in the week (e.g. on a Sunday) a calendar
  week renders almost empty, with all the recent data stranded in the
  previous week.

### Week-on-week campaign tracker (green / amber / red)

Below those, a full-width panel tracks the campaign against the weekly
operating plan from the *2026 Registration Outlook* (§3). One bar per
campaign week (Open, W1…W8 through 14 September): week label on top,
bar height = teams recruited that week, count below, with a dotted tick
marking that week's target. Hover any bar for target vs actual,
cumulative position, and the reason for its color.

**The plan lives in `data/plan.json`** — targets, thresholds, and week
boundaries are all editable there without touching any code.

**Status rules (report §6), driven by the _cumulative_ position:**

| Status | Trigger |
|---|---|
| 🟢 Green | Cumulative at or above the week's cumulative target |
| 🟡 Amber | Cumulative below target by up to 10%, **or** a week under 90% of its plan |
| 🔴 Red | Cumulative more than 10% below target, **or** two weak weeks in a row |

Cumulative (not weekly) is the basis because a single soft week is
expected noise in a back-loaded curve — the report's own §2 warns "a
quiet week is not automatically a crisis." The trend triggers are what
catch genuine stalls, and they can turn a week red *even while you're
ahead on cumulative* — that case is labeled "two weak weeks in a row"
in the status line so it isn't mistaken for a target miss.

Two judgment calls worth knowing:

- The report defines green as "at or above target" and amber as "5–10%
  below," leaving **0–5% below undefined**. That gap is folded into
  amber, so a shortfall is never painted green.
- The in-flight week is **pro-rated by days elapsed** (day 3 of 7 is
  judged against 3/7 of the week's target), and the weak-week flag is
  suppressed for the first 2 days, so a quiet Monday doesn't raise a
  false alarm.

## Data source: Webscorer API (preferred) or Wix (fallback)

The collector prefers the **Webscorer JSON API** and falls back to the
Wix `_functions/counts` endpoint when Webscorer credentials aren't
available. Webscorer is preferred because it exposes the
**general-vs-sponsor split** that the Wix endpoint sums away before
returning.

| | Wix `_functions/counts` | Webscorer JSON API |
|---|---|---|
| Course split (full/half/quarter) | ✅ | ✅ |
| General vs sponsor | ❌ collapsed server-side | ✅ separate lists |
| Per-entry detail | ❌ | ✅ |
| Credentials needed | none | API ID + token, PRO Results sub |

Configured in `data/webscorer_config.json` (race IDs, course-label
mapping). **No credentials in that file** — it's safe to commit.

### How the API key stays private

GitHub Actions runs on GitHub's servers, not in the visitor's browser:

```
GitHub Actions runner  (holds the secrets)
  → webscorer.com/json/registerlist?...&apipriv=SECRET
  → aggregates in memory, discards personal data
  → commits ONLY counts to data/*.json
         ↓
GitHub Pages serves those static JSON files
         ↓
  Visitor's browser — never sees the key
```

The published site only ever fetches same-origin `data/*.json`. The key
is never in the page source, the committed files, or any browser
request.

**Setup — two secrets, then a probe run:**

1. Repo Settings → Secrets and variables → Actions → New repository
   secret:
   - `WEBSCORER_API_ID` — digits at the end of your "Unique organizer
     URL" (Organizers → My organizer settings)
   - `WEBSCORER_API_TOKEN` — the 8-character JSON API Token at the
     bottom of that same settings page
2. Actions tab → **"Webscorer probe (run this first)"** → Run workflow.
   This prints the connection result, how Webscorer labels each course,
   and whether one row means one team — cross-checked against the
   current Wix total. It prints **no personal data and no token**.
3. If the probe flags unmapped course labels or a counting-mode
   mismatch, adjust `courseMap` / `countMode` in
   `data/webscorer_config.json`. Then the scheduled collector picks
   Webscorer up automatically.

Never paste the token into `index.html`, `webscorer_config.json`, or
any other committed file — this repo is public.

### Privacy

`registerlist` returns participant names, emails, and other personal
data. **None of it is ever written to the repo.** `scripts/webscorer.py`
aggregates in memory and returns only counts; the probe reports field
*names* and course labels but never field *values*. This is deliberate
and load-bearing — the repo is public, and Japan's APPI and the GDPR
both apply to that roster. The API token is likewise scrubbed from every
error message and log line, since it travels as a URL query parameter
and would otherwise surface in Actions logs on any failure.

### Known data limits

- **Cancellations and duplicates.** Per report §6, counts are raw
  registrations — not adjusted for cancellations, duplicates,
  transfers, or unpaid entries.
- **Seeded opening-week rows.** `history.csv` includes three rows
  marked `source=report` (12 Jul = 15, 13 Jul = 41, 19 Jul = 108) taken
  from the report so the opening week appears on the chart. Their
  *totals* are from the report; their course split is inferred from the
  current ratio and should not be treated as real. Only the totals feed
  the campaign tracker, so this doesn't affect any RAG status.
- **No cancellation/duplicate handling.** Per report §6, the counts are
  raw registrations — not adjusted for cancellations, duplicates,
  transfers, or unpaid entries.
- **`.github/workflows/collect.yml`** — runs every 15 minutes. Polls
  `https://www.tokyo-yamathon.com/_functions/counts` from GitHub's
  servers (no CORS issue there), writes `data/latest.json`, appends a
  row to `data/history.csv`, rebuilds `data/daily.json` (per-day
  totals, derived by diffing each day's closing total against the
  previous day's) and `data/weekly.json` (weekly actuals vs
  `data/plan.json`, with a green/amber/red status per week), and —
  whenever a course's count went up since the last run — logs an entry
  to `data/feed.json` (course, delta, new total, timestamp). This is
  what makes "registrations per day / per hour," the activity feed, and
  the campaign tracker possible, since the live endpoint itself only
  ever reports current totals, not history.
- **`.github/workflows/daily-report.yml`** — runs at 00:05 JST every
  day. Reads `data/history.csv`, summarizes the day that just ended
  (new teams per course, roughly when they came in, and cumulative
  totals/% filled), and emails it to **info@ivgjapan.org**.
- **`scripts/collect_snapshot.py`** / **`scripts/send_daily_report.py`**
  — the two Python scripts behind the workflows above. Pure standard
  library, no dependencies to install.
- **`scripts/build_index.py`** — a one-off generator, not part of the
  live site. Inlines `UpperClock-Regular.woff2` as base64 into
  `index.html`. Re-run it (`python3 scripts/build_index.py`) if you
  ever swap the font file or want to regenerate `index.html` from the
  template inside that script.

## One known data limit

The only API available right now is the Wix counts endpoint, which
returns aggregate numbers only:

```json
{"full":51,"half":40,"quarter":17,"total":108,"updated":"2026-07-19T07:58:55.505Z"}
```

There's no per-team or per-member data in it, so **"team members per
team" cannot be included in the report** — the email says so explicitly
rather than silently omitting it. If a Webscorer API key or a richer
endpoint becomes available later, extend `fetch_counts()` in
`scripts/collect_snapshot.py` and both the dashboard and report can
grow to use it.

## Setup

1. **Create a GitHub repo** and push this folder's contents to it
   (`git init`, `git add .`, `git commit`, then push to a new repo on
   GitHub).

2. **Enable GitHub Pages**: repo Settings → Pages → Source: "Deploy
   from a branch" → Branch: `main` (or whichever branch you push to),
   folder `/ (root)`. Your dashboard will be live at
   `https://<your-username>.github.io/<repo-name>/`.

3. **Allow the collector to commit**: repo Settings → Actions →
   General → "Workflow permissions" → select **"Read and write
   permissions"**. Without this, `collect.yml` can't push its updates.

4. **Add email secrets**: repo Settings → Secrets and variables →
   Actions → New repository secret. Add:
   - `SMTP_HOST` — e.g. `smtp.gmail.com` for a Gmail account, or your
     provider's SMTP host (SendGrid, Resend, etc.)
   - `SMTP_PORT` — usually `587` (STARTTLS) or `465` (SSL)
   - `SMTP_USER` — the account/login used to authenticate
   - `SMTP_PASS` — an app password (not your regular login password —
     e.g. a [Gmail App Password](https://myaccount.google.com/apppasswords)
     if using Gmail)
   - `MAIL_FROM` — the "from" address (can be the same as `SMTP_USER`)

5. **Test it manually** before waiting for the schedule: go to the
   Actions tab → select "Collect team count snapshot" or "Daily
   registration report" → "Run workflow". Check the run logs — if SMTP
   secrets aren't set yet, the report script prints the report instead
   of failing, so you can sanity-check the content first.

## Notes

- GitHub's `schedule` triggers are best-effort and can run a few
  minutes late, especially on free/public repos — this is normal and
  fine for a snapshot-every-15-minutes / report-once-daily use case.
- If a repo has no activity for 60 days, GitHub auto-disables scheduled
  workflows. A `workflow_dispatch` run (or any push) re-enables them.
- Slot capacities (`FULL_SLOTS`, `HALF_SLOTS`, `QUARTER_SLOTS`,
  `EVENT_GOAL`) are duplicated in `index.html`'s `CONFIG.LEGS[*].slots`/
  `CONFIG.EVENT_GOAL` and in `scripts/send_daily_report.py` — update
  both if the event's slot counts change.
- `UpperClock-Regular.woff2` is kept in the repo for reference/
  attribution, but `index.html` doesn't load it externally — it's
  embedded inline as base64 (see `scripts/build_index.py`).
- No race-day results integration yet (no `RESULTS_URL`, no finisher
  feed/leaderboard) since the event hasn't run — this dashboard only
  covers the registration phase. If you want it to flip into live
  race-day tracking later (matching `command-center.html`'s
  `poll()`/`RESULTS_URL` contract), that's a separate follow-up.
