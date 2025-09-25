# bot/summarize.py
# Retail-trend summarizer with robust BRAND counting (normalized text + aliases)

import os, json, re, yaml
from collections import Counter, defaultdict
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
    Lowercase; strip URLs; unify punctuation:
      - '&' -> ' and '
      - hyphens/commas/periods -> space (handled by NONWORD_GAPS)
      - collapse multiple spaces
    """
    s = s.lower()
    s = URL_RE.sub(" ", s)
    s = s.replace("&", " and ")
    s = NONWORD_GAPS.sub(" ", s)
    s = MULTISPACE_RE.sub(" ", s).strip()
    return s

# ---------------- Brand catalog (aliases -> canonical) ----------------
# NOTE: keys are already normalized (lowercase, spaces only)
BRAND_ALIASES = {
    # Big box & grocery
    "walmart": "Walmart",
    "target": "Target",
    "costco": "Costco",
    "kroger": "Kroger",
    "aldi": "Aldi",
    "publix": "Publix",
    "wegmans": "Wegmans",

    # Department / apparel
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
    "nike": "Nike",
    "adidas": "Adidas",
    "lululemon": "Lululemon", "lulelemon": "Lululemon",
    "h m": "H&M", "hm": "H&M",
    "zara": "Zara",
    "uniqlo": "Uniqlo",

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
    "goat": "GOAT",  # (can create false positives; remove if noisy)
    "vinted": "Vinted",

    # Pets / furniture / specialty
    "chewy": "Chewy",
    "wayfair": "Wayfair",
    "ikea": "IKEA", "i k e a": "IKEA",
    "world market": "World Market", "cost plus": "World Market", "cost plus world market": "World Market",
    "chicos": "Chico's", "chico s": "Chico's", "chico’s": "Chico's",
    "foot locker": "Foot Locker",
    "dicks sporting goods": "Dick's Sporting Goods", "dick s sporting goods": "Dick's Sporting Goods",
    "primark": "Primark",
    "jd sports": "JD Sports",
}

# For display order, we’ll aggregate counts per canonical name.
def count_brands_normalized(norm_blob: str) -> Counter:
    counts = Counter()
    # Build regex once per alias; match word-ish boundaries in normalized text
    for alias, canon in BRAND_ALIASES.items():
        # alias already normalized; treat as whole token/phrase in normalized blob
        pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
        hits = len(pattern.findall(norm_blob))
        if hits:
            counts[canon] += hits
    return counts

# ---------------- VERY SIMPLE trend keywords (unchanged) ----------------
# You can keep using your lexicon-based version; to keep this fix focused on brands,
# we’ll keep keywords as the top unique words/phrases from the text.
def top_keywords_simple(texts, k=18):
    blob = " ".join(texts).lower()
    tokens = re.findall(r"[a-z][a-z0-9\-']{3,}", blob)
    # light stopwording
    stop = set("the and for with from into over under while after before this that those these have has are was were will would could should their our your its it's they them you we his her him as of on to in by at or not".split())
    tokens = [t for t in tokens if t not in stop]
    return [w for w, _ in Counter(tokens).most_common(k)]

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

    # Prepare texts
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

    # --- Keywords (simple; you can plug back your lexicon-based function if you prefer) ---
    top_n_keywords = int(cfg.get("infographic", {}).get("top_n_keywords", 18))
    keywords = top_keywords_simple(cleaned_texts, k=top_n_keywords)

    # --- Brands (normalized + aliases) ---
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

    # Stats (also useful for Sources drawer)
    sources = [it.get("source") or "" for it in items]
    stats = {
        "items_considered": len(items),
        "unique_sources": len(set(sources)),
        "sources": sorted(set(sources)),
        "brand_total_detected": sum(c for _, c in brand_counts.items()),
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
    print(f"Wrote summary with {len(keywords)} keywords and {len(brands_sorted)} brands (total mentions: {stats['brand_total_detected']}).")

if __name__ == "__main__":
    run()
