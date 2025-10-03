# bot/site_builder.py
import pathlib, json, datetime, re
from collections import Counter

ROOT = pathlib.Path(".")
DATA, ASSETS = ROOT / "data", ROOT / "assets"
DATA.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
today = datetime.date.today().isoformat()

# ---------- Load data ----------
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

# ---------- Natural AI-ish summary per category ----------
BRAND_SEED = {
    "Amazon","Walmart","Target","Costco","Best Buy","Home Depot","Lowe's","Lowe’s","Kroger","Aldi",
    "Tesco","Carrefour","IKEA","H&M","Zara","Nike","Adidas","Lululemon","Gap","Old Navy",
    "Sephora","Ulta","Macy's","Nordstrom","Kohl's","TJX","TJ Maxx","Marshalls","Saks","Apple",
    "Shein","Temu","Wayfair","Etsy","eBay","Shopify","Instacart","DoorDash","Uber","FedEx","UPS"
}
STOPWORDS = {
    "a","an","the","and","or","but","if","then","else","for","with","of","to","in","on","at","by","from","is","are","was","were",
    "be","been","do","does","did","have","has","had","will","would","can","could","may","might","that","this","these","those",
    "it","its","as","about","so","such","not","no","yes","why","how","when","where","what","who","which","your","new","report",
    "update","today","week","month","year","online","retail","ecommerce"
}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-&]+")

def top_brands(items, k=2):
    c = Counter()
    for a in items:
        t = (a.get("title") or "").lower()
        for b in BRAND_SEED:
            if b.lower() in t:
                c[b] += 1
    return [b for b,_ in c.most_common(k)]

def top_terms(items, k=3):
    c = Counter()
    for a in items:
        t = (a.get("title") or "")
        for m in WORD_RE.finditer(t):
            w = m.group(0).strip("’'\"-–—").lower()
            if w and w not in STOPWORDS and w not in {x.lower() for x in BRAND_SEED}:
                c[w] += 1
    return [w for w,_ in c.most_common(k)]

def natural_sentence(cat: str, items: list) -> str:
    if not items:
        return f"{cat}: No notable coverage today."
    n = len(items)
    brands = top_brands(items, k=2)
    terms = top_terms(items, k=3)
    parts = [f"In {cat.lower()}, we tracked {n} stor{'y' if n==1 else 'ies'}"]
    if brands:
        parts.append(f"with attention on {', '.join(brands)}")
    if terms:
        # keep keyword phrasing natural
        parts.append(f"and themes like {', '.join(terms)}")
    sent = " ".join(parts) + "."
    # example headline
    ex = (items[0].get("title") or "").strip()
    if ex:
        sent += f' Example: “{ex}”.'
    # Capitalize first letter
    return sent[0].upper() + sent[1:]

ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]
ai_lines = [natural_sentence(cat, items) for cat, items in ordered]

# Persist daily summary & build archive later
sum_path = DATA / "summaries.json"
all_summaries = {}
if sum_path.exists():
    try: all_summaries = json.loads(sum_path.read_text(encoding="utf-8"))
    except Exception: all_summaries = {}
all_summaries[today] = {
    "generated_at": now,
    "by_category": {cat: natural_sentence(cat, items) for cat, items in ordered}
}
sum_path.write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- Helpers for charts / totals ----------
def chart_src(name: str) -> str:
    psvg = ASSETS / f"{name}.svg"
    ppng = ASSETS / f"{name}.png"
    if psvg.exists(): return f"assets/{name}.svg"
    if ppng.exists(): return f"assets/{name}.png"
    return ""

def totals_sum(items, label_key):
    return sum(int(x.get("count", 0)) for x in (items or []))

def nice_list(items, label_key, limit=10):
    if not items: return "<span class='note'>—</span>"
    return ", ".join(f"{esc(x.get(label_key,''))} ({int(x.get('count',0))})" for x in items[:limit])

def section_chart_row(title: str, img: str, side_list: list, label_key: str):
    right = ""
    if side_list:
        right = f"<div class='muted small'>Top: {nice_list(side_list, label_key)}</div>"
    img_tag = f"<img src='{esc(img)}' alt='{esc(title)}'/>" if img else "<p class='note'>No chart yet.</p>"
    return f"""<article class="card">
  <h2>{esc(title)}</h2>
  <div>{img_tag}</div>
  {right}
</article>"""

