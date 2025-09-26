# bot/infographic.py
# Modern header with optional background image + link to Weekly AI Summary

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

PALETTE_KEYWORDS = ["#2E93fA","#66DA26","#E91E63","#FF9800","#00E396","#775DD0","#008FFB",
                    "#FEB019","#FF4560","#00D9E9","#A300D6","#F86624","#D10CE8","#4CAF50","#9C27B0"]
PALETTE_BRANDS = ["#7B61FF","#FF6B6B","#00C49A","#FFB703","#219EBC","#8338EC","#FB5607","#06D6A0",
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
    mx = max(values) if values else 0
    offs = (mx * 0.02) if mx > 0 else 0.5
    for i, v in enumerate(values):
        ax.text(v + offs, i, str(v), va="center", ha="left", color="#111111")
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
:root{--stroke:#e5e7eb;--btn:#f8fafc;--primary:#7b61ff}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;margin:0}
.hero{position:relative;min-height:220px;background:linear-gradient(180deg, rgba(10,14,25,.65), rgba(10,14,25,.65)), url('assets/bg.jpg') center/cover no-repeat;display:flex;align-items:flex-end}
.hero .wrap{max-width:1100px;margin:0 auto;padding:28px 18px;width:100%}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.header-actions a,.header-actions button{display:inline-block;margin-right:8px;padding:8px 12px;border-radius:10px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}
.header-actions .primary{background:var(--primary);color:#fff;border:none}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 10px 0;font-size:18px}
.note{color:#6b7280;font-size:14px}
img{max-width:100%;border-radius:8px}
</style>"""

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name,
                has_keywords, has_brands):
    kw_block = (f"<img src='assets/{os.path.basename(keywords_img)}' alt='Top Keywords'>"
                if has_keywords else "<p class='note'>No keywords yet. This will populate after the next successful run.</p>")
    br_block = (f"<img src='assets/{os.path.basename(brands_img)}' alt='Brand Mentions'>"
                if has_brands else "<p class='note'>No brand mentions yet. This will populate after the next successful run.</p>")
    headlines_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title')}</a> "
        f"<span class='note'>({h.get('source','')})</span></li>"
        for h in highlights
    ) or "<li class='note'>No headlines yet.</li>"

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
    else:
        kw_labels = list(reversed(raw_keywords))
        kw_values = list(range(len(raw_keywords), 0, -1))

    brands = summary.get("brands", []) or []
    br_labels = [b["name"] for b in brands]
    br_values = [int(b.get("count", 0)) for b in brands]

    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img = os.path.join(ROOT, cfg["infographic"]["brands_image"])

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

    csv_name, json_name = write_headlines_exports(assets_dir, highlights)

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
