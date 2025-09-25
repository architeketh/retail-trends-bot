import os, json, feedparser
from datetime import datetime, timezone
from dateutil import parser as dateparser
import yaml, hashlib

BASE = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE, "data")
os.makedirs(DATA_DIR, exist_ok=True)

def load_config():
    with open(os.path.join(BASE, "..", "config.yml")) as f:
        return yaml.safe_load(f)

def hash_id(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:12]

def sanitize(entry, src_name):
    title = getattr(entry, "title", "") or ""
    link = getattr(entry, "link", "") or ""
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    published = None
    for k in ("published", "updated"):
        if hasattr(entry, k) and getattr(entry, k):
            try:
                published = dateparser.parse(getattr(entry, k)).astimezone(timezone.utc).isoformat()
                break
            except Exception:
                pass
    if not published:
        published = datetime.now(timezone.utc).isoformat()
    return {
        "id": hash_id(link or title),
        "title": title,
        "link": link,
        "summary": summary,
        "published": published,
        "source": src_name,
    }

def fetch_rss(url, src_name, limit=50):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries[:limit]:
        items.append(sanitize(e, src_name))
    return items

def run():
    cfg = load_config()
    collected = []
    for src in cfg["sources"]:
        try:
            stype = src.get("type", "rss")
            if stype == "rss":
                items = fetch_rss(src["url"], src["name"])
            else:
                print("Unsupported type:", stype, "for", src["name"])
                items = []
            collected.extend(items)
            print(f"Fetched {len(items)} from {src['name']}")
        except Exception as e:
            print("Error fetching", src.get("name", src.get("url")), "->", e)

    # sort newest first and dedupe by id
    seen = set()
    uniques = []
    for it in sorted(collected, key=lambda x: x["published"], reverse=True):
        if it["id"] in seen: continue
        seen.add(it["id"])
        uniques.append(it)

    out = {"fetched_at": datetime.now(timezone.utc).isoformat(), "items": uniques}
    with open(os.path.join(DATA_DIR, "items.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("Wrote", len(uniques), "items to data/items.json")

if __name__ == "__main__":
    run()
