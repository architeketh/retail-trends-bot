# bot/news_links_page.py
# Builds site/news.html listing trusted retail news sites with links.

import os
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
SITE_DIR = os.path.join(ROOT, "site")

INLINE_CSS = """<style>
body{font-family:system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
     background:#fff;color:#111;padding:2rem;max-width:900px;margin:auto}
h1{margin:0 0 1rem 0}
p.sub{color:#555;margin:.25rem 0 1rem}
.card{border:1px solid #eee;border-radius:10px;padding:1rem;margin:.6rem 0}
.card h3{margin:.2rem 0 .2rem;font-size:1.05rem}
.card p{margin:.2rem 0;color:#444}
a.site{color:#1d4ed8;text-decoration:none;border-bottom:1px dashed #bfdbfe}
a.site:hover{color:#0f172a;border-bottom:none}
.actions{margin-top:1rem}
.btn{background:#f8fafc;padding:8px 12px;border:1px solid #ccc;border-radius:10px;
     text-decoration:none;color:#111;display:inline-block;margin-right:8px}
.btn.primary{background:#2E93fA;color:#fff;border:none}
.footer{margin-top:16px;color:#666;font-size:12px}
</style>"""

SITES = [
    {
        "name": "Retail Dive",
        "url": "https://www.retaildive.com/",
        "why": "News & analysis across retail tech, ops, marketing, ecommerce."
    },
    {
        "name": "RetailWire",
        "url": "https://www.retailwire.com/",
        "why": "Expert commentary and daily discussion on retail topics."
    },
    {
        "name": "Chain Store Age",
        "url": "https://chainstoreage.com/",
        "why": "U.S. retail news and trends for multi-sector leaders."
    },
    {
        "name": "Retail TouchPoints",
        "url": "https://retailtouchpoints.com/",
        "why": "Customer experience, omnichannel, store ops & retail tech."
    },
    {
        "name": "Modern Retail",
        "url": "https://www.modernretail.co/",
        "why": "Shifts in commerce models, DTC, brand strategy."
    },
    {
        "name": "Retail Brew",
        "url": "https://www.morningbrew.com/retail",
        "why": "Daily newsletter focused on retail, DTC and trends."
    },
    {
        "name": "National Retail Federation (NRF)",
        "url": "https://nrf.com/",
        "why": "News, policy analysis, research & insights from the NRF."
    },
    {
        "name": "Retail Week",
        "url": "https://www.retail-week.com/",
        "why": "UK/European retail news, data & analysis."
    },
    {
        "name": "Reuters – Retail & Consumer",
        "url": "https://www.reuters.com/business/retail-consumer/",
        "why": "Global, real-time retail & consumer coverage."
    },
    {
        "name": "Forbes – Retail",
        "url": "https://www.forbes.com/retail/",
        "why": "Business-oriented views on trends and retail brands."
    },
    {
        "name": "Business Insider – Retail",
        "url": "https://www.businessinsider.com/retail",
        "why": "Timely coverage of retail & ecommerce stories."
    },
    {
        "name": "Vogue Business",
        "url": "https://www.voguebusiness.com/",
        "why": "Fashion/luxury retail lens on strategy & innovation."
    },
    {
        "name": "WWD (Women’s Wear Daily)",
        "url": "https://wwd.com/",
        "why": "Trade journal for fashion retail and trend intelligence."
    },
    {
        "name": "Drapers",
        "url": "https://www.drapersonline.com/",
        "why": "UK fashion retail trade coverage incl. tech & supply chain."
    },
    {
        "name": "FashionUnited",
        "url": "https://fashionunited.com/",
        "why": "Global fashion & retail news, business intelligence."
    },
    {
        "name": "Digital Commerce 360 (Internet Retailer)",
        "url": "https://www.digitalcommerce360.com/",
        "why": "Ecommerce intelligence, data and strategy."
    },
    {
        "name": "The Business of Fashion",
        "url": "https://www.businessoffashion.com/",
        "why": "Deep reporting on fashion & retail industry strategy."
    },
    {
        "name": "Retail Insider",
        "url": "https://retail-insider.com/",
        "why": "Niche/regional (Canada) retail coverage & analysis."
    },
    {
        "name": "infoRETAIL Magazine",
        "url": "https://www.inforetail.com/",
        "why": "Trade publication with retail news & insights."
    },
    {
        "name": "Retail Gazette",
        "url": "https://www.retailgazette.co.uk/",
        "why": "UK retail news, analysis, interviews & trends."
    },
]

def run():
    cards = []
    for s in SITES:
        cards.append(
            f"<div class='card'>"
            f"<h3>{s['name']}</h3>"
            f"<p>{s['why']}</p>"
            f"<p><a class='site' target='_blank' rel='noopener' href='{s['url']}'>{s['url']}</a></p>"
            f"</div>"
        )

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Retail News Sites</title>
  {INLINE_CSS}
</head>
<body>
  <h1>Retail News Sites</h1>
  <p class="sub">A curated list of reliable sources for retail trends and analysis.</p>
  {''.join(cards)}
  <div class="actions">
    <a class="btn" href="index.html">← Back to Dashboard</a>
  </div>
  <p class="footer">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body>
</html>"""
    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "news.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/news.html")

if __name__ == "__main__":
    run()
