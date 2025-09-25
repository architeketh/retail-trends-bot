# bot/summarize.py
# Retail-trends-only summarizer with expanded lexicon & aliases (your requested phrases included).

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

MULTISPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")
NONWORD_GAPS = re.compile(r"[^\w&'-]+")

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return MULTISPACE_RE.sub(" ", txt)

def normalize_text(s: str) -> str:
    s = s.lower()
    s = URL_RE.sub(" ", s)
    s = s.replace("&", " and ")
    s = s.replace("-", " ")
    s = NONWORD_GAPS.sub(" ", s)
    return MULTISPACE_RE.sub(" ", s).strip()

# ----------------- RETAIL TRENDS LEXICON (lowercase, canonical) -----------------
LEXICON = {
    # channels & journeys
    "omnichannel","multichannel","unified commerce","social commerce",
    "live shopping","marketplaces","d2c","dtc","subscription commerce",
    "last mile","same day delivery","curbside pickup","bopis","boris",
    "click and collect","store pickup","ship from store","buy online pickup in store",
    "ship to store","ship to home","home delivery","delivery services",

    # payments & checkout
    "mobile wallet","contactless payments","buy now pay later","bnpl",
    "pos financing","checkout optimization","fraud prevention",

    # marketing & media
    "retail media","connected tv","ctv","attribution","incrementality",
    "first party data","cookieless","cookie deprecation","ugc",
    "influencer marketing","email marketing","sms marketing","personalization",
    "brand awareness","customer focused",

    # experience & ai
    "artificial intelligence","generative ai","recommendation systems",
    "search merchandising","virtual try on","ar","vr","chatbots",
    "store analytics","computer vision","robotics","robotic automation",
    "phygital",

    # merchandising & pricing
    "assortment optimization","markdown optimization","price optimization",
    "private label","rfid","planogram","category management",

    # operations & supply chain
    "inventory visibility","inventory accuracy","order management system",
    "micro fulfillment","warehouse automation","supply chain resilience",
    "demand forecasting","returns management","reverse logistics","shrink",
    "panama canal","dark stores","micro stores",

    # metrics & economics
    "customer lifetime value","clv","average order value","aov",
    "conversion rate","cpi","gmv","same store sales","comps",
    "gross margin","price elasticity","basket size","tariffs","taxes",

    # seasonal & events
    "holiday sales","prime day","back to school","black friday","cyber monday",

    # sustainability & packaging
    "sustainability","esg","recyclable packaging","frustration free packaging",
    "net zero","net zero commitments","decarbonization","circular economy",

    # store format & fleet
    "store openings","store closures","small format stores","experiential retail",

    # broad context (you requested these)
    "online","grocery","international","amazon",
}

# --------- Aliases / synonyms (normalized) -> canonical in LEXICON -----
ALIASES = {
    # pickup / fulfillment
    "click n collect":"click and collect",
    "buy online pick up in store":"bopis",
    "pick up in store":"bopis",
    "in store pickup":"bopis",
    "instore pickup":"bopis",
    "in store pick up":"bopis",
    "bopac":"curbside pickup",
    "curb side pickup":"curbside pickup",

    # bnpl
    "bnpl financing":"buy now pay later",

    # retail media / ctv
    "retail media networks":"retail media",
    "rmn":"retail media",
    "connected television":"connected tv",
    "ctv advertising":"connected tv",
    "tv streaming ads":"connected tv",

    # ai & robotics
    "ai":"artificial intelligence",
    "gen ai":"generative ai",
    "generative ai models":"generative ai",
    "robotics machinery":"robotics",
    "robotic process automation":"robotic automation",

    # d2c
    "direct to consumer":"d2c",
    "direct to consumer brands":"d2c",
    "direct to consumer channel":"d2c",

    # oms
    "order management":"order management system",
    "oms":"order management system",

    # vto / ar / vr
    "virtual try on":"virtual try on",
    "augmented reality":"ar",
    "virtual reality":"vr",

    # same-day delivery variants
    "same day-delivery":"same day delivery",
    "same day ship":"same day delivery",

    # sustainability
    "net zero targets":"net zero",
    "net zero goal":"net zero",
    "netzero":"net zero",
    "net zero slot":"net zero",

    # store format
    "small store format":"small format stores",
}

