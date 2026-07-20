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

### Week-on-week campaign tracker (green / yellow / red)

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
| 🟡 Yellow | Cumulative below target by up to 10%, **or** a week under 90% of its plan |
| 🔴 Red | Cumulative more than 10% below target, **or** two weak weeks in a row |

Cumulative (not weekly) is the basis because a single soft week is
expected noise in a back-loaded curve — the report's own §2 warns "a
quiet week is not automatically a crisis." The trend triggers are what
catch genuine stalls, and they can turn a week red *even while you're
ahead on cumulative* — that case is labeled "two weak weeks in a row"
in the status line so it isn't mistaken for a target miss.

Two judgment calls worth knowing:

- The report defines green as "at or above target" and yellow as "5–10%
  below," leaving **0–5% below undefined**. That gap is folded into
  yellow, so a shortfall is never painted green.
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

## Data accuracy and collection timing

**Read this before quoting any number from the dashboard.**

This system is a *sampler*, not a ledger. It polls Webscorer on a
schedule and reconstructs history from those samples. Everything below
follows from that one fact.

### What is reliable

- **Cumulative total, course split, general-vs-sponsor split.** Taken
  directly from Webscorer at poll time. These are accurate as of the
  "UPDATED hh:mm" stamp in the dashboard header — not before it. The
  campaign RAG status is built on the cumulative figure, so the
  red/yellow/green call is as sound as the source data.

### What is approximate, and why

- **Daily counts depend on sampling cadence.** A day's total is
  computed by diffing that day's *closing* snapshot against the
  previous day's closing snapshot. If the last snapshot of a day lands
  at, say, 21:00, any team registering between 21:00 and midnight is
  attributed to the *following* day. Expect ±1–2 teams on any given
  day. The error is self-correcting — it never accumulates, because
  the cumulative total is always read fresh from the source.

  This is not hypothetical. On 20 July the dashboard reported 5 teams
  for the day when Webscorer showed 4: the 19 July seed row was stamped
  `23:59:59` but the underlying export had been taken earlier that
  evening, so a team registering at 23:01 fell outside the 19 July
  baseline and was swept into the 20th. **Any backfilled row must carry
  the timestamp of the moment its data was actually true, not a
  cosmetic end-of-day time.**

- **The tighter the polling, the smaller the boundary error.** GitHub's
  `schedule` trigger is heavily throttled in practice (a `*/15` cron
  was observed firing roughly every 3 hours). The `repository_dispatch`
  hook driven by an external scheduler every 30 minutes is what keeps
  the cadence honest — see `SETUP.md`. Without it, multi-hour gaps
  appear and day-boundary attribution degrades accordingly.

- **Activity-feed timestamps are detection times, not registration
  times.** The feed records when the collector *first saw* a team, not
  when that team signed up. A team registering at 23:01 and first seen
  at 00:34 shows 00:34. The Webscorer API exposes no registration
  timestamp, so polling time is the closest available proxy. Do not
  read those times as exact.

- **Collection outages are shown, not hidden.** A day with no snapshots
  on both sides renders as a hatched bar with `·` rather than `0`, and
  the daily email prints "not measured" rather than a fabricated
  figure. An outage must never be readable as "nobody registered."

- **Participant counts are a stale snapshot.** People (368) and average
  team size (3.38) come from a manually uploaded registration export,
  not the API — Webscorer's JSON returns no roster or team-size field.
  Both the dashboard and the email label this with its `asOf` date.
  It drifts further from truth every day until the export is refreshed.

### What the numbers deliberately exclude

- **Cancellations, duplicates, transfers, unpaid entries.** Per report
  §6, these are raw registration counts with no adjustment.
- **Payment processing fees.** FUNDS RAISED is `teams × ¥16,000`, and
  ¥16,000 is the net figure by design — Webscorer lists a ¥16,560 gross
  entry fee, and the processing margin is deliberately not counted as
  funds raised. The ¥17,600,000 goal is set on the same net basis
  (1,100 × ¥16,000), so target and actual are consistent.
