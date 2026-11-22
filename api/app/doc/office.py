"""Calls the LibreOffice worker (system python + uno) and renders page previews."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import DATA_DIR, FONTS_DIR

UNO_PYTHON = os.getenv("PROPRE_UNO_PYTHON", "/usr/bin/python3")
PIPE = os.getenv("PROPRE_LO_PIPE", "propre_lo")
SOFFICE = os.getenv("PROPRE_SOFFICE", "soffice")
WORKER = Path(__file__).with_name("uno_worker.py")
_lock = threading.Lock()  # the command-line conversions (fallback): one at a time
# Several LibreOffice kept open, each with its own pipe and profile: as many documents laid out at the same time
# (~200 Mo of memory each). 1 on a small machine; the VPS (4 cœurs, 8 Go) runs 3 (Dockerfile).
WORKERS = max(1, int(os.getenv("PROPRE_LO_WORKERS", "1")))
_slots: queue.Queue[int] = queue.Queue()
for _i in range(WORKERS):
    _slots.put(_i)

PREVIEW_DPI = 120  # sharp enough to read on a phone or a desktop screen, still light as WebP
FIRST_PAGES = 3  # rendered before answering; the rest follow in the background


class OfficeError(RuntimeError):
    pass


def _slot_paths(slot: int) -> tuple[str, Path]:
    pipe = PIPE if slot == 0 else f"{PIPE}_{slot}"
    profile = DATA_DIR / ("lo-profile" if slot == 0 else f"lo-profile-{slot}")
    profile.mkdir(parents=True, exist_ok=True)
    return pipe, profile


def warm() -> None:
    """Starts the LibreOffice instances one after the other, before the first customers: a cold start next to an
    instance at work is slow, and on some versions fails."""
    for _ in range(WORKERS):
        slot = _slots.get()
        try:
            pipe, profile = _slot_paths(slot)
            subprocess.run([UNO_PYTHON, str(WORKER), pipe, str(profile), "-", "-", "-"], capture_output=True, timeout=120)
        except (subprocess.TimeoutExpired, OSError):
            pass
        finally:
            _slots.put(slot)


def finalize(src_docx: Path, out_docx: Path | None, out_pdf: Path | None, out_layout: Path | None = None) -> None:
    """Real indexes + exports. Pass None to skip an output (previews only need the PDF).
    A PowerPoint goes through too: it is printed to PDF (the preview of the slides)."""
    expected = out_pdf or out_docx or out_layout
    slot = _slots.get()  # waits for a free LibreOffice
    try:
        pipe, profile = _slot_paths(slot)
        for attempt in range(2):
            proc = subprocess.run(
                [UNO_PYTHON, str(WORKER), pipe, str(profile), str(src_docx), str(out_docx or "-"), str(out_pdf or "-"),
                 str(out_layout or "-")],
                capture_output=True, timeout=240,
            )
            if proc.returncode == 0 and expected is not None and expected.is_file():
                return
            if attempt == 0:
                # A crashed soffice leaves a dead pipe: kill it (this one only: ";" ends its name) and retry once.
                subprocess.run(["pkill", "-f", f"pipe,name={pipe};"], capture_output=True)
        raise OfficeError(proc.stderr.decode("utf-8", "replace")[-800:] or "Échec de la mise en page")
    finally:
        _slots.put(slot)


def to_docx(src: Path, dst: Path) -> None:
    """An old Word (.doc), OpenDocument (.odt) or RTF file saved as .docx by LibreOffice, so the rest works as usual.

    The LibreOffice already running for the layouts does it (no second start, no second copy in memory; a second
    instance started while the first one listens can also crash on recent LibreOffice). The command line is the fallback."""
    try:
        finalize(src, dst, None)
        if dst.is_file() and dst.stat().st_size:
            return
    except (OfficeError, subprocess.TimeoutExpired, OSError):
        pass
    profile = DATA_DIR / "lo-convert"  # its own profile: the layout worker keeps the other one open
    profile.mkdir(parents=True, exist_ok=True)
    out_dir = dst.parent / "converted"
    out_dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            proc = subprocess.run(
                ["soffice", f"-env:UserInstallation=file://{profile}", "--headless", "--norestore", "--convert-to", "docx:MS Word 2007 XML",
                 "--outdir", str(out_dir), str(src)], capture_output=True, timeout=180)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise OfficeError("Conversion impossible") from exc
    made = out_dir / f"{src.stem}.docx"
    if not made.is_file() or made.stat().st_size == 0:
        raise OfficeError(proc.stderr.decode("utf-8", "replace")[-400:] or "Conversion impossible")
    made.replace(dst)
    out_dir.rmdir()


def slides_to_pdf(src: Path, dst: Path) -> None:
    """A PowerPoint printed to PDF by LibreOffice Impress: the preview of the slides. An open LibreOffice does it
    (a slideshow needs one PDF per step: starting LibreOffice each time cost ~2 s); the command line is the fallback."""
    try:
        finalize(src, None, dst)
        if dst.is_file() and dst.stat().st_size:
            return
    except (OfficeError, subprocess.TimeoutExpired, OSError):
        pass
    profile = DATA_DIR / "lo-convert"
    profile.mkdir(parents=True, exist_ok=True)
    out_dir = dst.parent / "slides-pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            proc = subprocess.run(
                [SOFFICE, f"-env:UserInstallation=file://{profile}", "--headless", "--norestore", "--convert-to", "pdf:impress_pdf_Export",
                 "--outdir", str(out_dir), str(src)], capture_output=True, timeout=180)
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise OfficeError("Conversion impossible") from exc
    made = out_dir / f"{src.stem}.pdf"
    if not made.is_file() or made.stat().st_size == 0:
        raise OfficeError(proc.stderr.decode("utf-8", "replace")[-400:] or "Conversion impossible")
    made.replace(dst)
    out_dir.rmdir()


def layout(src_docx: Path, cache: Path, out_pdf: Path | None = None) -> list[list] | None:
    """The real page of each top-level paragraph ([[page, text]], a table is page 0), read once then cached.

    None when LibreOffice cannot tell: callers fall back on what the file itself says.
    """
    if not cache.is_file():
        try:
            finalize(src_docx, None, out_pdf, cache)
        except (OfficeError, subprocess.TimeoutExpired, OSError):
            return None
    try:
        rows = json.loads(cache.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return rows if isinstance(rows, list) else None


def page_count(pdf: Path) -> int:
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def _rasterize(pdf: Path, out_dir: Path, first: int, last: int, watermark: bool, dpi: int, alive=lambda: True) -> None:
    prefix = out_dir / f"r{first}"
    # Raw PPM output: pdftoppm's own PNG compression costs ~15x the drawing itself.
    subprocess.run(["pdftoppm", "-r", str(dpi), "-f", str(first), "-l", str(last), str(pdf), str(prefix)],
                   check=True, capture_output=True)
    for raw in sorted(out_dir.glob(f"r{first}-*.ppm")):
        if not alive():
            raw.unlink(missing_ok=True)  # a newer layout started: these pages are no longer the document
            continue
        n = int(raw.stem.rsplit("-", 1)[1])
        with Image.open(raw) as img:
            page = img.convert("RGB")
        if watermark:
            page = Image.alpha_composite(page.convert("RGBA"), _watermark_layer(page.size)).convert("RGB")
        tmp = out_dir / f".{n}.webp"
        page.save(tmp, "WEBP", quality=80, method=2)
        tmp.replace(out_dir / f"{n}.webp")  # atomic: a reader never sees half a file
        raw.unlink()


# One background drawing per document at a time: {folder: (generation, thread)}. Laying a document out again while
# the pages of the previous layout are still being drawn used to mix old pages into the new ones, and the old
# job removed the new ".pending" marker (pages then answered "not found").
_jobs: dict[str, tuple[int, threading.Thread | None]] = {}
_jobs_lock = threading.Lock()


def previews(pdf: Path, out_dir: Path, watermark: bool, dpi: int = PREVIEW_DPI, pages: int | None = None) -> int:
    """First pages now, the others in a background thread (the page route waits for them)."""
    key = str(out_dir)
    with _jobs_lock:
        generation = _jobs.get(key, (0, None))[0] + 1
        previous = _jobs.get(key, (0, None))[1]
        _jobs[key] = (generation, None)
    if previous is not None and previous.is_alive():
        previous.join(timeout=60)  # it stops at its next page
    alive = lambda: _jobs.get(key, (0, None))[0] == generation  # noqa: E731

    out_dir.mkdir(parents=True, exist_ok=True)
    for old in [*out_dir.glob("*.webp"), *out_dir.glob("*.png"), *out_dir.glob("*.ppm"), *out_dir.glob(".*.webp")]:
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
                    if not alive():
                        return
                    _rasterize(pdf, out_dir, start, min(start + 7, total), watermark, dpi, alive)
            except (OSError, subprocess.CalledProcessError):
                pass  # the folder was removed or replaced under us (document deleted, new layout)
            finally:
                if alive():
                    marker.unlink(missing_ok=True)

        thread = threading.Thread(target=rest, daemon=True)
        with _jobs_lock:
            if alive():
                _jobs[key] = (generation, thread)
        thread.start()
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
