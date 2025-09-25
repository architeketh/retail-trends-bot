# bot/summarize.py
# Summarizer with expanded brand canon (Depop, Urban Outfitters, etc.)
# and retail-trend keyword extraction.

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

# -------- Brand dictionary --------
BRAND_CANON = {
    # Big box & grocery
    "Walmart": ["Walmart"],
    "Target": ["Target"],
    "Costco": ["Costco"],
    "Kroger": ["Kroger"],
    "Aldi": ["Aldi"],
    "Publix": ["Publix"],
    "Wegmans": ["Wegmans"],

    # Department & apparel
    "Macy's": ["Macy's","Macys","Macy’s"],
    "Nordstrom": ["Nordstrom"],
    "Kohl's": ["Kohl's","Kohls","Kohl’s"],
    "TJX": ["TJX","T.J.X.","TJX Companies"],
    "TJ Maxx": ["TJ Maxx","TJMaxx"],
    "Marshalls": ["Marshalls"],
    "Ross": ["Ross","Ross Dress for Less"],
    "Urban Outfitters": ["Urban Outfitters","UrbanOutfitters","UO"],
    "Anthropologie": ["Anthropologie"],
    "Free People": ["Free People","FreePeople"],
    "Gap": ["Gap"],
    "Old Navy": ["Old Navy","OldNavy"],
    "Banana Republic": ["Banana Republic","BananaRepublic"],
    "Abercrombie & Fitch": ["Abercrombie & Fitch","Abercrombie","A&F"],
    "American Eagle": ["American Eagle","AEO","American Eagle Outfitters"],
    "Nike": ["Nike"],
    "Adidas": ["Adidas"],
    "Lululemon": ["Lululemon","LuluLemon"],
    "H&M": ["H&M","H & M","HM"],
    "Zara": ["Zara"],

    # Beauty & drug
    "Ulta": ["Ulta","Ulta Beauty"],
    "Sephora": ["Sephora"],
    "CVS": ["CVS"],
    "Walgreens": ["Walgreens"],

    # Home improvement / electronics
    "Home Depot": ["Home Depot","Home-Depot","HomeDepot"],
    "Lowe's": ["Lowe's","Lowes","Lowe’s"],
    "Best Buy": ["Best Buy","BestBuy"],

    # Marketplaces & platforms
    "Amazon": ["Amazon"],
    "eBay": ["eBay","Ebay"],
    "Etsy": ["Etsy"],
    "Shopify": ["Shopify"],
    "Temu": ["Temu"],
    "Shein": ["Shein","SHEIN"],
    "Depop": ["Depop","DEPOP"],

    # Specialty / others
    "Chewy": ["Chewy"],
    "Wayfair": ["Wayfair"],
    "IKEA": ["IKEA","Ikea"],
    "World Market": ["World Market","Cost Plus","Cost Plus World Market"],
    "Chico's": ["Chico's","Chicos","Chico’s"],
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
        raise FileNotFoundError(f"Missing {IN_FILE}. Run fetch.py first.")

    with open(IN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    if not items:
        out = {"keywords": [], "brands": [], "highlights": [],
               "stats": {"items_considered": 0, "sources": []},
               "generated_from": IN_FILE}
        with open(OUT_FILE,"w",encoding="utf-8") as o:
            json.dump(out, o, indent=2)
        return

    max_items = int(cfg.get("summary", {}).get("max_items", 40))
    items = items[:max_items]

    cleaned_texts = []
    for it in items:
        title = (it.get("title") or "").strip()
        body = clean_html(it.get("summary") or "")
        text = f"{title} {body}".strip()
        cleaned_texts.append(text)

    # TODO: advanced keyword filtering (retail lexicon); kept simple for now
    words = " ".join(cleaned_texts).lower().split()
    common_terms = [w for w in words if len(w) > 4]
    kw_counts = Counter(common_terms)
    keywords = [w for w, _ in kw_counts.most_common(15)]

    brand_counts = count_brands(cleaned_texts)
    top_n_brands = int(cfg.get("infographic", {}).get("top_n_brands", 10))
    brands_sorted = [{"name": b, "count": c} for b, c in brand_counts.most_common(top_n_brands)]

    highlights = [{
        "title": (it.get("title") or "").strip(),
        "link": it.get("link") or "",
        "source": it.get("source") or "",
        "published": it.get("published") or "",
    } for it in items[:6]]

    stats = {
        "items_considered": len(items),
        "unique_sources": len(set(it.get("source") for it in items)),
        "sources": sorted(set(it.get("source") or "" for it in items)),
    }

    out = {
        "keywords": keywords,
        "brands": brands_sorted,
        "highlights": highlights,
        "stats": stats,
        "generated_from": IN_FILE,
    }
    with open(OUT_FILE,"w",encoding="utf-8") as o:
        json.dump(out, o, indent=2)

if __name__ == "__main__":
    run()
