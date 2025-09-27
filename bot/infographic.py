# bot/infographic.py
# Builds site/index.html with 7-day totals (keywords & brands) + visitor counter.
# Robust to missing config.yml; uses defaults.

import os, json, csv
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # headless for CI
import matplotlib.pyplot as plt
from matplotlib import ticker

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
ARCHIVE = os.path.join(DATA_DIR, "daily_summaries.json")
SUMMARY = os.path.join(DATA_DIR, "summary.json")
SITE_DIR = os.path.join(ROOT, "site")
ASSETS_DIR = os.path.join(SITE_DIR, "assets")

# Safe defaults if config.yml is missing
DEFAULT_TITLE = "Retail Trends Dashboard"
DEFAULT_DESC  = "Daily updated retail trend insights."
KEYWORDS_IMG  = os.path.join(ROOT, "site", "assets", "keywords.png")
BRANDS_IMG    = os.path.join(ROOT, "site", "assets", "brands.png")

plt.rcParams.update({
    "figure.facecolor": "#ffffff",
    "axes.facecolor":   "#ffffff",
    "axes.edgecolor":   "#cccccc",
    "axes.labelcolor":  "#111111",
    "axes.titlecolor":  "#111111",
    "xtick.color":      "#111111",
    "ytick.color":      "#111111",
    "font.size":        10,
})

PALETTE_KEYWORDS = ["#2E93fA","#66DA26","#E91E63","#FF9800","#00E396","#775DD0",
                    "#008FFB","#FEB019","#FF4560","#00D9E9","#A300D6","#F86624",
                    "#D10CE8","#4CAF50","#9C27B0"]
PALETTE_BRANDS = ["#7B61FF","#FF6B6B","#00C49A","#FFB703","#219EBC","#8338EC",
                  "#FB5607","#06D6A0","#118AB2","#EF476F","#3A86FF","#FFBE0B"]

def ensure_dir_for_file(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def pick_colors(n, pal):
    return (pal * ((n + len(pal) - 1)//len(pal)))[:n]

def style_axes(ax):
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    for s in ("left","bottom"): ax.spines[s].set_color("#e0e0e0")
    ax.grid(axis="x", color="#eeeeee", linewidth=0.9, zorder=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))

def save_barh(labels, values, title, outpath, palette, xlabel):
    ensure_dir_for_file(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8,6), dpi=150)
    style_axes(ax); ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel(xlabel)
    y = range(len(labels)); colors = pick_colors(len(labels), palette)
    ax.barh(y, values, color=colors, edgecolor="#fff")
    ax.set_yticks(list(y)); ax.set_yticklabels(labels)
    mx = max(values) if values else 0; offs = mx*0.02 if mx>0 else 0.5
    for i,v in enumerate(values): ax.text(v+offs, i, str(v), va="center", ha="left", color="#111111")
    fig.tight_layout(); fig.savefig(outpath, bbox_inches="tight"); plt.close(fig)

def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    jp = os.path.join(assets_dir, "headlines.json"); cp = os.path.join(assets_dir, "headlines.csv")
    with open(jp, "w", encoding="utf-8") as jf: json.dump(highlights, jf, indent=2)
    with open(cp, "w", encoding="utf-8", newline="") as cf:
        w = csv.DictWriter(cf, fieldnames=["title","link","source","published"])
        w.writeheader(); [w.writerow(h) for h in highlights]
    return os.path.basename(cp), os.path.basename(jp)

INLINE_CSS = """<style>
:root{--stroke:#e5e7eb;--btn:#f8fafc;--primary:#7b61ff}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;margin:0}
.hero{position:relative;min-height:240px;background:
  linear-gradient(180deg, rgba(10,14,25,.60), rgba(10,14,25,.60)),
  url('assets/bg.jpg') center/cover no-repeat;}
.hero::after{
  content:"";position:absolute;inset:0;pointer-events:none;opacity:.28;
  background-image:url("data:image/svg;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncA type='table' tableValues='0 0.6'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  background-size:160px 160px;
}
.hero .wrap{max-width:1100px;margin:0 auto;padding:28px 18px;position:relative;z-index:1}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.header-actions a,.header-actions button{display:inline-block;margin-right:8px;padding:8px 12px;border-radius:12px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}
.header-actions .primary{background:var(--primary);color:#fff;border:none}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 10px 0;font-size:18px}
.note{color:#6b7280;font-size:14px}
img{max-width:100%;border-radius:8px}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:#f3f4f6;color:#111;border:1px solid var(--stroke)}
.kpi b{font-weight:700}
#visitor-count{font-size:14px;color:#fff;margin-top:8px}
.badge{display:inline-block;margin-left:10px;vertical-align:middle}
</style>"""

def build_index(title, description, keywords_img, brands_img, highlights,
                has_keywords, has_brands, kw_top, br_top):
    kw_block = (f"<img src='assets/{os.path.basename(keywords_img)}' alt='Top Keywords (7-day)'>"
                if has_keywords else "<p class='note'>No keywords yet.</p>")
    br_block = (f"<img src='assets/{os.path.basename(brands_img)}' alt='Brand Mentions (7-day)'>"
                if has_brands else "<p class='note'>No brand mentions yet.</p>")
    headlines_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title')}</a> "
        f"<span class='note'>({h.get('source','')})</span></li>"
        for h in highlights
    ) or "<li class='note'>No headlines yet.</li>"
    kpis = []
    if kw_top: kpis.append(f"<span class='kpi'><b>{kw_top[1]}</b> “{kw_top[0]}”</span>")
    if br_top: kpis.append(f"<span class='kpi'><b>{br_top[1]}</b> {br_top[0]}</span>")
    kpi_html = f"<div class='kpis'>{''.join(kpis)}</div>" if kpis else ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>{INLINE_CSS}</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>{title}</h1>
    <p>{description}</p>
    <div class="header-actions" style="margin-top:10px">
      <a href="weekly.html">Weekly Summary</a>
      <a href="news.html">News Sites</a>
      <a href="stats.html">Stats</a>
      <button class="primary" onclick="location.reload()">Refresh</button>
    </div>
    {kpi_html}
    <div id="visitor-count">Visitors: loading… 
      <img class="badge" alt="Visitors badge" src="https://hits.seeyoufarm.com/api/count/incr/badge.svg?url=https://architeketh.github.io/retail-trends-bot/&title=Visitors">
    </div>
    <script>
      (function(){{
        // Increment + get total page views using countapi.xyz
        fetch('https://api.countapi.xyz/hit/architeketh/retail-trends')
          .then(function(res){{return res.json();}})
          .then(function(data){{document.getElementById('visitor-count').firstChild.nodeValue='Visitors: '+data.value+' ';}})
          .catch(function(_){{/* keep badge fallback */}});
      }})();
    </script>
  </div>
