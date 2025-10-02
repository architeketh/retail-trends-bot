# bot/fetch.py
import feedparser, json, pathlib, datetime

DATA = pathlib.Path("data")
DATA.mkdir(parents=True, exist_ok=True)

FEEDS = {
    "Retail Dive": "https://www.retaildive.com/feeds/news/"
}

def fetch_feeds():
    all_articles = []
    for source, url in FEEDS.items():
        print(f"Fetching {source} …")
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:  # limit to first 20
            all_articles.append({
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": source
            })
    out = {
        "fetched_at": datetime.datetime.utcnow().isoformat(),
        "articles": all_articles
    }
    (DATA / "headlines.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {len(all_articles)} articles to data/headlines.json")

if __name__ == "__main__":
    fetch_feeds()
