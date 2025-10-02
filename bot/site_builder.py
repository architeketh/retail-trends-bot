# bot/site_builder.py
import pathlib, datetime

SITE = pathlib.Path("site")
SITE.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

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
  </style>
</head>
<body>
  <div class="card">
    <h1>Retail Trends Bot</h1>
    <p><b>Last updated:</b> {now}</p>
    <p>This is a clean reset. The bot is working — content will be added step by step.</p>
  </div>
</body>
</html>"""

(SITE / "index.html").write_text(html, encoding="utf-8")
print("Wrote site/index.html")
