# bot/stats_page.py
# Writes site/stats.html every run. Shows today's items + 7-day totals (articles, keyword mentions, brand mentions).

import os, json
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA = os.path.join(BASE, "data")
SITE = os.path.join(ROOT, "site")
SUMMARY = os.path.join(DATA, "summary.json")
ARCHIVE = os.path.join(DATA, "daily_summaries.json")

CSS = """<style>
:root{--stroke:#e5e7eb}
*{box-sizing:border-box} body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;background:#fff}
.wrap{max-width:900px;margin:0 auto;padding:18px}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h1{margin:0 0 8px 0;font-size:26px} h2{margin:0 0 8px 0;font-size:18px}
.small{font-size:12px;color:#6b7280}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.stat{border:1px solid var(--stroke);border-radius:12px;padding:12px}
.stat b{font-size:20px}
</style>"""

def load_json(p):
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return None
    return None

def week_totals(arch):
    if not isinstance(arch, dict): return 0,0,0
    dates = sorted(arch.keys(), reverse=True)[:7]
    w_items = w_kw = w_br = 0
    for d in dates:
        day = arch.get(d, {}) or {}
        w_items += int(day.get("stats", {}).get("items_considered", 0))
        for k in (day.get("keywords", []) or []):
            w_kw += int(k.get("count", 1)) if isinstance(k, dict) else 1
        for b in (day.get("brands", []) or []):
            w_br += int(b.get("count", 0)) if isinstance(b, dict) else 0
    return w_items, w_kw, w_br

def run():
    os.makedirs(SITE, exist_ok=True)
    s = load_json(SUMMARY) or {}
    arch = load_json(ARCHIVE) or {}

    today_date = s.get("stats", {}).get("date", "—")
    today_items = int(s.get("stats", {}).get("items_considered", 0))
    today_sources = int(s.get("stats", {}).get("unique_sources", 0))

    w_items, w_kw, w_br = week_totals(arch)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Stats</title>{CSS}</head>
<body>
<div class="wrap">
  <h1>Stats</h1>
  <div class="grid">
    <div class="stat"><div>Today’s Articles</div><b>{today_items}</b><div class="small">Date: {today_date}</div></div>
    <div class="stat"><div>Today’s Sources</div><b>{today_sources}</b></div>
    <div class="stat"><div>7-Day Articles</div><b>{w_items}</b></div>
    <div class="stat"><div>7-Day Keyword Mentions</div><b>{w_kw}</b></div>
    <div class="stat"><div>7-Day Brand Mentions</div><b>{w_br}</b></div>
  </div>
  <div class="card">
    <h2>Notes</h2>
    <p class="small">Counts from <code>summary.json</code> (today) and <code>daily_summaries.json</code> (last 7 days).</p>
    <p class="small">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
    <p class="small"><a href="index.html">← Dashboard</a> · <a href="weekly.html">Weekly</a></p>
  </div>
</div>
</body></html>"""
    with open(os.path.join(SITE, "stats.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/stats.html")

if __name__ == "__main__":
    run()
