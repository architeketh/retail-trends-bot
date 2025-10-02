# bot/charts.py
import json, pathlib, re, collections, datetime as dt, traceback
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT   = pathlib.Path(".")
DATA   = ROOT / "data"
ASSETS = ROOT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

TODAY = dt.date.today()
TODAY_ISO = TODAY.isoformat()

# -------------------------
# Config
# -------------------------
STOPWORDS = {
    "a","an","the","and","or","but","if","then","else","for","with","without","of","to","in","on","at","by","from","into","over","under",
    "is","are","was","were","be","being","been","do","does","did","done","have","has","had","having",
    "will","would","should","can","could","may","might","must","shall",
    "that","this","these","those","it","its","it’s","as","about","than","so","such","not","no","yes",
    "why","how","when","where","what","who","whom","which","you","your","yours","we","our","ours","they","them","their","theirs",
    "new","news","report","update","amid","after","before","during","today","week","month","year",
    "retail","ecommerce","online"
}

BRAND_SEED = {
    "Amazon","Walmart","Target","Costco","Best Buy","Home Depot","Lowe's","Lowe’s","Kroger","Aldi",
    "Tesco","Carrefour","IKEA","H&M","Zara","Nike","Adidas","Lululemon","Gap","Old Navy",
    "Sephora","Ulta","Macy's","Nordstrom","Kohl's","TJX","TJ Maxx","Marshalls","Saks","Apple",
    "Shein","Temu","Wayfair","Etsy","eBay","Shopify","Instacart","DoorDash","Uber","FedEx","UPS"
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’\-&]+")

# -------------------------
# Helpers
# -------------------------
def tokenize(text: str):
    for m in WORD_RE.finditer(text or ""):
        w = m.group(0).strip("’'\"-–—").lower()
        if w and (w not in STOPWORDS):
            yield w

def load_articles():
    p = DATA/"headlines.json"
    if not p.exists(): return []
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj.get("articles", [])
    except Exception:
        print("charts.py: failed to parse headlines.json\n", traceback.format_exc())
        return []

