# bot/infographic.py
# Modern charts (distinct colors per bar) + inline CSS + CSV/JSON exports + Sources drawer.

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

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# ---------- Chart Styling ----------
plt.rcParams.update({
    "figure.facecolor": "#0f1218",
    "axes.facecolor":   "#0f1218",
    "axes.edgecolor":   "#2b3242",
    "axes.labelcolor":  "#cfe5ff",
    "axes.titlecolor":  "#e7ebf3",
    "xtick.color":      "#dfe7ff",
    "ytick.color":      "#dfe7ff",
    "font.size":        10,
})

PALETTE_KEYWORDS = [
    "#7BDFF2","#B2F7EF","#F7D6E0","#F2B5D4","#B39DDB",
    "#80CBC4","#FFD54F","#FFAB91","#90CAF9","#A5D6A7",
    "#F48FB1","#CE93D8","#FFCC80","#81D4FA","#EF9A9A",
    "#C5E1A5","#E6EE9C","#9FA8DA","#26C6DA","#FF8A65"
]
PALETTE_BRANDS = [
    "#6CC0FF","#A18CFF","#FF8EC7","#FFC46C","#7BE495",
    "#FFD166","#06D6A0","#EF476F","#8892F6","#42C2FF",
    "#F0A6CA","#9CDAF1","#6EE7B7","#FCD34D","#F472B6",
    "#B39DDB","#90CAF9","#A5D6A7","#FFCC80","#EF9A9A"
]

def pick_colors(n, palette):
    if n <= len(palette):
        return palette[:n]
    reps = (n + len(palette) - 1) // len(palette)
    return (palette * reps)[:n]

def style_axes(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left","bottom"):
        ax.spines[s].set_color("#2b3242")
        ax.spines[s].set_linewidth(1)
    ax.grid(axis="x", color="#2b3242", linewidth=0.8, alpha=0.5, zorder=0)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
    ax.set_xlabel("Relative Importance", labelpad=8)

def save_barh_modern(labels, values, title, outpath, palette):
    ensure_dir(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8.6, 6.2), dpi=170)

    style_axes(ax)
    ax.set_title(title, pad=10, fontsize=12, fontweight="bold")

    y = list(range(len(labels)))
    colors = pick_colors(len(labels), palette)
    bars = ax.barh(y, values, color=colors, edgecolor="none", zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)

    for bar, val in zip(bars, values):
        ax.text(val + (max(values) * 0.02 if values else 0.2), bar.get_y() + bar.get_height()/2,
                f"{val}", va="center", ha="left", color="#cfe5ff", fontsize=9)

    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

