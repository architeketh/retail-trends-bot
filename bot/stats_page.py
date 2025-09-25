# bot/stats_page.py
# Builds site/stats.html styled to match index.html

import os, json
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(ROOT, "site")

INLINE_CSS = """<style>
body{font-family:system-ui;background:#fff;color:#111;padding:2rem;max-width:800px;margin:auto}
h1{margin:0 0 1rem 0}
.card{border:1px solid #eee;border-radius:8px;padding:1rem;margin-top:1rem}
.btn{background:#f8fafc;padding:6px 10px;border:1px solid #ccc;border-radius:8px;text-decoration:none;color:#111}
.btn.primary{background:#2E93fA;color:#fff}
</style>"""

def run():
    hist_file = os.path.join(DATA_DIR, "history.json")
    if not os.path.exists(hist_file):
        print("No history.json yet")
        return

    with open(hist_file, "r", encoding="utf-8") as f:
        history = json.load(f)

    if not history:
        return

    start_date = history[0]["date"]
    days = len(history)
    weeks = days // 7
    months = days // 30
    total_items = sum(h.get("items", 0) for h in history)

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Retail Trends – Stats</title>{INLINE_CSS}</head>
<body>
<h1>Retail Trends – Data Collection Stats</h1>
<div class="card">
  <p>Tracking since <b>{start_date}</b></p>
  <ul>
    <li><b>{days}</b> days</li>
    <li><b>{weeks}</b> weeks (approx.)</li>
    <li><b>{months}</b> months (approx.)</li>
    <li><b>{total_items}</b> total articles processed</li>
  </ul>
</div>
<p style="margin-top:1rem;"><a class="btn" href="index.html">← Back to Dashboard</a></p>
<p style="font-size:12px;color:#666;">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""

    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "stats.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/stats.html")

if __name__ == "__main__":
    run()
