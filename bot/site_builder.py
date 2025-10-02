# bot/site_builder.py
import pathlib, json, datetime

ROOT = pathlib.Path(".")
DATA, ASSETS = ROOT / "data", ROOT / "assets"
DATA.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

# Load categorized and headlines
cats = {}
cpath = ASSETS / "categorized.json"
if not cpath.exists():
    cpath = DATA / "categorized.json"
if cpath.exists():
    try:
        cats = json.loads(cpath.read_text(encoding="utf-8"))
    except Exception:
        cats = {}

arts = []
hpath = DATA / "headlines.json"
if hpath.exists():
    try:
        arts = json.loads(hpath.read_text(encoding="utf-8")).get("articles", [])
    except Exception:
        pass

# Totals JSON (for side labels)
kw_tot = {}
br_tot = {}
kwt = ASSETS / "kw_totals.json"
brt = ASSETS / "brand_totals.json"
if kwt.exists():
    try: kw_tot = json.loads(kwt.read_text(encoding="utf-8"))
    except Exception: pass
if brt.exists():
    try: br_tot = json.loads(brt.read_text(encoding="utf-8"))
    except Exception: pass

# Chart asset paths
def chart_src(name: str) -> str:
    psvg = ASSETS / f"{name}.svg"
    ppng = ASSETS / f"{name}.png"
    if psvg.exists(): return f"assets/{name}.svg"
    if ppng.exists(): return f"assets/{name}.png"
    return ""

ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]

def section_chart_row(title: str, img: str, side_list: list, label_key: str):
    right = ""
    if side_list:
        items = ", ".join(f"{esc(x.get(label_key,''))} ({int(x.get('count',0))})" for x in side_list[:10])
        right = f"<div class='muted small'>Top: {items}</div>"
    img_tag = f"<img src='{esc(img)}' alt='{esc(title)}'/>" if img else "<p class='note'>No chart yet.</p>"
    return f"""<article class="card">
  <h2>{esc(title)}</h2>
  <div>{img_tag}</div>
  {right}
</article>"""

# Build HTML
html = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Trends – Dashboard</title>
<style>
:root{{--bg:#0b1220;--card:#0e172a;--text:#e5e7eb;--muted:#94a3b8;--accent:#6ee7b7;--stroke:#1f2a44;--chip:#1e293b}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
.wrap{{max-width:1200px;margin:0 auto;padding:26px 18px}}
.hero{{background:linear-gradient(135deg,#0e172a,#111827 60%,#0b1220);border:1px solid var(--stroke);border-radius:16px;padding:28px;margin-bottom:18px}}
.hero h1{{margin:0 0 8px 0;font-size:32px;letter-spacing:.4px}}
.hero p{{margin:0;color:var(--muted)}}
.actions a{{display:inline-block;margin-right:10px;padding:8px 12px;border-radius:10px;border:1px solid var(--stroke);background:#0b1430;color:#e5e7eb;text-decoration:none}}
.grid2{{display:grid;gap:16px}}
@media(min-width:900px){{.grid2{{grid-template-columns:1fr 1fr}}}}
.card{{background:var(--card);border:1px solid var(--stroke);border-radius:12px;padding:16px}}
h2{{margin:0 0 10px 0;font-size:18px}}
.muted{{color:var(--muted)}}.small{{font-size:12px}}.note{{color:var(--muted)}}
ul{{margin:0;padding-left:18px}}img{{max-width:100%;border-radius:10px}}
.cat h3{{margin:14px 0 8px}}
.footer{{margin-top:16px;color:var(--muted);font-size:12px}}
.badge{{display:inline-block;background:#1f2937;color:#a7f3d0;border:1px solid #1f2a44;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:8px}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}
.chips a{{text-decoration:none;background:var(--chip);color:#e5e7eb;border:1px solid #1f2a44;padding:6px 10px;border-radius:999px;font-size:13px}}
.chips a:hover{{filter:brightness(1.1)}}
.anchor{{scroll-margin-top:90px}}
</style></head><body><div class="wrap">

<section class="hero">
  <h1>Plan boldly. Retire confidently.</h1>
  <p class="muted">Daily retail headlines with 7-day, month-to-date, and year-to-date trends.</p>
  <div class="actions" style="margin-top:10px">
    <!-- These now DOWNLOAD instead of opening raw JSON in the browser -->
    <a href="assets/kw_totals.json" download>Download Keyword Totals (JSON)</a>
    <a href="assets/brand_totals.json" download>Download Brand Totals (JSON)</a>
    <a href="assets/categorized.json" download>Download Categories (JSON)</a>
  </div>
  <div class="chips">
"""

# Category quick-nav chips (scroll to section, not to JSON)
for name in ORDER:
    if cats.get(name):
        slug = "cat-" + name.lower().replace(" ", "-")
        html += f'    <a href="#{esc(slug)}">{esc(name)}</a>\n'

html += """  </div>
</section>

<section class="grid2">
"""

html += section_chart_row("Top Keywords — Today", chart_src("keywords_today"), kw_tot.get("today", []), "token")
html += section_chart_row("Brand Mentions — Today", chart_src("brands_today"), br_tot.get("today", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""

html += section_chart_row("Top Keywords — 7-day (cumulative)", chart_src("keywords_7d"), kw_tot.get("week", []), "token")
html += section_chart_row("Brand Mentions — 7-day (cumulative)", chart_src("brands_7d"), br_tot.get("week", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""

html += section_chart_row("Top Keywords — Month-to-date", chart_src("keywords_mtd"), kw_tot.get("mtd", []), "token")
html += section_chart_row("Brand Mentions — Month-to-date", chart_src("brands_mtd"), br_tot.get("mtd", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""

html += section_chart_row("Top Keywords — Year-to-date", chart_src("keywords_ytd"), kw_tot.get("ytd", []), "token")
html += section_chart_row("Brand Mentions — Year-to-date", chart_src("brands_ytd"), br_tot.get("ytd", []), "brand")

html += """</section>

<section class="card cat" style="margin-top:18px">
  <h2>Headlines by Category</h2>
"""

# Category sections (anchors for in-page nav)
if ordered:
    for cat, items in ordered:
        slug = "cat-" + cat.lower().replace(" ", "-")
        html += f"<h3 id='{esc(slug)}' class='anchor'>{esc(cat)} <span class='badge'>{len(items)}</span></h3><ul>"
        for a in items[:12]:
            t = esc(a.get("title") or "(untitled)")
            l = esc(a.get("link") or "#")
            s = esc(a.get("source") or "")
            span = f' <span class="muted">({s})</span>' if s else ""
            html += f'<li><a href="{l}" target="_blank" rel="noopener">{t}</a>{span}</li>'
        html += "</ul>"
else:
    html += "<p class='note'>No categorized headlines yet.</p>"

html += f"""
</section>

<p class="footer">Last updated {esc(now)} · © {datetime.datetime.utcnow().year} Retail Trends Bot</p>
</div></body></html>
"""

(ROOT / "index.html").write_text(html, encoding="utf-8")
print("✓ Wrote index.html (no JSON links open in-page; categories are in-page anchors)")