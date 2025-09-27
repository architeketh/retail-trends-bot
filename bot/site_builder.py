# bot/site_builder.py
# Builds a SINGLE PAGE: site/index.html with sections:
# - Overview (charts + headlines)
# - Weekly Summary (7-day rollup lists)
# - Stats (today + 7-day totals)
#
# This eliminates weekly.html and stats.html 404s.

import os, json, csv
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless for CI
import matplotlib.pyplot as plt
from matplotlib import ticker

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA = os.path.join(BASE, "data")
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "assets")

ARCHIVE = os.path.join(DATA, "daily_summaries.json")
SUMMARY = os.path.join(DATA, "summary.json")

TITLE = "Retail Trends Dashboard"
DESC  = "Daily updated retail trend insights."

KW_IMG = os.path.join(ASSETS, "keywords.png")
BR_IMG = os.path.join(ASSETS, "brands.png")

plt.rcParams.update({
    "figure.facecolor": "#ffffff","axes.facecolor":"#ffffff","axes.edgecolor":"#cccccc",
    "axes.labelcolor":"#111111","axes.titlecolor":"#111111","xtick.color":"#111111",
    "ytick.color":"#111111","font.size":10,
})

PALETTE_KW = ["#2E93fA","#66DA26","#E91E63","#FF9800","#00E396","#775DD0",
              "#008FFB","#FEB019","#FF4560","#00D9E9","#A300D6","#F86624",
              "#D10CE8","#4CAF50","#9C27B0"]
PALETTE_BR = ["#7B61FF","#FF6B6B","#00C49A","#FFB703","#219EBC","#8338EC",
              "#FB5607","#06D6A0","#118AB2","#EF476F","#3A86FF","#FFBE0B"]

CSS = """<style>
:root{--stroke:#e5e7eb;--btn:#f8fafc;--primary:#7b61ff}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;margin:0}
.hero{position:relative;min-height:200px;background:#f9fafb;border-bottom:1px solid var(--stroke)}
.hero .wrap{max-width:1100px;margin:0 auto;padding:24px 18px}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
h1{margin:0 0 6px 0;font-size:28px}
h2{margin:0 0 10px 0;font-size:18px}
.note{color:#6b7280;font-size:14px}
.header-actions a,.header-actions button{display:inline-block;margin-right:8px;padding:8px 12px;border-radius:12px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}
.header-actions .primary{background:var(--primary);color:#fff;border:none}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:#f3f4f6;color:#111;border:1px solid var(--stroke)}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
img{max-width:100%;border-radius:8px}
#visitor-count{font-size:14px;color:#111;margin:10px 0}
.badge{display:inline-block;margin-left:10px;vertical-align:middle}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
ul{margin:.25rem 0 .75rem 1.25rem}
.anchor{scroll-margin-top:80px}
</style>"""

