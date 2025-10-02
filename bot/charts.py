# bot/charts.py
import json, pathlib, re, collections, datetime as dt, traceback, base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

TODAY = dt.date.today().isoformat()

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

CATEGORY_RULES = {
    "Retail":[r"\bretail(er|ing)?\b",r"\bstore(s)?\b",r"\bchain(s)?\b",r"\bmall(s)?\b",r"\bdepartment store(s)?\b"],
    "eCommerce":[r"\be-?commerce\b",r"\bonline\b",r"\bshopify\b",r"\bmarketplace\b",r"\bdigital\b"],
    "AI":[r"\bAI\b",r"\bartificial intelligence\b",r"\bmachine learning\b",r"\bgenerative\b",r"\bChatGPT\b"],
    "Supply Chain":[r"\bsupply\b",r"\blogistic(s)?\b",r"\bwarehouse(s|ing)?\b",r"\bshipping\b",r"\bfulfillment\b"],
    "Big Box":[r"\bwalmart\b",r"\btarget\b",r"\bcostco\b",r"\bhome depot\b",r"\bbest buy\b",r"\blowe['’]s\b"],
    "Luxury":[r"\blouis vuitton\b",r"\bgucci\b",r"\bprada\b",r"\bherm[eè]s\b",r"\bcartier\b",r"\bchanel\b",r"\bdior\b"],
    "Vintage":[r"\bvintage\b",r"\bresale\b",r"\bthrift\b",r"\bsecondhand\b",r"\bconsignment\b"],
}
CATEGORY_REGEX = {k:[re.compile(p,re.I) for p in v] for k,v in CATEGORY_RULES.items()}

def categorize(title:str):
    t = title or ""
    hits = [cat for cat, regs in CATEGORY_REGEX.items() if any(r.search(t) for r in regs)]
    return hits or ["Other"]

def tokenize(text:str):
    for m in WORD_RE.finditer(text or ""):
        w = m.group(0).strip("’'\"-–—").lower()
        if w and (w not in STOPWORDS):
            yield w

def load_articles():
    p = DATA/"headlines.json"
    if not p.exists(): return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("articles", [])
    except Exception:
        print("charts.py: parse error\n", traceback.format_exc())
        return []

def save_json(path: pathlib.Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def save_fig_basics(outfile_no_ext:str):
    """Save current matplotlib figure as both SVG and PNG."""
    svg = ASSETS / f"{outfile_no_ext}.svg"
    png = ASSETS / f"{outfile_no_ext}.png"
    plt.savefig(svg, bbox_inches="tight")
    plt.savefig(png, dpi=160, bbox_inches="tight")
    print(f"✓ Wrote {svg} and {png}")
    plt.close()

def plot_bar(pairs, title, outfile_no_ext):
    labels = [p[0] for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    plt.figure(figsize=(8, 4.8))
    if values:
        bars = plt.barh(range(len(values)), values)
        plt.yticks(range(len(values)), labels)
        vmax = max(values)
        for i, b in enumerate(bars):
            w = b.get_width()
            plt.text(w + (vmax * 0.02 if vmax else 0.2),
                     b.get_y()+b.get_height()/2, str(values[i]),
                     va="center", fontsize=9)
    else:
        plt.text(0.5, 0.5, "No data yet", ha="center", va="center", fontsize=14)
        plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    save_fig_basics(outfile_no_ext)

def aggregate_7d(history: dict):
    last7 = set((dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(7))
    totals = collections.Counter()
    for day, counts in history.items():
        if day in last7:
            totals.update(counts)
    return totals

def main():
    arts = load_articles()

    # Front-end headlines mirror
    front = [{"title": a.get("title",""), "link": a.get("link",""), "source": a.get("source","")} for a in arts]
    save_json(ASSETS/"headlines.json", front)

    # day counts
    day_kw = collections.Counter()
    day_br = collections.Counter()
    for a in arts:
        t = a.get("title","")
        for tok in tokenize(t):
            day_kw[tok]+=1
        lt = t.lower()
        for b in BRAND_SEED:
            if b.lower() in lt:
                day_br[b]+=1

    # history (last 30d)
    kw_hist_path = DATA/"history_keywords.json"
    br_hist_path = DATA/"history_brands.json"
    kw_hist = json.loads(kw_hist_path.read_text(encoding="utf-8")) if kw_hist_path.exists() else {}
    br_hist = json.loads(br_hist_path.read_text(encoding="utf-8")) if br_hist_path.exists() else {}
    kw_hist[TODAY] = day_kw
    br_hist[TODAY] = day_br
    def trim(h): 
        days = sorted(h.keys())[-30:]
        return {d:{k:int(v) for k,v in h[d].items()} for d in days}
    kw_hist = trim(kw_hist); br_hist = trim(br_hist)
    save_json(kw_hist_path, kw_hist); save_json(br_hist_path, br_hist)

    # charts = last 7 days
    kw7_counter = aggregate_7d(kw_hist)
    br7_counter = aggregate_7d(br_hist)
    kw7 = kw7_counter.most_common(12)
    br7 = br7_counter.most_common(12)

    # write top counts JSON for the page (and for debugging)
    save_json(ASSETS/"kw_top.json", [{"token":k, "count":v} for k,v in kw7])
    save_json(ASSETS/"brand_top.json", [{"brand":k, "count":v} for k,v in br7])

    plot_bar(kw7, "Top Keywords (last 7 days)", "keywords")
    plot_bar(br7, "Brand Mentions (last 7 days)", "brands")

    # categories
    cats = {}
    for a in arts:
        for c in categorize(a.get("title","")):
            cats.setdefault(c, []).append(a)
    save_json(DATA/"categorized.json", cats)
    save_json(ASSETS/"categorized.json", cats)
    print("✓ Categorized JSON written")

if __name__ == "__main__":
    main()
