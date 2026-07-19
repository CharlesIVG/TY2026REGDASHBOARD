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
Webscorer JSON API client for Tokyo Yamathon registration counts.

Pulls the general and sponsor registration lists directly from Webscorer
and reduces them to aggregate counts. Replaces the Wix /_functions/counts
endpoint, which collapses the general/sponsor split before it reaches us.

API reference:
  https://www.webscorer.com/blog/post/how-to-access-race-data-via-json-api
  GET /json/registerlist?raceid=r&apiid=n&apipriv=p
  GET /json/mystartlists?apiid=n&apipriv=p&filt=R
Requires an active PRO Results subscription on the organizer account.

TWO HARD RULES IN THIS FILE
---------------------------
1. NO PERSONAL DATA IS EVER RETURNED OR WRITTEN.
   registerlist responses contain participant names and contact details.
   This module aggregates in memory and returns only counts. Nothing that
   could identify a person leaves this file. The repo is public; Japan's
   APPI and the GDPR both apply to that roster.

2. THE API TOKEN IS NEVER LOGGED.
   It travels as a URL query parameter, so any exception, debug print, or
   traceback that includes a raw URL would leak it into the GitHub Actions
   log. Every outbound URL is scrubbed through _redact() before it can
   reach a log line.

Credentials come from the environment, never from a committed file:
  WEBSCORER_API_ID     -> apiid
  WEBSCORER_API_TOKEN  -> apipriv
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API_ID = os.environ.get("WEBSCORER_API_ID", "").strip()
API_TOKEN = os.environ.get("WEBSCORER_API_TOKEN", "").strip()

TIMEOUT = 30
USER_AGENT = "yamathon-tracker-bot/1.0"

# Fields we refuse to copy out of a response under any circumstances, even
# into diagnostics. Matched case-insensitively as substrings.
PERSONAL_FIELD_HINTS = (
    "name", "email", "phone", "address", "dob", "birth", "age", "gender",
    "city", "state", "zip", "postal", "country", "team", "club", "contact",
    "emergency", "bib", "comment", "note",
)


def _redact(text: str) -> str:
    """Strip credentials out of anything headed for a log."""
    out = str(text)
    if API_TOKEN:
        out = out.replace(API_TOKEN, "***TOKEN***")
    if API_ID:
        out = out.replace(API_ID, "***APIID***")
    # belt and braces: catch the query params even if the values differ
    out = re.sub(r"(apipriv=)[^&\s]+", r"\1***", out)
    out = re.sub(r"(apiid=)[^&\s]+", r"\1***", out)
    return out


def configured() -> bool:
    return bool(API_ID and API_TOKEN)


def _get(base_url: str, path: str, params: dict) -> dict:
    q = dict(params)
    q["apiid"] = API_ID
    q["apipriv"] = API_TOKEN
    url = f"{base_url}/{path}?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} from {_redact(url)}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error for {_redact(url)}: {_redact(exc.reason)}") from None
    except json.JSONDecodeError:
        raise RuntimeError(f"non-JSON response from {_redact(url)}") from None

    # Webscorer signals failure with {"Error": "..."} and HTTP 200
    if isinstance(data, dict) and data.get("Error"):
        raise RuntimeError(f"Webscorer API error: {data['Error']}")
    return data


def _rows(payload: dict) -> list:
    """registerlist responses put the entries under StartList (per the API
    docs, the same shape serves start lists and registration lists). Fall
    back across the plausible key names rather than assuming one."""
    for key in ("StartList", "Registrations", "RegisterList", "Racers"):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []


def classify_course(value: str, course_map: dict) -> str | None:
    """Map a Distance/Category string onto full / half / quarter.

    Order is load-bearing: 'half-a-half' contains 'half', so the quarter
    patterns must be tested first or every Half-a-Half entry silently
    lands in the Half bucket. courseMap in the config is ordered
    quarter -> half -> full for exactly this reason.
    """
    if not value:
        return None
    v = str(value).strip().lower()
    for course in ("quarter", "half", "full"):
        for pat in course_map.get(course, []):
            if str(pat).lower() in v:
                return course
    return None


def _detect_team_field(rows: list) -> str | None:
    for cand in ("Team", "TeamName", "Team name", "TeamNm"):
        for r in rows:
            if isinstance(r, dict) and cand in r:
                return cand
    return None


def fetch_list(base_url: str, race_id: str, cfg: dict) -> dict:
    """Fetch one registration list and reduce it to counts.

    Returns aggregate numbers plus diagnostics. No personal data.
    """
    payload = _get(base_url, "registerlist", {"raceid": race_id})
    rows = _rows(payload)

    dist_field = cfg.get("distanceField") or "Distance"
    course_map = cfg.get("courseMap", {})
    team_field = cfg.get("teamField") or _detect_team_field(rows)

    counts = {"full": 0, "half": 0, "quarter": 0}
    unmapped = {}
    teams = set()

    for r in rows:
        if not isinstance(r, dict):
            continue
        raw = r.get(dist_field) or r.get("Category") or ""
        course = classify_course(raw, course_map)
        if course:
            counts[course] += 1
        elif raw:
            key = str(raw)[:40]
            unmapped[key] = unmapped.get(key, 0) + 1
        if team_field:
            t = r.get(team_field)
            if t:
                teams.add(str(t).strip().lower())

    info = payload.get("RaceInfo") or {}
    return {
        "raceId": race_id,
        "raceName": info.get("Name", ""),
        "rowCount": len(rows),
        "distinctTeams": len(teams) if team_field else None,
        "teamField": team_field,
        "counts": counts,
        "unmappedDistances": unmapped,
        # field NAMES only - never values - so we can debug shape safely
        "fieldsSeen": sorted({k for r in rows[:50] if isinstance(r, dict) for k in r.keys()}),
    }


