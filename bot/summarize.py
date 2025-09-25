# bot/summarize.py
# --------------------------------------------------------------------
# Retail-trends-only summarizer:
# - Clean + normalize text (strip HTML, '&'->'and', hyphens->space, collapse spaces)
# - Match ONLY curated retail trend nouns/phrases (no verbs/adverbs)
# - Robust alias handling (BOPIS/BNPL/CTV/etc.)
# - Preserve brands, highlights, stats
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

# ----------------- HTML clean + normalization -----------------
MULTISPACE_RE = re.compile(r"\s+")
URL_RE = re.compile(r"https?://\S+")
NONWORD_GAPS = re.compile(r"[^\w&'-]+")

def clean_html(raw: str) -> str:
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    return MULTISPACE_RE.sub(" ", txt)

def normalize_text(s: str) -> str:
    """
    Normalize to improve phrase matching:
    - lowercase
    - remove URLs
    - replace '&' with 'and'
    - replace hyphens with space
    - collapse non-word runs to single space
    - collapse multi-space
    """
    s = s.lower()
    s = URL_RE.sub(" ", s)
    s = s.replace("&", " and ")
    s = s.replace("-", " ")
    s = NONWORD_GAPS.sub(" ", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s

# ----------------- Retail trend lexicon -----------------
# Canonical, normalized (lowercase, spaces only)
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
    "first party data", "cookieless", "cookie deprecation", "ugc",
    "influencer marketing", "email marketing", "sms marketing", "personalization",
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

# Aliases (normalized) -> canonical term in LEXICON
ALIASES = {
    # BOPIS & pickup variants
    "click and collect": "click and collect",
    "click n collect": "click and collect",
    "buy online pick up in store": "bopis",
    "buy online pickup in store": "bopis",
    "pick up in store": "bopis",
    "in store pickup": "bopis",
    "in store pick up": "bopis",
    "bopac": "curbside pickup",                 # buy online pickup at curbside
    "pickup at curbside": "curbside pickup",
    "curb side pickup": "curbside pickup",
    # BNPL variants
    "buy now pay later": "buy now pay later",
    "bnpl financing": "buy now pay later",
    # Retail media variants
    "retail media networks": "retail media",
    "rmn": "retail media",
    # CTV variants
    "connected television": "connected tv",
    "connected tv advertising": "connected tv",
    "tv streaming ads": "connected tv",
    "ctv advertising": "connected tv",
    # D2C
    "direct to consumer": "d2c",
    "direct to consumer brands": "d2c",
    "direct to consumer channel": "d2c",
    "direct to consumer sales": "d2c",
    "direct to consumer strategy": "d2c",
    "direct to consumer model": "d2c",
    "direct to consumer marketing": "d2c",
    "direct to consumer growth": "d2c",
    "direct to consumer commerce": "d2c",
    "direct to consumer retail": "d2c",
    "direct to consumer store": "d2c",
    "direct to consumer sales channels": "d2c",
    "direct to consumer ecommerce": "d2c",
    "direct to consumer advertising": "d2c",
    "direct to consumer operations": "d2c",
    "direct to consumer distribution": "d2c",
    # VTO / AR / VR
    "virtual try on": "virtual try on",
    "augmented reality": "ar",
    "virtual reality": "vr",
    # OMS
    "order management": "order management system",
    "oms": "order management system",
    # personalization spelling
    "personalisation": "personalization",
}

def lexicon_count(normalized_blob: str, max_terms: int = 18) -> list[str]:
    """
    Count lexicon/alias phrases by scanning the normalized corpus.
    Returns top phrases by count (desc) then phrase length desc, then alpha.
    """
    counts = Counter()

    # 1) Count aliases first (map to canonical)
    for alias, canon in ALIASES.items():
        alias_norm = normalize_text(alias)
        # word-boundary-ish: ensure spaces around alias or start/end
        pattern = re.compile(rf"(?<!\w){re.escape(alias_norm)}(?!\w)")
        c = len(pattern.findall(normalized_blob))
        if c:
            counts[canon] += c

    # 2) Count canonical terms directly
    for term in LEXICON:
        term_norm = normalize_text(term)
        pattern = re.compile(rf"(?<!\w){re.escape(term_norm)}(?!\w)")
        c = len(pattern.findall(normalized_blob))
        if c:
            counts[term] += c

    if not counts:
        return []

    def sort_key(k):
        return (-counts[k], -len(k.split()), k)

    ranked = sorted(counts.keys(), key=sort_key)
    return ranked[:max_terms]

# ----------------- Brand mentions (unchanged) -----------------
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

def count_brands(texts: list[str]) -> Counter:
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

# ----------------- Main -----------------
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

    # Cap how many items we consider
    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    # Clean + normalize article texts
    cleaned_texts = []
    norm_blob_parts = []
    for it in items:
        title = (it.get("title") or "").strip()
        body = clean_html(it.get("summary") or "")
        text = f"{title} {body}".strip()
        cleaned_texts.append(text)
        norm_blob_parts.append(normalize_text(text))
    norm_blob = " \n ".join(norm_blob_parts)

    # Retail-trend keywords only
    max_kw = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    trend_terms = lexicon_count(norm_blob, max_terms=max_kw)

    # Brands
    brand_counts = count_brands(cleaned_texts)
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
