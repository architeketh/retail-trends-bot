# bot/infographic.py
# Draw keyword/brand charts using ACTUAL COUNTS for keywords (fallback compatible).

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

# ---------- Chart style ----------
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
    for i, v in enumerate(values):
        ax.text(v + (max(values)*0.02 if max(values)>0 else 0.5), i, str(v), va="center", ha="left", color="#111111")
    fig.tight_layout()
    fig.savefig(outpath, bbox_inches="tight")
    plt.close(fig)

def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)
    json_path = os.path.join(assets_dir, "headlines.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(highlights, jf, indent=2)
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
body{font-family:system-ui;background:#fff;color:#111;padding:2rem;max-width:1100px;margin:auto}
.header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
h1{margin:0}
.btn{background:#f8fafc;padding:8px 12px;border:1px solid #ccc;border-radius:10px;text-decoration:none;color:#111;margin-left:6px;display:inline-block}
.btn.primary{background:#2E93fA;color:#fff;border:none}
.card{border:1px solid #eee;border-radius:10px;padding:1rem;margin-top:1rem}
.note{color:#666;font-size:14px}
</style>"""

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name,
                has_keywords, has_brands):
    kw_block = (f"<img src='assets/{os.path.basename(keywords_img)}' alt='Top Keywords'>"
                if has_keywords else "<p class='note'>No keywords yet. This will populate after the next successful run.</p>")
    br_block = (f"<img src='assets/{os.path.basename(brands_img)}' alt='Brand Mentions'>"
                if has_brands else "<p class='note'>No brand mentions yet. This will populate after the next successful run.</p>")

    headlines_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title')}</a> ({h.get('source','')})</li>"
        for h in highlights
    ) or "<li class='note'>No headlines yet.</li>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>{INLINE_CSS}</head>
<body>
<div class="header">
  <div><h1>{title}</h1><p>{description}</p></div>
  <div>
    <a class="btn" href="assets/{csv_name}" download>CSV</a>
    <a class="btn" href="assets/{json_name}" download>JSON</a>
    <a class="btn" href="news.html">News Sites</a>
    <a class="btn" href="stats.html">Stats</a>
    <button class="btn primary" onclick="location.reload()">Refresh</button>
  </div>
</div>

<div class="card"><h2>Top Keywords (by mentions)</h2>{kw_block}</div>
<div class="card"><h2>Brand Mentions</h2>{br_block}</div>

<div class="card"><h2>Headlines</h2><ul>
{headlines_html}
</ul></div>

{sources_list_html(highlights, stats)}
<p class="note">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""

def run():
    cfg = load_config()
    site_dir = os.path.join(ROOT, "site")
    assets_dir = os.path.join(site_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Load summary
    summary_path = os.path.join(DATA_DIR, "summary.json")
    summary = {}
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

    highlights = summary.get("highlights", []) or []
    stats = summary.get("stats", {}) or {}

    # ---- KEYWORDS: support new (objects w/ counts) and old (string list) formats
    raw_keywords = summary.get("keywords", []) or []
    kw_labels, kw_values = [], []
    if raw_keywords and isinstance(raw_keywords[0], dict) and "term" in raw_keywords[0]:
        # New format
        kw_labels = [k["term"] for k in raw_keywords]
        kw_values = [int(k.get("count", 0)) for k in raw_keywords]
    else:
        # Old format fallback: treat as rank (highest to lowest)
        kw_labels = list(reversed(raw_keywords))
        kw_values = list(range(len(raw_keywords), 0, -1))

    # ---- BRANDS
    brands = summary.get("brands", []) or []
    br_labels = [b["name"] for b in brands]
    br_values = [int(b.get("count", 0)) for b in brands]

    # Output image paths
    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    # Generate charts (only if lists non-empty)
    has_keywords = bool(kw_labels)
    has_brands = bool(br_labels)

    if has_keywords:
        # Highest at bottom: reverse both lists for horizontal bar aesthetics
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
        csv_name, json_name, has_keywords, has_brands
    )
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)
    print("Wrote site/index.html")

if __name__ == "__main__":
    run()
