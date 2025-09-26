# bot/news_links_page.py
# Categorized sources + nav links back to Dashboard and Stats

import os
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
SITE_DIR = os.path.join(ROOT, "site")

INLINE_CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;
     padding:2rem;max-width:1000px;margin:auto}
h1{margin:0 0 1rem 0}
p.sub{color:#555;margin:.25rem 0 1.25rem}
.section{margin:1.25rem 0 1.5rem}
.section h2{font-size:1.1rem;margin:.25rem 0 .5rem;color:#0f172a}
.grid{display:grid;grid-template-columns:1fr;gap:.6rem}
@media(min-width:800px){.grid{grid-template-columns:1fr 1fr}}
.card{border:1px solid #eee;border-radius:10px;padding:12px}
.card h3{margin:.1rem 0 .2rem;font-size:1.02rem}
.card p{margin:.2rem 0;color:#444;font-size:.95rem}
a.site{color:#1d4ed8;text-decoration:none;border-bottom:1px dashed #bfdbfe;word-break:break-word}
a.site:hover{color:#0f172a;border-bottom:none}
.actions{margin-top:1rem}
.btn{background:#f8fafc;padding:8px 12px;border:1px solid #ccc;border-radius:10px;
     text-decoration:none;color:#111;display:inline-block;margin-right:8px}
.btn.primary{background:#2E93fA;color:#fff;border:none}
.footer{margin-top:16px;color:#666;font-size:12px}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.nav a{font-size:12px;color:#0f172a;text-decoration:none;background:#eef6ff;border:1px solid #dbeafe;
       padding:6px 10px;border-radius:999px}
.nav a:hover{background:#e0efff}
.anchor{position:relative;top:-64px;visibility:hidden}
</style>"""

# (categories definition left unchanged for brevity)

def run():
    # build quick-jump pills
    nav = []
    for title, _ in CATEGORIES:
        anchor = title.lower().replace("&","and").replace("/"," ").replace("  "," ").replace(" ", "-")
        nav.append(f"<a href='#{anchor}'>{title}</a>")

    sections = [section_html(title, sites) for title, sites in CATEGORIES]

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Retail News Sites</title>
  {INLINE_CSS}
</head>
<body>
  <h1>Retail News Sites</h1>
  <p class="sub">A curated, categorized list of reliable sources for retail trends and analysis.</p>

  <div class="nav">{''.join(nav)}</div>

  {''.join(sections)}

  <div class="actions">
    <a class="btn" href="index.html">← Dashboard</a>
    <a class="btn" href="stats.html">Stats</a>
  </div>
  <p class="footer">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body>
</html>"""

    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "news.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/news.html")

if __name__ == "__main__":
    run()
