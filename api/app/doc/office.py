"""Calls the LibreOffice worker (system python + uno) and renders page previews."""
from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import DATA_DIR, FONTS_DIR

UNO_PYTHON = os.getenv("PROPRE_UNO_PYTHON", "/usr/bin/python3")
PIPE = os.getenv("PROPRE_LO_PIPE", "propre_lo")
WORKER = Path(__file__).with_name("uno_worker.py")
_lock = threading.Lock()  # one LibreOffice instance: one document at a time


class OfficeError(RuntimeError):
    pass


def finalize(src_docx: Path, out_docx: Path, out_pdf: Path) -> None:
    profile = DATA_DIR / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    with _lock:
        for attempt in range(2):
            proc = subprocess.run(
                [UNO_PYTHON, str(WORKER), PIPE, str(profile), str(src_docx), str(out_docx), str(out_pdf)],
                capture_output=True, timeout=240,
            )
            if proc.returncode == 0 and out_pdf.is_file():
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


def previews(pdf: Path, out_dir: Path, watermark: bool, dpi: int = 96) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.png"):
        old.unlink()
    subprocess.run(["pdftoppm", "-r", str(dpi), "-png", str(pdf), str(out_dir / "p")], check=True, capture_output=True)
    pages = sorted(out_dir.glob("p-*.png"))
    for i, page in enumerate(pages, start=1):
        target = out_dir / f"{i}.png"
        if watermark:
            _watermark(page, target)
            page.unlink()
        else:
            page.rename(target)
    return len(pages)


def _watermark(src: Path, dst: Path) -> None:
    with Image.open(src).convert("RGBA") as img:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        size = max(14, img.width // 11)
        try:
            font = ImageFont.truetype(str(FONTS_DIR / "poppins-ExtraBold.ttf"), size)
        except OSError:
            font = ImageFont.load_default()
        text = "APERÇU · PAGINYA"
        stamp = Image.new("RGBA", (int(size * 9.5), int(size * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(stamp).text((0, 0), text, font=font, fill=(6, 95, 70, 38))
        stamp = stamp.rotate(35, expand=True)
        for y in range(-stamp.height // 3, img.height, int(stamp.height * 0.9)):
            layer.alpha_composite(stamp, (max(0, (img.width - stamp.width) // 2), max(0, y)))
        Image.alpha_composite(img, layer).convert("RGB").save(dst, optimize=True)
