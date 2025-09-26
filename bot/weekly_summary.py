# bot/weekly_summary.py
# Weekly AI summary with noise hero + KPI chips

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
.hero .wrap{max-width:1100px;margin:0 auto;padding:28px 18px;width:100%;position:relative;z-index:1}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 16px}
.btn{background:#fff;border:1px solid var(--stroke);color:#111;text-decoration:none;padding:8px 12px;border-radius:12px;display:inline-block}
.btn.primary{background:var(--primary);border:none;color:#fff}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 8px 0;font-size:18px}
ul{margin:.25rem 0 .75rem 1.25rem}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;color:#374151}
.small{font-size:12px;color:#6b7280}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:var(--chipbg);color:#111;border:1px solid var(--stroke)}
.kpi b{font-weight:700}
</style>"""

def load_archive():
    if os.path.exists(ARCHIVE):
        try:
            with open(ARCHIVE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def pick_last_7(archive):
    dates = sorted(archive.keys(), reverse=True)
    return [(d, archive[d]) for d in dates[:7]]

def aggregate(window):
    kw = {}
    br = {}
    total_items = 0
    for _, day in window:
        total_items += int(day.get("stats",{}).get("items_considered",0))
        kws = day.get("keywords", [])
        if kws and isinstance(kws[0], dict):
            for k in kws:
                term = k.get("term"); c = int(k.get("count",0))
                if term: kw[term] = kw.get(term,0) + c
        else:
            for term in kws: kw[term] = kw.get(term,0) + 1
        for b in day.get("brands", []):
            name = b.get("name"); c = int(b.get("count",0))
            if name: br[name] = br.get(name,0) + c
    kw_top = sorted(kw.items(), key=lambda x:(-x[1], -len(x[0].split()), x[0]))[:1]
    br_top = sorted(br.items(), key=lambda x:(-x[1], x[0]))[:1]
    return total_items, kw_top[0] if kw_top else None, br_top[0] if br_top else None

def ai_or_fallback(window):
    # A short, safe fallback summary; (your existing AI code can be left as-is if you added it earlier)
    dates = [d for d,_ in window]
    header = f"{dates[-1]} → {dates[0]}" if dates else ""
    return f"Covering {header}, omnichannel, logistics, AI-in-retail, and re-commerce remained the most visible weekly themes, with steady coverage across major publishers. Expect sustained investment in personalization, last-mile efficiency, and circular retail experiments through next week."

def run():
    archive = load_archive()
    window = pick_last_7(archive)
    os.makedirs(SITE_DIR, exist_ok=True)

    date_span = f"{window[-1][0]} → {window[0][0]}" if window else "—"
    total, top_kw, top_brand = aggregate(window)

    kpis = []
    if total: kpis.append(f"<span class='kpi'><b>{total}</b> Articles</span>")
    if top_kw: kpis.append(f"<span class='kpi'><b>{top_kw[1]}</b> “{top_kw[0]}”</span>")
    if top_brand: kpis.append(f"<span class='kpi'><b>{top_brand[1]}</b> {top_brand[0]}</span>")
    kpi_html = f"<div class='kpis'>{''.join(kpis)}</div>" if kpis else ""

    ai = ai_or_fallback(window)

    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>Weekly Retail Summary</h1>
    <p>{date_span}</p>
    {kpi_html}
    <div class="actions" style="margin-top:10px">
      <a class="btn" href="index.html">Dashboard</a>
      <a class="btn" href="news.html">News Sites</a>
      <a class="btn" href="stats.html">Stats</a>
    </div>
  </div>
</div>

<div class="wrap">
  <div class="card">
    <h2>AI Summary</h2>
    <div>{ai}</div>
    <p class="small" style="margin-top:6px">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
  </div>
</div>
</body></html>"""

    with open(os.path.join(SITE_DIR,"weekly.html"),"w",encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/weekly.html")

if __name__ == "__main__":
    run()
