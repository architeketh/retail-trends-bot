# bot/stats_page.py
# Builds site/stats.html with summary + history chart + 7-day avg.
# Always writes a page, even if no history yet.

import os, json
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
SITE_DIR = os.path.join(ROOT, "site")
ASSETS_DIR = os.path.join(SITE_DIR, "assets")

INLINE_CSS = """<style>
body{font-family:system-ui;background:#fff;color:#111;padding:2rem;max-width:900px;margin:auto}
h1{margin:0 0 1rem 0}
.card{border:1px solid #eee;border-radius:8px;padding:1rem;margin-top:1rem}
.btn{background:#f8fafc;padding:6px 10px;border:1px solid #ccc;border-radius:8px;
     text-decoration:none;color:#111;display:inline-block;margin-right:6px}
.btn.primary{background:#2E93fA;color:#fff}
img{max-width:100%;border-radius:6px}
.note{color:#666;font-size:14px}
</style>"""

def build_chart(history, outpath):
    dates = [h["date"] for h in history]
    items = [h.get("items", 0) for h in history]

    # 7-day rolling average
    rolling = []
    for i in range(len(items)):
        window = items[max(0, i-6):i+1]
        rolling.append(sum(window)/len(window))

    plt.figure(figsize=(9,4), dpi=120)
    plt.plot(dates, items, marker="o", linestyle="-", color="#2E93fA", label="Daily")
    plt.plot(dates, rolling, linestyle="--", color="#FF9800", linewidth=2, label="7-day avg")
    plt.title("Articles Processed Per Day")
    plt.xlabel("Date"); plt.ylabel("Articles")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.legend(); plt.tight_layout()
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    plt.savefig(outpath, bbox_inches="tight"); plt.close()

def run():
    os.makedirs(SITE_DIR, exist_ok=True)

    hist_file = os.path.join(DATA_DIR, "history.json")
    history = []
    if os.path.exists(hist_file):
        try:
            with open(hist_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    start_date = "—"
    days = weeks = months = total_items = 0
    chart_block = "<p class='note'>Not enough history to render a chart yet.</p>"

    if history:
        start_date = history[0].get("date", "—")
        days = len(history)
        weeks = days // 7
        months = days // 30
        total_items = sum(h.get("items", 0) for h in history)

        chart_path = os.path.join(ASSETS_DIR, "history.png")
        build_chart(history, chart_path)
        chart_block = """<h2>Articles Processed Over Time</h2>
        <img src="assets/history.png" alt="Articles per day chart">"""

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
<div class="card">{chart_block}</div>
<p>
  <a class="btn" href="index.html">← Dashboard</a>
  <a class="btn" href="news.html">News Sites</a>
</p>
<p style="font-size:12px;color:#666;">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body></html>"""

    with open(os.path.join(SITE_DIR, "stats.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/stats.html")

if __name__ == "__main__":
    run()
