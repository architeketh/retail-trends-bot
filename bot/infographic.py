# bot/infographic.py
# White background, black text, per-bar colors, inline CSS.

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

# ---------- Chart style (white theme) ----------
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

PALETTE_KEYWORDS = ["#2E93fA","#66DA26","#E91E63","#FF9800",
                    "#00E396","#775DD0","#008FFB","#FEB019",
                    "#FF4560","#00D9E9","#A300D6","#F86624",
                    "#D10CE8","#4CAF50","#9C27B0"]
PALETTE_BRANDS = ["#7B61FF","#FF6B6B","#00C49A","#FFB703",
                  "#219EBC","#8338EC","#FB5607","#06D6A0",
                  "#118AB2","#EF476F","#3A86FF","#FFBE0B"]

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
    ax.set_xlabel("Relative Importance")

def save_barh(labels, values, title, outpath, palette):
    ensure_dir(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8,6), dpi=150)
    style_axes(ax)
    ax.set_title(title, fontsize=12, fontweight="bold")
    y = range(len(labels))
    colors = pick_colors(len(labels), palette)
    ax.barh(y, values, color=colors, edgecolor="#fff")
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    for i,v in enumerate(values):
        ax.text(v + 0.5, i, str(v), va="center", ha="left", color="#111111")
    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)

def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    json_path = os.path.join(assets_dir,"headlines.json")
    with open(json_path,"w",encoding="utf-8") as jf:
        json.dump(highlights,jf,indent=2)
    csv_path = os.path.join(assets_dir,"headlines.csv")
    with open(csv_path,"w",encoding="utf-8",newline="") as cf:
        w = csv.DictWriter(cf,fieldnames=["title","link","source","published"])
        w.writeheader()
        for h in highlights: w.writerow(h)
    return os.path.basename(csv_path), os.path.basename(json_path)

def sources_list_html(highlights, stats):
    counts = Counter([h.get("source","") for h in highlights if h.get("source")])
    lis = [f"<li>{s} ({n})</li>" for s,n in counts.items()]
    return f"<details><summary><b>Sources</b></summary><ul>{''.join(lis)}</ul></details>"

INLINE_CSS = """<style>
body{font-family:system-ui;background:#fff;color:#111;padding:2rem;max-width:1100px;margin:auto}
.header{display:flex;justify-content:space-between;align-items:center}
h1{margin:0}
.badge{background:#eef6ff;color:#111;font-size:12px;padding:4px 8px;border-radius:8px;margin-right:4px}
.btn{background:#f8fafc;padding:6px 10px;border:1px solid #ccc;border-radius:8px;text-decoration:none;color:#111;margin-left:4px}
.btn.primary{background:#2E93fA;color:#fff}
.card{border:1px solid #eee;border-radius:8px;padding:1rem;margin-top:1rem}
</style>"""

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name):
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>{INLINE_CSS}</head>
<body>
<div class="header">
 <div><h1>{title}</h1><p>{description}</p></div>
 <div>
  <a class="btn" href="assets/{csv_name}" download>CSV</a>
  <a class="btn" href="assets/{json_name}" download>JSON</a>
 </div>
</div>
<div class="card"><h2>Top Keywords</h2><img src="assets/{os.path.basename(keywords_img)}"></div>
<div class="card"><h2>Brand Mentions</h2><img src="assets/{os.path.basename(brands_img)}"></div>
<div class="card"><h2>Headlines</h2><ul>
{''.join(f"<li><a href='{h['link']}' target='_blank'>{h['title']}</a> ({h['source']})</li>" for h in highlights)}
</ul></div>
{sources_list_html(highlights, stats)}
<p>Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""

def run():
    cfg = load_config()
    with open(os.path.join(DATA_DIR,"summary.json"),"r",encoding="utf-8") as f:
        summary = json.load(f)

    keywords = summary.get("keywords",[])
    brands = summary.get("brands",[])
    highlights = summary.get("highlights",[])
    stats = summary.get("stats",{})

    keywords_img = os.path.join(ROOT,cfg["infographic"]["output_image"])
    brands_img = os.path.join(ROOT,cfg["infographic"]["brands_image"])

    if keywords:
        save_barh(list(reversed(keywords)), list(range(len(keywords),0,-1)),
                  "Retail Trend Keywords", keywords_img, PALETTE_KEYWORDS)
    if brands:
        save_barh([b["name"] for b in brands],[b["count"] for b in brands],
                  "Retail Brand Mentions", brands_img, PALETTE_BRANDS)

    site_dir = os.path.join(ROOT,"site"); assets_dir = os.path.join(site_dir,"assets")
    os.makedirs(assets_dir,exist_ok=True)
    csv_name,json_name = write_headlines_exports(assets_dir, highlights)

    index_html = build_index(cfg["website"]["title"], cfg["website"]["description"],
                             keywords_img, brands_img, highlights, stats,
                             csv_name, json_name)
    with open(os.path.join(site_dir,"index.html"),"w",encoding="utf-8") as f:
        f.write(index_html)

if __name__ == "__main__":
    run()
