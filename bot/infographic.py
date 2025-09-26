# bot/infographic.py
# Modern hero with noise overlay + rounded KPI chips + keyword/brand charts.

import os, json, csv
from datetime import datetime
from collections import Counter

import yaml
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir_for_file(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# Matplotlib theme
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

def pick_colors(n, palette):
    reps = (n + len(palette) - 1) // len(palette)
    return (palette * reps)[:n]

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left","bottom"):
        ax.spines[s].set_color("#e0e0e0")
    ax.grid(axis="x", color="#eeeeee", linewidth=0.9, zorder=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
    ax.set_xlabel("Mentions")

def save_barh(labels, values, title, outpath, palette):
    ensure_dir_for_file(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8,6), dpi=150)
    style_axes(ax)
    ax.set_title(title, fontsize=12, fontweight="bold")
    y = range(len(labels))
    colors = pick_colors(len(labels), palette)
    ax.barh(y, values, color=colors, edgecolor="#fff")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    mx = max(values) if values else 0
    offs = (mx * 0.02) if mx > 0 else 0.5
    for i, v in enumerate(values):
        ax.text(v + offs, i, str(v), va="center", ha="left", color="#111111")
    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)

def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    # JSON
    json_path = os.path.join(assets_dir, "headlines.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(highlights, jf, indent=2)
    # CSV
    csv_path = os.path.join(assets_dir, "headlines.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as cf:
        w = csv.DictWriter(cf, fieldnames=["title","link","source","published"])
        w.writeheader()
        for h in highlights: w.writerow(h)
    return os.path.basename(csv_path), os.path.basename(json_path)

def sources_list_html(highlights, stats):
    counts = Counter([h.get("source","") for h in highlights if h.get("source")])
    lis = [f"<li>{s} ({n})</li>" for s,n in counts.items()] or ["<li>—</li>"]
    return f"<details><summary><b>Sources</b></summary><ul>{''.join(lis)}</ul></details>"

INLINE_CSS = """<style>
:root{--stroke:#e5e7eb;--btn:#f8fafc;--primary:#7b61ff;--chip:#111;--chipbg:#f3f4f6}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;margin:0}
.hero{position:relative;min-height:240px;background:
  linear-gradient(180deg, rgba(10,14,25,.60), rgba(10,14,25,.60)),
  url('assets/bg.jpg') center/cover no-repeat;}
.hero::after{ /* subtle noise overlay */
  content:"";position:absolute;inset:0;pointer-events:none;opacity:.28;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncA type='table' tableValues='0 0.6'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  background-size:160px 160px;
}
.hero .wrap{max-width:1100px;margin:0 auto;padding:28px 18px;width:100%;position:relative;z-index:1}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.header-actions a,.header-actions button{display:inline-block;margin-right:8px;padding:8px 12px;border-radius:12px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}
.header-actions .primary{background:var(--primary);color:#fff;border:none}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:var(--chipbg);color:var(--chip);border:1px solid var(--stroke)}
.kpi b{font-weight:700}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 10px 0;font-size:18px}
.note{color:#6b7280;font-size:14px}
img{max-width:100%;border-radius:8px}
</style>"""

def kpi_chips_html(stats, top_keyword, top_brand):
    chips = []
    if stats.get("items_considered"):
        chips.append(f"<span class='kpi'><b>{stats['items_considered']}</b> Articles</span>")
    if stats.get("unique_sources"):
        chips.append(f"<span class='kpi'><b>{stats['unique_sources']}</b> Sources</span>")
    if top_keyword:
        term, count = top_keyword
        chips.append(f"<span class='kpi'><b>{count}</b> “{term}”</span>")
    if top_brand:
        name, count = top_brand
        chips.append(f"<span class='kpi'><b>{count}</b> {name}</span>")
    return f"<div class='kpis'>{''.join(chips)}</div>" if chips else ""

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name,
                has_keywords, has_brands, top_keyword, top_brand):
    kw_block = (f"<img src='assets/{os.path.basename(keywords_img)}' alt='Top Keywords'>"
                if has_keywords else "<p class='note'>No keywords yet. This will populate after the next successful run.</p>")
    br_block = (f"<img src='assets/{os.path.basename(brands_img)}' alt='Brand Mentions'>"
                if has_brands else "<p class='note'>No brand mentions yet. This will populate after the next successful run.</p>")
    headlines_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title')}</a> "
        f"<span class='note'>({h.get('source','')})</span></li>"
        for h in highlights
    ) or "<li class='note'>No headlines yet.</li>"

    kpis = kpi_chips_html(stats, top_keyword, top_brand)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>{INLINE_CSS}</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>{title}</h1>
    <p>{description}</p>
    <div class="header-actions" style="margin-top:10px">
      <a href="assets/{csv_name}" download>CSV</a>
      <a href="assets/{json_name}" download>JSON</a>
      <a href="weekly.html">Weekly Summary</a>
      <a href="news.html">News Sites</a>
      <a href="stats.html">Stats</a>
      <button class="primary" onclick="location.reload()">Refresh</button>
    </div>
    {kpis}
  </div>
