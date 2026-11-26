"""Gather decks made by designers: the free PowerPoint templates of SlidesCarnival (free for any use, credit asked).

Usage: python -I fetch.py <out_dir> [max]
Reads the tag pages that match what Paginya makes (talks, reports, pitches, lessons), keeps the PowerPoint links,
leaves out the themes that have nothing to do with a defence or a report (games, parties, kids), and downloads
them, resuming the ones a slow connection cut. A download is kept only once it opens as a zip.
The decks are only measured (measure.py) and looked at: they are never shipped nor copied into Paginya.
"""
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

SITE = "https://www.slidescarnival.com"
AGENT = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) paginya-study"}
TAGS = ("morph", "animated", "keynote", "professional", "modern", "minimalist", "simple", "elegant", "business", "pitch-deck",
        "technology", "report", "education", "marketing")
LINK = re.compile(r"https://www\.slidescarnival\.com/download/(sc\d+)/([^/\"]+)/pptx")
OFF_TOPIC = re.compile(r"cute|game|kid|cartoon|halloween|christmas|valentine|birthday|baby|wedding|doodle|cottage|y2k|calendar|planner|"
                       r"scrapbook|memory|party|easter|holiday|camp|recipe|food|mother|father|love|girl|princess|pastel|pink|toy|anime|"
                       r"comic|fairy|spooky|cat-|dog-|dino|unicorn|zodiac|tarot|aesthetic|newsletter|resume")


def page(url: str) -> str:
    req = urllib.request.Request(url, headers=AGENT)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def links(pages: int = 4) -> list[tuple[str, str]]:
    """(name, url), animated and professional tags first."""
    seen: dict[str, str] = {}
    for tag in TAGS:
        for n in range(1, pages + 1):
            url = f"{SITE}/tag/{tag}" + (f"/page/{n}" if n > 1 else "")
            try:
                html = page(url)
            except OSError:
                break
            found = LINK.findall(html)
            if not found:
                break
            for code, slug in found:
                if not OFF_TOPIC.search(slug):
                    seen.setdefault(f"{code}_{slug}", f"{SITE}/download/{code}/{slug}/pptx")
    return list(seen.items())


def whole(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return "ppt/presentation.xml" in z.namelist()
    except (zipfile.BadZipFile, OSError):
        return False


def download(url: str, path: Path, tries: int = 4) -> bool:
    for _ in range(tries):
        if path.exists() and whole(path):
            return True
        have = path.stat().st_size if path.exists() else 0
        headers = dict(AGENT, Range=f"bytes={have}-") if have else AGENT
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
                mode = "ab" if have and r.status == 206 else "wb"
                with open(path, mode) as out:
                    while chunk := r.read(1 << 16):
                        out.write(chunk)
        except OSError:
            time.sleep(3)
    return path.exists() and whole(path)


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    todo = links()[:limit]
    print(len(todo), "modèles", flush=True)
    for i, (name, url) in enumerate(todo, 1):
        ok = download(url, out / f"{name}.pptx")
        print(i, "ok" if ok else "échec", name, flush=True)
