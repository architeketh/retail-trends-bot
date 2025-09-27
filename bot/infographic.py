# bot/infographic.py
# Builds index.html dashboard with keywords, brands, headlines, stats + visitor counter

import os, json
from datetime import datetime
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA = os.path.join(BASE, "data")
SITE = os.path.join(ROOT, "site")
ASSETS = os.path.join(SITE, "assets")

CSS = """<style>
:root{--stroke:#e5e7eb}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;background:#fff}
.wrap{max-width:900px;margin:0 auto;padding:18px}
.hero{background:#f9fafb;border-bottom:1px solid var(--stroke);padding:24px 0}
h1{margin:0 0 8px 0;font-size:28px} h2{margin:0 0 8px 0;font-size:20px}
.note{font-size:13px;color:#6b7280}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
img{max-width:100%}
.header-actions a, .header-actions button{margin-right:12px;text-decoration:none;color:#0b6cff;font-size:14px}
.header-actions button{background:#0b6cff;color:#fff;border:none;padding:6px 10px;border-radius:6px;cursor:pointer}
.kpis{margin-top:8px;font-size:14px;color:#374151}
.kpi{margin-right:14px}
#visitor-count{font-size:14px;color:#111;margin-top:8px}
</style>"""

def bar_chart(data, title, outfile):
    if not data: return None
    labels, values = zip(*data)
    fig, ax = plt.subplots(figsize=(6,4))
    bars = ax.barh(range(len(labels)), values)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_title(title)
    for i, v in enumerate(values):
        ax.text(v+0.2, i, str(v), va="center")
    plt.tight_layout()
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, outfile)
    plt.savefig(path)
    plt.close(fig)
    return path

def build_index(title, description, keywords_img, brands_img, highlights, stats, csv_name, json_name,
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
<html><head><meta charset="utf-8"><title>{title}</title>{CSS}</head>
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
    {kpi_html}
    <div id="visitor-count">Visitors: …</div>
    <script>
      fetch('https://api.countapi.xyz/hit/architeketh/retail-trends')
        .then(res => res.json())
        .then(data => {{
          document.getElementById('visitor-count').innerText = "Visitors: " + data.value;
        }});
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

def run():
    os.makedirs(SITE, exist_ok=True)
    s_path = os.path.join(DATA, "summary.json")
    if not os.path.exists(s_path):
        print("summary.json missing")
        return
    with open(s_path, "r", encoding="utf-8") as f:
        s = json.load(f)

    keywords = [(k["word"], k["count"]) for k in s.get("keywords", []) if "word" in k]
    brands = [(b["brand"], b["count"]) for b in s.get("brands", []) if "brand" in b]

    kw_chart = bar_chart(keywords[:15], "Top Keywords (7-day totals)", "keywords.png")
    br_chart = bar_chart(brands[:15], "Brand Mentions (7-day totals)", "brands.png")

    html = build_index(
        "Retail Trends Dashboard",
        "Daily updated retail trend insights.",
        kw_chart, br_chart,
        s.get("headlines", []),
        s.get("stats", {}),
        "headlines.csv",
        "headlines.json",
        bool(keywords), bool(brands),
        keywords[0] if keywords else None,
        brands[0] if brands else None
    )

    out_path = os.path.join(SITE, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/index.html with visitor count")

if __name__ == "__main__":
    run()
