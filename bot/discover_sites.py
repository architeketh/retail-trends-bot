# bot/discover_sites.py
# Discover new publisher sites from today's items and append to data/news_sites_auto.json

import os, json, re, time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

BASE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(BASE, ".."))
DATA_DIR = os.path.join(BASE, "data")
ITEMS = os.path.join(DATA_DIR, "items.json")
AUTO = os.path.join(DATA_DIR, "news_sites_auto.json")

HEADERS = {
    "User-Agent": "RetailTrendsBot/1.0 (+https://github.com) requests"
}
TIMEOUT = 10

def norm_domain(u: str) -> str:
    try:
        p = urlparse(u)
        host = (p.netloc or "").lower()
        # strip common prefixes
        if host.startswith("www."): host = host[4:]
        if host.startswith("m."): host = host[2:]
        return host
    except Exception:
        return ""

def homepage_from_url(u: str) -> str:
    p = urlparse(u)
    scheme = p.scheme or "https"
    host = p.netloc
    if host.startswith("www."): host = host[4:]
    return urlunparse((scheme, host, "/", "", "", ""))

def fetch_title(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        t = soup.find("title")
        if t and t.text.strip():
            title = re.sub(r"\s+", " ", t.text).strip()
            return title[:140]
    except Exception:
        pass
    # fallback to domain
    d = norm_domain(url)
    return d or url

def try_find_rss(url: str) -> str | None:
    # Try common feed endpoints first
    candidates = ["feed", "rss", "rss.xml", "atom.xml"]
    for c in candidates:
        test = url.rstrip("/") + "/" + c
        try:
            r = requests.get(test, headers=HEADERS, timeout=TIMEOUT)
            ctype = r.headers.get("Content-Type","").lower()
            if r.ok and ("xml" in ctype or "rss" in ctype or "<rss" in r.text[:200].lower()):
                return test
        except Exception:
            pass
    # Try <link rel="alternate"...> discovery
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.ok:
            soup = BeautifulSoup(r.text, "lxml")
            for link in soup.find_all("link", rel=True, href=True):
                rel = " ".join(link.get("rel", [])).lower()
                typ = (link.get("type") or "").lower()
                href = link.get("href")
                if ("alternate" in rel) and ("rss" in typ or "xml" in typ):
                    return href if href.startswith("http") else url.rstrip("/") + "/" + href.lstrip("/")
    except Exception:
        pass
    return None

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def run():
    items = load_json(ITEMS, {}).get("items", [])
    if not items:
        print("discover_sites: no items.json yet; nothing to discover.")
        return

    # Existing auto sites
    auto = load_json(AUTO, [])

    # Build lookup by domain (existing)
    existing_domains = { (s.get("domain") or norm_domain(s.get("url",""))) for s in auto if (s.get("url") or s.get("domain")) }
    existing_domains = {d for d in existing_domains if d}

    # Also avoid duplicates of curated sites that are already on news.html (hardcode a few well-known)
    curated_domains = {
        "www.retaildive.com", "retaildive.com",
        "www.retailwire.com", "retailwire.com",
        "chainstoreage.com", "www.chainstoreage.com",
        "retailtouchpoints.com", "www.retailtouchpoints.com",
        "www.modernretail.co", "modernretail.co",
        "www.morningbrew.com", "morningbrew.com",
        "nrf.com", "www.nrf.com",
        "www.retail-week.com", "retail-week.com",
        "www.reuters.com", "reuters.com",
        "www.forbes.com", "forbes.com",
        "www.businessinsider.com", "businessinsider.com",
        "www.voguebusiness.com", "voguebusiness.com",
        "wwd.com", "www.wwd.com",
        "www.drapersonline.com", "drapersonline.com",
        "fashionunited.com", "www.fashionunited.com",
        "www.digitalcommerce360.com", "digitalcommerce360.com",
        "www.businessoffashion.com", "businessoffashion.com",
        "retail-insider.com", "www.retail-insider.com",
        "www.inforetail.com", "inforetail.com",
        "www.retailgazette.co.uk", "retailgazette.co.uk",
    }

    today = datetime.utcnow().strftime("%Y-%m-%d")
    new_entries = []

    # From today’s items, collect new domains
    for it in items:
        link = it.get("link") or ""
        if not link: continue
        d = norm_domain(link)
        if not d: continue
        if d in existing_domains or d in curated_domains:
            continue
        # Skip obvious platforms that aren't news publishers
        if any(d.endswith(suf) for suf in ("medium.com", "substack.com")):
            continue

        # Probe the site a bit
        home = homepage_from_url(link)
        title = fetch_title(home)
        rss = try_find_rss(home)

        entry = {
            "name": title,
            "url": home,
            "why": "Auto-discovered from daily headlines",
            "domain": d,
            "rss": rss,
            "first_seen": today
        }
        existing_domains.add(d)
        new_entries.append(entry)
        # be polite
        time.sleep(0.5)

    if not new_entries:
        print("discover_sites: no new domains discovered today.")
    else:
        print(f"discover_sites: discovered {len(new_entries)} new site(s).")

    # Merge and keep last 100 by first_seen (stable)
    merged = auto + new_entries
    # Deduplicate by domain, newest wins
    seen = set()
    deduped = []
    for e in sorted(merged, key=lambda x: x.get("first_seen","")):
        dom = e.get("domain")
        if dom and dom not in seen:
            deduped.append(e)
            seen.add(dom)
    if len(deduped) > 100:
        deduped = deduped[-100:]

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(AUTO, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2)

    print(f"discover_sites: wrote {len(deduped)} auto sites to {AUTO}")

if __name__ == "__main__":
    run()
