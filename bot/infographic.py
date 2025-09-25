# bot/infographic.py
# Builds modern-styled charts + site page, writes CSV/JSON headline exports,
# shows ~10-bar brand chart (Top 9 + "Other"), and adds a sources drawer.

import os
import json
import csv
from datetime import datetime
import yaml
import matplotlib.pyplot as plt
from matplotlib import ticker
from collections import Counter

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

# ——————————————————————————————————————————
# Modern chart styling helpers
# ——————————————————————————————————————————

# Palettes (distinct, modern). Feel free to tweak hex values.
PALETTE_KEYWORDS = [
    "#7BDFF2","#B2F7EF","#EFF7F6","#F7D6E0","#F2B5D4",
    "#B39DDB","#80CBC4","#FFD54F","#FFAB91","#90CAF9",
    "#A5D6A7","#F48FB1","#CE93D8","#FFCC80","#81D4FA",
    "#EF9A9A","#C5E1A5","#E6EE9C"
]
PALETTE_BRANDS = [
    "#6CC0FF","#A18CFF","#FF8EC7","#FFC46C","#7BE495",
    "#FFD166","#06D6A0","#EF476F","#8892F6","#42C2FF",
    "#F0A6CA","#9CDAF1","#6EE7B7","#FCD34D","#F472B6"
]

def pick_colors(n, palette):
    if n <= len(palette):
        return palette[:n]
    # repeat palette if more bars than colors
    reps = (n + len(palette) - 1) // len(palette)
    return (palette * reps)[:n]

def style_axes(ax):
    # Dark-ish look to match your CSS
    ax.set_facecolor("#0f1218")
    ax.figure.set_facecolor("#0f1218")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    for s in ("left","bottom"):
        ax.spines[s].set_color("#2b3242")
        ax.spines[s].set_linewidth(1)
    ax.tick_params(colors="#dfe7ff", labelsize=10)
    ax.grid(axis="x", color="#2b3242", linewidth=0.8, alpha=0.6)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(6))
    ax.set_xlabel("Relative Importance", color="#cfe5ff", labelpad=8)

def save_barh_modern(labels, values, title, outpath, palette):
    ensure_dir(outpath)
    plt.close("all")
    fig, ax = plt.subplots(figsize=(8, 6), dpi=170)

    style_axes(ax)
    ax.set_title(title, color="#e7ebf3", pad=10, fontsize=12)

    # reverse to show highest at top (we’ll draw from low→high y)
    labels = list(labels)
    values = list(values)
    if len(labels) != len(values):
        return
    # Draw bars one-by-one to color individually
    y_pos = range(len(labels))
    colors = pick_colors(len(labels), palette)
    bars = ax.barh(y_pos, values, color=colors, edgecolor="none")

    # Rounded feel: small alpha shadow behind bars
    for b in bars:
        b.set_alpha(0.95)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, color="#e7ebf3")
    plt.tight_layout()
    fig.savefig(outpath, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)

# ——————————————————————————————————————————
# Data utilities
# ——————————————————————————————————————————

