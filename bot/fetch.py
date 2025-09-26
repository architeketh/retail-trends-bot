# bot/fetch.py
# Fetches retail trend headlines from multiple RSS feeds.
# Outputs bot/data/items.json with:
#   {"items":[{"title","link","source","published","summary"}...]}

import os, json, time
from datetime import datetime
from typing import List, Dict
import feedparser
import requests
from bs4 import BeautifulSoup

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
OUT_FILE = os.path.join(DATA_DIR, "items.json")
CONFIG_FILE = os.path.join(ROOT, "config.yml")  # optional extra feeds

# --------- Feeds (curated; safe if some 404 — we skip gracefully) ----------
FEEDS: List[Dict[str, str]] = [
    {"name": "Retail Dive",            "url": "https://www.retaildive.com/feeds/news/"},
    {"name": "RetailWire",             "url": "https://www.retailwire.com/feed/"},
    {"name": "Chain Store Age",        "url": "https://chainstoreage.com/rss.xml"},
    {"name": "Retail TouchPoints",     "url": "https://www.retailtouchpoints.com/feed"},
    {"name": "Modern Retail",          "url": "https://www.modernretail.co/feed/"},
    {"name": "Retail Brew",            "url": "https://www.morningbrew.com/retail/rss"},
    {"name": "NRF",                    "url": "https://nrf.com/rss.xml"},
    {"name": "Digital Commerce 360",   "url": "https://www.digitalcommerce360.com/feed/"},
    {"name": "Total Retail",           "url": "https://www.mytotalretail.com/feed/"},
    {"name": "Supply Chain 24/7",      "url": "https://www.supplychain247.com/rss"},
    {"name": "Tinuiti",                "url": "https://tinuiti.com/blog/feed/"},
    # Extras (fashion / resale / global retail)
    {"name": "Business of Fashion",    "url": "https://www.businessoffashion.com/feed/"},
    {"name": "FashionUnited",          "url": "https://fashionunited.com/rss"},
]

# --------- Helpers ----------
UA = {"User-Agent": "retail-trends-bot/1.0 (+https://github.com/)"}

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def to_iso(published_struct) -> str:
    """Convert time.struct_time to ISO string (UTC) or return ''."""
    try:
        # feedparser dates are in local/unknown; treat as UTC-ish for charts
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", published_struct)
    except Exception:
        return ""

def clean_html(html: str) -> str:
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
        txt = soup.get_text(" ", strip=True)
        # collapse spaces
        return " ".join(txt.split())
    except Exception:
        return html

def http_get_text(url: str, timeout=8) -> str:
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        if r.ok and "text" in r.headers.get("Content-Type", ""):
            return r.text
    except Exception:
        pass
    return ""

def best_effort_summary(entry) -> str:
    # Prefer summary from feed; fallback to fetching the article and taking the first paragraph
    summ = entry.get("summary") or entry.get("description") or ""
    summ = clean_html(summ)
    if summ:
        return summ
    link = entry.get("link") or ""
    if not link:
        return ""
    html = http_get_text(link)
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
        # try typical article containers
        cand = None
        for sel in ["article p", ".article__content p", ".post-content p", ".entry-content p", "p"]:
            p = soup.select(sel)
            if p:
                cand = p[0].get_text(" ", strip=True)
                if cand:
                    break
        return (cand or "")[:400]
    except Exception:
        return ""

def fetch_feed(url: str) -> feedparser.FeedParserDict:
    # Let feedparser fetch (it handles redirects, gzip, etc.)
    return feedparser.parse(url)

def add_config_feeds():
    """Optional: if config.yml has sources.feeds: [ {name,url}, ... ], include them."""
    try:
        import yaml
        cfg_path = CONFIG_FILE
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            extra = (cfg.get("sources", {}) or {}).get("feeds", []) or []
            for e in extra:
                if isinstance(e, dict) and e.get("name") and e.get("url"):
                    FEEDS.append({"name": e["name"], "url": e["url"]})
    except Exception:
        pass

def run():
    ensure_dirs()
    add_config_feeds()

    items = []
    seen_links = set()
    per_feed_cap = 20   # keep each feed modest
    total_cap = 150     # overall cap

    for feed in FEEDS:
        name, url = feed["name"], feed["url"]
        try:
            parsed = fetch_feed(url)
            entries = parsed.entries[:per_feed_cap] if parsed.entries else []
            for e in entries:
                if len(items) >= total_cap:
                    break
                link = e.get("link") or ""
                if not link or link in seen_links:
                    continue
                seen_links.add(link)

                title = (e.get("title") or "").strip()
                published = ""
                # Try published_parsed, then updated_parsed
                if getattr(e, "published_parsed", None):
                    published = to_iso(e.published_parsed)
                elif getattr(e, "updated_parsed", None):
                    published = to_iso(e.updated_parsed)

                summary = best_effort_summary(e)
                if not summary:
                    summary = title  # minimal fallback so downstream never breaks

                items.append({
                    "title": title or "(untitled)",
                    "link": link,
                    "source": name,
                    "published": published,
                    "summary": summary,
                })
        except Exception as ex:
            print(f"[warn] Skipping feed {name}: {ex}")

    # Sort newest first, then title
    items.sort(key=lambda x: (x.get("published") or "", x.get("title") or ""), reverse=True)

    # Write output
    out = {"items": items}
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Fetched {len(items)} items from {len(FEEDS)} feeds → wrote {OUT_FILE}")

if __name__ == "__main__":
    run()