# ---------- Build index.html ----------
html = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Trends – Dashboard</title>
<style>
:root{{--bg:#0b1220;--card:#0e172a;--text:#e5e7eb;--muted:#cbd5e1;--stroke:#1f2a44;--chip:#1e293b}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.45}}
a, a:visited{{color:#ffffff;text-decoration:none}}
a:hover{{text-decoration:underline;filter:brightness(1.05)}}

.wrap{{max-width:1200px;margin:0 auto;padding:22px 14px}}
@media(min-width:768px){{.wrap{{padding:26px 18px}}}}

.hero{{
  border:1px solid var(--stroke);border-radius:16px;padding:22px;margin-bottom:18px;
  background: linear-gradient(135deg,#0ea5e9 0%, #7c3aed 40%, #22c55e 75%, #ef4444 100%);
}}
.hero h1{{margin:0 0 8px 0;font-size:28px;letter-spacing:.4px}}
@media(min-width:768px){{.hero h1{{font-size:32px}}}}
.hero p{{margin:0;color:#f1f5f9}}

.grid2{{display:grid;gap:12px}}
@media(min-width:900px){{.grid2{{grid-template-columns:1fr 1fr;gap:16px}}}}

.card{{background:var(--card);border:1px solid var(--stroke);border-radius:12px;padding:14px}}
@media(min-width:768px){{.card{{padding:16px}}}}
h2{{margin:0 0 10px 0;font-size:18px}}
.muted{{color:var(--muted)}} .small{{font-size:12px}} .note{{color:var(--muted)}}
ul{{margin:0;padding-left:18px}} li{{margin:6px 0}}
img{{max-width:100%;border-radius:10px}}

.cat h3{{margin:14px 0 8px}}
.footer{{margin-top:16px;color:var(--muted);font-size:12px}}
.badge{{display:inline-block;background:#1f2937;color:#a7f3d0;border:1px solid #1f2a44;border-radius:999px;padding:2px 8px;font-size:12px}}
.totals{{display:grid;gap:12px}}
@media(min-width:900px){{.totals{{grid-template-columns:1.3fr 1fr 1fr}}}}
.kv{{display:grid;grid-template-columns:1fr auto;gap:8px}}
.table{{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}}
.table th,.table td{{border-bottom:1px solid #1f2a44;padding:8px 8px;text-align:left}}
.table th{{color:#e2e8f0;font-weight:600}}
.chips{{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}}
.chip{{background:#1e293b;color:#ffffff;border:1px solid #1f2a44;padding:6px 10px;border-radius:999px;font-size:13px}}
.anchor{{scroll-margin-top:90px}}
.card a, .table a, .cat a{{color:#ffffff}}
</style></head><body><div class="wrap">

<section class="hero">
  <h1>Retail Trends</h1>
  <p>Daily retail headlines with week-to-date, month-to-date, and year-to-date trends.</p>
  <div class="chips">
"""

# Quick nav
ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]
for name in ORDER:
    if cats.get(name):
        slug = "cat-" + name.lower().replace(" ", "-")
        html += f'    <span class="chip"><a href="#{esc(slug)}">{esc(name)}</a></span>\n'

html += """  </div>
</section>

<section class="card">
  <h2>Daily AI Summary</h2>
  <ul>
"""
for line in ai_lines:
    html += f"    <li>{esc(line)}</li>\n"
html += """  </ul>
</section>

<section class="card">
  <h2>Totals</h2>
  <div class="totals">
    <div>
      <h3 style="margin:0 0 8px 0">Articles by Category</h3>
      <table class="table">
        <thead><tr><th>Category</th><th>Articles</th></tr></thead>
        <tbody>
"""

# Category totals table
total_articles = 0
for cat, items in ordered:
    cnt = len(items); total_articles += cnt
    slug = "cat-" + cat.lower().replace(" ", "-")
    html += f"<tr><td><a href='#{esc(slug)}'>{esc(cat)}</a></td><td>{cnt}</td></tr>"
html += f"<tr><td><b>Total</b></td><td><b>{total_articles}</b></td></tr>"

def totals_block(title: str, data: dict, key: str, label_key: str):
    lst = data.get(key, []) if data else []
    total = sum(int(x.get("count", 0)) for x in lst)
    top = ", ".join(f"{esc(x.get(label_key,''))} ({int(x.get('count',0))})" for x in lst[:10]) if lst else "<span class='note'>—</span>"
    return f"""
      <h3 style="margin:12px 0 6px 0">{esc(title)}</h3>
      <div class="kv">
        <div class="muted">Total mentions</div><div><b>{total}</b></div>
      </div>
      <div class="small"><span class="muted">Top:</span> {top}</div>
    """

html += """        </tbody></table>
    </div>
    <div>
      <h3 style="margin:0 0 8px 0">Keyword Mentions</h3>
"""
html += totals_block("Today", kw_tot, "today", "token")
html += totals_block("Week-to-date", kw_tot, "wtd", "token")
html += totals_block("Month-to-date", kw_tot, "mtd", "token")
html += totals_block("Year-to-date", kw_tot, "ytd", "token")

html += """
    </div>
    <div>
      <h3 style="margin:0 0 8px 0">Brand Mentions</h3>
"""
html += totals_block("Today", br_tot, "today", "brand")
html += totals_block("Week-to-date", br_tot, "wtd", "brand")
html += totals_block("Month-to-date", br_tot, "mtd", "brand")
html += totals_block("Year-to-date", br_tot, "ytd", "brand")

html += """
    </div>
  </div>
</section>

<section class="grid2">
"""
# Today charts
html += section_chart_row("Top Keywords — Today", chart_src("keywords_today"), kw_tot.get("today", []), "token")
html += section_chart_row("Brand Mentions — Today", chart_src("brands_today"), br_tot.get("today", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""
# WTD (resets weekly)
html += section_chart_row("Top Keywords — Week-to-date", chart_src("keywords_wtd"), kw_tot.get("wtd", []), "token")
html += section_chart_row("Brand Mentions — Week-to-date", chart_src("brands_wtd"), br_tot.get("wtd", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""
# MTD
html += section_chart_row("Top Keywords — Month-to-date", chart_src("keywords_mtd"), kw_tot.get("mtd", []), "token")
html += section_chart_row("Brand Mentions — Month-to-date", chart_src("brands_mtd"), br_tot.get("mtd", []), "brand")

html += """</section>

<section class="grid2" style="margin-top:16px">
"""
# YTD
html += section_chart_row("Top Keywords — Year-to-date", chart_src("keywords_ytd"), kw_tot.get("ytd", []), "token")
html += section_chart_row("Brand Mentions — Year-to-date", chart_src("brands_ytd"), br_tot.get("ytd", []), "brand")

html += """</section>

<section class="card cat" style="margin-top:18px">
  <h2>Headlines by Category</h2>
"""

# Category sections (anchors)
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

# Archive link at very bottom
html += f"""
</section>

<p class="footer">Last updated {esc(now)} · © {datetime.datetime.utcnow().year} Retail Trends Bot · <a href="archive.html">Daily Summary Archive</a></p>
</div></body></html>
"""

(ROOT / "index.html").write_text(html, encoding="utf-8")
print("✓ Wrote index.html (natural AI summary + WTD labels + archive link)")

# ---------- Build archive.html from data/summaries.json ----------
arch_items = sorted(all_summaries.items(), key=lambda kv: kv[0], reverse=True)
arch = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Summary Archive – Retail Trends</title>
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#0b1220;color:#e5e7eb}
.wrap{max-width:1000px;margin:0 auto;padding:24px 16px}
.card{background:#0e172a;border:1px solid #1f2a44;border-radius:12px;padding:16px;margin-bottom:14px}
h1{margin:0 0 10px 0}
a{color:#fff;text-decoration:none}
a:hover{text-decoration:underline}
.muted{color:#cbd5e1}
</style></head><body><div class="wrap">
<h1>Daily Summary Archive</h1>
<p class="muted">One-paragraph summaries saved each day.</p>
"""
for d, payload in arch_items:
    arch += f'<div class="card"><h3>{d}</h3>\n<ul>'
    for cat in ORDER:
        line = payload.get("by_category", {}).get(cat)
        if line:
            arch += f"<li>{esc(line)}</li>"
    arch += "</ul></div>\n"
arch += '<p><a href="index.html">← Back to dashboard</a></p></div></body></html>'
(ROOT/"archive.html").write_text(arch, encoding="utf-8")
print("✓ Wrote archive.html")


# Persist daily summary
sum_path = DATA / "summaries.json"
all_summaries = {}
if sum_path.exists():
    try:
        all_summaries = json.loads(sum_path.read_text(encoding="utf-8"))
    except Exception:
        all_summaries = {}

if today not in all_summaries:
    all_summaries[today] = {
        "generated_at": now,
        "by_category": {cat: natural_sentence(cat, items) for cat, items in ordered}
    }

sum_path.write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")