</div>

<div class="wrap">
  <div class="card"><h2>Top Keywords (by mentions)</h2>{kw_block}</div>
  <div class="card"><h2>Brand Mentions</h2>{br_block}</div>
  <div class="card"><h2>Headlines</h2><ul>{headlines_html}</ul></div>
  {sources_list_html(highlights, stats)}
  <p class="note">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
</body></html>"""

def run():
    cfg = load_config()
    site_dir = os.path.join(ROOT, "site"); assets_dir = os.path.join(site_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Load summary
    summary_path = os.path.join(DATA_DIR, "summary.json")
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

    highlights = summary.get("highlights", []) or []
    stats = summary.get("stats", {}) or {}

    # Keywords (supports new schema with counts)
    raw_keywords = summary.get("keywords", []) or []
    if raw_keywords and isinstance(raw_keywords[0], dict) and "term" in raw_keywords[0]:
        kw_labels = [k["term"] for k in raw_keywords]
        kw_values = [int(k.get("count", 0)) for k in raw_keywords]
        top_keyword = (kw_labels[0], kw_values[0]) if kw_labels else None
    else:
        kw_labels = list(reversed(raw_keywords))
        kw_values = list(range(len(raw_keywords), 0, -1))
        top_keyword = (kw_labels[-1], kw_values[-1]) if kw_labels else None  # fallback

    # Brands
    brands = summary.get("brands", []) or []
    br_labels = [b["name"] for b in brands]
    br_values = [int(b.get("count", 0)) for b in brands]
    top_brand = (br_labels[0], br_values[0]) if br_labels else None

    # Output image paths
    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    # Generate charts
    has_keywords = bool(kw_labels)
    has_brands = bool(br_labels)

    if has_keywords:
        # Highest at bottom for barh
        save_barh(list(reversed(kw_labels)), list(reversed(kw_values)),
                  "Retail Trend Keywords (Mentions)", keywords_img, PALETTE_KEYWORDS)
    else:
        ensure_dir_for_file(keywords_img); open(keywords_img, "wb").close()

    if has_brands:
        save_barh(br_labels, br_values, "Retail Brand Mentions", brands_img, PALETTE_BRANDS)
    else:
        ensure_dir_for_file(brands_img); open(brands_img, "wb").close()

    # CSV/JSON exports
    csv_name, json_name = write_headlines_exports(assets_dir, highlights)

    # Build index.html
    index_html = build_index(
        cfg["website"]["title"], cfg["website"]["description"],
        keywords_img, brands_img, highlights, stats,
        csv_name, json_name, has_keywords, has_brands,
        top_keyword, top_brand
    )
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Wrote site/index.html")

if __name__ == "__main__":
    run()
