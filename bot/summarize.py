# bot/summarize.py
# --------------------------------------------------------------------
# Summarize fetched items as RETAIL TRENDS ONLY (noun/noun-phrases):
# - Strip HTML
# - Extract only terms from a curated retail-trends lexicon (no verbs/adverbs)
# - Handle common aliases (e.g., BOPIS, BNPL, CTV)
# - Keep brand mentions + highlights + stats
#
# Output: bot/data/summary.json
# {
#   "keywords": ["omnichannel", "BOPIS", "connected TV", ...],  # retail trends only
#   "brands": [{"name":"Target","count":7}, ...],
#   "highlights": [...],
#   "stats": {...},
#   "generated_from": "bot/data/items.json"
# }
# --------------------------------------------------------------------

import os
import json
import re
from collections import Counter
import yaml
from bs4 import BeautifulSoup

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
IN_FILE = os.path.join(DATA_DIR, "items.json")
OUT_FILE = os.path.join(DATA_DIR, "summary.json")

def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------- Cleaning ----------
MULTISPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"[a-z][a-z0-9\-&']+")

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return MULTISPACE_RE.sub(" ", txt)

def tokenize(text: str):
    # lowercase tokens; keep hyphens/ampersand within terms
    return [t for t in WORD_RE.findall(text.lower())]

# ---------- Retail trends lexicon (noun/noun phrases only) ----------
# Normalize all to lowercase for matching.
LEXICON = {
    # channels & journeys
    "omnichannel", "multichannel", "unified commerce", "social commerce",
    "live shopping", "marketplaces", "d2c", "dtc", "subscription commerce",
    "last mile", "same day delivery", "curbside pickup", "bopis", "boris",
    "click and collect", "store pickup", "ship from store", "buy online pickup in store",

    # payments & checkout
    "mobile wallet", "contactless payments", "buy now pay later", "bnpl",
    "pos financing", "checkout optimization", "fraud prevention",

    # marketing & media
    "retail media", "connected tv", "ctv", "attribution", "incrementality",
    "first party data", "cookieless", "cookie deprecation", "ugc", "influencer marketing",
    "email marketing", "sms marketing", "personalization",

    # experience & ai
    "generative ai", "recommendation systems", "search merchandising", "virtual try on",
    "ar", "vr", "chatbots", "store analytics", "computer vision",

    # merchandising & pricing
    "assortment optimization", "markdown optimization", "price optimization",
    "private label", "rfid", "planogram", "category management",

    # operations & supply chain
    "inventory visibility", "inventory accuracy", "order management system",
    "micro fulfillment", "warehouse automation", "supply chain resilience",
    "demand forecasting", "returns management", "reverse logistics", "shrink",

    # metrics & economics
    "customer lifetime value", "clv", "average order value", "aov",
    "conversion rate", "cpi", "gmv", "same store sales", "comps",
    "gross margin", "price elasticity", "basket size",

    # seasonal & events
    "holiday sales", "prime day", "back to school", "black friday", "cyber monday",

    # sustainability & packaging
    "sustainability", "esg", "recyclable packaging", "frustration free packaging",

    # store format & fleet
    "store openings", "store closures", "small format stores", "experiential retail",
}

# Aliases/synonyms → canonical forms (all lowercase)
ALIASES = {
    "click & collect": "click and collect",
    "click-and-collect": "click and collect",
    "bopac": "bopis",  # buy online pickup at curbside
    "buy online pick up in store": "bopis",
    "buy-online pick-up in-store": "bopis",
    "buy online pickup in store": "bopis",
    "pick up in store": "bopis",
    "in-store pickup": "bopis",
    "pick up at curbside": "curbside pickup",
    "buy now, pay later": "buy now pay later",
    "bnpl financing": "buy now pay later",
    "retail media networks": "retail media",
    "rmn": "retail media",
    "connected-tv": "connected tv",
    "connected television": "connected tv",
    "tv streaming ads": "connected tv",
    "vto": "virtual try on",
    "augmented reality": "ar",
    "virtual reality": "vr",
    "direct to consumer": "d2c",
    "direct-to-consumer": "d2c",
    "first-party data": "first party data",
    "lifetime value": "customer lifetime value",
    "average basket size": "basket size",
    "order management": "order management system",
    "oms": "order management system",
    "retail shrink": "shrink",
    "computer-vision": "computer vision",
    "personalisation": "personalization",
}

