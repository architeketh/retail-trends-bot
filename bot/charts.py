# bot/charts.py
import json, pathlib, re, collections, datetime as dt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = pathlib.Path(".")
DATA = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

TODAY = dt.date.today().isoformat()

STOPWORDS = {"a","an","the","and","or","if","with","of","to","in","on","at","by",
             "is","are","was","were","be","been","do","does","did","done",
             "have","has","had","will","would","can","could","may","might",
             "your","its","why","how","when","what","who","which"}

BRAND_SEED = {"Amazon","Walmart","Target","Costco","Home Depot","Best Buy","Gap","Nike","Adidas"}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]+")

def tokenize(text):
    for m in WORD_RE.finditer(text or ""):
        w = m.group(0).lower()
        if w not in STOPWORDS:
            yield w

def load_articles():
    p = DATA/"headlines.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("articles", [])
    return []

def save_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def plot_bar(counter, title, outfile):
    pairs = counter.most_common(12)
    labels, values = zip(*pairs) if pairs else ([],[])
    plt.figure(figsize=(8,4.8))
    if values:
        bars = plt.barh(range(len(values)), values)
        plt.yticks(range(len(values)), labels)
        for i,b in enumerate(bars):
            plt.text(b.get_width()+0.3, b.get_y()+b.get_height()/2,
                     str(values[i]), va="center")
    else:
        plt.text(0.5,0.5,"No data",ha="center",va="center")
        plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(ASSETS/f"{outfile}.png", dpi=150, bbox_inches="tight")
    plt.close()

def aggregate_7d(hist):
    last7 = { (dt.date.today()-dt.timedelta(days=i)).isoformat() for i in range(7) }
    total = collections.Counter()
    for d,counts in hist.items():
        if d in last7:
            total.update(counts)
    return total

def main():
    arts = load_articles()

    day_kw, day_br = collections.Counter(), collections.Counter()
    for a in arts:
        t = a.get("title","")
        for tok in tokenize(t): day_kw[tok]+=1
        lt = t.lower()
        for b in BRAND_SEED:
            if b.lower() in lt: day_br[b]+=1

    # Load / update history
    kw_hist_path, br_hist_path = DATA/"history_keywords.json", DATA/"history_brands.json"
    kw_hist = json.loads(kw_hist_path.read_text()) if kw_hist_path.exists() else {}
    br_hist = json.loads(br_hist_path.read_text()) if br_hist_path.exists() else {}
    kw_hist[TODAY] = day_kw; br_hist[TODAY] = day_br

    # Trim to last 30 days
    def trim(h): return {k:{x:int(y) for x,y in v.items()} for k,v in sorted(h.items())[-30:]}
    kw_hist, br_hist = trim(kw_hist), trim(br_hist)
    save_json(kw_hist_path, kw_hist); save_json(br_hist_path, br_hist)

    # Daily charts
    plot_bar(day_kw, "Top Keywords (today)", "keywords")
    plot_bar(day_br, "Brand Mentions (today)", "brands")

    # Weekly cumulative charts
    kw7 = aggregate_7d(kw_hist); br7 = aggregate_7d(br_hist)
    plot_bar(kw7, "Top Keywords (7-day cumulative)", "keywords_weekly")
    plot_bar(br7, "Brand Mentions (7-day cumulative)", "brands_weekly")

if __name__ == "__main__":
    main()