def ensure_dir_for_file(path): os.makedirs(os.path.dirname(path), exist_ok=True)
def pick_colors(n, p): return (p * ((n+len(p)-1)//len(p)))[:n]

def style_axes(ax):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for s in ("left","bottom"): ax.spines[s].set_color("#e0e0e0")
    ax.grid(axis="x", color="#eeeeee", linewidth=0.9, zorder=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))

def save_barh(labels, values, title, outpath, palette, xlabel):
    ensure_dir_for_file(outpath); plt.close("all")
    fig, ax = plt.subplots(figsize=(8,6), dpi=150)
    style_axes(ax); ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    y = range(len(labels)); colors = pick_colors(len(labels), palette)
    ax.barh(y, values, color=colors, edgecolor="#fff")
    ax.set_yticks(list(y)); ax.set_yticklabels(labels)
    mx = max(values) if values else 0; offs = mx*0.02 if mx>0 else 0.5
    for i,v in enumerate(values): ax.text(v+offs, i, str(v), va="center", ha="left", color="#111")
    fig.tight_layout(); fig.savefig(outpath, bbox_inches="tight"); plt.close(fig)

def write_headlines_exports(highlights):
    os.makedirs(ASSETS, exist_ok=True)
    jp = os.path.join(ASSETS, "headlines.json"); cp = os.path.join(ASSETS, "headlines.csv")
    with open(jp, "w", encoding="utf-8") as jf: json.dump(highlights, jf, indent=2)
    import csv as _csv
    with open(cp, "w", encoding="utf-8", newline="") as cf:
        w = _csv.DictWriter(cf, fieldnames=["title","link","source","published"])
        w.writeheader(); [w.writerow(h) for h in highlights]
    return os.path.basename(cp), os.path.basename(jp)

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f: return json.load(f)
        except Exception: return None
    return None

def aggregate_week(archive: dict):
    dates = sorted(archive.keys(), reverse=True)[:7]
    kw = {}; br = {}; newest = None; headlines = []
    for i, d in enumerate(dates):
        day = archive[d]
        if i == 0: newest = day
        for k in day.get("keywords", []):
            if isinstance(k, dict): term, c = k.get("term"), int(k.get("count", 0))
            else: term, c = k, 1
            if term: kw[term] = kw.get(term, 0) + c
        for b in day.get("brands", []):
            name, c = b.get("name"), int(b.get("count", 0))
            if name: br[name] = br.get(name, 0) + c
    kw_top = sorted(kw.items(), key=lambda x:(-x[1], -len(x[0].split()), x[0]))
    br_top = sorted(br.items(), key=lambda x:(-x[1], x[0]))
    headlines = (newest.get("highlights", []) if newest else [])[:10]
    return kw_top, br_top, headlines

def build_html(head_html, kw_img_rel, br_img_rel, headlines_html, kpi_html,
               weekly_html, stats_html, updated_str):
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{TITLE}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
{CSS}
</head>
<body>
<div class="hero"><div class="wrap">
  <h1>{TITLE}</h1>
  <p class="note">{DESC}</p>
  <div class="header-actions" style="margin-top:10px">
    <a href="#weekly">Weekly Summary</a>
    <a href="#stats">Stats</a>
    <a href="news.html">News Sites</a>
    <button class="primary" onclick="location.reload()">Refresh</button>
  </div>
  {kpi_html}
</div></div>

<div class="wrap">
  <div id="visitor-count">Visitors: loading…
    <img class="badge" alt="Visitors badge" src="https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://architeketh.github.io/retail-trends-bot/&title=Visitors">
  </div>
  <script>
    (function(){{
      fetch('https://api.countapi.xyz/hit/architeketh/retail-trends')
        .then(function(r){{return r.json();}})
        .then(function(d){{document.getElementById('visitor-count').firstChild.nodeValue='Visitors: '+d.value+' ';}})
        .catch(function(_){{/* badge fallback stays visible */}});
    }})();
  </script>

  <div class="grid">
    <div class="card">
      <h2>Top Keywords (7-day totals)</h2>
      <img src="{kw_img_rel}" alt="Top Keywords (7-day)">
    </div>
    <div class="card">
      <h2>Brand Mentions (7-day totals)</h2>
      <img src="{br_img_rel}" alt="Brand Mentions (7-day)">
    </div>
  </div>

  <div class="card">
    <h2>Headlines</h2>
    <ul>{head_html}</ul>
  </div>

  <a id="weekly" class="anchor"></a>
  <div class="card">
    <h2>Weekly Summary</h2>
    {weekly_html}
  </div>

  <a id="stats" class="anchor"></a>
  <div class="card">
    <h2>Stats</h2>
    {stats_html}
  </div>

  <p class="note">Updated {updated_str}</p>
</div>
</body></html>"""

def run():
    os.makedirs(ASSETS, exist_ok=True)
    archive = load_json(ARCHIVE) or {}
    summary = load_json(SUMMARY) or {}

    # 7-day aggregation
    kw_pairs, br_pairs, heads = aggregate_week(archive) if archive else ([], [], [])
    if not (kw_pairs and br_pairs):
        # fallback to today so charts still render
        rk = summary.get("keywords", []) or []
        if rk:
            if isinstance(rk[0], dict): kw_pairs = [(k["term"], int(k.get("count", 0))) for k in rk]
            else: kw_pairs = [(x, 1) for x in rk]
        rb = summary.get("brands", []) or []
        if rb: br_pairs = [(b["name"], int(b.get("count", 0))) for b in rb]
        if not heads: heads = summary.get("highlights", []) or []

    # Charts (always write image files so <img> never 404s)
    if kw_pairs:
        labels = [p[0] for p in kw_pairs[:18]]
        values = [p[1] for p in kw_pairs[:18]]
        save_barh(list(reversed(labels)), list(reversed(values)),
                  "Retail Trend Keywords (7-day totals)", KW_IMG, PALETTE_KW, "Mentions (7-day total)")
        kw_top = kw_pairs[0]
    else:
        ensure_dir_for_file(KW_IMG); open(KW_IMG, "wb").close(); kw_top = None

    if br_pairs:
        labels = [p[0] for p in br_pairs[:12]]
        values = [p[1] for p in br_pairs[:12]]
        save_barh(labels, values, "Retail Brand Mentions (7-day totals)", BR_IMG, PALETTE_BR, "Mentions (7-day total)")
        br_top = br_pairs[0]
    else:
        ensure_dir_for_file(BR_IMG); open(BR_IMG, "wb").close(); br_top = None

    # Headlines list + exports
    head_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title')}</a> "
        f"<span class='note'>({h.get('source','')})</span></li>"
        for h in (heads or [])
    ) or "<li class='note'>No headlines yet.</li>"
    write_headlines_exports(heads or [])

    # KPIs
    kpis = []
    if kw_top: kpis.append(f"<span class='kpi'><b>{kw_top[1]}</b> “{kw_top[0]}”</span>")
    if br_top: kpis.append(f"<span class='kpi'><b>{br_top[1]}</b> {br_top[0]}</span>")
    kpi_html = f"<div class='kpis'>{''.join(kpis)}</div>" if kpis else ""

    # Weekly Summary section (compact lists)
    wk_kw = "".join(f"<li>{k} — <b>{v}</b></li>" for k,v in kw_pairs[:15]) or "<li class='note'>No keywords yet.</li>"
    wk_br = "".join(f"<li>{b} — <b>{v}</b></li>" for b,v in br_pairs[:12]) or "<li class='note'>No brands yet.</li>"
    weekly_html = f"<div class='grid'><div><ul>{wk_kw}</ul></div><div><ul>{wk_br}</ul></div></div>"

    # Stats section
    # Today's
    today_date = summary.get("stats", {}).get("date", "—")
    today_items = int(summary.get("stats", {}).get("items_considered", 0))
    today_sources = int(summary.get("stats", {}).get("unique_sources", 0))

    # 7-day totals
    w_items = w_kw = w_br = 0
    if isinstance(archive, dict) and archive:
        dates = sorted(archive.keys(), reverse=True)[:7]
        for d in dates:
            day = archive[d]
            w_items += int(day.get("stats", {}).get("items_considered", 0))
            for k in day.get("keywords", []) or []:
                w_kw += int(k.get("count", 1)) if isinstance(k, dict) else 1
            for b in day.get("brands", []) or []:
                w_br += int(b.get("count", 0)) if isinstance(b, dict) else 0

    stats_html = f"""
<div class="grid">
  <div class="card"><div>Today’s Articles</div><b style="font-size:20px">{today_items}</b><div class="note">Date: {today_date}</div></div>
  <div class="card"><div>Today’s Sources</div><b style="font-size:20px">{today_sources}</b></div>
  <div class="card"><div>7-Day Articles</div><b style="font-size:20px">{w_items}</b></div>
  <div class="card"><div>7-Day Keyword Mentions</div><b style="font-size:20px">{w_kw}</b></div>
  <div class="card"><div>7-Day Brand Mentions</div><b style="font-size:20px">{w_br}</b></div>
</div>"""

    html = build_html(head_html, "assets/keywords.png", "assets/brands.png",
                      head_html, kpi_html, weekly_html, stats_html,
                      datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'))

    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote single-page site/index.html (no 404s)")

if __name__ == "__main__":
    run()
