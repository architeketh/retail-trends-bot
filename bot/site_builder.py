# bot/site_builder.py
import pathlib, json, datetime, re, random
from collections import Counter

ROOT = pathlib.Path(".")
DATA, ASSETS = ROOT / "data", ROOT / "assets"
DATA.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

def esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
today = datetime.date.today().isoformat()

# -------- Load categorized (optional) --------
cats = {}
for p in (ASSETS/"categorized.json", DATA/"categorized.json"):
    if p.exists():
        try:
            cats = json.loads(p.read_text(encoding="utf-8")); break
        except Exception:
            cats = {}
            break

# -------- Load totals written by charts.py --------
kw_tot = {}
br_tot = {}
try:
    if (ASSETS/"kw_totals.json").exists():
        kw_tot = json.loads((ASSETS/"kw_totals.json").read_text(encoding="utf-8"))
    if (ASSETS/"brand_totals.json").exists():
        br_tot = json.loads((ASSETS/"brand_totals.json").read_text(encoding="utf-8"))
except Exception:
    kw_tot = {}; br_tot = {}

# -------- Build TODAY signals (history -> totals fallback) --------
today_kw = []
today_br = []
try:
    hk = json.loads((DATA/"history_keywords.json").read_text(encoding="utf-8"))
    hb = json.loads((DATA/"history_brands.json").read_text(encoding="utf-8"))
    if today in hk: today_kw = sorted(hk[today].items(), key=lambda kv: kv[1], reverse=True)
    if today in hb: today_br = sorted(hb[today].items(), key=lambda kv: kv[1], reverse=True)
except Exception:
    pass

if not today_kw:
    for row in kw_tot.get("today", []):
        today_kw.append((row.get("token",""), int(row.get("count",0))))
    today_kw.sort(key=lambda kv: kv[1], reverse=True)

if not today_br:
    for row in br_tot.get("today", []):
        today_br.append((row.get("brand",""), int(row.get("count",0))))
    today_br.sort(key=lambda kv: kv[1], reverse=True)

TOP_TODAY_KW = [k for k,_ in today_kw[:8] if k]
TOP_TODAY_BR = [b for b,_ in today_br[:8] if b]

# -------- Natural language sentence with rotation + robust fallback --------
lead_phrases = [
    "Today's retail pulse spotlights",
    "Retail headlines today center on",
    "Across the sector, attention turns to",
    "In the latest cycle, momentum builds around",
    "This session’s stories highlight",
]
brand_phrases = [
    "with strong mentions of",
    "driven by activity from",
    "as major players like",
    "showing traction for",
    "where brands such as",
]
trend_phrases = [
    "shaping themes in",
    "pushing trends across",
    "influencing moves in",
    "reshaping focus on",
    "driving activity in",
]
random.seed(today)  # stable phrasing for the day

brands_txt = ", ".join(TOP_TODAY_BR[:3]) if TOP_TODAY_BR else ""
terms_txt  = ", ".join(TOP_TODAY_KW[:3]) if TOP_TODAY_KW else ""

sentence = ""
if brands_txt and terms_txt:
    sentence = f"{random.choice(lead_phrases)} {brands_txt} {random.choice(brand_phrases)} {terms_txt}, {random.choice(trend_phrases)} retail, eCommerce, and AI."
elif brands_txt:
    sentence = f"{random.choice(lead_phrases)} {brands_txt}, {random.choice(trend_phrases)} retail, eCommerce, and AI."
elif terms_txt:
    sentence = f"{random.choice(lead_phrases)} {terms_txt}, {random.choice(trend_phrases)} retail, eCommerce, and AI."

# FINAL BACKSTOP: build a sentence from category counts so it's never blank
if not sentence:
    # compute category counts from categorized list if available
    ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
    cat_counts = [(c, len(cats.get(c, []))) for c in ORDER if cats.get(c)]
    cat_counts = sorted(cat_counts, key=lambda x: x[1], reverse=True)
    if cat_counts:
        topbits = ", ".join([f"{c} ({n})" for c,n in cat_counts[:3]])
        sentence = f"Today’s coverage spans {topbits}, reflecting the latest shifts across the retail landscape."
    else:
        sentence = "Today’s coverage is light; updates will appear after the next successful fetch."

