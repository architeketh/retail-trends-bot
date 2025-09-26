# bot/news_links_page.py
# Categorized curated sources + Auto-Discovered section from data/news_sites_auto.json

import os, json
from datetime import datetime, timedelta

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
SITE_DIR = os.path.join(ROOT, "site")
DATA_DIR = os.path.join(BASE, "data")
AUTO = os.path.join(DATA_DIR, "news_sites_auto.json")

INLINE_CSS = """<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;background:#fff;color:#111;
     padding:2rem;max-width:1000px;margin:auto}
h1{margin:0 0 1rem 0}
p.sub{color:#555;margin:.25rem 0 1.25rem}
.section{margin:1.25rem 0 1.5rem}
.section h2{font-size:1.1rem;margin:.25rem 0 .5rem;color:#0f172a}
.grid{display:grid;grid-template-columns:1fr;gap:.6rem}
@media(min-width:800px){.grid{grid-template-columns:1fr 1fr}}
.card{border:1px solid #eee;border-radius:10px;padding:12px}
.card h3{margin:.1rem 0 .2rem;font-size:1.02rem}
.card p{margin:.2rem 0;color:#444;font-size:.95rem}
a.site{color:#1d4ed8;text-decoration:none;border-bottom:1px dashed #bfdbfe;word-break:break-word}
a.site:hover{color:#0f172a;border-bottom:none}
.actions{margin-top:1rem}
.btn{background:#f8fafc;padding:8px 12px;border:1px solid #ccc;border-radius:10px;
     text-decoration:none;color:#111;display:inline-block;margin-right:8px}
.footer{margin-top:16px;color:#666;font-size:12px}
.nav{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
.nav a{font-size:12px;color:#0f172a;text-decoration:none;background:#eef6ff;border:1px solid #dbeafe;
       padding:6px 10px;border-radius:999px}
.nav a:hover{background:#e0efff}
.anchor{position:relative;top:-64px;visibility:hidden}
.badge{background:#eef6ff;border:1px solid #dbeafe;color:#0f172a;border-radius:999px;padding:2px 8px;font-size:12px}
</style>"""

# ---- Curated categories (same as before) ----
CATEGORIES = [
    ("Core US Retail News", [
        ("Retail Dive", "https://www.retaildive.com/", "News & analysis across retail tech, ops, marketing, ecommerce."),
        ("RetailWire", "https://www.retailwire.com/", "Expert commentary + daily discussion on retail topics."),
        ("Chain Store Age", "https://chainstoreage.com/", "U.S. retail news & trends for multi-sector leaders."),
        ("Retail TouchPoints", "https://retailtouchpoints.com/", "Customer experience, omnichannel & retail tech."),
        ("Retail Brew", "https://www.morningbrew.com/retail", "Daily newsletter on retail, DTC & trends."),
        ("National Retail Federation (NRF)", "https://nrf.com/", "Policy, research & industry insights."),
        ("Reuters – Retail & Consumer", "https://www.reuters.com/business/retail-consumer/", "Global, real-time retail/consumer coverage."),
        ("Forbes – Retail", "https://www.forbes.com/retail/", "Business-oriented views on retail trends & brands."),
        ("Business Insider – Retail", "https://www.businessinsider.com/retail", "Timely coverage of retail & ecommerce stories."),
        ("Retail Insider", "https://retail-insider.com/", "Regional (Canada) retail coverage & analysis."),
    ]),
    ("Fashion & Luxury Retail", [
        ("Vogue Business", "https://www.voguebusiness.com/", "Fashion/luxury retail strategy & innovation."),
        ("WWD (Women’s Wear Daily)", "https://wwd.com/", "Trade journal for fashion retail & trend intel."),
        ("Drapers", "https://www.drapersonline.com/", "UK fashion retail trade coverage, tech & supply chain."),
        ("FashionUnited", "https://fashionunited.com/", "Global fashion & retail news, business intelligence."),
        ("The Business of Fashion", "https://www.businessoffashion.com/", "Deep reporting on global fashion/retail strategy."),
        ("Modern Retail", "https://www.modernretail.co/", "Commerce model shifts, DTC, brand strategy."),
    ]),
    ("Ecommerce & Data / Intelligence", [
        ("Digital Commerce 360 (Internet Retailer)", "https://www.digitalcommerce360.com/", "Ecommerce intelligence, data & strategy."),
    ]),
    ("UK/Europe & International Focus", [
        ("Retail Week", "https://www.retail-week.com/", "UK/European retail news, data & analysis."),
        ("Retail Gazette", "https://www.retailgazette.co.uk/", "UK retail news, analysis, interviews & trends."),
        ("infoRETAIL Magazine", "https://www.inforetail.com/", "Spanish trade publication with retail insights."),
    ]),
]

