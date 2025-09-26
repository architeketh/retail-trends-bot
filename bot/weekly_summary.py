# bot/weekly_summary.py
# Weekly page with matching hero/noise, KPI chips, and 7-day totals.
# Always writes site/weekly.html. Optional AI summary if OPENAI_API_KEY is present.

import os, json
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(ROOT, "site")
ARCHIVE = os.path.join(DATA_DIR, "daily_summaries.json")

INLINE_CSS = """<style>
:root{--stroke:#e5e7eb;--primary:#7b61ff;--chipbg:#f3f4f6}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;background:#fff}
.hero{position:relative;min-height:240px;background:
  linear-gradient(180deg, rgba(10,14,25,.60), rgba(10,14,25,.60)),
  url('assets/bg.jpg') center/cover no-repeat;}
.hero::after{
  content:"";position:absolute;inset:0;pointer-events:none;opacity:.28;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='2' stitchTiles='stitch'/><feColorMatrix type='saturate' values='0'/><feComponentTransfer><feFuncA type='table' tableValues='0 0.6'/></feComponentTransfer></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  background-size:160px 160px;
}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.hero .wrap{padding:28px 18px;position:relative;z-index:1}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 16px}
.btn{background:#fff;border:1px solid var(--stroke);color:#111;text-decoration:none;padding:8px 12px;border-radius:12px;display:inline-block}
.kpis{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.kpi{display:inline-flex;align-items:center;gap:8px;padding:8px 12px;border-radius:999px;background:var(--chipbg);color:#111;border:1px solid var(--stroke)}
.kpi b{font-weight:700}
.card{background:#fff;border:1px solid var(--stroke);border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 8px 0;font-size:18px}
.small{font-size:12px;color:#6b7280}
ul{margin:.25rem 0 .75rem 1.25rem}
</style>"""

def load_archive() -> dict:
    if os.path.exists(ARCHIVE):
        try:
            with open(ARCHIVE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def last7(archive: dict):
    # newest first
    dates = sorted(archive.keys(), reverse=True)[:7]
    return [(d, archive[d]) for d in dates]

def aggregate(window):
    # Aggregate 7-day totals for keywords/brands; keep a few headlines from newest day
    kw = {}
    br = {}
    items = 0
    headlines = []
    newest = window[0][1] if window else {}
    for d, day in window:
        items += int(day.get("stats", {}).get("items_considered", 0))
        # keywords (support both new dict format and old string list)
        for k in day.get("keywords", []):
            if isinstance(k, dict):
                term = k.get("term"); c = int(k.get("count", 0))
            else:
                term, c = k, 1
            if term:
                kw[term] = kw.get(term, 0) + c
        # brands
        for b in day.get("brands", []):
            name = b.get("name"); c = int(b.get("count", 0))
            if name:
                br[name] = br.get(name, 0) + c
    # top lists
    kw_top = sorted(kw.items(), key=lambda x: (-x[1], -len(x[0].split()), x[0]))
    br_top = sorted(br.items(), key=lambda x: (-x[1], x[0]))
    headlines = newest.get("highlights", [])[:10] if newest else []
    return items, kw_top, br_top, headlines

def ai_summary(kw_top, br_top, items, span_text):
    # Optional AI summary if OPENAI_API_KEY is provided; safe fallback otherwise
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return (
            f"Covering {span_text}, weekly coverage concentrated on omnichannel, logistics, AI-in-retail, "
            f"and re-commerce. Expect continued investment in personalization, last-mile efficiency, "
            f"and circular retail experiments into next week."
        )
    try:
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        top_kw = ", ".join([f"{k} ({v})" for k, v in kw_top[:8]]) or "—"
        top_br = ", ".join([f"{b} ({v})" for b, v in br_top[:8]]) or "—"
        prompt = (
            "You are a retail strategy analyst. Produce a crisp weekly retail summary with:"
            " 1) 5–7 bullet key takeaways; 2) a ~120-word narrative; 3) a brief outlook."
            " Focus on ecommerce/omnichannel, AI, logistics/last-mile, re-commerce (resale), retail media,"
            " and macro indicators. Use ONLY the data below.\n\n"
            f"Date span: {span_text}\n"
            f"Articles processed: {items}\n"
            f"Top Keywords (7-day totals): {top_kw}\n"
            f"Top Brands (7-day totals): {top_br}\n"
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role":"system","content":"You produce crisp, factual retail insights."},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 650,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return (
            f"{span_text}: Omnichannel, logistics, AI-in-retail and re-commerce dominated coverage. "
            f"Retailers continue to optimize last-mile and personalization while experimenting with circular models."
        )

def build_page(span_text, items, kw_top, br_top, headlines, ai_text):
    kw_html = "".join(f"<li>{k} — <b>{v}</b></li>" for k, v in kw_top[:15]) or "<li class='small'>No keywords.</li>"
    br_html = "".join(f"<li>{b} — <b>{v}</b></li>" for b, v in br_top[:12]) or "<li class='small'>No brands.</li>"
    hl_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title','(untitled)')}</a> "
        f"<span class='small'>({h.get('source','')})</span></li>"
        for h in headlines
    ) or "<li class='small'>No headlines.</li>"

    kpis = []
    if items: kpis.append(f"<span class='kpi'><b>{items}</b> Articles</span>")
    if kw_top: kpis.append(f"<span class='kpi'><b>{kw_top[0][1]}</b> “{kw_top[0][0]}”</span>")
    if br_top: kpis.append(f"<span class='kpi'><b>{br_top[0][1]}</b> {br_top[0][0]}</span>")
    kpi_html = f"<div class='kpis'>{''.join(kpis)}</div>" if kpis else ""

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>Weekly Retail Summary</h1>
    <p>{span_text}</p>
    {kpi_html}
    <div class="actions" style="margin-top:10px">
      <a class="btn" href="index.html">Dashboard</a>
      <a class="btn" href="news.html">News Sites</a>
      <a class="btn" href="stats.html">Stats</a>
    </div>
  </div>