daily_summary_sentence = sentence

# -------- Persist summaries.json (append once; never wipe history) --------
sum_path = DATA/"summaries.json"
all_summaries = {}
if sum_path.exists():
    try:
        all_summaries = json.loads(sum_path.read_text(encoding="utf-8"))
    except Exception:
        all_summaries = {}

if today not in all_summaries:
    all_summaries[today] = {
        "generated_at": now,
        "summary": daily_summary_sentence,
        "top_keywords": TOP_TODAY_KW,
        "top_brands": TOP_TODAY_BR,
    }
else:
    # if a previous run wrote an empty summary, backfill it (do not alter non-empty text)
    if not all_summaries[today].get("summary"):
        all_summaries[today]["summary"] = daily_summary_sentence
        all_summaries[today]["generated_at"] = now

sum_path.write_text(json.dumps(all_summaries, ensure_ascii=False, indent=2), encoding="utf-8")

# -------- Helpers for HTML --------
def chart_src(name: str) -> str:
    for ext in ("svg","png"):
        p = ASSETS/f"{name}.{ext}"
        if p.exists(): return f"assets/{name}.{ext}"
    return ""

def nice_list(items, label_key, limit=10):
    if not items: return "<span class='note'>—</span>"
    return ", ".join(f"{esc(x.get(label_key,''))} ({int(x.get('count',0))})" for x in items[:limit])

def latest_hero():
    img = ROOT/"assets"/"hero"/"latest.jpg"
    meta = ROOT/"assets"/"hero"/"latest.json"
    if img.exists():
        info = {}
        if meta.exists():
            try: info = json.loads(meta.read_text(encoding="utf-8"))
            except Exception: info = {}
        return "assets/hero/latest.jpg", info
    return "", {}

ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]

# -------- Build index.html --------
html = []
html.append("<!doctype html><html lang='en'><head>")
html.append("<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>")
html.append("<title>Retail Trends – Dashboard</title>")
html.append("""
<style>
:root{--bg:#0b1220;--card:#0e172a;--text:#e5e7eb;--muted:#cbd5e1;--stroke:#1f2a44;--chip:#1e293b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.45}
a,a:visited{color:#fff;text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1200px;margin:0 auto;padding:22px 14px}
@media(min-width:768px){.wrap{padding:26px 18px}}
.hero{border:1px solid var(--stroke);border-radius:16px;padding:22px;margin-bottom:18px;
       background:linear-gradient(135deg,#0ea5e9 0%, #7c3aed 40%, #22c55e 75%, #ef4444 100%);}
.hero h1{margin:0 0 8px 0;font-size:28px;letter-spacing:.4px}
@media(min-width:768px){.hero h1{font-size:32px}}
.hero p{margin:0;color:#f1f5f9}
.grid2{display:grid;gap:12px} @media(min-width:900px){.grid2{grid-template-columns:1fr 1fr;gap:16px}}
.card{background:var(--card);border:1px solid var(--stroke);border-radius:12px;padding:14px}
@media(min-width:768px){.card{padding:16px}}
h2{margin:0 0 10px 0;font-size:18px}
.muted{color:var(--muted)} .small{font-size:12px} .note{color:var(--muted)}
ul{margin:0;padding-left:18px} li{margin:6px 0}
img{max-width:100%;border-radius:12px}
.badge{display:inline-block;background:#1f2937;color:#a7f3d0;border:1px solid #1f2a44;border-radius:999px;padding:2px 8px;font-size:12px;margin-left:8px}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{background:#1e293b;color:#fff;border:1px solid #1f2a44;padding:6px 10px;border-radius:999px;font-size:13px}
.totals{display:grid;gap:12px} @media(min-width:900px){.totals{grid-template-columns:1.3fr 1fr 1fr}}
.kv{display:grid;grid-template-columns:1fr auto;gap:8px}
.table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}
.table th,.table td{border-bottom:1px solid var(--stroke);padding:8px 8px;text-align:left}
.table th{color:#e2e8f0;font-weight:600}
.anchor{scroll-margin-top:90px} .card a,.table a,.cat a{color:#fff}
.footer{margin-top:16px;color:var(--muted);font-size:12px}
</style>""")
html.append("</head><body><div class='wrap'>")

