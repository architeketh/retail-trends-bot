import os, json, yaml
from datetime import datetime
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")

def load_config():
    with open(os.path.join(ROOT, "config.yml")) as f:
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

def build_index(title, description, keywords_img, brands_img, highlights):
    lines = []
    lines.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    lines.append(f"<title>{title}</title>")
    lines.append("<link rel='stylesheet' href='assets/style.css'>")
    lines.append("</head><body>")
    lines.append(f"<h1>{title}</h1>")
    lines.append(f"<p class='tagline'>{description}</p>")
    lines.append("<section class='charts'>")
    lines.append("<div class='chart-card'><h2>Top Keywords</h2>")
    lines.append(f"<img src='assets/{os.path.basename(keywords_img)}' width='700'></div>")
    lines.append("<div class='chart-card'><h2>Brand Mentions</h2>")
    lines.append(f"<img src='assets/{os.path.basename(brands_img)}' width='700'></div>")
    lines.append("</section>")
    if highlights:
        lines.append("<h2>Headlines</h2><ul class='headlines'>")
        for h in highlights:
            t = h.get("title","").replace("&","&amp;").replace("<","&lt;")
            lines.append(f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{t}</a> <span class='src'>({h.get('source','')})</span></li>")
        lines.append("</ul>")
    lines.append(f"<footer><p>Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p></footer>")
    lines.append("</body></html>")
    return "\n".join(lines)

def run():
    cfg = load_config()
    with open(os.path.join(DATA_DIR, "summary.json")) as f:
        summary = json.load(f)

    keywords = summary.get("keywords", [])
    brands = summary.get("brands", [])
    keywords_img = os.path.join(ROOT, cfg["infographic"]["output_image"])
    brands_img = os.path.join(ROOT, cfg["infographic"]["brands_image"])

    if keywords:
        save_barh(list(reversed(keywords)), list(range(len(keywords), 0, -1)), cfg["infographic"]["title"], keywords_img)
    else:
        ensure_dir(keywords_img); open(keywords_img, "wb").close()

    if brands:
        labels = [b["name"] for b in brands]
        vals = [b["count"] for b in brands]
        save_barh(list(reversed(labels)), list(reversed(vals)), "Top Retail Brand Mentions", brands_img)
    else:
        ensure_dir(brands_img); open(brands_img, "wb").close()

    site_dir = os.path.join(ROOT, "site")
    assets_dir = os.path.join(site_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    index_html = build_index(cfg["website"]["title"], cfg["website"]["description"],
                             keywords_img, brands_img, summary.get("highlights", []))
    with open(os.path.join(site_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    css_path = os.path.join(assets_dir, "style.css")
    if not os.path.exists(css_path):
        with open(css_path, "w") as f:
            f.write("""body{font-family:system-ui; margin:2rem; background:#fafafa; color:#222}
h1{margin-bottom:.25rem}.tagline{color:#555;margin-top:0}
.charts{display:grid;grid-template-columns:1fr;gap:1.5rem}
.chart-card{background:#fff;border:1px solid #e6e6e6;border-radius:12px;padding:1rem;box-shadow:0 1px 3px rgba(0,0,0,.04)}
.headlines li{margin:.4rem 0}.src{color:#777;font-size:.9em;margin-left:.25rem}
@media(min-width:1100px){.charts{grid-template-columns:1fr 1fr}}""")
    print("Wrote site/index.html and charts")

if __name__ == "__main__":
    run()
