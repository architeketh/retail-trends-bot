# bot/summarize.py
# Retail-trends-only keywords (noun/noun-phrases, strict whitelist) + robust brand counting.

import os, json, re, yaml
from collections import Counter
from bs4 import BeautifulSoup

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
IN_FILE = os.path.join(DATA_DIR, "items.json")
OUT_FILE = os.path.join(DATA_DIR, "summary.json")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------------- Text cleaning / normalization ----------------
MULTISPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")
NONWORD_GAPS = re.compile(r"[^\w&']+")  # keep word chars, &, and apostrophes

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return MULTISPACE_RE.sub(" ", txt)

def normalize_text(s: str) -> str:
    """
    Normalize to maximize phrase matching:
    - lowercase
    - strip URLs
    - '&' -> ' and '
    - collapse non-word runs to single spaces
    """
    s = s.lower()
    s = URL_RE.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD_GAPS.sub(" ", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s

# ---------------- Retail-trend LEXICON (nouns / noun phrases only) ----------------
# All canonical keys are normalized (lowercase, spaces only).
LEXICON = {
    # shopping & channels
    "online", "online shopping", "omnichannel", "multichannel", "unified commerce",
    "social commerce", "live shopping", "marketplaces", "d2c", "dtc",
    "subscription commerce",

    # fulfillment & pickup/returns
    "bopis", "boris", "bopus", "bops", "click and collect", "in store pickup",
    "store pickup", "curbside pickup", "last mile", "same day delivery",
    "ship from store", "ship to store", "ship to home", "home delivery",
    "delivery services",

    # payments & checkout
    "mobile wallet", "contactless payments", "buy now pay later", "bnpl",
    "pos financing", "checkout optimization", "fraud prevention",

    # marketing & media
    "retail media", "retail media networks", "connected tv", "ctv",
    "attribution", "incrementality", "first party data", "cookieless",
    "cookie deprecation", "ugc", "influencer marketing", "email marketing",
    "sms marketing", "personalization", "brand awareness", "customer focused",

    # experience & ai
    "artificial intelligence", "generative ai", "recommendation systems",
    "search merchandising", "virtual try on", "ar", "vr", "chatbots",
    "store analytics", "computer vision", "robotics", "robotic automation",
    "phygital",

    # merchandising & pricing
    "assortment optimization", "markdown optimization", "price optimization",
    "private label", "rfid", "planogram", "category management",

    # operations & supply chain
    "inventory visibility", "inventory accuracy", "order management system",
    "micro fulfillment", "warehouse automation", "supply chain resilience",
    "demand forecasting", "returns management", "reverse logistics", "shrink",
    "panama canal", "dark stores", "micro stores",

    # metrics & economics
    "customer lifetime value", "clv", "average order value", "aov",
    "conversion rate", "cpi", "gmv", "same store sales", "comps",
    "gross margin", "price elasticity", "basket size", "tariffs", "taxes",

    # seasonal & events
    "holiday sales", "prime day", "back to school", "black friday", "cyber monday",

    # sustainability & packaging
    "sustainability", "esg", "recyclable packaging", "frustration free packaging",
    "net zero", "net zero commitments", "decarbonization", "circular economy",

    # store format & fleet
    "store openings", "store closures", "small format stores", "experiential retail",

    # broad retail context you asked to include
    "grocery", "international", "amazon",
}

# Aliases/synonyms -> canonical (all normalized)
ALIASES = {
    # BOPIS universe
    "buy online pickup in store": "bopis",
    "buy online pick up in store": "bopis",
    "pick up in store": "bopis",
    "in store pick up": "bopis",
    "bopac": "curbside pickup",
    "curb side pickup": "curbside pickup",
    "click n collect": "click and collect",
    # BOPUS/BOPS → treat as BOPIS family per your request
    "bopus": "bopus",
    "bops": "bops",

    # retail media / ctv
    "rmn": "retail media networks",
    "connected television": "connected tv",
    "ctv advertising": "connected tv",
    "tv streaming ads": "connected tv",

    # ai & robotics
    "ai": "artificial intelligence",
    "gen ai": "generative ai",
    "generative ai models": "generative ai",
    "robotic process automation": "robotic automation",

    # d2c
    "direct to consumer": "d2c",
    "direct to consumer brands": "d2c",
    "direct to consumer channel": "d2c",

    # oms
    "order management": "order management system",

    # ar/vr/vto
    "augmented reality": "ar",
    "virtual reality": "vr",
    "virtual try-on": "virtual try on",
}

def count_trend_terms(norm_blob: str, max_terms: int = 18) -> list[str]:
    """
    Strict whitelist: count only LEXICON (and ALIASES mapped to canonical).
    Returns ranked terms by frequency desc, then phrase length desc, then alpha.
    """
    counts = Counter()

    # 1) count aliases and map to canonical
    for alias, canon in ALIASES.items():
        a = normalize_text(alias)
        pattern = re.compile(rf"(?<!\w){re.escape(a)}(?!\w)")
        hits = len(pattern.findall(norm_blob))
        if hits:
            counts[canon] += hits

    # 2) count canonical terms
    for term in LEXICON:
        t = normalize_text(term)
        pattern = re.compile(rf"(?<!\w){re.escape(t)}(?!\w)")
        hits = len(pattern.findall(norm_blob))
        if hits:
            counts[term] += hits

    if not counts:
        return []

    def sort_key(term):
        # frequency desc, then #words desc (favor phrases), then alpha
        return (-counts[term], -len(term.split()), term)

    ranked = sorted(counts.keys(), key=sort_key)
    return ranked[:max_terms]

# ---------------- Brand catalog (aliases -> canonical) ----------------
# keys are normalized; values are display names
BRAND_ALIASES = {
    # Big box & grocery
    "walmart": "Walmart",
    "target": "Target",
    "costco": "Costco",
    "kroger": "Kroger",
    "aldi": "Aldi",
    "publix": "Publix",
    "wegmans": "Wegmans",

    # Department / apparel (with URBN variants)
    "macys": "Macy's", "macy s": "Macy's", "macy’s": "Macy's",
    "nordstrom": "Nordstrom",
    "kohls": "Kohl's", "kohl s": "Kohl's", "kohl’s": "Kohl's",
    "tjx": "TJX", "tjx companies": "TJX",
    "tj maxx": "TJ Maxx", "tjmaxx": "TJ Maxx",
    "marshalls": "Marshalls",
    "ross": "Ross",
    "urban outfitters": "Urban Outfitters", "uo": "Urban Outfitters", "urbn": "Urban Outfitters",
    "anthropologie": "Anthropologie",
    "free people": "Free People",
    "gap": "Gap",
    "old navy": "Old Navy", "oldnavy": "Old Navy",
    "banana republic": "Banana Republic", "bananarepublic": "Banana Republic",
    "abercrombie and fitch": "Abercrombie & Fitch", "abercrombie": "Abercrombie & Fitch", "a f": "Abercrombie & Fitch",
    "american eagle": "American Eagle", "aeo": "American Eagle", "american eagle outfitters": "American Eagle",
    "nike": "Nike", "adidas": "Adidas",
    "lululemon": "Lululemon",
    "h m": "H&M", "hm": "H&M",
    "zara": "Zara", "uniqlo": "Uniqlo",

    # Beauty / drug
    "ulta": "Ulta", "ulta beauty": "Ulta",
    "sephora": "Sephora",
    "cvs": "CVS",
    "walgreens": "Walgreens",

    # Home improvement / electronics
    "home depot": "Home Depot", "homedepot": "Home Depot",
    "lowes": "Lowe's", "lowe s": "Lowe's", "lowe’s": "Lowe's",
    "best buy": "Best Buy", "bestbuy": "Best Buy",

    # Marketplaces / platforms / resale
    "amazon": "Amazon",
    "ebay": "eBay", "eb ay": "eBay",
    "etsy": "Etsy",
    "shopify": "Shopify",
    "temu": "Temu",
    "shein": "Shein",
    "depop": "Depop",
    "poshmark": "Poshmark",
    "thredup": "ThredUp", "thread up": "ThredUp",
    "stockx": "StockX",
    "asos": "ASOS",
    "farfetch": "Farfetch",
    "goat": "GOAT",
    "vinted": "Vinted",

    # Specialty / others
    "chewy": "Chewy",
    "wayfair": "Wayfair",
    "ikea": "IKEA",
    "world market": "World Market", "cost plus": "World Market", "cost plus world market": "World Market",
    "chicos": "Chico's", "chico s": "Chico's", "chico’s": "Chico's",
    "foot locker": "Foot Locker",
    "dicks sporting goods": "Dick's Sporting Goods", "dick s sporting goods": "Dick's Sporting Goods",
    "primark": "Primark",
    "jd sports": "JD Sports",
}

def count_brands_normalized(norm_blob: str) -> Counter:
    counts = Counter()
    for alias, canon in BRAND_ALIASES.items():
        pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
        hits = len(pattern.findall(norm_blob))
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
               "stats": {"items_considered": 0, "sources": [], "unique_sources": 0},
               "generated_from": IN_FILE}
        with open(OUT_FILE, "w", encoding="utf-8") as o:
            json.dump(out, o, indent=2)
        print("No items; wrote empty summary.")
        return

    # Consider up to N items
    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    # Build cleaned texts and one normalized blob for matching
    cleaned_texts, norm_parts = [], []
    for it in items:
        title = (it.get("title") or "").strip()
        body = clean_html(it.get("summary") or "")
        text = f"{title} {body}".strip()
        cleaned_texts.append(text)
        norm_parts.append(normalize_text(text))
    norm_blob = " \n ".join(norm_parts)

    # --- Retail trend keywords (STRICT WHITELIST) ---
    top_n_keywords = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    keywords = count_trend_terms(norm_blob, max_terms=top_n_keywords)

    # --- Brand mentions (normalized + aliases) ---
    brand_counts = count_brands_normalized(norm_blob)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 12))
    brands_sorted = [{"name": b, "count": c} for b, c in brand_counts.most_common(top_n_brands)]

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
        "items_considered": len(items),
        "unique_sources": len(set(sources)),
        "sources": sorted(set(sources)),
        "brand_total_detected": sum(brand_counts.values()),
    }

    out = {
        "keywords": keywords,
        "brands": brands_sorted,
        "highlights": highlights,
        "stats": stats,
        "generated_from": IN_FILE,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as o:
        json.dump(out, o, indent=2)
    print(f"Wrote summary with {len(keywords)} retail-trend keywords and {len(brands_sorted)} brands.")

if __name__ == "__main__":
    run()
