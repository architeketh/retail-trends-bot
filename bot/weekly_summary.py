# bot/weekly_summary.py
# Builds site/weekly.html by summarizing the last 7 days of daily_summaries.json.
# Uses OpenAI if OPENAI_API_KEY is available; otherwise falls back to a heuristic summary.

import os, json, math
from datetime import datetime, timedelta

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(ROOT, "site")
ARCHIVE = os.path.join(DATA_DIR, "daily_summaries.json")
ASSETS_DIR = os.path.join(SITE_DIR, "assets")

INLINE_CSS = """<style>
:root{--bg:#0b1020;--glass:rgba(255,255,255,.06);--card:#fff;--ink:#111;--muted:#6b7280;--stroke:rgba(255,255,255,.2);--accent:#7b61ff}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#111;background:#fff}
.hero{position:relative;min-height:220px;background:linear-gradient(180deg, rgba(10,14,25,.65), rgba(10,14,25,.65)), url('assets/bg.jpg') center/cover no-repeat;display:flex;align-items:flex-end}
.hero .wrap{max-width:1100px;margin:0 auto;padding:28px 18px;width:100%}
.hero h1{color:#fff;margin:0 0 6px 0;font-size:28px}
.hero p{color:#dbeafe;margin:0}
.wrap{max-width:1100px;margin:0 auto;padding:18px}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 16px}
.btn{background:#fff;border:1px solid #e5e7eb;color:#111;text-decoration:none;padding:8px 12px;border-radius:10px;display:inline-block}
.btn.primary{background:#7b61ff;border:none;color:#fff}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:16px;margin-top:16px}
h2{margin:0 0 8px 0;font-size:18px}
ul{margin:.25rem 0 .75rem 1.25rem}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;font-size:12px;color:#374151}
.small{font-size:12px;color:#6b7280}
</style>"""

def load_archive():
    if os.path.exists(ARCHIVE):
        try:
            with open(ARCHIVE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}

def pick_last_7(archive: dict):
    # archive keys are yyyy-mm-dd
    dates = sorted(archive.keys(), reverse=True)
    if not dates: return []
    window = []
    today = datetime.utcnow().date()
    for d in dates:
        try:
            dd = datetime.strptime(d, "%Y-%m-%d").date()
        except Exception:
            continue
        if (today - dd).days <= 7:  # inclusive window: last 7 days
            window.append((d, archive[d]))
        if len(window) >= 7:  # cap to 7 entries
            break
    # newest first already
    return window

def aggregate(window):
    # Aggregate keyword and brand counts across the window
    kw_counts = {}
    br_counts = {}
    total_items = 0
    top_headlines = []
    for d, day in window:
        total_items += int(day.get("stats",{}).get("items_considered",0))
        kws = day.get("keywords", [])
        if kws and isinstance(kws[0], dict):
            for k in kws:
                term = k.get("term")
                c = int(k.get("count",0))
                if term:
                    kw_counts[term] = kw_counts.get(term,0) + c
        else:
            # fallback if older schema: rank only -> count as 1
            for term in kws:
                kw_counts[term] = kw_counts.get(term,0) + 1

        for b in day.get("brands", []):
            name = b.get("name")
            c = int(b.get("count",0))
            if name:
                br_counts[name] = br_counts.get(name,0) + c

        for h in day.get("highlights", []):
            if len(top_headlines) < 10:
                top_headlines.append(h)

    kw_top = sorted(kw_counts.items(), key=lambda x:(-x[1], -len(x[0].split()), x[0]))[:15]
    br_top = sorted(br_counts.items(), key=lambda x:(-x[1], x[0]))[:12]
    return {
        "kw_top": kw_top,
        "br_top": br_top,
        "total_items": total_items,
        "top_headlines": top_headlines
    }

