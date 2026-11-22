"""The backgrounds of a presentation, drawn here, and real photos found on the internet. No AI pictures: the customers
do not want them, and they look generated.

Photos, best first: Pexels when PEXELS_API_KEY is set (free key, no card: the most modern pictures); then Openverse
without a key, first on its modern CC0 banks (StockSnap, the WordPress Photo Directory), then everywhere it may be used
commercially; then Wikimedia Commons. Only two or three English keywords per picture leave the server ("warehouse
shelves"), never the document. Each photo keeps its author and licence: they go into the speaker notes and on the last
slide. If nothing answers in time, a slide keeps its colours.
"""
from __future__ import annotations

import html
import io
import logging
import os
import random
import re
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from functools import lru_cache
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

log = logging.getLogger("paginya.art")
MAX_PICTURES = 6
HEADERS = {"User-Agent": "Paginya/1.0 (presentations; https://paginya.vercel.app)"}  # Wikimedia asks every client to say who it is
OLD = re.compile(r"\b1[5-9]\d\d\b|circa|vintage|museum|archive|histor|library|collection|illustration|drawing|engraving|painting|lithograph|\bmap\b|poster|scan", re.I)
# words on a picture fight the slide's own words; a protest or a brand is never neutral in a defence
OFF = re.compile(r"protest|rally|march\b|strike|demonstrat|union|activis|riot|sign\b|signs\b|banner|placard|poster|logo|meme|screenshot|"
                 r"text|quote|infographic|walmart|amazon|trump|election|campaign|police|army|military|soldier|weapon|gun|blood|nude", re.I)
DEADLINE = 40  # seconds for all the photos of a presentation: past it, the slides keep their colours
STOP = {"a", "an", "the", "of", "in", "on", "at", "with", "and", "for", "to", "by", "from", "his", "her", "their", "its", "some", "two", "three"}


def _rgb(value: str) -> tuple[int, int, int]:
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


@lru_cache(maxsize=32)
def mesh(colors: tuple[str, ...], seed: int, width: int = 1600, height: int = 900) -> bytes:
    """A blurred field of colour: first colour as the ground, the others as large soft lights."""
    rng = random.Random(seed)
    small = Image.new("RGB", (240, 135), _rgb(colors[0]))
    draw = ImageDraw.Draw(small)
    for i in range(7):
        color = _rgb(colors[1 + i % (len(colors) - 1)])
        x, y = rng.randint(-20, 260), rng.randint(-20, 155)
        r = rng.randint(40, 95)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)
    wide = small.filter(ImageFilter.GaussianBlur(26)).resize((width, height), Image.BICUBIC)
    grain = Image.effect_noise((width, height), 9).convert("RGB")
    out = io.BytesIO()
    Image.blend(wide, grain, 0.035).save(out, "JPEG", quality=84)
    return out.getvalue()


@lru_cache(maxsize=16)
def halo(accent: str, second: str, ground: str, seed: int = 0, width: int = 1600, height: int = 900) -> bytes:
    """A veil of colour at the top of a white slide, and a touch of light in a corner. Pale enough to write on."""
    small = Image.new("RGB", (240, 135), _rgb(ground))
    draw = ImageDraw.Draw(small)
    def tint(color: str, part: float) -> tuple[int, ...]:
        return tuple(round(a * (1 - part) + b * part) for a, b in zip(_rgb(ground), _rgb(color)))
    draw.ellipse((-40, -46, 280, 6), fill=tint(accent, 0.62))
    draw.ellipse((40, -30, 200, 8), fill=tint(second, 0.8))
    corner = (170, 95, 300, 190) if seed % 2 == 0 else (-60, 95, 70, 190)
    draw.ellipse(corner, fill=tint(second, 0.2))
    out = io.BytesIO()
    small.filter(ImageFilter.GaussianBlur(13)).resize((width, height), Image.BICUBIC).save(out, "JPEG", quality=88)
    return out.getvalue()


def _pexels(query: str, key: str) -> list[dict]:
    found = httpx.get("https://api.pexels.com/v1/search", params={"query": query, "per_page": 10, "orientation": "landscape"},
                      headers={"Authorization": key}, timeout=20)
    photos = found.json().get("photos") or [] if found.status_code == 200 else []
    return [{"url": x["src"]["large2x"], "w": x["width"], "h": x["height"], "credit": f"Photo : {x.get('photographer') or 'Pexels'}, Pexels"} for x in photos]


def _openverse(query: str, sources: str = "") -> list[dict]:
    params = {"q": query, "mature": "false", "page_size": 12, "license_type": "commercial"}
    if sources:
        params["source"] = sources
    found = httpx.get("https://api.openverse.org/v1/images/", params=params, headers=HEADERS, timeout=15)
    rows = found.json().get("results") or [] if found.status_code == 200 else []
    out = []
    for x in rows:
        about = f"{x.get('title') or ''} {x.get('creator') or ''} {' '.join(t.get('name', '') for t in x.get('tags') or [])}"
        if (not sources and OLD.search(about)) or OFF.search(about):
            continue  # an archive or a drawing, a protest, a sign: not the photo a presentation wants
        licence = "CC0" if x.get("license") == "cc0" else f"CC {str(x.get('license', '')).upper()} {x.get('license_version') or ''}".strip()
        who = x.get("creator") or x.get("source") or "Openverse"
        out.append({"url": x["url"], "w": x.get("width") or 0, "h": x.get("height") or 0, "credit": f"Photo : {who}, {licence}, via Openverse"})
    return out


