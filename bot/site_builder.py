# bot/site_builder.py
import pathlib, datetime, json

DATA = pathlib.Path("data")
SITE = pathlib.Path("site")
SITE.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# Load fetched headlines
articles = []
f = DATA / "headlines.json"
if f.exists():
    try:
        obj = json.loads(f.read_text(encoding="utf-8"))
        articles = obj.get("articles", [])
    except Exception as e:
        print("WARN: could not read headlines.json:", e)

# Build HTML
html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Retail Trends Bot</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
    .card {{ max-width: 800px; margin: auto; padding: 1.5rem;
             border: 1px solid #ccc; border-radius: 10px; }}
    h1,h2 {{ margin-top: 0 }}
    ul {{ padding-left: 1.2rem }}
    li {{ margin-bottom: 6px }}
    .muted {{ color: #666; font-size: 0.9em }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Retail Trends Bot</h1>
    <p><b>Last updated:</b> {now}</p>
  </div>
  <div class="card">
    <h2>Latest Headlines</h2>
    <ul>
"""

if articles:
    for art in articles[:10]:  # top 10 headlines
        title = art.get("title", "Untitled")
        link = art.get("link", "#")
        src = art.get("source", "")
        html += f'<li><a href="{link}" target="_blank">{title}</a>'
        if src:
            html += f' <span class="muted">({src})</span>'
        html += "</li>\n"
else:
    html += "<li class='muted'>No articles yet. Run fetch.py first.</li>"

html += """
    </ul>
  </div>
</body>
</html>
"""

(SITE / "index.html").write_text(html, encoding="utf-8")
print("Wrote site/index.html")
