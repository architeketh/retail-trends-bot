# bot/fetch.py
import feedparser, json, pathlib, datetime

DATA = pathlib.Path("data")
DATA.mkdir(parents=True, exist_ok=True)

FEEDS = {
    "Retail Dive": "https://www.retaildive.com/feeds/news/",
    "NRF": "https://nrf.com/rss.xml",
    "Supply Chain Dive": "https://www.supplychaindive.com/feeds/news/",
    "Chain Store Age": "https://www.chainstoreage.com/rss.xml",
    "Digital Commerce 360": "https://www.digitalcommerce360.com/feed/",
}

def fetch_feeds(limit_per_feed=25):
    all_articles = []
    for source, url in FEEDS.items():
        print(f"Fetching {source} …")
        feed = feedparser.parse(url)
        entries = getattr(feed, "entries", []) or []
        kept = 0
        for e in entries[:limit_per_feed]:
            title = e.get("title", "").strip()
            link  = e.get("link", "").strip()
            if not title or not link:
                continue
            all_articles.append({
                "title": title,
                "link": link,
                "published": e.get("published", ""),
                "source": source,
            })
            kept += 1
        print(f"  kept {kept}/{len(entries)} from {source}")

    out = {
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "articles": all_articles,
    }
    (DATA / "headlines.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"✓ Wrote {len(all_articles)} articles to data/headlines.json")

if __name__ == "__main__":
    fetch_feeds()
