# bot/charts.py
import json, pathlib, re, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# -------------------------
# Stopwords & Brand Seeds
# -------------------------
STOPWORDS = {
    "a","an","the","and","or","but","if","then","else","for","with","without","of","to","in","on","at","by","from","into","over","under",
    "is","are","was","were","be","being","been","do","does","did","done","have","has","had","having",
    "will","would","should","can","could","may","might","must","shall",
    "that","this","these","those","it","its","it’s","as","about","than","so","such","not","no","yes",
    "why","how","when","where","what","who","whom","which",
    "you","your","yours","we","our","ours","they","them","their","theirs",
    "new","news","report","update","amid","after","before","during","today","week","month","year",
    "retail","ecommerce","online"
}

BRAND_SEED = {
    "Amazon","Walmart","Target","Costco","Best Buy","Home Depot","Lowe's","Lowe’s","Kroger","Aldi",
    "Tesco","Carrefour","IKEA","H&M","Zara","Nike","Adidas","Lululemon","Gap","Old Navy",
    "Sephora","Ulta","Macy's","Nordstrom","Kohl's","TJX","TJ Maxx","Marshalls","Saks","Apple",
    "Shein","Temu","Wayfair","Etsy","eBay","Shopify","Instacart","DoorDash","Uber","FedEx","UPS",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-&]+")

# -------------------------
# Category Rules (simple keyword heuristics)
# -------------------------
CATEGORY_RULES = {
    "Retail": [
        r"\bretail(er|ing)?\b", r"\bstore(s)?\b", r"\bchain(s)?\b", r"\bmall(s)?\b",
        r"\bdepartment store(s)?\b"
    ],
    "eCommerce": [
        r"\be-?commerce\b", r"\bonline\b", r"\bshopify\b", r"\bmarketplace\b", r"\bdigital\b"
    ],
    "AI": [
        r"\bAI\b", r"\bartificial intelligence\b", r"\bmachine learning\b", r"\bgenerative\b", r"\bChatGPT\b"
    ],
    "Supply Chain": [
        r"\bsupply\b", r"\blogistic(s)?\b", r"\bwarehouse(s|ing)?\b", r"\bshipping\b", r"\bfulfillment\b"
    ],
    "Big Box": [
        r"\bwalmart\b", r"\btarget\b", r"\bcostco\b", r"\bhome depot\b", r"\bbest buy\b", r"\blowe['’]s\b"
    ],
    "Luxury": [
        r"\blouis vuitton\b", r"\bgucci\b", r"\bprada\b", r"\bherm[eè]s\b", r"\bcartier\b", r"\bchanel\b", r"\bdior\b"
    ],
    "Vintage": [
        r"\bvintage\b", r"\bresale\b", r"\bthrift\b", r"\bsecondhand\b", r"\bconsignment\b"
    ]
}
CATEGORY_REGEX = {k: [re.compile(p, re.I) for p in v] for k, v in CATEGORY_RULES.items()}

def categorize(title: str):
    t = title or ""
    hits = []
    for cat, regs in CATEGORY_REGEX.items():
        if any(r.search(t) for r in regs):
            hits.append(cat)
    if not hits:
        hits = ["Other"]
    return hits

def tokenize(text: str):
    for m in WORD_RE.finditer(text or ""):
        w = m.group(0).strip("’'\"-–—").lower()
        if w and (w not in STOPWORDS):
            yield w

def load_articles():
    src = DATA / "headlines.json"
    if not src.exists():
        return []
    obj = json.loads(src.read_text(encoding="utf-8"))
    return obj.get("articles", [])

def save_json(path: pathlib.Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def plot_bar(pairs, title, outfile):
    if not pairs:
        return
    labels = [p[0] for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    plt.figure(figsize=(8, 4.8))
    bars = plt.barh(range(len(values)), values)
    plt.yticks(range(len(values)), labels)
    plt.title(title)
    plt.tight_layout()
    # value labels
    vmax = max(values) if values else 0
    for i, b in enumerate(bars):
        w = b.get_width()
        plt.text(w + (vmax * 0.02 if vmax else 0.2),
                 b.get_y() + b.get_height()/2, str(values[i]),
                 va="center", fontsize=9)
    plt.savefig(ASSETS / outfile, dpi=160, bbox_inches="tight")
    plt.close()

def main():
    arts = load_articles()

    # Write a front-end friendly headlines file too
    front = [{"title": a.get("title",""), "link": a.get("link",""), "source": a.get("source","")} for a in arts]
    save_json(ASSETS / "headlines.json", front)

    # Keywords / Brands
    word_counts = collections.Counter()
    brand_counts = collections.Counter()

    for a in arts:
        title = a.get("title", "")
        for tok in tokenize(title):
            word_counts[tok] += 1
        # brand mentions: simple substring match for seed names
        for b in BRAND_SEED:
            if b.lower() in (title or "").lower():
                brand_counts[b] += 1

    plot_bar(word_counts.most_common(12), "Top Keywords (latest run)", "keywords.png")
    plot_bar(brand_counts.most_common(12), "Brand Mentions (latest run)", "brands.png")

    # Categorize articles
    cats = {}
    for a in arts:
        for c in categorize(a.get("title","")):
            cats.setdefault(c, []).append(a)

    save_json(DATA / "categorized.json", cats)          # backend copy
    save_json(ASSETS / "categorized.json", cats)        # front-end copy

    print(f"✓ charts: assets/keywords.png, assets/brands.png")
    print(f"✓ categorization: data/categorized.json & assets/categorized.json")

if __name__ == "__main__":
    main()
