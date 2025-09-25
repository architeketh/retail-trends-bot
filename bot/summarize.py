# bot/summarize.py
# --------------------------------------------------------------------
# Summarize fetched retail items:
# - Clean HTML from feed summaries
# - Build high-signal keywords (unigrams + bigrams)
# - Count brand mentions (canonicalized)
# - Emit compact highlights for the page
#
# Outputs bot/data/summary.json with shape:
# {
#   "keywords": ["holiday demand", "discounts", ...],
#   "brands": [{"name":"Target","count":7}, ...],
#   "highlights": [{"title": "...", "link": "...", "source": "...", "published": "..."}, ...],
#   "stats": {...},
#   "generated_from": "bot/data/items.json"
# }
# --------------------------------------------------------------------

import os
import json
import re
from collections import Counter, defaultdict
import yaml
from bs4 import BeautifulSoup

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
IN_FILE = os.path.join(DATA_DIR, "items.json")
OUT_FILE = os.path.join(DATA_DIR, "summary.json")

# -------------------------
# Config helpers
# -------------------------
def load_config():
    with open(os.path.join(ROOT, "config.yml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# -------------------------
# Text cleaning + tokenizing
# -------------------------
HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"\s+")

# Broad, retail-tuned stopwords (add as needed)
STOPWORDS = set("""
a an the and or but if then else of in on at to for from by as is are was were be been being
this that those these it its it's you your we our their they i he she them will would could should
with without within about into over after before during between across under above per via vs
new latest today update news report blog guide analysis announces launch unveils reveals says notes sees
retail retailer retailers store stores chain chains ecommerce online digital brick mortar omnichannel
sales shopper shoppers customers traffic demand supply category categories product products pricing price prices percent percentage
growth decline increase decrease higher lower up down quarter qoq yoy fiscal year season seasonal holiday cyber monday black friday
forecast outlook trend trends overview highlights make made make's making company companies
https http www com net org img src figure div span nbsp br amp
""".split())

WORD_RE = re.compile(r"[a-z][a-z0-9\-']+")

def clean_html(raw: str) -> str:
    """Strip HTML to plain text; preserve spaces where tags removed."""
    if not raw:
        return ""
    # BeautifulSoup handles edge cases & entities well
    text = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    text = MULTISPACE_RE.sub(" ", text)
    return text

def tokenize(text: str):
    """Lowercase word tokens; filter stopwords and very short tokens."""
    text = text.lower()
    tokens = [t for t in WORD_RE.findall(text) if t not in STOPWORDS and len(t) > 2]
    return tokens

def top_keywords(texts, k_unigrams=12, k_bigrams=6, total_cap=18):
    """
    Build a keyword list mixing unigrams and bigrams.
    - Rank unigrams by frequency
    - Build bigrams from adjacent tokens and rank them
    - Merge (de-dup by string) up to total_cap
    """
    # Unigrams
    uni_counter = Counter()
    # Bigrams
    bi_counter = Counter()

    for txt in texts:
        toks = tokenize(txt)
        if not toks:
            continue
        uni_counter.update(toks)
        bigrams = [" ".join(pair) for pair in zip(toks, toks[1:])]
        # Filter bigrams with stopword starts/ends or duplicates like "retail retail"
        for bg in bigrams:
            a, b = bg.split()
            if a == b or a in STOPWORDS or b in STOPWORDS:
                continue
            bi_counter[bg] += 1

    uni = [w for w, _ in uni_counter.most_common(k_unigrams)]
    bi  = [w for w, _ in bi_counter.most_common(k_bigrams)]

    merged = []
    seen = set()
    for w in bi + uni:  # prefer bigrams first for more meaning
        if w not in seen:
            merged.append(w)
            seen.add(w)
        if len(merged) >= total_cap:
            break
    return merged

# -------------------------
# Brand mentions
# -------------------------
# Canonical forms → variants to match. Add brands you care about.
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
    """
    Count brand mentions using case-insensitive exact-phrase matching
    for each brand's variants. Returns Counter of canonical names.
    """
    blob = " \n ".join(texts)
    counts = Counter()
    for canon, variants in BRAND_CANON.items():
        c = 0
        for v in variants:
            # word boundary around first/last word; allow punctuation in middle (e.g., Lowe's)
            pattern = re.compile(rf"(?i)\b{re.escape(v)}\b")
            c += len(pattern.findall(blob))
        if c:
            counts[canon] = c
    return counts

# -------------------------
# Main summarization
# -------------------------
def run():
    cfg = load_config()

    # Load fetched items
    if not os.path.exists(IN_FILE):
        raise FileNotFoundError(f"Missing input: {IN_FILE}. Run bot/fetch.py first.")

    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        summary = {
            "keywords": [],
            "brands": [],
            "highlights": [],
            "stats": {"items_considered": 0, "sources": [], "unique_sources": 0},
            "generated_from": IN_FILE,
        }
        with open(OUT_FILE, "w", encoding="utf-8") as out:
            json.dump(summary, out, indent=2)
        print("No items found; wrote empty summary.")
        return

    # Respect config cap
    max_items = int(cfg.get("summary", {}).get("max_items", 25))
    items = items[:max_items]

    # Clean text & prepare corpus
    cleaned_texts = []
    for it in items:
        title = (it.get("title") or "").strip()
        summary_raw = it.get("summary") or ""
        summary_clean = clean_html(summary_raw)
        cleaned_texts.append(f"{title} {summary_clean}".strip())

    # Build keywords (unigrams + bigrams)
    kw = top_keywords(cleaned_texts,
                      k_unigrams=12,
                      k_bigrams=6,
                      total_cap=int(cfg.get("infographic", {}).get("top_n_keywords", 18)))

    # Count brand mentions
    brand_counts = count_brands(cleaned_texts)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 12))
    brands_sorted = [{"name": b, "count": c} for b, c in brand_counts.most_common(top_n_brands)]

    # Highlights (titles + links)
    highlights_cap = 6
    highlights = [{
        "title": (it.get("title") or "").strip(),
        "link": it.get("link") or "",
        "source": it.get("source") or "",
        "published": it.get("published") or "",
    } for it in items[:highlights_cap]]

    # Stats block (optional, handy for badges/KPIs)
    sources = [it.get("source") or "" for it in items]
    stats = {
        "items_considered": len(items),
        "unique_sources": len(set(sources)),
        "sources": sorted(list(set(sources))),
        "top_brand": brands_sorted[0]["name"] if brands_sorted else None,
        "brand_mentions_total": sum(b["count"] for b in brands_sorted),
    }

    out = {
        "keywords": kw,
        "brands": brands_sorted,
        "highlights": highlights,
        "stats": stats,
        "generated_from": IN_FILE,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote summary to {OUT_FILE} with {len(kw)} keywords and {len(brands_sorted)} brands.")

if __name__ == "__main__":
    run()