# Hero with optional image
hero_src, hero_meta = latest_hero()
html.append("<section class='hero'>")
html.append("<h1>Retail Trends</h1>")
html.append("<p>Daily retail headlines with week-to-date, month-to-date, and year-to-date trends.</p>")
html.append("<div class='chips'>")
for name in ORDER:
    if cats.get(name):
        slug = "cat-" + name.lower().replace(" ", "-")
        html.append(f"<span class='chip'><a href='#{esc(slug)}'>{esc(name)}</a></span>")
html.append("</div>")
if hero_src:
    html.append(f"<img src='{hero_src}' alt='Headline image' style='margin-top:10px'/>")
    t = esc(hero_meta.get("title","")); s = esc(hero_meta.get("source","")); u = esc(hero_meta.get("article_url",""))
    if u and (t or s):
        html.append(f"<div class='small muted' style='margin-top:6px'>Image from <a href='{u}' target='_blank' rel='noopener'>{t or s}</a></div>")
html.append("</section>")

# Daily AI Summary block
html.append("<section class='card'><h2>Daily AI Summary</h2>")
html.append(f"<p>{esc(daily_summary_sentence)}</p></section>")

# Totals
def nice_list(items, label_key, limit=10):
    if not items: return "<span class='note'>—</span>"
    return ", ".join(f"{esc(x.get(label_key,''))} ({int(x.get('count',0))})" for x in items[:limit])