</div>
<div class="wrap">
  <div class="card"><h2>Top Keywords (7-day totals)</h2>{kw_block}</div>
  <div class="card"><h2>Brand Mentions (7-day totals)</h2>{br_block}</div>
  <div class="card"><h2>Headlines</h2><ul>{headlines_html}</ul></div>
  <p class="note">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
</body></html>"""

def load_archive():
    if os.path.exists(ARCHIVE):
        try:
            with open(ARCHIVE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict): return data
        except Exception: pass
    return {}

def aggregate_week(archive: dict):
    dates = sorted(archive.keys(), reverse=True)[:7]
    kw = {}; br = {}; latest = None; highlights = []
    for i, d in enumerate(dates):
        day = archive[d]
        if i == 0: latest = day  # newest day for headlines
        for k in day.get("keywords", []):
            if isinstance(k, dict):
                term = k.get("term"); c = int(k.get("count", 0))
            else:
                term, c = k, 1
            if term: kw[term] = kw.get(term, 0) + c
        for b in day.get("brands", []):
            name = b.get("name"); c = int(b.get("count", 0))
            if name: br[name] = br.get(name, 0) + c
    kw_top_pairs = sorted(kw.items(), key=lambda x: (-x[1], -len(x[0].split()), x[0]))
    br_top_pairs = sorted(br.items(), key=lambda x: (-x[1], x[0]))
    if latest: highlights = latest.get("highlights", [])
    return kw_top_pairs, br_top_pairs, highlights

def run():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    # Prefer 7-day archive; fallback to today's summary if needed
    archive = load_archive()
    kw_pairs, br_pairs, highlights = aggregate_week(archive) if archive else ([], [], [])
    if not (kw_pairs and br_pairs) and os.path.exists(SUMMARY):
        with open(SUMMARY, "r", encoding="utf-8") as f:
            today = json.load(f)
        highlights = today.get("highlights", []) or highlights
        rk = today.get("keywords", [])
        if rk:
            if isinstance(rk[0], dict): kw_pairs = [(k["term"], int(k.get("count", 0))) for k in rk]
            else: kw_pairs = list(zip(list(reversed(rk)), list(range(len(rk), 0, -1))))
        rb = today.get("brands", [])
        if rb: br_pairs = [(b["name"], int(b.get("count", 0))) for b in rb]

    # Charts (always create image files, even empty)
    if kw_pairs:
        labels = [p[0] for p in kw_pairs[:18]]
        values = [p[1] for p in kw_pairs[:18]]
        save_barh(list(reversed(labels)), list(reversed(values)),
                  "Retail Trend Keywords (7-day totals)", KEYWORDS_IMG, PALETTE_KEYWORDS,
                  xlabel="Mentions (7-day total)")
        kw_top = kw_pairs[0]; has_keywords = True
    else:
        ensure_dir_for_file(KEYWORDS_IMG); open(KEYWORDS_IMG, "wb").close()
        kw_top = None; has_keywords = False

    if br_pairs:
        labels = [p[0] for p in br_pairs[:12]]
        values = [p[1] for p in br_pairs[:12]]
        save_barh(labels, values, "Retail Brand Mentions (7-day totals)", BRANDS_IMG, PALETTE_BRANDS,
                  xlabel="Mentions (7-day total)")
        br_top = br_pairs[0]; has_brands = True
    else:
        ensure_dir_for_file(BRANDS_IMG); open(BRANDS_IMG, "wb").close()
        br_top = None; has_brands = False

    # Export headlines (from newest day we have)
    write_headlines_exports(ASSETS_DIR, highlights or [])

    html = build_index(
        DEFAULT_TITLE, DEFAULT_DESC,
        KEYWORDS_IMG, BRANDS_IMG, highlights or [],
        has_keywords, has_brands, kw_top, br_top
    )
    out_path = os.path.join(SITE_DIR, "index.html")
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/index.html (7-day totals + visitor counter)")

if __name__ == "__main__":
    run()