- **Money actually received.** FUNDS RAISED is registrations converted
  to yen — a fundraising thermometer, not an accounting record. It will
  not reconcile against a bank statement.
- **Seeded opening-week rows.** `history.csv` contains rows marked
  `source=export` / `source=report` covering 12–19 July, backfilled so
  the opening week appears on the chart. Their totals are real; where a
  course split was inferred rather than measured it should not be
  treated as exact. Only totals feed the campaign tracker, so no RAG
  status depends on the inferred splits.

### Bottom line

Sound for: *are we on pace, which course is lagging, was this week
weak, how close are we to goal.* Not sound for: exact daily figures
quoted to an outside party, live participant headcount, or anything
requiring financial reconciliation.

## Components

- **`.github/workflows/collect.yml`** — runs every 30 minutes (cron as
  a safety net, `repository_dispatch` from an external scheduler for
  real cadence). Fetches from Webscorer (falling back to the Wix counts
  endpoint), writes `data/latest.json`, appends a row to
  `data/history.csv`, rebuilds `data/daily.json` (per-day totals,
  derived by diffing each day's closing total against the previous
  day's) and `data/weekly.json` (weekly actuals vs `data/plan.json`,
  with a green/yellow/red status per week), and logs newly seen teams
  by name to `data/feed.json`.

  The feed is written **only** from a Webscorer roster. When the
  collector falls back to Wix — which returns counts without names —
  it deliberately writes nothing to the feed. An earlier version logged
  anonymous count deltas in that case, which double-logged every
  registration: once as an unnamed "+3 Half" when Wix answered, then
  again by name at the next successful Webscorer poll. Counts still
  update from the fallback; only the feed waits.

- **`.github/workflows/daily-report.yml`** — runs at 00:05 JST every
  day. Reads `data/history.csv`, summarizes the day that just ended,
  and emails it to **allivg@ivgjapan.org**. Fixed opening and closing
  lines live in `GREETING` / `SIGNOFF` at the top of
  `scripts/send_daily_report.py`.
- **`scripts/collect_snapshot.py`** / **`scripts/send_daily_report.py`**
  — the two Python scripts behind the workflows above. Pure standard
  library, no dependencies to install.
- **`scripts/build_index.py`** — a one-off generator, not part of the
  live site. Inlines `UpperClock-Regular.woff2` as base64 into
  `index.html`. Re-run it (`python3 scripts/build_index.py`) if you
  ever swap the font file or want to regenerate `index.html` from the
  template inside that script.
- **`.nojekyll`** — disables Jekyll processing on GitHub Pages. This
  site is hand-written static HTML and needs no build step; leaving
  Jekyll on caused Pages deploys to fail outright when a stray file
  collided with a directory Jekyll wanted to create.

## What the live API actually returns

Confirmed by the probe run on 19 July 2026 against the real Webscorer
lists:

| | General (432537) | Sponsor (434355) |
|---|---|---|
| Rows | 108 | 1 |
| Fields | `Distance`, `Email`, `Name`, `Wave` | same |
| Team field | none | none |

Three things this settles:

- **One row = one team.** There's no team field; `Name` is the team's
  own name. `countMode` is therefore `rows`.
- **Course labels map cleanly.** The probe reported no unmapped
  `Distance` values, so `courseMap` needs no adjustment.
- **Team size is genuinely unavailable.** No roster or member-count
  field exists, so "members per team" cannot be computed. The daily
  email states this rather than silently omitting it.

### The Wix endpoint is stale

At the time of the probe, Webscorer reported **109** teams
(108 general + 1 sponsor) while `/_functions/counts` still returned
**108** with an `updated` timestamp of `07:58:55Z` — hours old and not
advancing. The Wix figure also splits differently (`full:51, half:40`
vs Webscorer's `full:50, half:41` for general).

This is the reason to prefer Webscorer as the source. It also means any
display still driven by the Wix endpoint — including the tracker
embedded on tokyo-yamathon.com — may be showing stale numbers. Worth
checking whoever maintains that Velo function.

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