def save_json(path: pathlib.Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

def distinct_colors(n: int):
    cmap = plt.get_cmap("tab20")
    return [cmap(i % 20) for i in range(n)]

def plot_bar(counter: collections.Counter, title: str, outfile_no_ext: str):
    pairs = counter.most_common(12)
    labels = [p[0] for p in pairs][::-1]
    values = [p[1] for p in pairs][::-1]
    plt.figure(figsize=(8.5, 5))
    if values:
        colors = distinct_colors(len(values))
        bars = plt.barh(range(len(values)), values, color=colors)
        plt.yticks(range(len(values)), labels)
        vmax = max(values)
        for i, b in enumerate(bars):
            w = b.get_width()
            plt.text(w + (0.03 * (vmax if vmax > 0 else 1)),
                     b.get_y()+b.get_height()/2, str(values[i]),
                     va="center", fontsize=9)
    else:
        plt.text(0.5, 0.5, "No data yet", ha="center", va="center", fontsize=14)
        plt.axis("off")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(ASSETS/f"{outfile_no_ext}.png", dpi=160, bbox_inches="tight")
    plt.savefig(ASSETS/f"{outfile_no_ext}.svg", bbox_inches="tight")
    plt.close()
    print(f"✓ Wrote assets/{outfile_no_ext}.png and .svg")

# Windows
def is_same_iso_week(day_iso: str) -> bool:
    try:
        d = dt.date.fromisoformat(day_iso)
        return d.isocalendar()[:2] == TODAY.isocalendar()[:2]  # (ISO year, ISO week)
    except Exception:
        return False

def is_in_month(day_iso: str) -> bool:
    try:
        d = dt.date.fromisoformat(day_iso)
        return d.year == TODAY.year and d.month == TODAY.month
    except Exception:
        return False

def is_in_year(day_iso: str) -> bool:
    try:
        d = dt.date.fromisoformat(day_iso)
        return d.year == TODAY.year
    except Exception:
        return False

def aggregate_window(history: dict, pred) -> collections.Counter:
    total = collections.Counter()
    for day, counts in history.items():
        if pred(day):
            total.update(counts)
    return total

def normalize_history(h: dict) -> dict:
    return {d:{k:int(v) for k,v in counts.items()} for d, counts in sorted(h.items())}

# -------------------------
# Main
# -------------------------
def main():
    arts = load_articles()

    # Today counts
    kw_day = collections.Counter()
    br_day = collections.Counter()
    for a in arts:
        t = a.get("title", "")
        for tok in tokenize(t):
            kw_day[tok] += 1
        lt = t.lower()
        for b in BRAND_SEED:
            if b.lower() in lt:
                br_day[b] += 1

    # Persist daily history (keep ~400 days so YTD works)
    kw_hist_path = DATA/"history_keywords.json"
    br_hist_path = DATA/"history_brands.json"
    kw_hist = json.loads(kw_hist_path.read_text(encoding="utf-8")) if kw_hist_path.exists() else {}
    br_hist = json.loads(br_hist_path.read_text(encoding="utf-8")) if br_hist_path.exists() else {}

    kw_hist[TODAY_ISO] = {k:int(v) for k,v in kw_day.items()}
    br_hist[TODAY_ISO] = {k:int(v) for k,v in br_day.items()}

    def trim(h: dict):
        days = sorted(h.keys())[-400:]
        return {d: h[d] for d in days}

    kw_hist = trim(kw_hist)
    br_hist = trim(br_hist)

    save_json(kw_hist_path, normalize_history(kw_hist))
    save_json(br_hist_path, normalize_history(br_hist))

    # Aggregations: WTD (resets each ISO week), MTD, YTD
    kw_wtd = aggregate_window(kw_hist, is_same_iso_week)
    br_wtd = aggregate_window(br_hist, is_same_iso_week)
    kw_mtd = aggregate_window(kw_hist, is_in_month)
    br_mtd = aggregate_window(br_hist, is_in_month)
    kw_ytd = aggregate_window(kw_hist, is_in_year)
    br_ytd = aggregate_window(br_hist, is_in_year)

    # Charts
    plot_bar(kw_day, "Top Keywords (today)", "keywords_today")
    plot_bar(br_day, "Brand Mentions (today)", "brands_today")
    plot_bar(kw_wtd, "Top Keywords (week-to-date)", "keywords_wtd")
    plot_bar(br_wtd, "Brand Mentions (week-to-date)", "brands_wtd")
    plot_bar(kw_mtd, "Top Keywords (month-to-date)", "keywords_mtd")
    plot_bar(br_mtd, "Brand Mentions (month-to-date)", "brands_mtd")
    plot_bar(kw_ytd, "Top Keywords (year-to-date)", "keywords_ytd")
    plot_bar(br_ytd, "Brand Mentions (year-to-date)", "brands_ytd")

    # Totals JSON for site
    save_json(ASSETS/"kw_totals.json", {
        "today":   [{"token":k,"count":int(v)} for k,v in kw_day.most_common(20)],
        "wtd":     [{"token":k,"count":int(v)} for k,v in kw_wtd.most_common(20)],
        "mtd":     [{"token":k,"count":int(v)} for k,v in kw_mtd.most_common(20)],
        "ytd":     [{"token":k,"count":int(v)} for k,v in kw_ytd.most_common(20)],
    })
    save_json(ASSETS/"brand_totals.json", {
        "today":   [{"brand":k,"count":int(v)} for k,v in br_day.most_common(20)],
        "wtd":     [{"brand":k,"count":int(v)} for k,v in br_wtd.most_common(20)],
        "mtd":     [{"brand":k,"count":int(v)} for k,v in br_mtd.most_common(20)],
        "ytd":     [{"brand":k,"count":int(v)} for k,v in br_ytd.most_common(20)],
    })

    # Simple categorization (kept as-is)
    import re as _re
    def categorize(title: str):
        t = title or ""
        rules = {
            "Big Box":      [r"\bwalmart\b", r"\btarget\b", r"\bcostco\b", r"\bhome depot\b", r"\bbest buy\b"],
            "eCommerce":    [r"\be-?commerce\b", r"\bonline\b", r"\bshopify\b", r"\bmarketplace\b"],
            "AI":           [r"\bAI\b", r"\bgenerative\b", r"\bmachine learning\b", r"\bchatgpt\b"],
            "Supply Chain": [r"\bsupply\b", r"\blogistic", r"\bwarehouse", r"\bshipping\b", r"\bfulfillment\b"],
            "Luxury":       [r"\bgucci\b|\bprada\b|\bchanel\b|\bdior\b|\blouis vuitton\b|\bherm[eè]s\b"],
            "Vintage":      [r"\bvintage\b|\bthrift\b|\bresale\b|\bsecondhand\b|\bconsignment\b"],
            "Retail":       [r"\bretail\b|\bstore\b|\bchain\b|\bmall\b|\bdepartment store\b"]
        }
        for cat, pats in rules.items():
            for p in pats:
                if _re.search(p, t, _re.I):
                    return cat
        return "Other"

    cats = {}
    for a in arts:
        cat = categorize(a.get("title",""))
        cats.setdefault(cat, []).append(a)

    save_json(DATA/"categorized.json", cats)
    save_json(ASSETS/"categorized.json", cats)
    print("✓ Wrote charts + WTD/MTD/YTD totals + categorized JSON")

if __name__ == "__main__":
    main()