def _commons(query: str) -> list[dict]:
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": 6,
              "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1800}
    found = httpx.get("https://commons.wikimedia.org/w/api.php", params=params, headers=HEADERS, timeout=15)
    pages = (found.json().get("query") or {}).get("pages") or {} if found.status_code == 200 else {}
    out = []
    for page in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        title = page.get("title", "")
        licence = (meta.get("LicenseShortName") or {}).get("value", "")
        if OLD.search(title) or OFF.search(title) or not re.search(r"(?i)cc|public domain", licence):
            continue
        who = re.sub(r"<[^>]+>", "", html.unescape((meta.get("Artist") or {}).get("value", ""))).strip() or "Wikimedia Commons"
        out.append({"url": info.get("thumburl") or info.get("url"), "w": info.get("width") or 0, "h": info.get("height") or 0,
                    "credit": f"Photo : {who[:60]}, {licence}, Wikimedia Commons"})
    return out


def _sources(query: str):
    key = os.getenv("PEXELS_API_KEY", "")
    if key:
        yield lambda: _pexels(query, key)
    yield lambda: _openverse(query, "stocksnap,wordpress")  # modern stock photos, CC0
    yield lambda: _openverse(query)
    yield lambda: _commons(query)


def keywords(text: str) -> str:
    """"Workers checking boxes on shelves in a large warehouse" → "workers checking boxes": a search engine wants few words."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", text or "") if w.lower() not in STOP]
    return " ".join(words[:3])


def _colourful(img: Image.Image) -> bool:
    """A black-and-white or washed-out picture looks like an archive on a modern slide."""
    small = img.resize((64, 64)).convert("HSV")
    return sum(small.getchannel("S").getdata()) / (64 * 64) > 38


def find_photo(query: str, seed: int, path: Path, taken: set[str], lock: threading.Lock, deadline: float = DEADLINE) -> dict | None:
    """The best photo for these keywords, saved at `path`: {"credit"} or None. Every source is asked at once (some
    take 15 s to answer); the answers are then read in order of preference, waiting for a better one while time allows."""
    import time

    end = time.monotonic() + deadline
    sources = list(_sources(query))
    pool = ThreadPoolExecutor(max_workers=len(sources))
    futures = [pool.submit(source) for source in sources]
    try:
        for future in futures:
            try:
                found = future.result(timeout=max(0.1, end - time.monotonic() - 8))  # keep time to download the picture
            except Exception:  # noqa: BLE001 - slow, down or odd: the next source
                continue
            found = [c for c in found if c.get("url") and (c["w"] or 1000) >= 900]
            wide = [c for c in found if c["w"] >= 1.15 * c["h"]] + [c for c in found if c["w"] < 1.15 * c["h"]]  # landscape first
            start = seed % 3
            for pick in (wide[start:] + wide[:start])[:4]:
                with lock:
                    if pick["url"] in taken:
                        continue
                    taken.add(pick["url"])
                try:
                    image = httpx.get(pick["url"], headers=HEADERS, timeout=max(3.0, min(20.0, end - time.monotonic())), follow_redirects=True)
                    with Image.open(io.BytesIO(image.content)) as img:
                        img = img.convert("RGB")
                        if not _colourful(img):
                            continue
                        if img.width > 1800:
                            img = img.resize((1800, round(img.height * 1800 / img.width)), Image.LANCZOS)
                        img.save(path, "JPEG", quality=86)
                    return {"credit": pick["credit"]}
                except (httpx.HTTPError, OSError, ValueError):
                    continue
        return None
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


PHOTO_TYPES = ("section", "liste", "grand", "panneau", "encadre", "chiffres")


def illustrate(deck: dict, images_dir: Path) -> None:
    """Finds the real photos the presentation asks for (the cover, then a few slides), all at once. Those that fail are
    forgotten: every layout works without a photo."""
    images_dir.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[dict, str]] = []
    cover = deck.get("photo") or keywords(deck.get("visual", ""))
    if cover:
        jobs.append((deck, cover))
    for s in deck["slides"]:
        query = s.get("photo") or keywords(s.get("visual", ""))
        if query and s.get("type") in PHOTO_TYPES and len(jobs) < MAX_PICTURES:
            jobs.append((s, query))
    taken: set[str] = set()
    lock = threading.Lock()

    pool = ThreadPoolExecutor(max_workers=max(len(jobs), 1))
    futures = {pool.submit(find_photo, query, n, images_dir / f"deck-photo-{n}.jpg", taken, lock): (n, owner) for n, (owner, query) in enumerate(jobs)}
    done, _late = wait(futures, timeout=DEADLINE)
    pool.shutdown(wait=False, cancel_futures=True)  # a photo still on its way is dropped, the presentation does not wait
    for future, (n, owner) in futures.items():
        got = future.result() if future in done and future.exception() is None else None
        owner["art"] = f"deck-photo-{n}.jpg" if got else ""
        owner["credit"] = got["credit"] if got else ""
