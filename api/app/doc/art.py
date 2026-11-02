"""The backgrounds of a presentation, drawn here, and real photos. No AI pictures: the customers do not want them.

Photos come from Pexels when PEXELS_API_KEY is set (free key, no card). Only a short description of the picture leaves
the server, never the document. Without a key, or if nothing answers, a slide simply keeps its colours and curves.
"""
from __future__ import annotations

import io
import logging
import os
import random
from functools import lru_cache
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

log = logging.getLogger("paginya.art")
MAX_PICTURES = 4


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


def _pexels(prompt: str, seed: int, path: Path, key: str) -> bool:
    try:
        found = httpx.get("https://api.pexels.com/v1/search", params={"query": prompt, "per_page": 8, "orientation": "landscape"}, headers={"Authorization": key}, timeout=20)
        photos = found.json().get("photos") or [] if found.status_code == 200 else []
        if not photos:
            return False
        image = httpx.get(photos[seed % len(photos)]["src"]["large2x"], timeout=30, follow_redirects=True)
        with Image.open(io.BytesIO(image.content)) as img:
            img.convert("RGB").save(path, "JPEG", quality=86)
        return True
    except (httpx.HTTPError, OSError, ValueError, KeyError):
        log.warning("photo indisponible")
        return False


def _picture(prompt: str, seed: int, path: Path) -> bool:
    key = os.getenv("PEXELS_API_KEY", "")
    return bool(key) and _pexels(prompt, seed, path, key)


def illustrate(deck: dict, images_dir: Path) -> None:
    """Draws the pictures the AI asked for. Those that fail are forgotten: the layouts work without them."""
    images_dir.mkdir(parents=True, exist_ok=True)
    wanted = [s for s in deck["slides"] if s.get("visual")][:MAX_PICTURES - 1]
    jobs = []
    if deck.get("visual"):
        jobs.append((deck, deck["visual"]))
    jobs += [(s, s["visual"]) for s in wanted]

    def run(job: tuple[int, tuple[dict, str]]) -> None:
        n, (owner, prompt) = job
        name = f"deck-art-{n}.jpg"
        owner["art"] = name if _picture(prompt, 1000 + n, images_dir / name) else ""

    for job in enumerate(jobs):
        run(job)