</div>

<div class="wrap">
  <div class="card">
    <h2>AI Summary</h2>
    <div>{ai_text.replace("\n","<br/>")}</div>
    <p class="small" style="margin-top:6px">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
  </div>

  <div class="card">
    <h2>Top Keywords (7-day totals)</h2>
    <ul>{kw_html}</ul>
  </div>

  <div class="card">
    <h2>Top Brands (7-day totals)</h2>
    <ul>{br_html}</ul>
  </div>

  <div class="card">
    <h2>Representative Headlines</h2>
    <ul>{hl_html}</ul>
  </div>
</div>
</body></html>"""

def run():
    os.makedirs(SITE_DIR, exist_ok=True)
    archive = load_archive()
    window = last7(archive)

    if not window:
        # Write a graceful empty page (no 404 ever)
        html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero"><div class="wrap">
  <h1>Weekly Retail Summary</h1>
  <p>No archive yet — this page will populate after the first daily run.</p>
  <div class="actions">
    <a class="btn" href="index.html">Dashboard</a>
    <a class="btn" href="news.html">News Sites</a>
    <a class="btn" href="stats.html">Stats</a>
  </div>
</div></div>
<div class="wrap"><div class="card"><p class="small">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p></div></div>
</body></html>"""
        with open(os.path.join(SITE_DIR, "weekly.html"), "w", encoding="utf-8") as f:
            f.write(html)
        print("Wrote site/weekly.html (no data yet)")
        return

    # Build date span text
    span_text = f"{window[-1][0]} → {window[0][0]}"
    items, kw_top, br_top, headlines = aggregate(window)
    ai_text = ai_summary(kw_top, br_top, items, span_text)

    page = build_page(span_text, items, kw_top, br_top, headlines, ai_text)
    with open(os.path.join(SITE_DIR, "weekly.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("Wrote site/weekly.html")

if __name__ == "__main__":
    run()