# ---------- Data helpers ----------
def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    json_path = os.path.join(assets_dir, "headlines.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(highlights, jf, indent=2, ensure_ascii=False)
    csv_path = os.path.join(assets_dir, "headlines.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=["title","link","source","published"])
        writer.writeheader()
        for h in highlights:
            writer.writerow(h)
    return os.path.basename(csv_path), os.path.basename(json_path)

def sources_list_html(highlights, stats):
    counts = Counter([h.get("source","").strip() for h in highlights if h.get("source")])
    unique_sources = (stats or {}).get("sources") or sorted(s for s in counts if s)
    lis = []
    if counts:
        for src, n in sorted(counts.items(), key=lambda kv:(-kv[1], kv[0])):
            if src: lis.append(f"<li><span class='src-name'>{src}</span> <span class='src-count'>({n})</span></li>")
    else:
        for src in unique_sources:
            if src: lis.append(f"<li><span class='src-name'>{src}</span></li>")
    total = len(unique_sources) if unique_sources else len(counts)
    return f"""
    <details class="card" style="margin-top:18px">
      <summary style="cursor:pointer"><strong>Sources</strong> (today: {total})</summary>
      <ul class="list" style="margin-top:10px">
        {''.join(lis) if lis else '<li><em>No sources detected.</em></li>'}
      </ul>
    </details>
    """

# ---------- Build HTML with inline CSS ----------
INLINE_CSS = """<style>
:root{
  --bg:#0b0c10; --panel:#111319; --text:#e7ebf3;
  --muted:#a4aec2; --stroke:#1b1e28; --accent:#6cc0ff; --accent2:#a18cff;
}
body{margin:0;padding:0;font-family:system-ui;background:linear-gradient(180deg,#0b0c10 0%,#0a0c12 100%);color:var(--text)}
.container{max-width:1200px;margin:0 auto;padding:32px 20px}
.header{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:24px}
.brand h1{margin:0;font-size:30px;background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;color:transparent}
.brand p{margin:6px 0 0;color:var(--muted);font-size:14px}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
.badge{font-size:12px;color:#cfe5ff;background:rgba(108,192,255,.10);border:1px solid rgba(108,192,255,.35);padding:6px 10px;border-radius:999px}
.actions{display:flex;gap:10px}
.btn{border:1px solid var(--stroke);background:#0f1218;color:var(--text);padding:10px 14px;border-radius:12px;font-size:14px;cursor:pointer;transition:.2s}
.btn:hover{transform:translateY(-1px);border-color:#2b3242}
.btn.primary{background:linear-gradient(95deg,#2c4cff,#4bc2ff);color:white;border:none}
.grid{display:grid;gap:18px;margin-top:8px}
@media(min-width:1100px){.grid{grid-template-columns:1fr 1fr}}
.card{background:rgba(17,19,25,.9);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:18px;backdrop-filter:blur(8px)}
.card h2{font-size:18px;margin:4px 0 12px}
.card img{width:100%;border-radius:10px;background:#0c0f14}
.list{margin:0;padding-left:18px}
.list li{margin:8px 0}
.list a{color:#d8e7ff;text-decoration:none;border-bottom:1px dashed rgba(108,192,255,.35)}
.list a:hover{color:white;border-bottom:none}
.src{color:var(--muted);font-size:12px;margin-left:6px}
.footer{margin-top:22px;color:var(--muted);font-size:12px;text-align:center}
</style>"""

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>{INLINE_CSS}
</head>
<body>
<div class="container">
<header class="header">
  <div class="brand">
    <h1>{title}</h1>
    <p>{description}</p>
    <div class="badges">
      <span class="badge">Auto-updated daily</span>
      <span class="badge">NRF · Retail Dive · Shopify · Supply Chain 24/7 · + More</span>
    </div>
  </div>
  <div class="actions">
    <a class="btn" href="assets/{os.path.basename(keywords_img)}" download>Download Keywords PNG</a>
    <a class="btn" href="assets/{os.path.basename(brands_img)}" download>Download Brands PNG</a>
    <a class="btn" href="assets/{csv_name}" download>Download Headlines CSV</a>
    <a class="btn" href="assets/{json_name}" download>Download Headlines JSON</a>
    <button class="btn primary" onclick="location.reload()">Refresh</button>
  </div>
</header>

<section class="grid">
  <article class="card"><h2>Top Keywords</h2><img src="assets/{os.path.basename(keywords_img)}"></article>
  <article class="card"><h2>Brand Mentions</h2><img src="assets/{os.path.basename(brands_img)}"></article>
</section>

<section class="card" style="margin-top:18px">
  <h2>Headlines</h2>
  <ul class="list">
    {''.join(f"<li><a href='{h.get('link','#')}' target='_blank'>{h.get('title','')}</a><span class='src'>({h.get('source','')})</span></li>" for h in highlights)}
  </ul>
</section>

{sources_list_html(highlights, stats)}

<p class="footer">Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div></body></html>"""

# ---------- Main ----------
def run():
    cfg = load_config()
    with open(os.path.join(DATA_DIR, "summary.json"), "r", encoding="utf-8") as f:
        summary = json.load(f)

    keywords = summary.get("keywords", [])
    brands   = summary.get("brands", [])
    stats    = summary.get("stats", {})
    highlights = summary.get("highlights", [])

    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img   = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    if keywords:
        labels_kw = list(reversed(keywords))
        vals_kw   = list(range(len(keywords), 0, -1))
        save_barh_modern(labels_kw, vals_kw, "Retail Trend Keywords", keywords_img, PALETTE_KEYWORDS)
    else:
        ensure_dir(keywords_img); open(keywords_img,"wb").close()

    if brands:
        labels_b = [b["name"] for b in brands]
        vals_b   = [b["count"] for b in brands]
        save_barh_modern(list(reversed(labels_b)), list(reversed(vals_b)),
                         "Retail Brand Mentions", brands_img, PALETTE_BRANDS)
    else:
        ensure_dir(brands_img); open(brands_img,"wb").close()

    site_dir = os.path.join(ROOT,"site")
    assets_dir = os.path.join(site_dir,"assets")
    os.makedirs(assets_dir, exist_ok=True)
    csv_name,json_name = write_headlines_exports(assets_dir, highlights)

    index_html = build_index(cfg["website"]["title"], cfg["website"]["description"],
                             keywords_img, brands_img, highlights, stats,
                             csv_name, json_name)
    with open(os.path.join(site_dir,"index.html"),"w",encoding="utf-8") as f:
        f.write(index_html)
    print("Wrote site/index.html with inline CSS + modern colorful charts")

if __name__ == "__main__":
    run()
