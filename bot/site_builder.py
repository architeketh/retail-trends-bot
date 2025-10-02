# bot/site_builder.py
import pathlib, datetime, json

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# Load headlines (array for fast render)
articles = []
src_json = DATA / "headlines.json"
if src_json.exists():
    try:
        obj = json.loads(src_json.read_text(encoding="utf-8"))
        articles = obj.get("articles", [])
    except Exception as e:
        print("WARN: could not parse data/headlines.json:", e)

# Prepare a light JSON for the front-end (optional)
(front_json := ASSETS / "headlines.json").write_text(
    json.dumps(
        [{"title": a.get("title",""), "link": a.get("link",""), "source": a.get("source","")} for a in articles],
        ensure_ascii=False, indent=2
    ),
    encoding="utf-8"
)
print(f"✓ Wrote {front_json.relative_to(ROOT)} ({len(articles)} items)")

kw_img = (ASSETS / "keywords.png").exists()
br_img = (ASSETS / "brands.png").exists()

def esc(s: str) -> str:
    return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Retail Trends – Dashboard</title>
<style>
  :root{{--bg:#fff;--text:#111;--card:#fff;--stroke:#e5e7eb;--btn:#f8fafc;--primary:#2E93fA}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
  .wrap{{max-width:1100px;margin:0 auto;padding:28px 18px}}
  .header{{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}}
  .title{{margin:0;font-size:28px}}
  .desc{{margin:4px 0 0;color:#4b5563}}
  .actions a,.actions button{{display:inline-block;margin-left:8px;padding:8px 12px;border-radius:10px;border:1px solid var(--stroke);background:var(--btn);color:#111;text-decoration:none;cursor:pointer}}
  .primary{{background:var(--primary);color:#fff;border:none}}
  .grid{{display:grid;gap:16px;margin-top:16px}}
  @media(min-width:900px){{.grid{{grid-template-columns:1fr 1fr}}}}
  .card{{background:var(--card);border:1px solid var(--stroke);border-radius:12px;padding:16px}}
  h2{{margin:0 0 10px 0;font-size:18px}}
  .muted{{color:#6b7280}}
  ul{{margin:0;padding-left:18px}}
  img{{max-width:100%;border-radius:8px}}
  details{{margin-top:12px}}
  .note{{color:#6b7280;font-size:14px}}
  .footer{{margin-top:18px;color:#6b7280;font-size:12px}}
  .pill{{display:inline-block; padding:2px 8px; background:#eef2ff; color:#4338ca; border-radius:999px; font-size:12px; margin-left:6px}}
</style>
</head>
<body>
<div class="wrap">
  <header class="header">
    <div>
      <h1 class="title">Retail Trends – Dashboard</h1>
      <p class="desc">Daily retail headlines, keywords & brand mentions</p>
    </div>
    <div class="actions">
      <a href="assets/headlines.json" download>JSON</a>
      <button class="primary" onclick="location.reload()">Refresh</button>
    </div>
  </header>

  <section class="grid">
    <article class="card">
      <h2>Top Keywords <span class="pill">Latest Run</span></h2>
      <div id="kw">{"<img src='assets/keywords.png' alt='Top Keywords'/>" if kw_img else "<p class='note'>Run charts step to generate keywords.png.</p>"}</div>
    </article>
    <article class="card">
      <h2>Brand Mentions <span class="pill">Latest Run</span></h2>
      <div id="brands">{"<img src='assets/brands.png' alt='Brand Mentions'/>" if br_img else "<p class='note'>Run charts step to generate brands.png.</p>"}</div>
    </article>
  </section>

  <section class="card" style="margin-top:16px">
    <h2>Latest Headlines</h2>
    <ul>
"""

if articles:
    for h in articles[:12]:
        t = esc(h.get("title") or "(untitled)")
        l = esc(h.get("link") or "#")
        s = esc(h.get("source") or "")
        html += f'      <li><a href="{l}" target="_blank" rel="noopener">{t}</a>'
        if s: html += f' <span class="muted">({s})</span>'
        html += "</li>\n"
else:
    html += "      <li class='note'>No headlines yet. Will appear after the fetch step runs successfully.</li>\n"

html += f"""    </ul>
  </section>

  <details class="card">
    <summary><b>About</b></summary>
    <p class="note">Last updated: {esc(now)}. This dashboard refreshes automatically every 12 hours.</p>
    <p class="note">Headlines are mirrored to <code>assets/headlines.json</code> for light front-end rendering.</p>
  </details>

  <p class="footer">© {datetime.datetime.utcnow().year} Retail Trends Bot</p>
</div>

<div id="visitor-count" style="position:fixed;right:12px;bottom:12px;background:#fff;border:1px solid #e5e7eb;border-radius:999px;padding:6px 10px;font-size:12px;color:#374151">Visitors: …</div>
<script>
  fetch('https://api.countapi.xyz/hit/architeketh/retail-trends')
    .then(res => res.json())
    .then(data => {{ document.getElementById('visitor-count').innerText = "Visitors: " + data.value; }})
    .catch(()=>{{}});
</script>
</body>
</html>
"""

(ROOT / "index.html").write_text(html, encoding="utf-8")
print("✓ Wrote index.html at repo root")
