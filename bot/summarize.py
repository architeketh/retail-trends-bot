import os, json, re, yaml
from collections import Counter

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")

BRANDS = [
    "Amazon","Walmart","Target","Costco","Home Depot","Lowe's","Best Buy","Kroger","Aldi",
    "Dollar General","Dollar Tree","TJX","Marshalls","TJ Maxx","Macy's","Nordstrom","Kohl's",
    "Nike","Adidas","Lululemon","H&M","Zara","Shein","Temu","Ulta","Sephora","CVS","Walgreens",
    "Publix","Wegmans","eBay","Shopify","Etsy","SHEIN"
]

def load_config():
    with open(os.path.join(BASE, "..", "config.yml")) as f:
        return yaml.safe_load(f)

def simple_keywords(texts, top_k=18):
    stop = set("""the and of to in on at a an is are was were be this that it with for as from by about into over after before more most less least very
    retail sales shoppers customers ecommerce online store stores growth revenue margins inflation price prices pricing promotion promotions discount discounts holiday cyber monday black friday
    yoy qoq quarter fiscal update report announces launch new plans expands guide blog analysis outlook trend trends overview vs increase decrease sees notes says
    """.split())
    words = re.findall(r"[A-Za-z][A-Za-z\-]+", " ".join(texts).lower())
    freq = Counter(w for w in words if w not in stop and len(w) > 2)
    return [w for w,_ in freq.most_common(top_k)]

def count_brands(texts):
    text = " \n ".join(texts)
    counts = Counter()
    for b in BRANDS:
        pattern = re.compile(r"\b" + re.escape(b) + r"\b", re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            counts[b] += len(matches)
    return counts

def run():
    cfg = load_config()
    infile = os.path.join(DATA_DIR, "items.json")
    with open(infile) as f:
        data = json.load(f)

    items = data["items"][: cfg["summary"]["max_items"]]
    texts = [(i.get("title","") + " " + i.get("summary","")) for i in items]
    keywords = simple_keywords(texts, 18)
    brand_counts = count_brands(texts)
    top_brands = brand_counts.most_common(cfg["infographic"].get("top_n_brands", 12))

    highlights = [{
        "title": i.get("title",""), "link": i.get("link",""),
        "source": i.get("source",""), "published": i.get("published","")
    } for i in items[:6]]

    out = {
        "keywords": keywords,
        "brands": [{"name": b, "count": c} for b,c in top_brands],
        "highlights": highlights,
        "generated_from": infile
    }
    with open(os.path.join(DATA_DIR, "summary.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("Wrote summary.json")

if __name__ == "__main__":
    run()
