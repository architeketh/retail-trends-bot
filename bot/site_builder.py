# bot/site_builder.py
import pathlib, datetime, json, base64

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

def esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def data_url(path: pathlib.Path) -> str | None:
    if not path.exists(): return None
    try:
        raw = path.read_bytes()
        if path.suffix.lower()==".svg":
            # Inline SVG as utf-8 (safer than base64 for SVG)
            txt = path.read_text(encoding="utf-8")
            return "data:image/svg+xml;utf8," + txt.replace("#","%23").replace("\n","")
        else:
            b64 = base64.b64encode(raw).decode("ascii")
            mime = "image/png" if path.suffix.lower()==".png" else "image/svg+xml"
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# Load categories (front first)
cats = {}
src = ASSETS / "categorized.json"
if not src.exists(): src = DATA / "categorized.json"
if src.exists():
    try: cats = json.loads(src.read_text(encoding="utf-8"))
    except Exception: cats = {}

# Headlines fallback
articles = []
hjson = ASSETS / "headlines.json"
if hjson.exists():
    try: articles = json.loads(hjson.read_text(encoding="utf-8"))
    except Exception: pass

# Top counts (for side labels)
kw_top = []
br_top = []
kw_top_path = ASSETS / "kw_top.json"
br_top_path = ASSETS / "brand_top.json"
if kw_top_path.exists():
    try: kw_top = json.loads(kw_top_path.read_text(encoding="utf-8"))
    except Exception: pass
if br_top_path.exists():
    try: br_top = json.loads(br_top_path.read_text(encoding="utf-8"))
    except Exception: pass

# Prefer file path to SVG, else PNG; if neither, embed data URL if available
kw_svg = ASSETS / "keywords.svg"
kw_png = ASSETS / "keywords.png"
br_svg = ASSETS / "brands.svg"
br_png = ASSETS / "brands.png"

def img_tag(svg_path: pathlib.Path, png_path: pathlib.Path, alt: str) -> str:
    if svg_path.exists():
        return f'<img src="assets/{svg_path.name}" alt="{alt}"/>'
    if png_path.exists():
        return f'<img src="assets/{png_path.name}" alt="{alt}"/>'
    # embed as data URL if file exists but pathing fails
    for p in (svg_path, png_path):
        du = data_url(p)
        if du: return f'<img src="{du}" alt="{alt}"/>'
    return "<p class='note'>No chart available.</p>"

ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]

# Build HTML
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
.small{{font-size:12px;color:#6b7280;margin-top:8px}}
.kv{{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:start}}
.badge{{background:#eef2ff;color:#4338ca;border-radius:999px;padding:2px 8px;font-size:12px}}
</style></head><body><div class="wrap">
<header class="header">
  <div><h1 class="title">Retail Trends – Dashboard</h1><p class="desc">Daily retail headlines, 7-day keyword & brand trends</p></div>
  <div class="actions"><a href="assets/headlines.json">JSON</a><a href="assets/categorized.json">Categories JSON</a><button class="primary" onclick="location.reload()">Refresh</button></div>
</header>

<section class="grid">
  <article class="card">
    <h2>Top Keywords <span class="badge">7-day</span></h2>
    <div>{img_tag(kw_svg, kw_png, "Top Keywords")}</div>
    <div class="small">
"""

# Add keyword totals list
if kw_top:
    html += "      <div>Top terms: "
    html += ", ".join(f"{esc(x['token'])} ({int(x['count'])})" for x in kw_top[:10])
    html += "</div>\n"
else:
    html += "      <div class='note'>No keyword totals yet.</div>\n"

html += """    </div>
  </article>

  <article class="card">
    <h2>Brand Mentions <span class="badge">7-day</span></h2>
    <div>"""

html += img_tag(br_svg, br_png, "Brand Mentions") + "</div>\n<div class='small'>"

if br_top:
    html += "      <div>Top brands: "
    html += ", ".join(f"{esc(x['brand'])} ({int(x['count'])})" for x in br_top[:10])
    html += "</div>\n"
else:
    html += "      <div class='note'>No brand totals yet.</div>\n"

html += """    </div>
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
print("✓ Wrote index.html (embeds charts if needed + shows totals)")