def fetch_all(cfg: dict) -> dict:
    """Fetch every configured list and combine into the counts payload the
    rest of the pipeline expects, plus a general/sponsor channel split."""
    base = cfg.get("baseUrl", "https://www.webscorer.com/json")
    per_channel = {}
    combined = {"full": 0, "half": 0, "quarter": 0}
    diagnostics = []

    for entry in cfg.get("lists", []):
        res = fetch_list(base, str(entry["raceId"]), cfg)
        channel = entry.get("channel", "general")

        mode = cfg.get("countMode", "auto")
        if mode == "distinctTeam" and res["distinctTeams"] is not None:
            total = res["distinctTeams"]
        else:
            total = res["rowCount"]

        per_channel[channel] = {
            "total": total,
            "rowCount": res["rowCount"],
            "distinctTeams": res["distinctTeams"],
            **res["counts"],
        }
        for k in combined:
            combined[k] += res["counts"][k]

        diagnostics.append(
            {
                "channel": channel,
                "raceId": res["raceId"],
                "raceName": res["raceName"],
                "rowCount": res["rowCount"],
                "distinctTeams": res["distinctTeams"],
                "teamField": res["teamField"],
                "counts": res["counts"],
                "unmappedDistances": res["unmappedDistances"],
                "fieldsSeen": res["fieldsSeen"],
            }
        )

    total = sum(combined.values())
    out = {
        **combined,
        "total": total,
        "general": per_channel.get("general", {}).get("total", 0),
        "sponsor": per_channel.get("sponsor", {}).get("total", 0),
        "byChannel": per_channel,
        "_diagnostics": diagnostics,
    }
    return out


def probe(cfg: dict, expected_total: int | None = None) -> int:
    """Structure-only report: what the API returns, without exposing anyone.

    Prints field NAMES, distinct course labels, and row vs team counts, so we
    can confirm whether one row means one team or one racer. If the current
    Wix total is passed in, says which counting mode matches it.
    """
    if not configured():
        print("WEBSCORER_API_ID / WEBSCORER_API_TOKEN not set in the environment.", file=sys.stderr)
        return 2
    try:
        data = fetch_all(cfg)
    except RuntimeError as exc:
        print(f"ERROR: {_redact(exc)}", file=sys.stderr)
        return 1

    print("=" * 64)
    print("WEBSCORER PROBE - structure only, no personal data")
    print("=" * 64)
    for d in data["_diagnostics"]:
        print(f"\n[{d['channel']}] raceid={d['raceId']}  {d['raceName']}")
        print(f"  rows in list      : {d['rowCount']}")
        print(f"  distinct teams    : {d['distinctTeams']}  (team field: {d['teamField']})")
        print(f"  course split      : full={d['counts']['full']} half={d['counts']['half']} quarter={d['counts']['quarter']}")
        if d["unmappedDistances"]:
            print(f"  !! UNMAPPED course labels (add these to courseMap in webscorer_config.json):")
            for k, v in sorted(d["unmappedDistances"].items(), key=lambda x: -x[1]):
                print(f"       {k!r}: {v} entries")
        print(f"  fields available  : {', '.join(d['fieldsSeen']) or '(none)'}")

    print("\n" + "-" * 64)
    print(f"COMBINED  full={data['full']} half={data['half']} quarter={data['quarter']} total={data['total']}")
    print(f"CHANNELS  general={data['general']} sponsor={data['sponsor']}")

    if expected_total is not None:
        rows_total = sum(d["rowCount"] for d in data["_diagnostics"])
        teams_total = sum(d["distinctTeams"] or 0 for d in data["_diagnostics"])
        print(f"\nCross-check against the Wix counts endpoint (total={expected_total}):")
        print(f"  counting rows          -> {rows_total}  {'MATCH' if rows_total == expected_total else 'differs'}")
        print(f"  counting distinct teams-> {teams_total}  {'MATCH' if teams_total == expected_total else 'differs'}")
        if rows_total == expected_total:
            print('  => set "countMode": "rows" in data/webscorer_config.json')
        elif teams_total == expected_total:
            print('  => set "countMode": "distinctTeam" in data/webscorer_config.json')
        else:
            print("  => neither matches exactly; the Wix figure may be filtered or stale.")
    return 0


def main() -> int:
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg_path = os.path.join(here, "data", "webscorer_config.json")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = json.load(f)

    if "--probe" in sys.argv:
        expected = None
        for i, a in enumerate(sys.argv):
            if a == "--expect" and i + 1 < len(sys.argv):
                expected = int(sys.argv[i + 1])
        return probe(cfg, expected)

    if not configured():
        print("WEBSCORER_API_ID / WEBSCORER_API_TOKEN not set.", file=sys.stderr)
        return 2
    try:
        data = fetch_all(cfg)
    except RuntimeError as exc:
        print(f"ERROR: {_redact(exc)}", file=sys.stderr)
        return 1
    data.pop("_diagnostics", None)
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
