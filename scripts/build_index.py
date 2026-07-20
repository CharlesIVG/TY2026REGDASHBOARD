#!/usr/bin/env python3
"""One-off generator for index.html — inlines UpperClock-Regular.woff2 as
base64 so the page has no external font dependency (matches the pattern
used in CharlesIVG/TokyoYamathon's own index.html / command-center.html).
Not part of the runtime site; just used to produce index.html from the
template below. Safe to delete after the file is generated, or keep for
future edits.
"""
import base64
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(ROOT, "UpperClock-Regular.woff2")
OUT_PATH = os.path.join(ROOT, "index.html")

with open(FONT_PATH, "rb") as f:
    FONT_B64 = base64.b64encode(f.read()).decode("ascii")

TEMPLATE = r"""<!DOCTYPE html>
<!-- ============================================================
     TOKYO YAMATHON 2026 - REGISTRATION DASHBOARD (LIVE)
     ------------------------------------------------------------
     Developed by SxS Partners for the International Volunteer
     Group-Japan and Tokyo Yamathon.

     This code is the intellectual property of SxS Partners.
     All rights remain the property of SxS Partners and the
     project developer, C. Stewart.

     (c) SxS Partners - All rights reserved.
     ============================================================ -->
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tokyo Yamathon — Registration Dashboard</title>
<meta name="description" content="Live team registration dashboard for Tokyo Yamathon — Full, Half, and Half-a-Half courses.">
<style>
  html,body{margin:0;padding:0;background:#0A0E13;}
  body{padding:14px;font-family:system-ui,sans-serif;}
  .page{max-width:1200px;margin:0 auto;}
  .foot{max-width:1200px;margin:10px auto 0;font-family:system-ui,sans-serif;font-size:11px;color:#7D8CA0;}
  .foot a{color:#7D8CA0;}
  .foot-ip{margin-top:8px;padding-top:10px;border-top:1px solid rgba(125,140,160,.25);
    font-size:10px;color:#5F6B7A;line-height:1.5;
    display:flex;align-items:flex-start;gap:10px;}
  .foot-ip strong{color:#7D8CA0;}
  .foot-logo{width:34px;height:34px;flex:none;opacity:.9;object-fit:contain;}
</style>
</head>
<body>
<div class="page">
<div id="yama-reg" class="dark"></div>
</div>

<script>
/* ============================================================
   REGISTRATION DASHBOARD CONFIG
   Same visual system as CharlesIVG/TokyoYamathon's race-day
   "Command Center" (oc- component set, Upper Clock font, dark
   theme), repointed at pre-race registration counts instead of
   finish-line results, since there's no results data until race
   day itself.
   ============================================================ */
const CONFIG = {
  TITLE: "Tokyo Yamathon",
  TAG: "Team Registration Dashboard",
  START_THEME: "dark",
  COUNTS_URL: "data/latest.json",   // same-origin file, refreshed every 15 min by GitHub Actions
  FEED_URL:   "data/feed.json",     // same-origin file, appended to whenever counts increase
  DAILY_URL:  "data/daily.json",    // per-day registration totals (JST), rebuilt every run
  WEEKLY_URL: "data/weekly.json",   // weekly actuals vs plan + green/amber/red status
  TEAMSIZE_URL: "data/teamsize.json", // member counts (from periodic export - API has none)
  REFRESH_SECONDS: 60,
  FEED_MAX: 150,
  EVENT_GOAL: 1100,
  // Fundraising: entry fee counted at the event fee only (excludes the
  // Y560 processing fee, which goes to the payment processor, not the cause).
  FEE_PER_TEAM: 16000,
  FUNDS_GOAL: 17600000,        // = 1,100 teams x Y16,000
  FUNDS_AMBER_AT: 50,          // % of goal - below this is red
  FUNDS_GREEN_AT: 85,          // % of goal - at/above this is green
  UPDATE_MINUTES: 30,          // collector cadence, shown in the UI
  CHART_SCALE: 100,                 // bar chart tops out at 100 teams/day; auto-grows if a day exceeds it
  LEGS: {
    full:    { label: "Full",        labelJa: "フル",              sub: "≈ 42 km", subJa: "約42km",   color: "#9ACD32", slots: 700 },
    half:    { label: "Half",        labelJa: "ハーフ",            sub: "≈ 21 km", subJa: "約21km",   color: "#F89825", slots: 250 },
    quarter: { label: "Half-a-Half", labelJa: "ハーフ・ア・ハーフ", sub: "≈ 10 km", subJa: "約10km",   color: "#7EB7E4", slots: 150 }
  }
};
/* ============================================================ */

(function () {
  const ROOT = document.getElementById("yama-reg");
  const ORDER = ["full", "half", "quarter"];
  const CY = "#35D0D6";
  const RAG = { green: "#3DD68C", yellow: "#F0B429", red: "#E5484D", pending: "#2A3A4D" };
  // weekly.json still stores "amber" as its status value; map it for display.
  RAG.amber = RAG.yellow;
  const R = 42, C = 2 * Math.PI * R;

  const css = document.createElement("style");
  css.textContent = `
  @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;700&display=swap');
  @font-face{font-family:'Upper Clock';
    src:url(data:font/woff2;base64,__FONT_B64__) format('woff2');
    font-weight:normal;font-style:normal;font-display:block;}

  #yama-reg{font-family:'Inter',system-ui,sans-serif;color:var(--ink);background:var(--bg);
    padding:16px;border-radius:14px;box-sizing:border-box;transition:background .3s,color .3s;
    background-image:linear-gradient(var(--grid) 1px,transparent 1px),linear-gradient(90deg,var(--grid) 1px,transparent 1px);
    background-size:34px 34px;}
  #yama-reg{--numfont:'Upper Clock','IBM Plex Mono',monospace;}
  #yama-reg.dark{--bg:#0A0E13;--barbg:linear-gradient(180deg,#0F1722,#0B111A);--panel:#111823;--panel2:#0D131C;
    --line:#1E2A38;--line2:#2A3A4D;--track:#0B111A;--ink:#E6EDF3;--muted:#7D8CA0;
    --grid:rgba(53,208,214,.04);--guide:rgba(53,208,214,.14);}
  #yama-reg.light{--bg:#EEF1F4;--barbg:linear-gradient(180deg,#FFFFFF,#F3F6F9);--panel:#FFFFFF;--panel2:#FBFCFD;
    --line:#E2E7EC;--line2:#D2DAE1;--track:#EAEEF2;--ink:#141A21;--muted:#5C6875;
    --grid:rgba(30,60,80,.05);--guide:rgba(30,90,110,.16);}
  #yama-reg *{box-sizing:border-box;}
  .mono{font-family:'IBM Plex Mono',monospace;font-variant-numeric:tabular-nums;}

  .oc-bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;
    padding:10px 14px;border:1px solid var(--line2);border-radius:10px;background:var(--barbg);}
  .oc-brand{display:flex;align-items:baseline;gap:12px;}
  .oc-name{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:26px;letter-spacing:.05em;text-transform:uppercase;line-height:1;}
  .oc-tag{color:var(--muted);font-size:11px;letter-spacing:.16em;text-transform:uppercase;}
  .oc-ctrls{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
  .oc-live{display:flex;align-items:center;gap:7px;padding:4px 10px;border:1px solid ${CY};border-radius:20px;
    color:${CY};font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;
    font-variant-numeric:tabular-nums;}
  /* Same reason as the clock: the age text grows and shrinks as it ticks
     from "(45M AGO)" to "(2H 15M AGO)". Reserve the width up front. */
  #oc-livetxt{display:inline-block;min-width:25ch;}
  .oc-live b{width:8px;height:8px;border-radius:50%;background:${CY};animation:oc-blink 1.6s infinite;}
  @keyframes oc-blink{0%,100%{opacity:1}50%{opacity:.25}}
  .oc-clock{text-align:right;}
  .oc-clock .k{display:block;color:var(--muted);font-size:9px;letter-spacing:.16em;text-transform:uppercase;}
  #yama-reg .oc-clock .v{font-family:var(--numfont);font-weight:600;font-size:23px;letter-spacing:.02em;
    /* The header controls sit in a right-aligned flex row, so anything
       whose width changes drags its neighbours sideways. The clock
       repaints every second and its glyphs are not all the same width,
       which made the theme and language buttons jitter once a second.
       tabular-nums fixes it where the font supports it; the fixed
       min-width guarantees it even where it does not. */
    display:inline-block;min-width:8ch;text-align:right;
    font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1,"lnum" 1;}
  .oc-toggle{display:flex;border:1px solid var(--line2);border-radius:20px;overflow:hidden;cursor:pointer;}
  .oc-toggle button{border:0;background:transparent;color:var(--muted);font-family:'IBM Plex Mono',monospace;
    font-size:10px;letter-spacing:.1em;text-transform:uppercase;padding:5px 10px;cursor:pointer;}
  .oc-toggle button.on{background:${CY};color:#03272a;font-weight:600;}

  .oc-kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:12px;}
  @media(max-width:700px){.oc-kpis{grid-template-columns:1fr;}}
  .oc-funds{--kc:${CY};}
  .fundshead{display:flex;align-items:baseline;justify-content:space-between;gap:10px;}
  #yama-reg .fundspct{font-family:var(--numfont);font-weight:600;font-size:19px;line-height:1;}
  .fundsbar{margin-top:9px;height:12px;border-radius:7px;background:var(--track);
    border:1px solid var(--line);overflow:hidden;}
  .fundsfill{height:100%;width:0;border-radius:6px;transition:width .7s cubic-bezier(.22,1,.36,1),background .4s;}
  .oc-kpi{border:1px solid var(--line);border-radius:10px;background:var(--panel);padding:12px 14px;position:relative;overflow:hidden;}
  .oc-kpi::before{content:"";position:absolute;left:0;top:0;bottom:0;width:3px;background:var(--kc,var(--muted));}
  .oc-kpi .lab{color:var(--muted);font-size:10px;letter-spacing:.14em;text-transform:uppercase;}
  #yama-reg .oc-kpi .num{font-family:var(--numfont);font-weight:600;font-size:36px;line-height:1.05;margin-top:2px;}
  .oc-kpi .sub{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);margin-top:2px;}

  .oc-segs{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:12px;}
  @media(max-width:860px){.oc-segs{grid-template-columns:1fr;}.oc-kpis{grid-template-columns:repeat(2,1fr);}.oc-ctrls{gap:10px;}}
  .oc-seg{border:1px solid var(--line);border-radius:10px;background:var(--panel2);padding:14px;transition:opacity .25s;}
  .oc-seg.dim{opacity:.32;}
  .oc-seghead{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:8px;}
  .oc-seglabel{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:22px;letter-spacing:.05em;text-transform:uppercase;}
  .oc-segsub{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);}

  .oc-gauge{position:relative;width:172px;height:172px;margin:6px auto 12px;}
  .oc-gauge svg{position:absolute;inset:0;transform:rotate(-90deg);}
  .oc-track{fill:none;stroke:var(--track);stroke-width:7;}
  .oc-arc{fill:none;stroke-width:7;stroke-linecap:round;transition:stroke-dashoffset .7s ease;}
  .oc-guides{position:absolute;inset:14px;border-radius:50%;pointer-events:none;}
  .oc-guides::before,.oc-guides::after{content:"";position:absolute;border-radius:50%;border:1px solid var(--guide);}
  .oc-guides::before{inset:16%;}.oc-guides::after{inset:36%;}
  .oc-cross{position:absolute;inset:14px;pointer-events:none;}
  .oc-cross::before,.oc-cross::after{content:"";position:absolute;background:var(--guide);}
  .oc-cross::before{left:50%;top:0;bottom:0;width:1px;transform:translateX(-.5px);}
  .oc-cross::after{top:50%;left:0;right:0;height:1px;transform:translateY(-.5px);}
  /* radar sweep removed - too busy for an internal dashboard. The coloured
     progress arc and static crosshair guides are retained. */
  .oc-center{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;}
  #yama-reg .oc-cnum{font-family:var(--numfont);font-weight:600;font-size:38px;line-height:1;}
  .oc-csub{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.08em;margin-top:3px;}
  .oc-cpct{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;letter-spacing:.1em;margin-top:2px;}

  .oc-segrow{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;}
  .oc-stat{text-align:center;padding:8px 4px;border:1px solid var(--line);border-radius:8px;background:var(--track);}
  #yama-reg .oc-stat .n{font-family:var(--numfont);font-weight:600;font-size:22px;line-height:1;}
  .oc-stat .l{color:var(--muted);font-size:9px;letter-spacing:.08em;text-transform:uppercase;margin-top:5px;}

  /* ---- daily report + weekly chart ---- */
  .oc-rep{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.7fr);gap:10px;margin-top:10px;}
  @media(max-width:860px){.oc-rep{grid-template-columns:1fr;}}
  .oc-card{border:1px solid var(--line2);border-radius:10px;background:var(--panel2);padding:14px;}
  .oc-cardh{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:10px;}
  .oc-cardt{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:16px;letter-spacing:.1em;text-transform:uppercase;}
  .oc-cardt span{color:${CY};}
  .oc-cardnote{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);}

  .oc-repdate{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);letter-spacing:.08em;text-transform:uppercase;}
  #yama-reg .oc-repbig{font-family:var(--numfont);font-weight:600;font-size:54px;line-height:1;color:${CY};margin:4px 0 2px;}
  .oc-replab{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;}
  .oc-repsplit{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:12px;}
  .oc-repcell{text-align:center;padding:7px 3px;border:1px solid var(--line);border-radius:8px;background:var(--track);}
  #yama-reg .oc-repcell .n{font-family:var(--numfont);font-weight:600;font-size:19px;line-height:1;}
  .oc-repcell .l{font-family:'IBM Plex Mono','Noto Sans JP',monospace;font-size:8px;color:var(--muted);letter-spacing:.06em;text-transform:uppercase;margin-top:4px;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .oc-reptot{margin-top:11px;padding-top:9px;border-top:1px solid var(--line);display:flex;align-items:baseline;justify-content:space-between;}
  .oc-repnote{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);opacity:.75;margin-top:5px;line-height:1.4;}
  .oc-reptot .l{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);letter-spacing:.1em;text-transform:uppercase;}
  #yama-reg .oc-reptot .v{font-family:var(--numfont);font-weight:600;font-size:20px;}

  .oc-chart{display:flex;gap:10px;}
  .oc-yaxis{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;
    height:150px;font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);flex:none;padding-bottom:1px;}
  .oc-plot{flex:1;min-width:0;position:relative;}
  .oc-grid{position:absolute;left:0;right:0;top:0;height:150px;pointer-events:none;}
  .oc-gl{position:absolute;left:0;right:0;border-top:1px dashed var(--line);}
  .oc-week{display:grid;grid-template-columns:repeat(7,1fr);gap:6px;position:relative;}
  .oc-wcol{display:flex;flex-direction:column;align-items:center;min-width:0;}
  .oc-wtrack{width:100%;height:150px;display:flex;align-items:flex-end;justify-content:center;}
  .oc-wbar{width:70%;max-width:34px;border-radius:4px 4px 0 0;background:${CY};
    transition:height .6s cubic-bezier(.22,1,.36,1);min-height:2px;position:relative;}
  .oc-wbar.zero{background:var(--line2);}
  .oc-wbar.gap{background:repeating-linear-gradient(45deg,var(--line) 0 3px,transparent 3px 7px);
    border:1px dashed var(--line2);border-bottom:0;border-radius:4px 4px 0 0;opacity:.7;}
  .oc-wcol.today .oc-wbar{box-shadow:0 0 0 1px ${CY},0 0 14px ${CY}66;}
  #yama-reg .oc-wnum{font-family:var(--numfont);font-weight:600;font-size:17px;line-height:1;margin-top:7px;}
  .oc-wcol[title] .oc-wnum{color:var(--muted);opacity:.6;}
  .oc-wday{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:14px;letter-spacing:.08em;
    color:var(--muted);margin-top:3px;text-transform:uppercase;}
  .oc-wcol.today .oc-wday{color:${CY};}
  .oc-wdate{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--muted);opacity:.65;margin-top:1px;}

  /* ---- campaign tracker (week on week vs plan) ---- */
  .oc-camp{margin-top:10px;border:1px solid var(--line2);border-radius:10px;background:var(--panel2);padding:14px;}
  .oc-camph{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:4px;}
  .oc-status{display:flex;align-items:center;gap:8px;padding:5px 12px;border-radius:20px;
    font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;
    border:1px solid;}
  .oc-status b{width:9px;height:9px;border-radius:50%;}
  .oc-campsub{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);margin-bottom:12px;}
  .oc-campsub em{font-style:normal;color:var(--ink);}

  .oc-cwrap{display:flex;gap:10px;}
  .oc-cyax{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end;
    height:170px;font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);flex:none;padding-bottom:1px;}
  .oc-cplot{flex:1;min-width:0;position:relative;}
  .oc-cgridl{position:absolute;left:0;right:0;border-top:1px dashed var(--line);}
  .oc-cweeks{display:grid;grid-template-columns:repeat(9,1fr);gap:5px;position:relative;}
  @media(max-width:700px){.oc-cweeks{gap:3px;}}
  .oc-ccol{display:flex;flex-direction:column;align-items:center;min-width:0;}
  .oc-clabel{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:13px;letter-spacing:.06em;
    color:var(--muted);margin-bottom:5px;text-transform:uppercase;white-space:nowrap;}
  .oc-ccol.now .oc-clabel{color:${CY};}
  .oc-ctrack{width:100%;height:170px;display:flex;align-items:flex-end;justify-content:center;position:relative;}
  .oc-cbar{width:76%;max-width:44px;border-radius:4px 4px 0 0;min-height:2px;position:relative;
    transition:height .6s cubic-bezier(.22,1,.36,1);}
  .oc-cbar.pending{background:repeating-linear-gradient(45deg,var(--line) 0 3px,transparent 3px 7px);
    border:1px dashed var(--line2);border-bottom:0;opacity:.55;}
  .oc-ccol.now .oc-cbar{box-shadow:0 0 0 1px currentColor,0 0 14px -2px currentColor;}
  .oc-ctick{position:absolute;left:-3px;right:-3px;height:0;border-top:2px dotted var(--ink);opacity:.55;}
  .oc-ctick::after{content:attr(data-t);position:absolute;right:100%;margin-right:3px;top:-6px;
    font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--muted);white-space:nowrap;}
  #yama-reg .oc-cnum2{font-family:var(--numfont);font-weight:600;font-size:18px;line-height:1;margin-top:7px;}
  .oc-cdates{font-family:'IBM Plex Mono',monospace;font-size:8px;color:var(--muted);opacity:.7;margin-top:3px;white-space:nowrap;}
  .oc-ctgt{font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);margin-top:2px;white-space:nowrap;}
  .oc-legend{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px;padding-top:10px;border-top:1px solid var(--line);
    font-family:'IBM Plex Mono',monospace;font-size:9px;color:var(--muted);letter-spacing:.04em;}
  .oc-lg{display:flex;align-items:center;gap:5px;}
  .oc-lg i{width:9px;height:9px;border-radius:2px;display:inline-block;font-style:normal;}

  .oc-feedwrap{margin-top:10px;border:1px solid var(--line2);border-radius:10px;background:var(--panel2);overflow:hidden;}
  .oc-feedhead{display:flex;align-items:center;justify-content:space-between;padding:9px 14px;border-bottom:1px solid var(--line);}
  .oc-feedtitle{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:16px;letter-spacing:.1em;text-transform:uppercase;}
  .oc-feedtitle span{color:${CY};}
  .oc-feednote{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);}
  .oc-feed{height:220px;overflow-y:auto;scroll-behavior:smooth;padding:4px 0;}
  .oc-feed::-webkit-scrollbar{width:8px;}.oc-feed::-webkit-scrollbar-thumb{background:var(--line2);border-radius:8px;}
  .oc-fr{display:grid;grid-template-columns:92px minmax(0,1fr) 110px 70px;align-items:center;gap:10px;
    padding:7px 14px;border-bottom:1px solid var(--line);font-size:12px;transition:background .4s;}
  .oc-fr:last-child{border-bottom:0;}
  .oc-fr.flash{background:linear-gradient(90deg,${CY}22,transparent);}
  .oc-chip{justify-self:start;font-family:'IBM Plex Mono','Noto Sans JP',monospace;font-size:10px;font-weight:600;
    padding:2px 8px;border-radius:20px;border:1px solid;}
  .oc-fteam{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
  .oc-fchan{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);text-align:right;text-transform:uppercase;letter-spacing:.06em;}
  .oc-ftotal{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);text-align:right;}
  .oc-fago{font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--muted);}
  .oc-fempty{color:var(--muted);font-size:11px;font-family:'IBM Plex Mono',monospace;padding:16px;text-align:center;}
  @media (prefers-reduced-motion:reduce){.oc-fr,.oc-live b{animation:none!important;}.oc-feed{scroll-behavior:auto;}}
  `;
  document.head.appendChild(css);

  ROOT.classList.remove("dark", "light");
  ROOT.classList.add(CONFIG.START_THEME === "light" ? "light" : "dark");

  ROOT.innerHTML += `
  <div class="oc-bar">
    <div class="oc-brand">
      <div class="oc-name">${esc(CONFIG.TITLE)}</div>
      <div class="oc-tag" id="oc-tagtxt">${esc(CONFIG.TAG)}</div>
    </div>
    <div class="oc-ctrls">
      <div class="oc-toggle" id="oc-lang">
        <button data-l="en">EN</button><button data-l="ja">日本語</button>
      </div>
      <div class="oc-toggle" id="oc-theme">
        <button data-t="dark">Dark</button><button data-t="light">Light</button>
      </div>
      <div class="oc-live" id="oc-live"><b id="oc-livedot"></b><span id="oc-livetxt">—</span></div>
      <div class="oc-clock"><span class="k" id="oc-clocklab">Local (JST)</span><span class="v" id="oc-local">--:--:--</span></div>
    </div>
  </div>

  <div class="oc-kpis">
    <div class="oc-kpi oc-funds" id="teams-tile">
      <div class="fundshead">
        <div class="lab" id="lab-all">Total Teams</div>
        <div class="fundspct mono" id="teams-pct">0%</div>
      </div>
      <div class="num mono" id="k-all">0</div>
      <div class="fundsbar"><div class="fundsfill" id="teams-fill"></div></div>
      <div class="sub" id="k-all-sub">of 1100 goal</div>
    </div>
    <div class="oc-kpi oc-funds" id="funds-tile">
      <div class="fundshead">
        <div class="lab" id="lab-funds">Funds Raised</div>
        <div class="fundspct mono" id="funds-pct">0%</div>
      </div>
      <div class="num mono" id="funds-amt">&yen;0</div>
      <div class="fundsbar"><div class="fundsfill" id="funds-fill"></div></div>
      <div class="sub" id="funds-sub">of &yen;0 goal</div>
    </div>
  </div>

  <div class="oc-segs" id="oc-segs"></div>

  <div class="oc-rep">
    <div class="oc-card">
      <div class="oc-cardh">
        <div class="oc-cardt" id="rep-title">Daily <span>Report</span></div>
      </div>
      <div class="oc-repdate" id="rep-date">—</div>
      <div class="oc-repbig mono" id="rep-total">0</div>
      <div class="oc-replab" id="rep-lab">Teams registered today</div>
      <div class="oc-repsplit">
        <div class="oc-repcell"><div class="n mono" id="rep-full" style="color:${CONFIG.LEGS.full.color}">0</div><div class="l" id="rep-full-l">Full</div></div>
        <div class="oc-repcell"><div class="n mono" id="rep-half" style="color:${CONFIG.LEGS.half.color}">0</div><div class="l" id="rep-half-l">Half</div></div>
        <div class="oc-repcell"><div class="n mono" id="rep-quarter" style="color:${CONFIG.LEGS.quarter.color}">0</div><div class="l" id="rep-quarter-l">Half-a-Half</div></div>
      </div>
      <div class="oc-reptot">
        <span class="l" id="rep-cum-l">Cumulative</span><span class="v mono" id="rep-cum">0</span>
      </div>
      <div class="oc-reptot" id="rep-people-row" style="display:none">
        <span class="l" id="rep-people-l">Participants</span><span class="v mono" id="rep-people">0</span>
      </div>
      <div class="oc-repnote" id="rep-people-note"></div>
    </div>

    <div class="oc-card">
      <div class="oc-cardh">
        <div class="oc-cardt" id="wk-title">This <span>Week</span></div>
        <div class="oc-cardnote" id="wk-note">—</div>
      </div>
      <div class="oc-chart">
        <div class="oc-yaxis" id="wk-yaxis"></div>
        <div class="oc-plot">
          <div class="oc-grid" id="wk-grid"></div>
          <div class="oc-week" id="oc-week"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="oc-camp">
    <div class="oc-camph">
      <div class="oc-cardt" id="camp-title">Week on <span>Week</span></div>
      <div class="oc-status" id="camp-status"><b></b><span id="camp-statustxt">—</span></div>
    </div>
    <div class="oc-campsub" id="camp-sub">—</div>
    <div class="oc-cwrap">
      <div class="oc-cyax" id="camp-yaxis"></div>
      <div class="oc-cplot">
        <div id="camp-grid"></div>
        <div class="oc-cweeks" id="camp-weeks"></div>
      </div>
    </div>
    <div class="oc-legend">
      <span class="oc-lg"><i style="background:${RAG.green}"></i><span id="lg-green">On or above target</span></span>
      <span class="oc-lg"><i style="background:${RAG.amber}"></i><span id="lg-amber">Up to 10% short</span></span>
      <span class="oc-lg"><i style="background:${RAG.red}"></i><span id="lg-red">Over 10% short, or 2 weak weeks</span></span>
      <span class="oc-lg"><i style="border:1px dashed var(--line2);background:transparent"></i><span id="lg-pending">Not started</span></span>
      <span class="oc-lg"><i style="border-top:2px dotted var(--ink);background:transparent;border-radius:0;height:0"></i><span id="lg-tick">Weekly target</span></span>
    </div>
  </div>

  <div class="oc-feedwrap">
    <div class="oc-feedhead">
      <div class="oc-feedtitle" id="oc-feedtitle">Registration <span>Activity</span></div>
      <div class="oc-feednote" id="oc-feednote">standing by…</div>
    </div>
    <div class="oc-feed" id="oc-feed"></div>
  </div>`;

  // The View filter (All / Full / Half / Half-a-Half) was removed: this is an
  // internal dashboard where the useful reading is always all three courses at
  // once. activeFilter stays pinned to "all" so the feed and gauges render
  // unfiltered without needing the control.
  // segment gauges
  const segsEl = ROOT.querySelector("#oc-segs");
  for (const key of ORDER) {
    const L = CONFIG.LEGS[key];
    const el = document.createElement("div");
    el.className = "oc-seg"; el.dataset.seg = key;
    el.innerHTML = `
      <div class="oc-seghead">
        <div class="oc-seglabel" id="sl-${key}" style="color:${L.color}">${esc(L.label)}</div>
        <div class="oc-segsub" id="ss-${key}">${esc(L.sub)}</div>
      </div>
      <div class="oc-gauge">
        <svg viewBox="0 0 100 100"><circle class="oc-track" cx="50" cy="50" r="${R}"></circle>
          <circle class="oc-arc" id="arc-${key}" cx="50" cy="50" r="${R}" stroke="${L.color}"
            stroke-dasharray="${C.toFixed(1)}" stroke-dashoffset="${C.toFixed(1)}"></circle></svg>
        <div class="oc-guides"></div><div class="oc-cross"></div>
        <div class="oc-center">
          <div class="oc-cnum" id="cnum-${key}">0</div>
          <div class="oc-csub" id="csub-${key}">of ${L.slots} slots</div>
          <div class="oc-cpct" style="color:${L.color}" id="cpct-${key}">0%</div>
        </div>
      </div>
      <div class="oc-segrow">
        <div class="oc-stat"><div class="n mono" id="s-${key}-reg">0</div><div class="l" id="l-${key}-reg">Registered</div></div>
        <div class="oc-stat"><div class="n mono" id="s-${key}-rem">0</div><div class="l" id="l-${key}-rem">Remaining</div></div>
        <div class="oc-stat"><div class="n mono" id="s-${key}-pct">0%</div><div class="l" id="l-${key}-pct">Full</div></div>
      </div>`;
    segsEl.appendChild(el);
  }

  /* ---------------- state ---------------- */
  const legState = {};
  for (const key of ORDER) legState[key] = { registered: 0, slots: CONFIG.LEGS[key].slots };
  const feedEl = ROOT.querySelector("#oc-feed");
  let feedCount = 0, lastFeedTs = 0;
  const activeFilter = "all";   // filter UI removed - always show every course

  /* ---------------- language ---------------- */
  const I18N = {
    en: { dark:"Dark", light:"Light", totalTeams:"Total Teams", view:"View ▸", all:"All",
          localJst:"Local (JST)", registered:"Registered", remaining:"Remaining", full:"Full",
          feedTitle:"Registration", feedTitle2:"Activity", logged:"logged", standby:"standing by…",
          now:"now", ago:(n,u)=>n+u+" ago", sysLive:"System Live", recon:"Reconnecting…",
          noData:"No data", updatedAt:(hhmm,mins)=>"Updated "+hhmm+(mins<2?" (just now)":mins<60?" ("+mins+"m ago)":" ("+Math.floor(mins/60)+"h "+(mins%60)+"m ago)"),
          ofGoal:"of "+CONFIG.EVENT_GOAL+" goal", tag:"Team Registration Dashboard", noActivity:"No registration activity yet",
          repTitle:"Daily", repTitle2:"Report", repLab:"Teams registered today", repCum:"Cumulative total",
          repNoData:"Not measured yet - tracking starts from first full day",
          fundsRaised:"Funds Raised", fundsOf:(g)=>"of \u00a5"+g+" goal",
          every:(m)=>"updates every "+m+" min",
          repPeople:"Participants",
          peopleNote:(dist,teams,asOf)=>dist+" \u00b7 "+teams+" teams \u00b7 from registration export "+asOf,
          wkTitle:"Last 7", wkTitle2:"Days", wkNote:(n)=>n+" teams in 7 days",
          dows:["S","M","T","W","T","F","S"], noSnap:"no snapshots this day", chGeneral:"General", chSponsor:"Sponsor",
          campTitle:"Week on", campTitle2:"Week",
          st_green:"On track", st_amber:"Yellow", st_red:"Behind", st_pending:"Not started",
          campCum:(c,g)=>"<em>"+c+"</em> of "+g+" teams",
          campAhead:(d,t)=>"<em>"+d+" ahead</em> of plan ("+t+")",
          campBehind:(d,t)=>"<em>"+d+" behind</em> plan ("+t+")",
          campDays:(d)=>d+" days to close",
          campTwoWeak:"two weak weeks in a row",
          lgGreen:"Green: on or above target", lgYellow:"Yellow: up to 10% short",
          lgRed:"Red: over 10% short, or 2 weak weeks", lgPending:"Not started", lgTick:"Weekly target",
          tgtOpen:"opening", tipBaseline:"Opening week (baseline, no plan target)",
          tipTarget:(n,c)=>"Target: +"+n+" teams (cumulative "+c+")",
          tipActual:(n,c)=>"Actual: +"+n+" teams (cumulative "+c+")",
          tipPending:"Not started yet",
          tipShort:(p)=>p+"% below cumulative target",
          tipAhead:(p)=>p+"% above cumulative target",
          why_at_or_above_target:"Green: at or above cumulative target",
          why_below_target:"Measured against cumulative target",
          why_weak_week:"Yellow: week came in under 90% of plan",
          why_two_weak_weeks:"Red: two weak weeks in a row (report §6)",
          why_baseline:"Opening week actual" },
    ja: { dark:"ダーク", light:"ライト", totalTeams:"合計チーム数",
          view:"表示 ▸", all:"すべて", localJst:"現地時刻 (JST)",
          registered:"登録済", remaining:"残り", full:"充充率",
          feedTitle:"登録", feedTitle2:"アクティビティ", logged:"件",
          standby:"待機中…", now:"たった今",
          ago:(n,u)=>n+(u==="s"?"秒":"分")+"前", sysLive:"システム稼働中",
          recon:"再接続中…", ofGoal:"目標 "+CONFIG.EVENT_GOAL+" 中",
          noData:"データなし", updatedAt:(hhmm,mins)=>hhmm+" 更新"+(mins<2?"（たった今）":mins<60?"（"+mins+"分前）":"（"+Math.floor(mins/60)+"時間"+(mins%60)+"分前）"),
          tag:"チーム登録ダッシュボード",
          noActivity:"まだ登録アクティビティはありません",
          repTitle:"デイリー", repTitle2:"レポート", repLab:"本日の登録チーム数",
          repNoData:"未計測 - 計測は初日の翌日から",
          fundsRaised:"募金額", fundsOf:(g)=>"目標 \u00a5"+g,
          every:(m)=>m+"分ごとに更新",
          repPeople:"参加者数",
          peopleNote:(dist,teams,asOf)=>dist+" \u00b7 "+teams+"チーム \u00b7 登録エクスポート "+asOf,
          repCum:"累計", wkTitle:"直近", wkTitle2:"7日間",
          wkNote:(n)=>"7日間で "+n+" チーム",
          dows:["日","月","火","水","木","金","土"], noSnap:"この日のデータなし", chGeneral:"一般", chSponsor:"スポンサー",
          campTitle:"週次", campTitle2:"進捗",
          st_green:"順調", st_amber:"要注意", st_red:"遅れ", st_pending:"未開始",
          campCum:(c,g)=>"<em>"+c+"</em> / "+g+" チーム",
          campAhead:(d,t)=>"計画より <em>"+d+" 先行</em> ("+t+")",
          campBehind:(d,t)=>"計画より <em>"+d+" 不足</em> ("+t+")",
          campDays:(d)=>"締切まで "+d+" 日",
          campTwoWeak:"2週連続で目標未達",
          lgGreen:"緑: 目標達成", lgYellow:"黄: 10%以内の不足",
          lgRed:"赤: 10%以上の不足、または2週連続未達", lgPending:"未開始", lgTick:"週次目標",
          tgtOpen:"開始週", tipBaseline:"開始週（基準値・目標なし）",
          tipTarget:(n,c)=>"目標: +"+n+" チーム（累計 "+c+"）",
          tipActual:(n,c)=>"実績: +"+n+" チーム（累計 "+c+"）",
          tipPending:"未開始",
          tipShort:(p)=>"累計目標より "+p+"% 不足",
          tipAhead:(p)=>"累計目標より "+p+"% 上回る",
          why_at_or_above_target:"緑: 累計目標を達成",
          why_below_target:"累計目標との比較",
          why_weak_week:"黄: 週次計画の90%未満",
          why_two_weak_weeks:"赤: 2週連続で目標未達（レポート §6）",
          why_baseline:"開始週の実績" }
  };
  let LANG = "en";
  const t = k => { const v = I18N[LANG][k]; return v === undefined ? k : v; };
  const legLabel = k => LANG === "ja" ? (CONFIG.LEGS[k].labelJa || CONFIG.LEGS[k].label) : CONFIG.LEGS[k].label;
  const legSub   = k => LANG === "ja" ? (CONFIG.LEGS[k].subJa   || CONFIG.LEGS[k].sub)   : CONFIG.LEGS[k].sub;

  function applyLang() {
    ROOT.querySelectorAll("#oc-lang button").forEach(b => b.classList.toggle("on", b.dataset.l === LANG));
    ROOT.querySelector("#oc-tagtxt").textContent = t("tag");
    ROOT.querySelector("#oc-clocklab").textContent = t("localJst");
    ROOT.querySelector("#lab-all").textContent = t("totalTeams");
    ROOT.querySelector("#k-all-sub").textContent = t("ofGoal");
    ROOT.querySelector("#lab-funds").textContent = t("fundsRaised");
    for (const key of ORDER) {
      const sl = ROOT.querySelector("#sl-" + key); if (sl) sl.textContent = legLabel(key);
      const ss = ROOT.querySelector("#ss-" + key); if (ss) ss.textContent = legSub(key);
      ROOT.querySelector("#l-" + key + "-reg").textContent = t("registered");
      ROOT.querySelector("#l-" + key + "-rem").textContent = t("remaining");
      ROOT.querySelector("#l-" + key + "-pct").textContent = t("full");
    }
    ROOT.querySelector("#oc-feedtitle").innerHTML = t("feedTitle") + ' <span>' + t("feedTitle2") + '</span>';
    ROOT.querySelector("#oc-feednote").textContent = feedCount ? feedCount + " " + t("logged") : t("standby");
    feedEl.querySelectorAll(".oc-chip").forEach(c => { c.textContent = legLabel(c.dataset.leg); });
    const empty = feedEl.querySelector(".oc-fempty"); if (empty) empty.textContent = t("noActivity");
    // daily report + weekly chart
    ROOT.querySelector("#rep-title").innerHTML = t("repTitle") + ' <span>' + t("repTitle2") + '</span>';
    ROOT.querySelector("#wk-title").innerHTML = t("wkTitle") + ' <span>' + t("wkTitle2") + '</span>';
    ROOT.querySelector("#rep-lab").textContent = t("repLab");
    ROOT.querySelector("#rep-cum-l").textContent = t("repCum");
    ROOT.querySelector("#rep-people-l").textContent = t("repPeople");
    for (const key of ORDER) ROOT.querySelector("#rep-" + key + "-l").textContent = legLabel(key);
    // campaign tracker
    ROOT.querySelector("#camp-title").innerHTML = t("campTitle") + ' <span>' + t("campTitle2") + '</span>';
    ROOT.querySelector("#lg-green").textContent = t("lgGreen");
    ROOT.querySelector("#lg-amber").textContent = t("lgYellow");
    ROOT.querySelector("#lg-red").textContent = t("lgRed");
    ROOT.querySelector("#lg-pending").textContent = t("lgPending");
    ROOT.querySelector("#lg-tick").textContent = t("lgTick");
    renderDaily();
    renderWeekly();
    tickAgo();
  }
  ROOT.querySelectorAll("#oc-lang button").forEach(b => { b.onclick = () => { LANG = b.dataset.l; applyLang(); }; });

  /* ---------------- theme toggle ---------------- */
  ROOT.querySelector("#oc-theme").querySelectorAll("button").forEach(btn => {
    if (btn.dataset.t === (CONFIG.START_THEME === "light" ? "light" : "dark")) btn.classList.add("on");
    btn.onclick = () => {
      const tt = btn.dataset.t;
      ROOT.classList.remove("dark", "light"); ROOT.classList.add(tt);
      ROOT.querySelectorAll("#oc-theme button").forEach(b => b.classList.toggle("on", b.dataset.t === tt));
    };
  });

  /* ---------------- paint ---------------- */
  function set(id, v) { const el = ROOT.querySelector("#" + id); if (el) el.textContent = v; }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
  function pad(n) { return String(n).padStart(2, "0"); }

  function paint() {
    let total = 0;
    for (const key of ORDER) {
      const s = legState[key];
      total += s.registered;
      const pct = s.slots ? Math.min(1, s.registered / s.slots) : 0;
      const arc = ROOT.querySelector("#arc-" + key);
      if (arc) arc.style.strokeDashoffset = (C * (1 - pct)).toFixed(1);
      set("cnum-" + key, s.registered);
      set("cpct-" + key, Math.round(pct * 100) + "%");
      set("s-" + key + "-reg", s.registered);
      set("s-" + key + "-rem", Math.max(0, s.slots - s.registered));
      set("s-" + key + "-pct", Math.round(pct * 100) + "%");
    }
    // --- progress bars: teams and funds share one red/yellow/green rule ---
    const ragFor = p => p >= CONFIG.FUNDS_GREEN_AT ? RAG.green
                      : p >= CONFIG.FUNDS_AMBER_AT ? RAG.yellow
                      : RAG.red;
    function bar(tileId, fillId, pctId, pct) {
      const col = ragFor(pct);
      const fill = ROOT.querySelector("#" + fillId);
      if (fill) { fill.style.width = Math.min(100, pct) + "%"; fill.style.background = col; }
      const tile = ROOT.querySelector("#" + tileId);
      if (tile) tile.style.setProperty("--kc", col);
      const pe = ROOT.querySelector("#" + pctId);
      if (pe) { pe.textContent = pct.toFixed(1) + "%"; pe.style.color = col; }
      return col;
    }

    set("k-all", total);
    bar("teams-tile", "teams-fill", "teams-pct",
        CONFIG.EVENT_GOAL ? (total / CONFIG.EVENT_GOAL) * 100 : 0);

    // --- funds raised ---
    // Straight calculation: every registered team = one entry fee. There is
    // no donation field in Webscorer (checked - the API returns no money data
    // at all), so this is derived, not reported. Labelled as such in the UI.
    const raised = total * CONFIG.FEE_PER_TEAM;
    const pct = CONFIG.FUNDS_GOAL ? (raised / CONFIG.FUNDS_GOAL) * 100 : 0;
    set("funds-amt", "\u00a5" + raised.toLocaleString());
    set("funds-sub", t("fundsOf")(CONFIG.FUNDS_GOAL.toLocaleString()));
    bar("funds-tile", "funds-fill", "funds-pct", pct);
  }

  /* ---------------- feed ---------------- */
  function renderFeed(items) {
    feedEl.innerHTML = "";
    feedCount = items.length;
    if (!items.length) {
      feedEl.innerHTML = `<div class="oc-fempty">${t("noActivity")}</div>`;
    } else {
      for (const row of items.slice(0, CONFIG.FEED_MAX)) {
        const L = CONFIG.LEGS[row.course] || { label: row.course, color: "#888" };
        const div = document.createElement("div");
        div.className = "oc-fr" + (row.ts > lastFeedTs ? " flash" : "");
        div.dataset.leg = row.course;
        if (activeFilter !== "all" && activeFilter !== row.course) div.style.display = "none";
        const d = new Date(row.ts);
        const jst = new Date(d.getTime() + (d.getTimezoneOffset() + 540) * 60000);
        const dateStr = (jst.getMonth() + 1) + "/" + jst.getDate();
        const timeStr = pad(jst.getHours()) + ":" + pad(jst.getMinutes());
        // Two shapes: named-team entries (from the Webscorer roster diff) and
        // older anonymous count-delta entries. Render whichever we're given.
        if (row.team) {
          div.innerHTML = `
            <div class="oc-fago">${dateStr} ${timeStr}</div>
            <div class="oc-fteam" title="${esc(row.team)}">${esc(row.team)}</div>
            <div class="oc-chip" data-leg="${row.course}" style="color:${L.color};border-color:${L.color}55;background:${L.color}14">${esc(legLabel(row.course))}</div>
            <div class="oc-fchan">${row.channel === "sponsor" ? t("chSponsor") : t("chGeneral")}</div>`;
        } else {
          div.innerHTML = `
            <div class="oc-fago">${dateStr} ${timeStr}</div>
            <div class="oc-fteam">&mdash;</div>
            <div class="oc-chip" data-leg="${row.course}" style="color:${L.color};border-color:${L.color}55;background:${L.color}14">${esc(legLabel(row.course))}</div>
            <div class="oc-fchan" style="color:${L.color}">+${row.delta}</div>`;
        }
        feedEl.appendChild(div);
      }
    }
    lastFeedTs = items.length ? items[0].ts : lastFeedTs;
    ROOT.querySelector("#oc-feednote").textContent = feedCount ? feedCount + " " + t("logged") : t("standby");
  }

  function tickAgo() { /* time-of-day feed rows don't need a live "ago" tick, kept as a hook for future use */ }

  /* ---------------- daily report + weekly chart ---------------- */
  let dailyData = { days: [] };

  function ymd(d) { return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()); }
  function jstNow() { const d = new Date(); return new Date(d.getTime() + (d.getTimezoneOffset() + 540) * 60000); }

  function renderDaily() {
    const days = (dailyData && dailyData.days) || [];
    const byDate = {};
    days.forEach(d => { byDate[d.date] = d; });

    const now = jstNow();
    const todayStr = ymd(now);
    const today = byDate[todayStr] || { total: 0, full: 0, half: 0, quarter: 0, cumulative: 0 };

    // --- daily report card ---
    const dateFmt = LANG === "ja"
      ? { year: "numeric", month: "long", day: "numeric", weekday: "long" }
      : { weekday: "long", year: "numeric", month: "short", day: "numeric" };
    try {
      set("rep-date", now.toLocaleDateString(LANG === "ja" ? "ja-JP" : "en-US", dateFmt) + " · JST");
    } catch (e) { set("rep-date", todayStr + " · JST"); }

    // A null total means the day was never measured (no snapshot today, or
    // none yesterday to compare against). Show a dash - never a number that
    // would actually be the backlog from an unsampled gap.
    const unmeasured = today.total == null;
    set("rep-total", unmeasured ? "–" : today.total);
    ROOT.querySelector("#rep-total").style.color = unmeasured ? "var(--muted)" : CY;
    ROOT.querySelector("#rep-lab").textContent = unmeasured ? t("repNoData") : t("repLab");
    for (const k of ORDER) set("rep-" + k, unmeasured ? "–" : (today[k] == null ? "–" : today[k]));
    // cumulative: today's figure if present, else the most recent day that has one
    let cum = today.cumulative || 0;
    if (!cum) { for (let i = days.length - 1; i >= 0; i--) { if (days[i].cumulative) { cum = days[i].cumulative; break; } } }
    set("rep-cum", cum);

    // --- weekly chart: rolling last 7 days, ending today ---
    // (A strict Sun->Sat calendar week renders almost empty early in the week,
    //  since the data would still be sitting in the previous week.)
    const week = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      const key = ymd(d);
      const rec = byDate[key];
      week.push({
        date: key,
        dow: d.getDay(),
        label: d.getDate(),
        total: rec ? rec.total : null,
        isToday: key === todayStr,
        isFuture: false,
        // A day counts as known only if it was actually measured: sampled on
        // the day AND on the day before. Anything else is a gap, and its
        // apparent "total" would really be the backlog swept up from the
        // unsampled days.
        hasData: !!rec && rec.measured === true && rec.total != null
      });
    }

    const weekTotal = week.reduce((a, w) => a + (w.hasData ? w.total : 0), 0);
    const peak = Math.max(0, ...week.map(w => (w.hasData ? w.total : 0)));
    // Fixed 100-team scale as requested; grows in 50s only if a day actually exceeds it,
    // so a big day is never silently clipped off the top of the chart.
    const scale = peak > CONFIG.CHART_SCALE ? Math.ceil(peak / 50) * 50 : CONFIG.CHART_SCALE;

    const yaxis = ROOT.querySelector("#wk-yaxis");
    yaxis.innerHTML = [scale, Math.round(scale / 2), 0].map(v => `<span>${v}</span>`).join("");

    const grid = ROOT.querySelector("#wk-grid");
    grid.innerHTML = [0, 25, 50, 75].map(p => `<div class="oc-gl" style="top:${p}%"></div>`).join("");

    const dows = t("dows");
    const weekEl = ROOT.querySelector("#oc-week");
    weekEl.innerHTML = week.map(w => {
      const h = Math.max(0, Math.min(100, (w.total / scale) * 100));
      // A day with no snapshots isn't a confirmed zero — mark it so a
      // collection outage can't be misread as "nobody registered".
      const gap = !w.hasData;
      const cls = gap ? "gap" : (w.total === 0 ? "zero" : "");
      const title = gap ? ` title="${esc(t("noSnap"))}"` : "";
      return `<div class="oc-wcol${w.isToday ? " today" : ""}"${title}>
        <div class="oc-wtrack"><div class="oc-wbar ${cls}" style="height:${gap ? 100 : h}%"></div></div>
        <div class="oc-wnum mono">${gap ? "·" : w.total}</div>
        <div class="oc-wday">${dows[w.dow]}</div>
        <div class="oc-wdate">${w.label}</div>
      </div>`;
    }).join("");

    ROOT.querySelector("#wk-note").textContent = t("wkNote")(weekTotal);
  }

  /* ---------------- data freshness ----------------
     This is a static site: the page can only ever be as fresh as the last
     collector run, and GitHub throttles scheduled workflows unpredictably.
     Showing a permanent "SYSTEM LIVE" badge therefore lies. Show the real
     age of the data and colour it, so a stalled collector is obvious at a
     glance instead of quietly serving old numbers.                        */
  let lastFetchedAt = null;

  function renderFreshness() {
    const el = ROOT.querySelector("#oc-livetxt");
    const dot = ROOT.querySelector("#oc-livedot");
    const wrap = ROOT.querySelector("#oc-live");
    if (!lastFetchedAt) { if (el) el.textContent = t("noData"); return; }

    const then = new Date(lastFetchedAt);
    const mins = Math.max(0, Math.round((Date.now() - then.getTime()) / 60000));
    const jst = new Date(then.getTime() + (then.getTimezoneOffset() + 540) * 60000);
    const hhmm = pad(jst.getHours()) + ":" + pad(jst.getMinutes());

    let col;
    if (mins <= 30)       col = "#3DD68C";   // fresh
    else if (mins <= 90)  col = CY;          // normal
    else if (mins <= 240) col = "#F0B429";   // getting stale
    else                  col = "#E5484D";   // stalled

    el.textContent = t("updatedAt")(hhmm, mins);
    if (dot) dot.style.background = col;
    if (wrap) { wrap.style.color = col; wrap.style.borderColor = col; }
  }

  /* ---------------- campaign tracker (week on week vs plan) ---------------- */
  let weeklyData = null;

  function renderWeekly() {
    if (!weeklyData || !Array.isArray(weeklyData.weeks)) return;
    const weeks = weeklyData.weeks;

    // --- status pill ---
    const st = weeklyData.status || "pending";
    const col = RAG[st] || RAG.pending;
    const pill = ROOT.querySelector("#camp-status");
    pill.style.color = col; pill.style.borderColor = col;
    pill.querySelector("b").style.background = col;
    set("camp-statustxt", t("st_" + st) || st);

    // --- sub line: where we are vs where the plan says we should be ---
    const cum = weeklyData.cumulative || 0;
    const tgt = weeklyData.targetNow;
    const goal = weeklyData.goal || 1100;
    const bits = [];
    bits.push(t("campCum")(cum, goal));
    if (tgt != null) {
      const diff = Math.round(cum - tgt);
      bits.push(diff >= 0 ? t("campAhead")(Math.abs(diff), Math.round(tgt))
                          : t("campBehind")(Math.abs(diff), Math.round(tgt)));
    }
    if (weeklyData.daysRemaining != null) bits.push(t("campDays")(weeklyData.daysRemaining));
    if (weeklyData.reason === "two_weak_weeks") bits.push(t("campTwoWeak"));
    ROOT.querySelector("#camp-sub").innerHTML = bits.join(" &nbsp;·&nbsp; ");

    // --- scale: fit the largest of actual / target new-teams across all weeks ---
    let peak = 0;
    weeks.forEach(w => {
      peak = Math.max(peak, w.targetNew || 0, w.actualNew || 0);
    });
    const scale = Math.max(50, Math.ceil(peak / 50) * 50);

    ROOT.querySelector("#camp-yaxis").innerHTML =
      [scale, Math.round(scale * 0.75), Math.round(scale / 2), Math.round(scale * 0.25), 0]
        .map(v => `<span>${v}</span>`).join("");
    ROOT.querySelector("#camp-grid").innerHTML =
      [0, 25, 50, 75].map(p => `<div class="oc-cgridl" style="top:${p * 1.7}px"></div>`).join("");

    const fmtRange = (s, e) => {
      const a = new Date(s + "T00:00:00"), b = new Date(e + "T00:00:00");
      const m = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
      return a.getMonth() === b.getMonth()
        ? `${m[a.getMonth()]} ${a.getDate()}-${b.getDate()}`
        : `${m[a.getMonth()]} ${a.getDate()}-${m[b.getMonth()]} ${b.getDate()}`;
    };

    ROOT.querySelector("#camp-weeks").innerHTML = weeks.map(w => {
      const started = w.started;
      const actual = w.actualNew;
      const target = w.targetNew || 0;
      const barCol = started ? (RAG[w.status] || RAG.pending) : null;
      const h = started && actual != null ? Math.max(0, Math.min(100, (actual / scale) * 100)) : 100;
      const tickPct = target > 0 ? Math.min(100, (target / scale) * 100) : null;

      const tip = [
        w.label + "  " + w.start + " → " + w.end,
        w.baseline ? t("tipBaseline") : t("tipTarget")(target, w.targetCum),
        started && actual != null ? t("tipActual")(actual, w.actualCum) : t("tipPending"),
        started && w.shortfallPct != null
          ? (w.shortfallPct > 0 ? t("tipShort")(w.shortfallPct) : t("tipAhead")(Math.abs(w.shortfallPct)))
          : "",
        started && w.reason ? t("why_" + w.reason) || "" : ""
      ].filter(Boolean).join("\n");

      return `<div class="oc-ccol${w.inProgress ? " now" : ""}" title="${esc(tip)}" style="color:${barCol || "inherit"}">
        <div class="oc-clabel">${esc(w.label)}</div>
        <div class="oc-ctrack">
          ${tickPct != null && !w.baseline ? `<div class="oc-ctick" data-t="${target}" style="bottom:${tickPct}%"></div>` : ""}
          <div class="oc-cbar${started ? "" : " pending"}" style="height:${h}%;${barCol ? "background:" + barCol + ";" : ""}"></div>
        </div>
        <div class="oc-cnum2 mono">${started && actual != null ? actual : "–"}</div>
        <div class="oc-ctgt">${w.baseline ? t("tgtOpen") : "/ " + target}</div>
        <div class="oc-cdates">${fmtRange(w.start, w.end)}</div>
      </div>`;
    }).join("");
  }

  /* ---------------- clock ---------------- */
  setInterval(() => {
    const jst = new Date(Date.now() + (new Date().getTimezoneOffset() + 540) * 60000);
    set("oc-local", pad(jst.getHours()) + ":" + pad(jst.getMinutes()) + ":" + pad(jst.getSeconds()));
    if (jst.getSeconds() === 0) renderFreshness();   // re-age once a minute
  }, 1000);

  /* ---------------- live polling ---------------- */
  async function poll() {
    try {
      const [counts, feed, daily, weekly, teamsize] = await Promise.all([
        fetch(CONFIG.COUNTS_URL + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.json()).catch(() => null),
        fetch(CONFIG.FEED_URL + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.json()).catch(() => []),
        fetch(CONFIG.DAILY_URL + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.json()).catch(() => null),
        fetch(CONFIG.WEEKLY_URL + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.json()).catch(() => null),
        fetch(CONFIG.TEAMSIZE_URL + "?t=" + Date.now(), { cache: "no-store" }).then(r => r.json()).catch(() => null)
      ]);
      if (counts) {
        for (const k of ORDER) if (counts[k] != null) legState[k].registered = +counts[k] || 0;
        lastFetchedAt = counts.fetched_at || null;
      }
      renderFreshness();
      if (daily && Array.isArray(daily.days)) dailyData = daily;
      if (weekly && Array.isArray(weekly.weeks)) weeklyData = weekly;
      /* A mean team size is not actionable - you cannot have a third of a
         person. Show the actual tally instead: "76x4  20x3  29x2". Sizes
         are read from the data, not hardcoded. */
      const teamSizeTally = d => !d ? "" : Object.keys(d)
        .sort((a, b) => Number(b) - Number(a))
        .filter(k => d[k])
        .map(k => d[k] + "\u00d7" + k)
        .join("  ");
      if (teamsize && teamsize.people) {
        // Member counts come from a manual Webscorer export - the JSON API has
        // no roster - so label the date it was taken rather than implying live.
        ROOT.querySelector("#rep-people-row").style.display = "";
        set("rep-people", teamsize.people.toLocaleString());
        ROOT.querySelector("#rep-people-note").textContent =
          t("peopleNote")(teamSizeTally(teamsize.distribution), teamsize.teams, teamsize.asOf);
      }
      paint();
      renderDaily();
      renderWeekly();
      renderFeed(Array.isArray(feed) ? feed : []);
    } catch (e) {
      set("oc-livetxt", t("recon"));
    }
  }

  paint();
  applyLang();
  poll();
  setInterval(poll, Math.max(15, CONFIG.REFRESH_SECONDS) * 1000);
})();
</script>

<div class="foot">
  Data refreshed automatically from Webscorer count by a GitHub Actions workflow.
  Updated in 30-minute intervals.
  <div class="foot-ip">
    <img id="sxs-logo" class="foot-logo" alt="SxS Partners" src="sxs-logo.png"
         onerror="this.style.display='none'">
    <span>
      Design and creative engineering by <strong>SxS Partners株式会社</strong> for the
      International Volunteer Group-Japan to be utilized for the Tokyo Yamathon 2026.
      This code is the intellectual property of SxS Partners株式会社. All rights remain
      the property of SxS Partners株式会社 and the project developer, C. Stewart.
      &copy; SxS Partners株式会社 — All rights reserved.
    </span>
  </div>
</div>
</body>
</html>
"""

html = TEMPLATE.replace("__FONT_B64__", FONT_B64)
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Wrote {OUT_PATH} ({len(html)} bytes)")
