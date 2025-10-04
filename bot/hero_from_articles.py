# bot/hero_from_articles.py
from __future__ import annotations
import pathlib, json, datetime as dt, io, sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

ROOT   = pathlib.Path(".")
DATA   = ROOT / "data"
ASSETS = ROOT / "assets" / "hero"
ASSETS.mkdir(parents=True, exist_ok=True)

W, H = 1792, 1024
TODAY = dt.date.today().isoformat()

HEADERS = {
    "User-Agent": "RetailTrendsBot/1.0 (+https://architeketh.github.io/retail-trends-bot/)"
}

def read_articles():
    p = DATA / "headlines.json"
    if not p.exists(): return []
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return obj.get("articles", [])
    except Exception:
        return []

def absolutize(base, maybe):
    try:
        return urljoin(base, maybe)
    except Exception:
        return maybe

def find_og_image(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=12, headers=HEADERS)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # common tags
        for prop in ("og:image", "og:image:secure_url"):
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                return absolutize(url, tag["content"].strip())
        # twitter fallback
        tag = soup.find("meta", attrs={"name": "twitter:image"})
        if tag and tag.get("content"):
            return absolutize(url, tag["content"].strip())
    except Exception:
        pass
    return None

def download_image(img_url: str) -> bytes | None:
    try:
        r = requests.get(img_url, timeout=12, headers=HEADERS, stream=True)
        r.raise_for_status()
        if "image" not in r.headers.get("Content-Type", ""):
            return None
        content = r.content
        if len(content) < 50_000:  # avoid tiny logos
            return None
        return content
    except Exception:
        return None

def save_hero(img_bytes: bytes, meta: dict):
    # Load, crop to 16:9 center, resize, slight darken for text legibility
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    target_ratio = W / H
    w, h = im.size
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        # too wide -> crop width
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        im = im.crop((left, 0, left + new_w, h))
    else:
        # too tall -> crop height
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        im = im.crop((0, top, w, top + new_h))
    im = im.resize((W, H), Image.LANCZOS)
    # subtle dark overlay
    overlay = Image.new("RGB", (W, H), (8, 12, 28))
    im = Image.blend(im, overlay, 0.18)

    # write files
    out_path = ASSETS / f"{TODAY}.jpg"
    im.save(out_path, "JPEG", quality=90, optimize=True)
    # also copy/update "latest.jpg"
    im.save(ASSETS / "latest.jpg", "JPEG", quality=90, optimize=True)

    meta_path = ASSETS / "latest.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ Saved hero image: {out_path.name}")

def main():
    articles = read_articles()
    if not articles:
        print("No articles found, skipping hero.")
        return

    for a in articles:
        url   = a.get("link") or ""
        title = a.get("title") or ""
        source= a.get("source") or ""
        if not url: 
            continue
        img_url = find_og_image(url)
        if not img_url:
            continue
        img_bytes = download_image(img_url)
        if not img_bytes:
            continue
        meta = {
            "date": TODAY,
            "title": title,
            "source": source,
            "article_url": url,
            "image_url": img_url,
        }
        save_hero(img_bytes, meta)
        return  # stop after first good image

    print("Could not find a usable OG image in today's articles; keeping existing hero.")

if __name__ == "__main__":
    main()