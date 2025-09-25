# bot/infographic.py
# Builds charts and the site page (with KPI row) from bot/data/summary.json

import os
import json
from datetime import datetime
import yaml
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def save_barh(labels, values, title, outpath):
    plt.figure(figsize=(8, 6))
    plt.barh(labels, values)
    plt.title(title)
    plt.xlabel("Relative Importance")
    plt.tight_layout()
    ensure_dir(outpath)
    plt.savefig(outpath)
    plt.close()

def kpi_card(label, value, sub=None):
    s = f"""
    <div class="kpi card">
      <div class="kpi-value">{value}</div>
      <div class="kpi-label">{label}</div>
      {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
    </div>
    """
    return s

def build_index(title, description, keywords_img, brands_img, highlights, stats):
    # KPI values
    mentions_total = (stats or {}).get("brand_mentions_total", 0)
    unique_sources = (stats or {}).get("unique_sources", 0)
    top_brand = (stats or {}).get("top_brand", "—")

    kpis_html = (
        kpi_card("Mentions Today", mentions_total)
        + kpi_card("Sources Fetched", unique_sources)
        + kpi_card("Top Brand", top_brand)
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="assets/style.css">
  <meta name="theme-color" content="#0b0c10">
  <style>
    /* Minimal KPI styling (works with your existing stylesheet) */
    .kpis {{ display:grid; grid-template-columns:1fr; gap:12px; margin:14px 0 18px }}
    @media(min-width:900px){{ .kpis {{ grid-template-columns:repeat(3,1fr); }} }}
    .kpi.card {{ text-align:center; padding:18px 14px }}
    .kpi-value {{ font-size:28px; font-weight:700; line-height:1; margin-bottom:6px }}
    .kpi-label {{ color:#a4aec2; font-size:13px }}
    .kpi-sub {{ color:#cfe5ff; font-size:12px; margin-top:6px }}
  </style>
</head>
<body>
  <div class="container">
    <header class="header">
      <div class="brand">
        <h1>{title}</h1>
        <p>{description}</p>
        <div class="badges">
          <span class="badge">Auto-updated daily</span>
          <span class="badge">Retail Dive · NRF · Shopify · Census MTIS</span>
        </div>
      </div>
      <div class="actions">
        <a class="btn" href="assets/{os.path.basename(keywords_img)}" download>Download Keywords PNG</a>
        <a class="btn" href="assets/{os.path.basename(brands_img)}" download>Download Brands PNG</a>
        <button class="btn primary" id="refreshBtn" onclick="location.reload()">Refresh</button>
      </div>
    </header>

    <section class="kpis">
      {kpis_html}
    </section>

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

    <p class="footer">Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
  </div>
</body>
</html>"""

def run():
    cfg = load_config()
    # read summary
    with open(os.path.join(DATA_DIR, "summary.json"), "r", encoding="utf-8") as f:
        summary = json.load(f)

    keywords = summary.get("keywords", [])
    brands   = summary.get("brands", [])
    stats    = summary.get("stats", {})
    highlights = summary.get("highlights", [])

    # output chart paths (under /site/assets)
    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img   = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    # charts
    if keywords:
        save_barh(list(reversed(keywords)), list(range(len(keywords), 0, -1)),
                  cfg["infographic"]["title"], keywords_img)
    else:
        ensure_dir(keywords_img); open(keywords_img, "wb").close()

    if brands:
        labels = [b["name"] for b in brands]
        vals   = [b["count"] for b in brands]
        save_barh(list(reversed(labels)), list(reversed(vals)),
                  "Top Retail Brand Mentions", brands_img)
    else:
        ensure_dir(brands_img); open(brands_img, "wb").close()

    # write site/index.html
    site_dir = os.path.join(ROOT, "site")
    assets_dir = os.path.join(site_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    index_html = build_index(
        cfg["website"]["title"],
        cfg["website"]["description"],
        keywords_img, brands_img,
        highlights, stats
    )
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # ensure CSS exists (don’t overwrite if user customized)
    css_path = os.path.join(assets_dir, "style.css")
    if not os.path.exists(css_path):
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("""body{font-family:system-ui; margin:2rem; background:#fafafa; color:#222}
h1{margin-bottom:.25rem}.tagline{color:#555;margin-top:0}
.charts{display:grid;grid-template-columns:1fr;gap:1.5rem}
.chart-card{background:#fff;border:1px solid #e6e6e6;border-radius:12px;padding:1rem;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.headlines li{margin:.4rem 0}.src{color:#777;font-size:.9em;margin-left:.25rem}
@media(min-width:1100px){.charts{grid-template-columns:1fr 1fr}}""")

    print("Wrote site/index.html with KPI row and charts")

if __name__ == "__main__":
    run()