def write_headlines_exports(assets_dir, highlights):
    os.makedirs(assets_dir, exist_ok=True)

    # JSON
    json_path = os.path.join(assets_dir, "headlines.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(highlights, jf, indent=2, ensure_ascii=False)

    # CSV
    csv_path = os.path.join(assets_dir, "headlines.csv")
    fieldnames = ["title", "link", "source", "published"]
    with open(csv_path, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for h in highlights:
            writer.writerow({
                "title": h.get("title", ""),
                "link": h.get("link", ""),
                "source": h.get("source", ""),
                "published": h.get("published", ""),
            })

    return os.path.basename(csv_path), os.path.basename(json_path)

def sources_list_html(highlights, stats):
    counts = Counter([h.get("source", "").strip() for h in highlights if h.get("source")])
    unique_sources = (stats or {}).get("sources") or sorted(s for s in counts if s)

    lis = []
    if counts:
        for src, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
            if not src: continue
            lis.append(f"<li><span class='src-name'>{src}</span> <span class='src-count'>({n})</span></li>")
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

def build_index(title, description, keywords_img, brands_img, highlights, stats,
                csv_name, json_name):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="assets/style.css">
  <meta name="theme-color" content="#0b0c10">
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="brand">
        <h1>{title}</h1>
        <p>{description}</p>
        <div class="badges">
          <span class="badge">Auto-updated daily</span>
          <span class="badge">NRF · Retail Dive · Shopify · Census MTIS · + More</span>
        </div>
      </div>
      <div class="actions">
        <a class="btn" href="assets/{os.path.basename(keywords_img)}" download>Download Keywords PNG</a>
        <a class="btn" href="assets/{os.path.basename(brands_img)}" download>Download Brands PNG</a>
        <a class="btn" href="assets/{csv_name}" download>Download Headlines CSV</a>
        <a class="btn" href="assets/{json_name}" download>Download Headlines JSON</a>
        <button class="btn primary" id="refreshBtn" onclick="location.reload()">Refresh</button>
      </div>
    </header>

    <section class="grid">
      <article class="card">
        <h2>Top Keywords</h2>
        <img src="assets/{os.path.basename(keywords_img)}" alt="Top Keywords chart">
      </article>

      <article class="card">
        <h2>Brand Mentions</h2>
        <img src="assets/{os.path.basename(brands_img)}" alt="Brand Mentions chart">
      </article>
    </section>

    <section class="card" style="margin-top:18px">
      <h2>Headlines</h2>
      <ul class="list">
        {''.join(f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{(h.get('title','')).replace('&','&amp;').replace('<','&lt;')}</a><span class='src'>({h.get('source','')})</span></li>" for h in highlights)}
      </ul>
    </section>

    {sources_list_html(highlights, stats)}

    <p class="footer">Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
  </div>
</body>
</html>"""

# ——————————————————————————————————————————
# Brands chart: ensure ~N bars (Top N-1 + Other)
# ——————————————————————————————————————————
def prepare_brand_bars(brands, desired_n):
    if not brands:
        return [], []
    if len(brands) >= desired_n:
        top = brands[:desired_n - 1]
        remainder = brands[desired_n - 1:]
        other_sum = sum(b["count"] for b in remainder)
        rows = top + ([{"name": "Other", "count": other_sum}] if other_sum > 0 else brands[:desired_n])
    else:
        rows = brands
    labels = [b["name"] for b in rows]
    values = [b["count"] for b in rows]
    return labels, values

# ——————————————————————————————————————————
# Main
# ——————————————————————————————————————————
def run():
    cfg = load_config()
    with open(os.path.join(DATA_DIR, "summary.json"), "r", encoding="utf-8") as f:
        summary = json.load(f)

    keywords   = summary.get("keywords", [])
    brands     = summary.get("brands", [])
    stats      = summary.get("stats", {})
    highlights = summary.get("highlights", [])

    # Output chart paths (under /site/assets)
    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img   = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    # ——— Keywords chart ———
    if keywords:
        # Highest at top → reverse label order and use rank as "importance"
        labels_kw = list(reversed(keywords))
        vals_kw   = list(range(len(keywords), 0, -1))
        save_barh_modern(labels_kw, vals_kw, "Retail Trend Keywords", keywords_img, PALETTE_KEYWORDS)
    else:
        ensure_dir(keywords_img); open(keywords_img, "wb").close()

    # ——— Brands chart (Top 9 + Other) ———
    desired_n = max(10, int(cfg["infographic"].get("top_n_brands", 10)))
    if brands:
        labels_b, vals_b = prepare_brand_bars(brands, desired_n)
        if labels_b:
            save_barh_modern(list(reversed(labels_b)), list(reversed(vals_b)),
                             f"Retail Brand Mentions", brands_img, PALETTE_BRANDS)
        else:
            ensure_dir(brands_img); open(brands_img, "wb").close()
    else:
        ensure_dir(brands_img); open(brands_img, "wb").close()

    # Write headline exports + page
    site_dir = os.path.join(ROOT, "site")
    assets_dir = os.path.join(site_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    csv_name, json_name = write_headlines_exports(assets_dir, highlights)

    index_html = build_index(
        cfg["website"]["title"],
        cfg["website"]["description"],
        keywords_img, brands_img,
        highlights, stats,
        csv_name, json_name
    )
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Ensure CSS exists (don’t overwrite if user customized)
    css_path = os.path.join(assets_dir, "style.css")
    if not os.path.exists(css_path):
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("""body{font-family:system-ui; margin:2rem; background:#0b0c10; color:#e7ebf3}
h1{margin-bottom:.25rem}.tagline{color:#a4aec2;margin-top:0}
.charts{display:grid;grid-template-columns:1fr;gap:1.5rem}
.chart-card{background:#111319;border:1px solid #1b1e28;border-radius:12px;padding:1rem;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.headlines li{margin:.4rem 0}.src{color:#a4aec2;font-size:.9em;margin-left:.25rem}
@media(min-width:1100px){.charts{grid-template-columns:1fr 1fr}}""")

    print(f"Wrote site/index.html and modern-styled charts (distinct colors for each bar)")

if __name__ == "__main__":
    run()
