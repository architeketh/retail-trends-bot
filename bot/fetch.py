# bot/fetch.py
import feedparser, json, pathlib, datetime

DATA = pathlib.Path("data")
DATA.mkdir(parents=True, exist_ok=True)

FEEDS = {
    "Retail Dive": "https://www.retaildive.com/feeds/news/",
    "NRF": "https://nrf.com/rss.xml",  # National Retail Federation
    "Supply Chain Dive": "https://www.supplychaindive.com/feeds/news/",
}

def fetch_feeds():
    all_articles = []
    for source, url in FEEDS.items():
        print(f"Fetching {source} …")
        feed = feedparser.parse(url)
        entries = getattr(feed, "entries", []) or []
        for e in entries[:20]:
            all_articles.append({
                "title": e.get("title", ""),
                "link": e.get("link", ""),
                "published": e.get("published", ""),
                "source": source,
            })
    out = {
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "articles": all_articles,
    }
    (DATA / "headlines.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Wrote {len(all_articles)} articles to data/headlines.json")

if __name__ == "__main__":
    fetch_feeds()