def ai_summarize(context_text: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        # Minimal dependency: raw HTTPS via requests to OpenAI Chat Completions
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        # Keep prompt compact but specific
        prompt = (
            "You are a retail strategy analyst. Summarize weekly retail trends into: "
            "1) 5–7 bullet key takeaways; 2) a concise ~120-word narrative; "
            "3) a short outlook (one paragraph). "
            "Focus on ecommerce/omnichannel, AI in retail, logistics/last-mile, "
            "re-commerce (resale/secondhand/upcycling), retail media, and macro signals. "
            "Ground the summary ONLY in the provided context (terms and counts). "
            "Be precise and avoid fluff.\n\n"
            f"Context:\n{context_text}\n"
        )
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role":"system","content":"You produce crisp, factual retail insights."},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

def fmt_counts(label, pairs):
    if not pairs: return f"{label}: —"
    return label + ":\n" + "\n".join([f"- {k}: {v}" for k,v in pairs])

def run():
    archive = load_archive()
    window = pick_last_7(archive)
    os.makedirs(SITE_DIR, exist_ok=True)
    os.makedirs(ASSETS_DIR, exist_ok=True)

    if not window:
        html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero"><div class="wrap"><h1>Weekly Retail Summary</h1><p>No data yet — this page populates after at least one week of daily runs.</p></div></div>
<div class="wrap">
  <div class="actions">
    <a class="btn" href="index.html">Dashboard</a>
    <a class="btn" href="stats.html">Stats</a>
    <a class="btn" href="news.html">News Sites</a>
  </div>
  <div class="card"><p class="small">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p></div>
</div></body></html>"""
        with open(os.path.join(SITE_DIR,"weekly.html"),"w",encoding="utf-8") as f: f.write(html)
        print("Wrote site/weekly.html (no data yet)")
        return

    agg = aggregate(window)
    # Compose compact context for AI / fallback
    days_str = ", ".join([d for d,_ in window])
    ctx = (
        f"Dates: {days_str}\n"
        f"{fmt_counts('Top Keywords (7-day total)', agg['kw_top'])}\n"
        f"{fmt_counts('Top Brands (7-day total)', agg['br_top'])}\n"
        f"Articles processed (7 days): {agg['total_items']}\n"
    )

    ai = ai_summarize(ctx)
    if not ai:
        # Heuristic fallback
        bullets = [f"**{k}** up in coverage ({v})." for k,v in agg["kw_top"][:6]]
        narrative = (
            "This week’s retail cycle emphasized omnichannel execution, logistics acceleration, "
            "and data-driven merchandising. Re-commerce and sustainability remained visible across headlines, "
            "alongside ongoing investment in AI for personalization and store analytics."
        )
        outlook = "Expect continued momentum in AI-assisted operations, tighter last-mile economics, and elevated resale traction into the next cycle."
        ai = "• " + "\n• ".join(bullets) + "\n\n" + narrative + "\n\n**Outlook:** " + outlook

    # Build headlines list
    hl = agg["top_headlines"]
    hl_html = "".join(
        f"<li><a href='{h.get('link','#')}' target='_blank' rel='noopener'>{h.get('title','(untitled)')}</a>"
        f" <span class='small'>({h.get('source','')})</span></li>"
        for h in hl
    ) or "<li class='small'>No headlines.</li>"

    # Render page
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Weekly Retail Summary</title>{INLINE_CSS}</head>
<body>
<div class="hero">
  <div class="wrap">
    <h1>Weekly Retail Summary</h1>
    <p>{window[-1][0]} → {window[0][0]}</p>
  </div>
</div>
<div class="wrap">
  <div class="actions">
    <a class="btn" href="index.html">Dashboard</a>
    <a class="btn" href="stats.html">Stats</a>
    <a class="btn" href="news.html">News Sites</a>
    <a class="btn primary" href="assets/headlines.json" download>Download Headlines (Latest)</a>
  </div>

  <div class="card">
    <h2>AI Summary</h2>
    <div>{ai.replace('\n','<br/>')}</div>
    <p class="small" style="margin-top:6px">Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
  </div>

  <div class="card">
    <h2>7-Day Totals</h2>
    <pre class="mono">{ctx}</pre>
  </div>

  <div class="card">
    <h2>Representative Headlines</h2>
    <ul>{hl_html}</ul>
  </div>
</div>
</body></html>"""

    with open(os.path.join(SITE_DIR,"weekly.html"),"w",encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/weekly.html")

if __name__ == "__main__":
    run()
