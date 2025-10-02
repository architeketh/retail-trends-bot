# bot/site_builder.py
import pathlib, json, datetime

ROOT = pathlib.Path(".")
DATA, ASSETS = ROOT/"data", ROOT/"assets"
DATA.mkdir(exist_ok=True); ASSETS.mkdir(exist_ok=True)

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def esc(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

# Load headlines
arts = []
hjson = DATA/"headlines.json"
if hjson.exists():
    arts = json.loads(hjson.read_text()).get("articles", [])

# Load or create summaries
sfile = DATA/"summaries.json"
summaries = json.loads(sfile.read_text()) if sfile.exists() else {}
today = datetime.date.today().isoformat()
if today not in summaries:
    # Basic AI-ish summary: just count categories and brands
    counts = len(arts)
    brands = sum(1 for a in arts if "Amazon" in a.get("title",""))
    text = f"On {today}, {counts} retail articles were tracked. Amazon appeared in {brands} headlines. Other top trends are reflected in the keyword and brand charts."
    summaries[today] = text
    sfile.write_text(json.dumps(summaries, indent=2))

# Build main index.html
html = f"""<!doctype html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Retail Trends Dashboard</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#fff;color:#111}}
.wrap{{max-width:1100px;margin:0 auto;padding:20px}}
.card{{border:1px solid #ddd;border-radius:10px;padding:16px;margin-bottom:18px}}
h1{{margin:0}} h2{{margin-top:0}}
img{{max-width:100%;}}
</style></head><body><div class="wrap">
<h1>Retail Trends – Dashboard</h1>
<p><i>Last updated {esc(now)}</i></p>

<div class="card"><h2>Daily Summary</h2>
<p>{esc(summaries[today])}</p>
<p><a href="archive.html">View Archive</a></p></div>

<div class="card"><h2>Top Keywords (Today)</h2>
<img src="assets/keywords.png"/></div>
<div class="card"><h2>Brand Mentions (Today)</h2>
<img src="assets/brands.png"/></div>
<div class="card"><h2>Top Keywords (7-day)</h2>
<img src="assets/keywords_weekly.png"/></div>
<div class="card"><h2>Brand Mentions (7-day)</h2>
<img src="assets/brands_weekly.png"/></div>

<div class="card"><h2>Latest Headlines</h2>
<ul>""" 
for a in arts[:15]:
    html += f"<li><a href='{esc(a.get('link','#'))}' target='_blank'>{esc(a.get('title'))}</a></li>"
html += "</ul></div></div></body></html>"

(ROOT/"index.html").write_text(html, encoding="utf-8")

# Build archive.html
arch = """<!doctype html><html><head><meta charset="utf-8"><title>Summary Archive</title></head><body>
<h1>Daily Summaries Archive</h1><ul>"""
for d,txt in sorted(summaries.items(), reverse=True):
    arch += f"<li><b>{d}</b>: {esc(txt)}</li>"
arch += "</ul><p><a href='index.html'>Back to dashboard</a></p></body></html>"
(ROOT/"archive.html").write_text(arch, encoding="utf-8")

print("✓ Built index.html and archive.html")
