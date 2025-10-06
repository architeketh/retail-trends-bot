# bot/hero_from_articles.py
from __future__ import annotations
import pathlib, json, datetime as dt, io, sys, traceback
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from PIL import Image

ROOT   = pathlib.Path(".")
DATA   = ROOT / "data"
HERO   = ROOT / "assets" / "hero"
HERO.mkdir(parents=True, exist_ok=True)

W, H = 1792, 1024
TODAY = dt.date.today().isoformat()

HEADERS = {
    "User-Agent": "RetailTrendsBot/1.0 (+https://architeketh.github.io/retail-trends-bot/)"
}

def log(msg): print(f"[hero] {msg}")

def read_articles():
    p = DATA / "headlines.json"
    if not p.exists():
        log("no data/headlines.json found")
        return []
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        arts = obj.get("articles", [])
        log(f"loaded {len(arts)} articles")
        return arts
    except Exception:
        log("failed to parse headlines.json")
        log(traceback.format_exc())
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
        for prop in ("og:image", "og:image:secure_url"):
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content"):
                return absolutize(url, tag["content"].strip())
        tag = soup.find("meta", attrs={"name": "twitter:image"})
        if tag and tag.get("content"):
            return absolutize(url, tag["content"].strip())
    except Exception:
        log(f"find_og_image error for {url}")
        log(traceback.format_exc())
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
        log(f"download_image error for {img_url}")
        log(traceback.format_exc())
        return None

def save_hero(img_bytes: bytes, meta: dict):
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    # center-crop to 16:9
    target_ratio = W / H
    w, h = im.size
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = max((w - new_w) // 2, 0)
        im = im.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = max((h - new_h) // 2, 0)
        im = im.crop((0, top, w, top + new_h))
    im = im.resize((W, H), Image.LANCZOS)

    # slight dark overlay for legibility
    overlay = Image.new("RGB", (W, H), (8, 12, 28))
    im = Image.blend(im, overlay, 0.18)

    out = HERO / f"{TODAY}.jpg"
    im.save(out, "JPEG", quality=90, optimize=True)
    im.save(HERO / "latest.jpg", "JPEG", quality=90, optimize=True)
    (HERO / "latest.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"saved hero image: {out.name}")

def main():
    try:
        for a in read_articles():
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
            save_hero(img_bytes, {
                "date": TODAY,
                "title": title,
                "source": source,
                "article_url": url,
                "image_url": img_url,
            })
            return
        log("no usable og:image found today; keeping previous hero")
    except Exception:
        # never fail the workflow
        log("unexpected error (ignored):")
        log(traceback.format_exc())

if __name__ == "__main__":
    main()