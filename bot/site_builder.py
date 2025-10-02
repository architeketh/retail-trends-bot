# bot/site_builder.py
import pathlib, datetime, json

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

def esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# Categorized data (front first, then back)
cats = {}
src = ASSETS / "categorized.json"
if not src.exists():
    src = DATA / "categorized.json"
if src.exists():
    try:
        cats = json.loads(src.read_text(encoding="utf-8"))
    except Exception:
        cats = {}

# Headlines fallback
articles = []
hjson = ASSETS / "headlines.json"
if hjson.exists():
    try:
        articles = json.loads(hjson.read_text(encoding="utf-8"))
    except Exception:
        pass

# Prefer SVG charts; fallback to PNG
kw_src = "assets/keywords.svg" if (ASSETS / "keywords.svg").exists() else (
         "assets/keywords.png" if (ASSETS / "keywords.png").exists() else "")
br_src = "assets/brands.svg" if (ASSETS / "brands.svg").exists() else (
         "assets/brands.png" if (ASSETS / "brands.png").exists() else "")

ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]

html = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8" /><meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Retail Trends – Dashboard</title>
<style>
:root{{--bg:#fff;--text:#111;--card:#fff;--stroke:#e5e7eb;--btn:#f8fafc;--primary:#2E93fA}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
.wrap{{max-width:1100px;margin:0 auto;padding:28px 18px}}
.header{{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
.title{{margin:0;font-size:28px}} .desc{{margin:4px 0 0;color:#4b5563}}
.actions a,.actions button{{display:inline-block;margin-left:8px;padding:8px 12px;border-radius:10px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}}
.primary{{background:var(--primary);color:#fff;border:none}}
.grid{{display:grid;gap:16px;margin-top:16px}} @media(min-width:900px){{.grid{{grid-template-columns:1fr 1fr}}}}
.card{{background:var(--card);border:1px solid var(--stroke);border-radius:12px;padding:16px}}
h2{{margin:0 0 10px 0;font-size:18px}} .muted{{color:#6b7280}} ul{{margin:0;padding-left:18px}}
img{{max-width:100%;border-radius:8px}} .note{{color:#6b7280;font-size:14px}}
</style></head><body><div class="wrap">
<header class="header">
  <div><h1 class="title">Retail Trends – Dashboard</h1><p class="desc">Daily retail headlines, keywords & brand mentions</p></div>
  <div class="actions"><a href="assets/headlines.json">JSON</a><a href="assets/categorized.json">Categories JSON</a><button class="primary" onclick="location.reload()">Refresh</button></div>
</header>

<section class="grid">
  <article class="card"><h2>Top Keywords <span style="background:#eef2ff;color:#4338ca;border-radius:999px;padding:2px 8px;font-size:12px">7-day</span></h2>
    <div>{('<img src="'+kw_src+'" alt="Top Keywords"/>') if kw_src else "<p class='note'>No keywords chart yet.</p>"}</div>
  </article>
  <article class="card"><h2>Brand Mentions <span style="background:#eef2ff;color:#4338ca;border-radius:999px;padding:2px 8px;font-size:12px">7-day</span></h2>
    <div>{('<img src="'+br_src+'" alt="Brand Mentions"/>') if br_src else "<p class='note'>No brands chart yet.</p>"}</div>
  </article>
</section>

<section class="card" style="margin-top:16px"><h2>Headlines by Category</h2>
"""

if ordered:
    for cat, items in ordered:
        html += f"<h3 style='margin:14px 0 8px'>{esc(cat)} <span class='muted'>({len(items)})</span></h3><ul>"
        for a in items[:12]:
            t = esc(a.get("title") or "(untitled)")
            l = esc(a.get("link") or "#")
            s = esc(a.get("source") or "")
            span = f' <span class="muted">({s})</span>' if s else ""
            html += f'<li><a href="{l}" target="_blank" rel="noopener">{t}</a>{span}</li>'
        html += "</ul>"
else:
    html += "<ul><li class='note'>No headlines available yet.</li></ul>"

html += f"""</section>
<p class="muted" style="margin-top:12px">Last updated: {esc(now)}</p>
</div></body></html>"""

(ROOT / "index.html").write_text(html, encoding="utf-8")
print("✓ Wrote index.html (prefers SVG charts)")
