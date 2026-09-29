"""Calls the LibreOffice worker (system python + uno) and renders page previews."""
from __future__ import annotations

import os
import subprocess
import threading
import time
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import DATA_DIR, FONTS_DIR

UNO_PYTHON = os.getenv("PROPRE_UNO_PYTHON", "/usr/bin/python3")
PIPE = os.getenv("PROPRE_LO_PIPE", "propre_lo")
WORKER = Path(__file__).with_name("uno_worker.py")
_lock = threading.Lock()  # one LibreOffice instance: one document at a time

PREVIEW_DPI = 120  # sharp enough to read on a phone or a desktop screen, still light as WebP
FIRST_PAGES = 3  # rendered before answering; the rest follow in the background


class OfficeError(RuntimeError):
    pass


def finalize(src_docx: Path, out_docx: Path | None, out_pdf: Path | None) -> None:
    """Real indexes + exports. Pass None to skip an output (previews only need the PDF)."""
    profile = DATA_DIR / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    expected = out_pdf or out_docx
    with _lock:
        for attempt in range(2):
            proc = subprocess.run(
                [UNO_PYTHON, str(WORKER), PIPE, str(profile), str(src_docx), str(out_docx or "-"), str(out_pdf or "-")],
                capture_output=True, timeout=240,
            )
            if proc.returncode == 0 and expected is not None and expected.is_file():
                return
            if attempt == 0:
                # A crashed soffice leaves a dead pipe: kill it and retry once.
                subprocess.run(["pkill", "-f", f"pipe,name={PIPE}"], capture_output=True)
        raise OfficeError(proc.stderr.decode("utf-8", "replace")[-800:] or "Échec de la mise en page")


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def _rasterize(pdf: Path, out_dir: Path, first: int, last: int, watermark: bool, dpi: int) -> None:
    prefix = out_dir / f"r{first}"
    # Raw PPM output: pdftoppm's own PNG compression costs ~15x the drawing itself.
    subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(first), "-l", str(last), str(pdf), str(prefix)],
                   check=True, capture_output=True)
    for raw in sorted(out_dir.glob(f"r{first}-*.ppm")):
        n = int(raw.stem.rsplit("-", 1)[1])
        with Image.open(raw) as img:
            page = img.convert("RGB")
        if watermark:
            page = Image.alpha_composite(page.convert("RGBA"), _watermark_layer(page.size)).convert("RGB")
        tmp = out_dir / f".{n}.webp"
        page.save(tmp, "WEBP", quality=80, method=2)
        tmp.replace(out_dir / f"{n}.webp")  # atomic: a reader never sees half a file
        raw.unlink()


def previews(pdf: Path, out_dir: Path, watermark: bool, dpi: int = PREVIEW_DPI, pages: int | None = None) -> int:
    """First pages now, the others in a background thread (the page route waits for them)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("*.webp"), *out_dir.glob("*.png")]:
        old.unlink(missing_ok=True)
    total = pages or page_count(pdf)
    if total == 0:
        return 0
    head = min(FIRST_PAGES, total)
    _rasterize(pdf, out_dir, 1, head, watermark, dpi)
    if total > head:
        marker = out_dir / ".pending"
        marker.write_text(str(total))

        def rest() -> None:
            try:
                for start in range(head + 1, total + 1, 8):
                    _rasterize(pdf, out_dir, start, min(start + 7, total), watermark, dpi)
            finally:
                marker.unlink(missing_ok=True)

        threading.Thread(target=rest, daemon=True).start()
    return total


def wait_for_page(out_dir: Path, n: int, timeout: float = 60) -> Path | None:
    """A page still being rendered in the background: wait for it rather than answer 404."""
    path = out_dir / f"{n}.webp"
    end = time.time() + timeout
    while not path.is_file() and (out_dir / ".pending").is_file() and time.time() < end:
        time.sleep(0.25)
    return path if path.is_file() else None


@lru_cache(maxsize=4)
def _watermark_layer(size: tuple[int, int]) -> Image.Image:
    """Built once per page size (all pages of a document share it), then just composited."""
    width, height = size
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    font_size = max(14, width // 11)
    try:
        font = ImageFont.truetype(str(FONTS_DIR / "poppins-ExtraBold.ttf"), font_size)
    except OSError:
        font = ImageFont.load_default()
    stamp = Image.new("RGBA", (int(font_size * 9.5), int(font_size * 1.6)), (0, 0, 0, 0))
    ImageDraw.Draw(stamp).text((0, 0), "APERÇU · PAGINYA", font=font, fill=(6, 95, 70, 38))
    stamp = stamp.rotate(35, expand=True)
    for y in range(-stamp.height // 3, height, int(stamp.height * 0.9)):
        layer.alpha_composite(stamp, (max(0, (width - stamp.width) // 2), max(0, y)))
    return layer
