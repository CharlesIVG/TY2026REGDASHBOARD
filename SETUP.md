# Setup — 6 steps

> © SxS Partners — All rights reserved. Developed by SxS Partners for
> the International Volunteer Group-Japan and Tokyo Yamathon. All rights
> remain the property of SxS Partners and the project developer,
> C. Stewart.


Full detail is in `README.md`. This is the short version.

---

## 1. Create the repo and push

Drop these files in the root of a new GitHub repo (public is fine — no
credentials are stored in any file here).

```bash
cd tokyo-yamathon-dashboard
git init
git add .
git commit -m "Tokyo Yamathon registration dashboard"
git branch -M main
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

## 2. Turn on GitHub Pages

**Settings → Pages** → Source: *Deploy from a branch* → Branch: `main`,
folder `/ (root)` → Save.

Live at `https://<you>.github.io/<repo>/` within a minute or two.

## 3. Let the collector commit

**Settings → Actions → General** → Workflow permissions → select
**Read and write permissions** → Save.

Without this the collector can't push its data updates.

## 4. Add the Webscorer secrets

**Settings → Secrets and variables → Actions → New repository secret.**

| Secret | Where to find it |
|---|---|
| `WEBSCORER_API_ID` | Webscorer → Organizers → My organizer settings → digits at the end of "Unique organizer URL" |
| `WEBSCORER_API_TOKEN` | Same page, bottom → JSON API Token (8 characters) |

Requires an active **PRO Results** subscription (separate from PRO
timing). Never put these in a file — only here.

## 5. Run the probe first

**Actions → "Webscorer probe (run this first)" → Run workflow.**

Confirms the connection and reports:

- how Webscorer labels each course (any unmapped labels are listed)
- whether one row = one team, cross-checked against the current total
- row counts for the general and sponsor lists

Prints no personal data and no token — the output is safe to share.

If it flags anything, edit `courseMap` / `countMode` in
`data/webscorer_config.json` and re-run.

**If you skip this step:** the collector still works, falling back to
the Wix endpoint — you just won't get the general/sponsor split.

## 6. Add the email secrets (daily report)

Same secrets screen, for the 00:05 JST report to **info@ivgjapan.org**:

| Secret | Value |
|---|---|
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | `587` (STARTTLS) or `465` (SSL) |
| `SMTP_USER` | sending account |
| `SMTP_PASS` | app password, **not** the account password |
| `MAIL_FROM` | from address (often same as `SMTP_USER`) |

Test it: **Actions → "Daily registration report" → Run workflow**. With
no SMTP secrets set it prints the report instead of failing, so you can
check the content first.

---

## What runs when

| Workflow | Schedule | Does |
|---|---|---|
| Collect team count snapshot | every 15 min | Fetch counts → update `data/*.json` → commit |
| Daily registration report | 00:05 JST | Email the previous day's summary |
| Webscorer probe | manual only | Connection/diagnostics check |

## Editing the plan

Weekly targets and RAG thresholds live in **`data/plan.json`** — edit
there, no code changes needed. Slot capacities appear in
`scripts/build_index.py` (`CONFIG.LEGS`) and
`scripts/send_daily_report.py`; if they change, update both and re-run
`python3 scripts/build_index.py`.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Dashboard shows zeros | The collector hasn't run yet. Actions → Collect → Run workflow. |
| Collector fails to push | Step 3 not done (needs read/write permissions). |
| Log says `[wix]` not `[webscorer]` | Secrets missing or wrong — check the probe output. |
| Probe: "PRO Results subscription required" | That subscription is inactive/expired. |
| A course reads 0 but shouldn't | Unmapped course label — probe lists it, add to `courseMap`. |
| Scheduled runs stopped | GitHub disables schedules after 60 days idle. Any manual run re-enables them. |
