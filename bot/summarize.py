# bot/summarize.py
# Retail-trends-only keywords (whitelist) + brand counting + capped history + daily archive.
# Outputs keyword COUNTS: out["keywords"] = [{"term": str, "count": int}, ...]

import os, json, re, yaml
from collections import Counter
from bs4 import BeautifulSoup
from datetime import datetime

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
IN_FILE = os.path.join(DATA_DIR, "items.json")
OUT_FILE = os.path.join(DATA_DIR, "summary.json")
HIST_FILE = os.path.join(DATA_DIR, "history.json")
ARCHIVE_FILE = os.path.join(DATA_DIR, "daily_summaries.json")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------------- Text cleaning ----------------
MULTISPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")
NONWORD_GAPS = re.compile(r"[^\w&']+")

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return MULTISPACE_RE.sub(" ", txt)

def normalize_text(s: str) -> str:
    s = s.lower()
    s = URL_RE.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD_GAPS.sub(" ", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s

# ---------------- Retail-trend lexicon ----------------
LEXICON = {
    "online", "online shopping", "omnichannel", "multichannel", "unified commerce",
    "social commerce", "live shopping", "marketplaces", "d2c", "dtc", "subscription commerce",
    "bopis", "boris", "bopus", "bops", "click and collect", "in store pickup",
    "store pickup", "curbside pickup", "last mile", "same day delivery",
    "ship from store", "ship to store", "ship to home", "home delivery", "delivery services",
    "mobile wallet", "contactless payments", "buy now pay later", "bnpl",
    "checkout optimization", "fraud prevention",
    "retail media", "retail media networks", "connected tv", "ctv",
    "attribution", "first party data", "ugc", "influencer marketing",
    "personalization", "brand awareness", "customer focused",
    "artificial intelligence", "generative ai", "recommendation systems",
    "virtual try on", "ar", "vr", "chatbots", "store analytics", "computer vision",
    "robotics", "robotic automation", "phygital",
    "assortment optimization", "markdown optimization", "price optimization",
    "private label", "rfid", "planogram", "category management",
    "inventory visibility", "inventory accuracy", "order management system",
    "micro fulfillment", "warehouse automation", "supply chain resilience",
    "demand forecasting", "returns management", "reverse logistics", "shrink",
    "dark stores", "micro stores",
    "customer lifetime value", "clv", "average order value", "aov",
    "conversion rate", "same store sales", "gross margin", "basket size",
    "tariffs", "taxes",
    "holiday sales", "prime day", "back to school", "black friday", "cyber monday",
    "sustainability", "esg", "recyclable packaging", "net zero", "circular economy",
    "store openings", "store closures", "small format stores", "experiential retail",
    "grocery", "international", "amazon",
    # Re-commerce / recycled clothing trends
    "recommerce", "re-commerce", "resale", "secondhand", "second hand",
    "thrift", "thrifting", "upcycling", "upcycled", "circular fashion",
    "resale marketplace", "rental", "fashion rental", "consignment",
    "re-commerce platforms", "sustainable fashion",
}

ALIASES = {
    "buy online pickup in store": "bopis",
    "pick up in store": "bopis",
    "bopac": "curbside pickup",
    "curb side pickup": "curbside pickup",
    "click n collect": "click and collect",
    "ai": "artificial intelligence",
    "gen ai": "generative ai",
    "augmented reality": "ar",
    "virtual reality": "vr",
    "virtual try-on": "virtual try on",
    "direct to consumer": "d2c",
    "order management": "order management system",
    "connected television": "connected tv",
}

def keyword_counts(norm_blob: str) -> Counter:
    counts = Counter()
    # aliases -> canonical
    for alias, canon in ALIASES.items():
        a = normalize_text(alias)
        hits = len(re.findall(rf"(?<!\w){re.escape(a)}(?!\w)", norm_blob))
        if hits:
            counts[canon] += hits
    # canonical terms
    for term in LEXICON:
        t = normalize_text(term)
        hits = len(re.findall(rf"(?<!\w){re.escape(t)}(?!\w)", norm_blob))
        if hits:
            counts[term] += hits
    return counts

# ---------------- Brand aliases ----------------
BRAND_ALIASES = {
    "walmart": "Walmart", "target": "Target", "costco": "Costco",
    "kroger": "Kroger", "aldi": "Aldi", "publix": "Publix", "wegmans": "Wegmans",
    "macys": "Macy's", "nordstrom": "Nordstrom", "kohls": "Kohl's",
    "tjx": "TJX", "tj maxx": "TJ Maxx", "marshalls": "Marshalls", "ross": "Ross",
    "urban outfitters": "Urban Outfitters", "uo": "Urban Outfitters", "urbn": "Urban Outfitters",
    "anthropologie": "Anthropologie", "free people": "Free People",
    "gap": "Gap", "old navy": "Old Navy", "banana republic": "Banana Republic",
    "abercrombie": "Abercrombie & Fitch", "american eagle": "American Eagle",
    "nike": "Nike", "adidas": "Adidas", "lululemon": "Lululemon",
    "h m": "H&M", "hm": "H&M", "zara": "Zara", "uniqlo": "Uniqlo",
    "ulta": "Ulta", "sephora": "Sephora", "cvs": "CVS", "walgreens": "Walgreens",
    "home depot": "Home Depot", "lowes": "Lowe's", "best buy": "Best Buy",
    "amazon": "Amazon", "ebay": "eBay", "etsy": "Etsy", "shopify": "Shopify",
    "temu": "Temu", "shein": "Shein", "depop": "Depop", "poshmark": "Poshmark",
    "thredup": "ThredUp", "stockx": "StockX", "asos": "ASOS", "farfetch": "Farfetch",
    "chewy": "Chewy", "wayfair": "Wayfair", "ikea": "IKEA",
    "world market": "World Market", "chicos": "Chico's",
    "foot locker": "Foot Locker", "dicks sporting goods": "Dick's Sporting Goods",
    "primark": "Primark", "jd sports": "JD Sports"
}

def brand_counts(norm_blob: str) -> Counter:
    counts = Counter()
    for alias, canon in BRAND_ALIASES.items():
        hits = len(re.findall(rf"(?<!\w){re.escape(alias)}(?!\w)", norm_blob))
        if hits:
            counts[canon] += hits
    return counts

# ---------------- Main ----------------
def run():
    cfg = load_config()
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(f"Missing input: {IN_FILE}. Run bot/fetch.py first.")

    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        out = {"keywords": [], "brands": [], "highlights": [],
               "stats": {"items_considered": 0, "sources": [], "unique_sources": 0,
                         "date": datetime.utcnow().strftime("%Y-%m-%d")},
               "generated_from": IN_FILE}
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(OUT_FILE, "w", encoding="utf-8") as o:
            json.dump(out, o, indent=2)
        # also write empty history / archive safely
        try:
            history = []
            with open(HIST_FILE, "w", encoding="utf-8") as hf:
                json.dump(history, hf, indent=2)
            archive = {}
            with open(ARCHIVE_FILE, "w", encoding="utf-8") as af:
                json.dump(archive, af, indent=2)
        except Exception:
            pass
        print("Wrote empty summary (no items).")
        return

    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    # Build normalized blob
    norm_parts = []
    for it in items:
        text = f"{(it.get('title') or '').strip()} {clean_html(it.get('summary') or '')}".strip()
        norm_parts.append(normalize_text(text))
    norm_blob = " \n ".join(norm_parts)

    # Keyword COUNTS
    k_counts = keyword_counts(norm_blob)
    top_n_keywords = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    def kw_sort_key(term):
        return (-k_counts[term], -len(term.split()), term)
    kw_terms_sorted = sorted(k_counts.keys(), key=kw_sort_key)[:top_n_keywords]
    keywords_out = [{"term": t, "count": int(k_counts[t])} for t in kw_terms_sorted]

    # Brand counts
    b_counts = brand_counts(norm_blob)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 12))
    brands_sorted = [{"name": b, "count": int(c)} for b, c in b_counts.most_common(top_n_brands)]

    # Highlights
    highlights_cap = 6
    highlights = [{
        "title": (it.get("title") or "").strip(),
        "link": it.get("link") or "",
        "source": it.get("source") or "",
        "published": it.get("published") or "",
    } for it in items[:highlights_cap]]

    # Stats
    sources = [it.get("source") or "" for it in items]
    stats = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "items_considered": len(items),
        "unique_sources": len(set(sources)),
        "sources": sorted(set(sources)),
        "brand_total_detected": int(sum(b_counts.values())),
        "keyword_total_detected": int(sum(k_counts.values())),
    }

    # Assemble output (THIS is the 'out' that was missing)
    out = {
        "keywords": keywords_out,
        "brands": brands_sorted,
        "highlights": highlights,
        "stats": stats,
        "generated_from": IN_FILE,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as o:
        json.dump(out, o, indent=2)

    # --- Update history log (capped to 180 days) ---
    entry = {"date": stats["date"],
             "items": stats["items_considered"],
             "brands_found": len(brands_sorted),
             "keywords_found": len(keywords_out)}
    history = []
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, "r", encoding="utf-8") as hf:
                history = json.load(hf)
        except Exception:
            history = []
    history.append(entry)
    if len(history) > 180:
        history = history[-180:]
    with open(HIST_FILE, "w", encoding="utf-8") as hf:
        json.dump(history, hf, indent=2)

    # --- Append today's snapshot into the daily archive used by weekly_summary.py (keep last 200 days) ---
    archive = {}
    if os.path.exists(ARCHIVE_FILE):
        try:
            with open(ARCHIVE_FILE, "r", encoding="utf-8") as af:
                archive = json.load(af)
        except Exception:
            archive = {}
    archive[stats["date"]] = out
    # keep at most 200 days
    dates_sorted = sorted(archive.keys())
    if len(dates_sorted) > 200:
        for d in dates_sorted[:-200]:
            archive.pop(d, None)
    with open(ARCHIVE_FILE, "w", encoding="utf-8") as af:
        json.dump(archive, af, indent=2)

    print(f"Wrote summary with {len(keywords_out)} keywords (total mentions: {stats['keyword_total_detected']}) and {len(brands_sorted)} brands.")

if __name__ == "__main__":
    run()