def lexicon_count(normalized_blob: str, max_terms: int = 18) -> list[str]:
    counts = Counter()
    # 1) aliases -> canonical
    for alias, canon in ALIASES.items():
        a = normalize_text(alias)
        pattern = re.compile(rf"(?<!\w){re.escape(a)}(?!\w)")
        c = len(pattern.findall(normalized_blob))
        if c:
            counts[canon] += c
    # 2) canonical direct
    for term in LEXICON:
        t = normalize_text(term)
        pattern = re.compile(rf"(?<!\w){re.escape(t)}(?!\w)")
        c = len(pattern.findall(normalized_blob))
        if c:
            counts[term] += c
    if not counts:
        return []
    def sk(k): return (-counts[k], -len(k.split()), k)
    ranked = sorted(counts.keys(), key=sk)
    return ranked[:max_terms]

# ----------------- Brand mentions -----------------
BRAND_CANON = {
    "Amazon":["Amazon"], "Walmart":["Walmart"], "Target":["Target"], "Costco":["Costco"],
    "Home Depot":["Home Depot","Home-Depot","HomeDepot"],
    "Lowe's":["Lowe's","Lowes","Lowe’s"], "Best Buy":["Best Buy","BestBuy"],
    "Kroger":["Kroger"], "Aldi":["Aldi"], "Dollar General":["Dollar General","DollarGeneral"],
    "Dollar Tree":["Dollar Tree","DollarTree"], "TJX":["TJX","T.J.X.","TJX Companies"],
    "TJ Maxx":["TJ Maxx","TJMaxx"], "Marshalls":["Marshalls"], "Macy's":["Macy's","Macys","Macy’s"],
    "Nordstrom":["Nordstrom"], "Kohl's":["Kohl's","Kohls","Kohl’s"], "Nike":["Nike"], "Adidas":["Adidas"],
    "Lululemon":["Lululemon","LuluLemon"], "H&M":["H&M","H & M","HM"], "Zara":["Zara"],
    "Shein":["Shein","SHEIN"], "Temu":["Temu"], "Ulta":["Ulta","Ulta Beauty"], "Sephora":["Sephora"],
    "CVS":["CVS"], "Walgreens":["Walgreens"], "Publix":["Publix"], "Wegmans":["Wegmans"],
    "eBay":["eBay","Ebay"], "Shopify":["Shopify"], "Etsy":["Etsy"],
}

def count_brands(texts):
    blob = " \n ".join(texts)
    counts = Counter()
    for canon, variants in BRAND_CANON.items():
        c = 0
        for v in variants:
            pattern = re.compile(rf"(?i)\b{re.escape(v)}\b")
            c += len(pattern.findall(blob))
        if c:
            counts[canon] = c
    return counts

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

    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    cleaned_texts = []
    norm_blob_parts = []
    for it in items:
        title = (it.get("title") or "").strip()
        body = clean_html(it.get("summary") or "")
        text = f"{title} {body}".strip()
        cleaned_texts.append(text)
        norm_blob_parts.append(normalize_text(text))
    norm_blob = " \n ".join(norm_blob_parts)

    max_kw = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    trend_terms = lexicon_count(norm_blob, max_terms=max_kw)

    brand_counts = count_brands(cleaned_texts)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 10))
    brands_sorted = [{"name": b, "count": c} for b, c in brand_counts.most_common(top_n_brands)]

    highlights_cap = 6
    highlights = [{
        "title": (it.get("title") or "").strip(),
        "link": it.get("link") or "",
        "source": it.get("source") or "",
        "published": it.get("published") or "",
    } for it in items[:highlights_cap]]

    sources = [it.get("source") or "" for it in items]
    stats = {
        "items_considered": len(items),
        "unique_sources": len(set(sources)),
        "sources": sorted(set(sources)),
        "top_brand": brands_sorted[0]["name"] if brands_sorted else None,
        "brand_mentions_total": sum(b["count"] for b in brands_sorted),
    }

    out = {
        "keywords": trend_terms,
        "brands": brands_sorted,
        "highlights": highlights,
        "stats": stats,
        "generated_from": IN_FILE,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as o:
        json.dump(out, o, indent=2)
    print(f"Wrote summary with {len(trend_terms)} retail trend keywords and {len(brands_sorted)} brands.")

if __name__ == "__main__":
    run()