def totals_block(title: str, data: dict, key: str, label_key: str):
    lst = data.get(key, []) if data else []
    total = sum(int(x.get('count',0)) for x in lst)
    top = nice_list(lst, label_key)
    return (f"<h3 style='margin:12px 0 6px 0'>{esc(title)}</h3>" +
            f\"<div class='kv'><div class='muted'>Total mentions</div><div><b>{total}</b></div></div>\" +
            f\"<div class='small'><span class='muted'>Top:</span> {top}</div>\")

# Category totals table
ORDER = ["Retail","eCommerce","AI","Supply Chain","Big Box","Luxury","Vintage","Other"]
ordered = [(k, cats.get(k, [])) for k in ORDER if cats.get(k)] + [(k, v) for k, v in cats.items() if k not in ORDER]

html.append("<section class='card'><h2>Totals</h2><div class='totals'>")
html.append("<div><h3 style='margin:0 0 8px 0'>Articles by Category</h3><table class='table'><thead><tr><th>Category</th><th>Articles</th></tr></thead><tbody>")
total_articles = 0
for cat, items in ordered:
    cnt = len(items); total_articles += cnt
    slug = "cat-" + cat.lower().replace(" ", "-")
    html.append(f"<tr><td><a href='#{esc(slug)}'>{esc(cat)}</a></td><td>{cnt}</td></tr>")
html.append(f"<tr><td><b>Total</b></td><td><b>{total_articles}</b></td></tr></tbody></table></div>")
html.append("<div><h3 style='margin:0 0 8px 0'>Keyword Mentions</h3>")
html.append(totals_block("Today", kw_tot, "today", "token"))
html.append(totals_block("Week-to-date", kw_tot, "wtd", "token"))
html.append(totals_block("Month-to-date", kw_tot, "mtd", "token"))
html.append(totals_block("Year-to-date", kw_tot, "ytd", "token"))
html.append("</div><div><h3 style='margin:0 0 8px 0'>Brand Mentions</h3>")
html.append(totals_block("Today", br_tot, "today", "brand"))
html.append(totals_block("Week-to-date", br_tot, "wtd", "brand"))
html.append(totals_block("Month-to-date", br_tot, "mtd", "brand"))
html.append(totals_block("Year-to-date", br_tot, "ytd", "brand"))
html.append("</div></div></section>")

# Charts rows
def chart_row(title, key, lst, label_key):
    src = chart_src(key)
    tl = nice_list(lst, label_key) if lst else ""
    right = f"<div class='muted small'>Top: {tl}</div>" if tl else ""
    body = f"<img src='{src}' alt='{esc(title)}'/>" if src else "<p class='note'>No chart yet.</p>"
    return f"<article class='card'><h2>{esc(title)}</h2><div>{body}</div>{right}</article>"

html.append("<section class='grid2'>")
html.append(chart_row("Top Keywords — Today","keywords_today", kw_tot.get("today", []),"token"))
html.append(chart_row("Brand Mentions — Today","brands_today", br_tot.get("today", []),"brand"))
html.append("</section><section class='grid2' style='margin-top:16px'>")
html.append(chart_row("Top Keywords — Week-to-date","keywords_wtd", kw_tot.get("wtd", []),"token"))
html.append(chart_row("Brand Mentions — Week-to-date","brands_wtd", br_tot.get("wtd", []),"brand"))
html.append("</section><section class='grid2' style='margin-top:16px'>")
html.append(chart_row("Top Keywords — Month-to-date","keywords_mtd", kw_tot.get("mtd", []),"token"))
html.append(chart_row("Brand Mentions — Month-to-date","brands_mtd", br_tot.get("mtd", []),"brand"))
html.append("</section><section class='grid2' style='margin-top:16px'>")
html.append(chart_row("Top Keywords — Year-to-date","keywords_ytd", kw_tot.get("ytd", []),"token"))
html.append(chart_row("Brand Mentions — Year-to-date","brands_ytd", br_tot.get("ytd", []),"brand"))
html.append("</section>")

# Headlines by category
html.append("<section class='card cat' style='margin-top:18px'><h2>Headlines by Category</h2>")
if ordered:
    for cat, items in ordered:
        slug = "cat-" + cat.lower().replace(" ", "-")
        html.append(f"<h3 id='{esc(slug)}' class='anchor'>{esc(cat)} <span class='badge'>{len(items)}</span></h3><ul>")
        for a in items[:12]:
            t = esc(a.get("title") or "(untitled)")
            l = esc(a.get("link") or "#")
            s = esc(a.get("source") or "")
            span = f" <span class='muted'>({s})</span>" if s else ""
            html.append(f"<li><a href='{l}' target='_blank' rel='noopener'>{t}</a>{span}</li>")
        html.append("</ul>")
else:
    html.append("<p class='note'>No categorized headlines yet.</p>")
html.append(f"</section><p class='footer'>Last updated {esc(now)} · © {datetime.datetime.utcnow().year} Retail Trends Bot · <a href='archive.html'>Daily Summary Archive</a></p>")
html.append("</div></body></html>")

(ROOT/"index.html").write_text("".join(html), encoding="utf-8")
print("✓ Wrote index.html")

# -------- Build archive.html from saved summaries --------
try:
    saved = json.loads((DATA/"summaries.json").read_text(encoding="utf-8"))
except Exception:
    saved = {}

arch = []
arch.append("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>")
arch.append("<title>Daily Summary Archive – Retail Trends</title>")
arch.append("""<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#0b1220;color:#e5e7eb}
.wrap{max-width:1000px;margin:0 auto;padding:24px 16px}
.card{background:#0e172a;border:1px solid #1f2a44;border-radius:12px;padding:16px;margin-bottom:14px}
a{color:#fff;text-decoration:none} a:hover{text-decoration:underline}
.muted{color:#cbd5e1}
</style></head><body><div class='wrap'><h1>Daily Summary Archive</h1><p class='muted'>One-paragraph summaries saved each day.</p>""")
for d, payload in sorted(saved.items(), key=lambda kv: kv[0], reverse=True):
    line = payload.get("summary","")
    arch.append(f"<div class='card'><h3>{esc(d)}</h3><p>{esc(line)}</p></div>")
arch.append("<p><a href='index.html'>← Back to dashboard</a></p></div></body></html>")
(ROOT/"archive.html").write_text("".join(arch), encoding="utf-8")
print("✓ Wrote archive.html")
