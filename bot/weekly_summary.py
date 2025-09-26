# bot/weekly_summary.py
# Always writes site/weekly.html. Uses last 7 days from daily_summaries.json if present.

import os, json
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(ROOT, "site")
ARCHIVE = os.path.join(DATA_DIR, "daily_summaries.json")

INLINE_CSS = """<style>
:root{--stroke:#e5e7eb;--primary:#7b61ff;--chipbg:#f3f4f6;--chip:#111}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;background:#fff}
.hero{position:relative;min-height:240px;background:
  linear-gradient(180deg, rgba(10,14,25,.60), rgba(10,14,25,.60)),
  url('assets/bg.jpg') center/cover no-repeat;}
.hero::after{
  content:"";position:absolute;inset:0;pointer-events:none;opacity:.28;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncA type='table' tableValues='0 0.6'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  background-size:160px 160px;
}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.hero .wrap{padding:28px 18px;position:relative;z-index:1}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 16px}
.btn{background:#fff;border:1px solid var(--stroke);color:#111;text-decoration:none;padding:8px 12px;border-radius:12px;display:inline-block}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:var(--chipbg);color:#111;border:1px solid var(--stroke)}
.kpi b{font-weight:700}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 8px 0;font-size:18px}
.small{font-size:12px;color:#6b7280}
ul{margin:.25rem 0 .75rem 1.25rem}
</style>"""

def load_archive():
    if os.path.exists(ARCHIVE):
        try:
            with open(ARCHIVE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def last7(archive: dict):
    dates = sorted(archive.keys(), reverse=True)[:7]
    return [(d, archive[d]) for d in dates]

def aggregate(window):
    kw = {}
    br = {}
    items = 0
    headlines = []
    for _, day in window:
        items += int(day.get("stats", {}).get("items_considered", 0))
        for k in day.get("keywords", []):
            if isinstance(k, dict):
                term = k.get("term"); c = int(k.get("count", 0))
            else:
                term, c = k, 1
            if term: kw[term] = kw.get(term, 0) + c
        for b in day.get("brands", []):
            name = b.get("name"); c = int(b.get("count", 0))
            if name: br[name] = br.get(name, 0) + c
        for h in day.get("highlights", []):
            if len(headlines) < 10:
                headlines.append(h)
    kw_top = sorted(kw.items(), key=lambda x: (-x[1], -len(x[0].split()), x[0]))[:10]
    br_top = sorted(br.items(), key=lambda x: (-x[1], x[0]))[:10]
    return items, kw_top, br_top, headlines

def html(window):
    os.makedirs(SITE_DIR, exist_ok=True)
    if not window:
        return f"""<!doctype html><html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero"><div class="wrap">
  <h1>Weekly Retail Summary</h1>
  <p>No archive yet — this page will populate after the first daily run.</p>
  <div class="actions">
    <a class="btn" href="index.html">Dashboard</a>
    <a class="btn" href="news.html">News Sites</a>
    <a class="btn" href="stats.html">Stats</a>
  </div>
</div></div>
<div class="wrap"><div class="card"><p class="small">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p></div></div>
</body></html>"""
    span = f"{window[-1][0]} → {window[0][0]}"
    items, kw_top, br_top, heads = aggregate(window)
    kw_html = "".join(f"<li>{k} — <b>{v}</b></li>" for k,v in kw_top) or "<li class='small'>No keywords.</li>"
    br_html = "".join(f"<li>{b} — <b>{v}</b></li>" for b,v in br_top) or "<li class='small'>No brands.</li>"
    hl_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title','(untitled)')}</a> "
        f"<span class='small'>({h.get('source','')})</span></li>" for h in heads
    ) or "<li class='small'>No headlines.</li>"
    kpis = []
    if items: kpis.append(f"<span class='kpi'><b>{items}</b> Articles</span>")
    if kw_top: kpis.append(f"<span class='kpi'><b>{kw_top[0][1]}</b> “{kw_top[0][0]}”</span>")
    if br_top: kpis.append(f"<span class='kpi'><b>{br_top[0][1]}</b> {br_top[0][0]}</span>")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero"><div class="wrap">
  <h1>Weekly Retail Summary</h1>
  <p>{span}</p>
  <div class="kpis">{''.join(kpis)}</div>
  <div class="actions" style="margin-top:10px">
    <a class="btn" href="index.html">Dashboard</a>
    <a class="btn" href="news.html">News Sites</a>
    <a class="btn" href="stats.html">Stats</a>
  </div>
</div></div>
<div class="wrap">
  <div class="card"><h2>Top Keywords (7-day totals)</h2><ul>{kw_html}</ul></div>
  <div class="card"><h2>Top Brands (7-day totals)</h2><ul>{br_html}</ul></div>
  <div class="card"><h2>Representative Headlines</h2><ul>{hl_html}</ul></div>
  <p class="small">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
</body></html>"""

def run():
    archive = load_archive()
    window = last7(archive)
    page = html(window)
    with open(os.path.join(SITE_DIR, "weekly.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("Wrote site/weekly.html")

if __name__ == "__main__":
    run()