def section_html(title, sites):
    cards = []
    for name, url, why in sites:
        cards.append(
            f"<div class='card'>"
            f"<h3>{name}</h3>"
            f"<p>{why}</p>"
            f"<p><a class='site' target='_blank' rel='noopener' href='{url}'>{url}</a></p>"
            f"</div>"
        )
    anchor = title.lower().replace("&","and").replace("/"," ").replace("  "," ").replace(" ", "-")
    return f"""
    <span id="{anchor}" class="anchor"></span>
    <div class="section">
      <h2>{title}</h2>
      <div class="grid">
        {''.join(cards)}
      </div>
    </div>
    """

def load_auto():
    if os.path.exists(AUTO):
        try:
            with open(AUTO, "r", encoding="utf-8") as f:
                data = json.load(f)
                # normalize
                for e in data:
                    e.setdefault("why", "Auto-discovered from daily headlines")
                return data
        except Exception:
            return []
    return []

def auto_sections():
    data = load_auto()
    if not data:
        return ""

    # Build two lists: recent (<=30 days) and all (cap show)
    today = datetime.utcnow().date()
    recent: list[tuple[str,str,str]] = []
    all_sites: list[tuple[str,str,str]] = []

    for e in data:
        name = e.get("name") or e.get("domain") or "New site"
        url = e.get("url") or (("https://" + e.get("domain")) if e.get("domain") else "#")
        why = e.get("why") or "Auto-discovered from daily headlines"
        first_seen = e.get("first_seen") or ""
        all_sites.append((name, url, why + (f"  •  <span class='badge'>first seen {first_seen}</span>" if first_seen else "")))

        try:
            d = datetime.strptime(first_seen, "%Y-%m-%d").date() if first_seen else None
            if d and (today - d).days <= 30:
                recent.append((name, url, why))
        except Exception:
            pass

    blocks = []
    if recent:
        blocks.append(section_html("Auto-Discovered (Last 30 Days)", recent))
    blocks.append(section_html("Auto-Discovered (All)", all_sites))
    return "\n".join(blocks)

def run():
    # quick-jump pills (curated only for simplicity)
    nav = []
    for title, _ in CATEGORIES:
        anchor = title.lower().replace("&","and").replace("/"," ").replace("  "," ").replace(" ", "-")
        nav.append(f"<a href='#{anchor}'>{title}</a>")

    sections = [section_html(title, sites) for title, sites in CATEGORIES]
    sections.append(auto_sections())

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Retail News Sites</title>
  {INLINE_CSS}
</head>
<body>
  <h1>Retail News Sites</h1>
  <p class="sub">Curated categories + sites auto-discovered from your daily headlines.</p>

  <div class="nav">{''.join(nav)}</div>

  {''.join(sections)}

  <div class="actions">
    <a class="btn" href="index.html">← Dashboard</a>
    <a class="btn" href="stats.html">Stats</a>
  </div>
  <p class="footer">Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
</body>
</html>"""

    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "news.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("Wrote site/news.html (with Auto-Discovered section)")

if __name__ == "__main__":
    run()