def canonicalize(term: str) -> str:
    t = term.strip().lower()
    # alias map first
    if t in ALIASES:
        return ALIASES[t]
    return t

def ngrams(tokens, n):
    for i in range(len(tokens) - n + 1):
        yield " ".join(tokens[i:i+n])

def extract_trend_terms(texts, max_terms=18):
    """
    Find only lexicon terms (1–3 grams). Prefer multi-word (bigrams/trigrams) first,
    then unigrams. Excludes verbs/adverbs implicitly by whitelisting noun/noun-phrases.
    """
    counts = Counter()

    for txt in texts:
        toks = tokenize(txt)
        # 3-grams then 2-grams then unigrams, to bias toward phrases
        for n in (3, 2, 1):
            for g in ngrams(toks, n):
                g_can = canonicalize(g)
                if g_can in LEXICON:
                    counts[g_can] += 1

    # Rank: phrases first (by length desc), then frequency
    def rank_key(term):
        return (-len(term.split()), -counts[term], term)

    ranked = sorted(counts.keys(), key=rank_key)
    return ranked[:max_terms]

# ---------- Brand mentions (same as before) ----------
BRAND_CANON = {
    "Amazon": ["Amazon"],
    "Walmart": ["Walmart"],
    "Target": ["Target"],
    "Costco": ["Costco"],
    "Home Depot": ["Home Depot", "Home-Depot", "HomeDepot"],
    "Lowe's": ["Lowe's", "Lowes", "Lowe’s"],
    "Best Buy": ["Best Buy", "BestBuy"],
    "Kroger": ["Kroger"],
    "Aldi": ["Aldi"],
    "Dollar General": ["Dollar General", "DollarGeneral"],
    "Dollar Tree": ["Dollar Tree", "DollarTree"],
    "TJX": ["TJX", "T.J.X.", "TJX Companies"],
    "TJ Maxx": ["TJ Maxx", "TJMaxx"],
    "Marshalls": ["Marshalls"],
    "Macy's": ["Macy's", "Macys", "Macy’s"],
    "Nordstrom": ["Nordstrom"],
    "Kohl's": ["Kohl's", "Kohls", "Kohl’s"],
    "Nike": ["Nike"],
    "Adidas": ["Adidas"],
    "Lululemon": ["Lululemon", "LuluLemon"],
    "H&M": ["H&M", "H & M", "HM"],
    "Zara": ["Zara"],
    "Shein": ["Shein", "SHEIN"],
    "Temu": ["Temu"],
    "Ulta": ["Ulta", "Ulta Beauty"],
    "Sephora": ["Sephora"],
    "CVS": ["CVS"],
    "Walgreens": ["Walgreens"],
    "Publix": ["Publix"],
    "Wegmans": ["Wegmans"],
    "eBay": ["eBay", "Ebay"],
    "Shopify": ["Shopify"],
    "Etsy": ["Etsy"],
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

# ---------- Main ----------
def run():
    cfg = load_config()

    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(f"Missing input: {IN_FILE}. Run bot/fetch.py first.")

    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        out = {
            "keywords": [],
            "brands": [],
            "highlights": [],
            "stats": {"items_considered": 0, "sources": [], "unique_sources": 0},
            "generated_from": IN_FILE,
        }
        with open(OUT_FILE, "w", encoding="utf-8") as o:
            json.dump(out, o, indent=2)
        print("No items; wrote empty summary.")
        return

    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    # Clean texts
    cleaned = []
    for it in items:
        title = (it.get("title") or "").strip()
        body = clean_html(it.get("summary") or "")
        cleaned.append(f"{title} {body}".strip())

    # Retail-trend keywords only
    max_kw = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    trend_terms = extract_trend_terms(cleaned, max_terms=max_kw)

    # Brands
    brand_counts = count_brands(cleaned)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 10))
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
