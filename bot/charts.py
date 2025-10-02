# bot/charts.py
import json, pathlib, re, collections
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

STOPWORDS = {
    # common stopwords + “why/its/how/your” and friends
    "a","an","the","and","or","but","if","then","else","for","with","without","of","to","in","on","at","by","from","into","over","under",
    "is","are","was","were","be","being","been","do","does","did","done","have","has","had","having",
    "will","would","should","can","could","may","might","must","shall",
    "that","this","these","those","it","its","it’s","as","about","than","so","such","not","no","yes",
    "why","how","when","where","what","who","whom","which",
    "you","your","yours","we","our","ours","they","them","their","theirs",
    "new","news","retail","ecommerce","online","report","update","amid","after","before","during",
    # punctuation-ish
    "—","–","-","’","‘","“","”","'","&"
}

BRAND_SEED = {
    # expand as you like
    "Amazon","Walmart","Target","Costco","Best Buy","Home Depot","Lowe's","Lowe’s","Kroger",
    "Aldi","Tesco","Carrefour","IKEA","H&M","Zara","Nike","Adidas","Lululemon","Gap","Old Navy",
    "Sephora","Ulta","Macy's","Nordstrom","Kohl's","TJX","TJ Maxx","Marshalls","Saks","Apple",
    "Shein","Temu","Wayfair","Etsy","eBay","Shopify","Instacart","DoorDash","Uber","FedEx","UPS"
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-&]+")  # words incl. apostrophes & dashes

def tokenize(text: str):
    for m in WORD_RE.finditer(text or ""):
        w = m.group(0).strip("’'\"-–—").lower()
        if not w or w in STOPWORDS:
            continue
        yield w

def titlecase_set(s: str) -> set:
    return {x.strip() for x in s.split(",") if x.strip()}

def main():
    src = DATA / "headlines.json"
    if not src.exists():
        print("No data/headlines.json yet; skipping charts.")
        return

    obj = json.loads(src.read_text(encoding="utf-8"))
    arts = obj.get("articles", [])

    word_counts = collections.Counter()
    brand_counts = collections.Counter()

    # Normalize and count
    for a in arts:
        title = a.get("title", "")
        source = a.get("source", "")
        # Keywords
        for tok in tokenize(title):
            word_counts[tok] += 1
        # Brand mentions (exact token match from seed OR titlecased multiword brands)
        title_words = set(re.findall(r"[A-Za-z][A-Za-z’']+", title))
        # Check multi-word brands by scanning presence
        for b in BRAND_SEED:
            if b in title:
                brand_counts[b] += 1

    # Top N
    topk = word_counts.most_common(12)
    topb = brand_counts.most_common(12)

    # Helpers to draw charts with value labels
    def plot_bar(pairs, title, outfile):
        if not pairs:
            print(f"No data for {outfile}")
            return
        labels = [p[0] for p in pairs][::-1]
        values = [p[1] for p in pairs][::-1]
        plt.figure(figsize=(8, 4.8))
        bars = plt.barh(range(len(values)), values)
        plt.yticks(range(len(values)), labels)
        plt.title(title)
        plt.tight_layout()
        # put value labels on bars
        for i, b in enumerate(bars):
            w = b.get_width()
            plt.text(w + max(values)*0.01, b.get_y()+b.get_height()/2,
                     str(values[i]), va='center', fontsize=9)
        plt.savefig(ASSETS / outfile, dpi=160, bbox_inches="tight")
        plt.close()
        print(f"✓ Wrote assets/{outfile}")

    plot_bar(topk, "Top Keywords (last fetch)", "keywords.png")
    plot_bar(topb, "Brand Mentions (last fetch)", "brands.png")

if __name__ == "__main__":
    main()
