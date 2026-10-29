"""What pdftotext loses in a PDF: pictures, diagrams and ruled tables.

The page is drawn once without its text (Ghostscript -dFILTERTEXT): what is left is the graphics. Each
patch of graphics is then
- a picture or diagram: cut out of the page as an image, its words (box labels) dropped from the text;
- a ruled table: rebuilt as a real table from its lines and the words in each cell;
- or only decoration around text (a frame around a title, a coloured band, a small arrow): ignored, the
  text stays text.
Pages without any of these keep pdftotext's own text, so ordinary pages read exactly as before.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

MARK = re.compile(r"^⟦pdf(img|tab):([\w.]+)⟧$")
MAX_PAGES = 700  # drawing + analysis ~15 ms a page over 4 cores; beyond this, text only
CUT_DPI = 150    # pictures cut out of the page
MAX_PER_PAGE = 12  # more pictures and tables than this on one page: the page is misread, it stays text

MM = 72 / 25.4   # the analysis render is at 72 dpi: 1 pixel = 1 point, the unit of pdftotext's boxes


@dataclass
class Region:
    x: float
    y: float
    w: float
    h: float
    fill: float
    tone: float = 0.0                        # mean grey of the drawn pixels (255 = white): a watermark is pale
    kind: str = "figure"                     # figure | table | text (decoration: ignored)
    ink: np.ndarray | None = None             # the drawn pixels of the patch (1 = ink)
    hlines: list[float] = field(default_factory=list)
    vlines: list[float] = field(default_factory=list)

    def holds(self, wx: float, wy: float, pad: float = 2) -> bool:
        return self.x - pad <= wx <= self.x + self.w + pad and self.y - pad <= wy <= self.y + self.h + pad


@dataclass
class Word:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def _runs(mask: np.ndarray) -> list[float]:
    """Centres of the thin runs of True: the ruled lines (a filled shape is wide, not a line)."""
    out, start = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start <= 4:
                out.append((start + i - 1) / 2)
            start = None
    return out


def _graphics(gray: np.ndarray) -> list[Region]:
    """Patches of graphics on a page drawn without its text."""
    H, W = gray.shape
    ink = (gray < 235).astype(np.uint8)
    pad = int(4 * MM)  # parts of one diagram (boxes, arrows) a few millimetres apart belong together
    # A border drawn around the whole page (covers, chapter pages) would hold everything on it in one patch:
    # its band along the edges is wiped first, what it surrounds is looked at on its own.
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    band = int(12 * MM)
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        if w > 0.7 * W and h > 0.7 * H:
            ring = np.zeros_like(ink)
            ring[y:y + h, x:x + w] = 1
            ring[y + band:y + h - band, x + band:x + w - band] = 0
            mine = labels == i
            if (mine & (ring == 1)).sum() >= 0.9 * mine.sum():  # a frame, not a full-page table (lines inside)
                ink[mine] = 0
    n, _, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(ink, np.ones((pad, pad), np.uint8)), 8)
    found = []
    for i in range(1, n):
        x, y, w, h, _ = stats[i]
        x, y, w, h = x + pad // 2, y + pad // 2, w - pad, h - pad
        if w < 12 * MM or h < 8 * MM or w * h > 0.8 * W * H:
            continue  # rules, underlines, bullets / the whole page (a scan under its text, a coloured page)
        box = ink[y:y + h, x:x + w]
        r = Region(float(x), float(y), float(w), float(h), float(box.mean()), float(gray[y:y + h, x:x + w][box > 0].mean()), ink=box)
        m = int(2 * MM)
        inner = ink[y + m:y + h - m, x + m:x + w - m]
        if not inner.size or inner.mean() < 0.01:
            r.kind = "text"  # an empty box drawn around text: a framed title, a page border
        else:
            hl = cv2.morphologyEx(box, cv2.MORPH_OPEN, np.ones((1, max(3, int(w * 0.6))), np.uint8))
            vl = cv2.morphologyEx(box, cv2.MORPH_OPEN, np.ones((max(3, int(h * 0.6)), 1), np.uint8))
            r.hlines = [y + v for v in _runs(hl.any(axis=1))]
            r.vlines = [x + v for v in _runs(vl.any(axis=0))]
            if len(r.hlines) >= 3 and len(r.vlines) >= 2:
                r.kind = "table"
        found.append(r)
    return _merge(found)


def _merge(regions: list[Region]) -> list[Region]:
    """An organigram drawn as separate boxes is one figure: figures touching or a few millimetres apart merge."""
    figs = [r for r in regions if r.kind == "figure"]
    rest = [r for r in regions if r.kind != "figure"]
    changed = True
    while changed:
        changed = False
        for a in range(len(figs)):
            for b in range(a + 1, len(figs)):
                p, q = figs[a], figs[b]
                gap = 6 * MM
                if p.x - gap < q.x + q.w and q.x - gap < p.x + p.w and p.y - gap < q.y + q.h and q.y - gap < p.y + p.h:
                    x, y = min(p.x, q.x), min(p.y, q.y)
                    w, h = max(p.x + p.w, q.x + q.w) - x, max(p.y + p.h, q.y + q.h) - y
                    ink = np.zeros((int(h), int(w)), np.uint8)
                    for z in (p, q):
                        if z.ink is not None:
                            oy, ox = int(z.y - y), int(z.x - x)
                            ink[oy:oy + z.ink.shape[0], ox:ox + z.ink.shape[1]] |= z.ink
                    figs[a] = Region(x, y, w, h, (p.fill * p.w * p.h + q.fill * q.w * q.h) / (w * h), min(p.tone, q.tone), ink=ink)
                    del figs[b]
                    changed = True
                    break
            if changed:
                break
    return figs + rest


def _classify(r: Region, words: list[Word], lines: list[list[Word]], page: int) -> None:
    """Decides, with the words that fall inside, whether a patch of graphics is worth keeping as a picture."""
    inside = [w for w in words if r.holds(w.cx, w.cy)]
    if inside and r.ink is not None and r.ink.any():
        # text drawn as shapes (Type 3 fonts, outlined text): its ink lies under the words pdftotext reads
        under = np.zeros_like(r.ink)
        for w in inside:
            under[max(0, int(w.y0 - r.y) - 1):max(0, int(w.y1 - r.y) + 2), max(0, int(w.x0 - r.x) - 1):max(0, int(w.x1 - r.x) + 2)] = 1
        if (r.ink & under).sum() > 0.7 * r.ink.sum():
            r.kind = "text"
            return
    if r.kind in ("table", "figure") and _banner(r, inside, lines):
        r.kind = "text"  # its outline can look like a one-cell table
        return
    if r.kind == "table":
        cols = max(0, len(r.vlines) - 1) or 1
        if inside and (cols >= 2 or len(r.hlines) >= 4):
            return
        r.kind = "figure"  # two boxes one above the other in a diagram, the end of a table on the next page…
        # …which the tests below may still find to be text in a frame
    if r.kind != "figure":
        return
    small = max(r.w, r.h) < 25 * MM or r.w * r.h < 900 * MM * MM
    if small and (page > 2 or inside):
        # an arrow or an icon in the text, a page number in a little box; on the first pages, small pictures
        # without words are the logos
        r.kind = "text"
        return
    sentences = sum(1 for ws in lines if any(r.holds(w.cx, w.cy) for w in ws) and sum(len(w.text) + 1 for w in ws) > 45)
    if r.tone > 215 or sentences >= 2 and r.tone > 185:
        r.kind = "text"  # a watermark: a pale picture with the text running over it
        return
    if not inside:
        return  # a photo, a logo, a chart drawn without text
    # sentences inside the patch (pdftotext's lines: the labels of separate boxes are separate lines)
    long_lines = sum(1 for ws in lines if all(r.holds(w.cx, w.cy) for w in ws) and sum(len(w.text) + 1 for w in ws) > 45)
    # share of the patch covered by words: a title on a coloured band is mostly words, a chart only a few labels
    covered = sum((w.x1 - w.x0) * (w.y1 - w.y0) for w in inside) / max(1.0, r.w * r.h)
    if r.fill > 0.5 and covered > 0.08 or long_lines >= 3 or _text_box(r, lines):
        r.kind = "text"  # a coloured band or a shaded box behind sentences: the text is the content


def _text_box(r: Region, lines: list[list[Word]]) -> bool:
    """Text in a frame (an algorithm, a definition, a box of advice): five lines or more, most of them starting
    at the same left margin. The labels of a diagram are spread over its boxes, or centred in them."""
    own = [ws for ws in lines if all(r.holds(w.cx, w.cy) for w in ws)]
    if len(own) < 5 or r.fill > 0.3:
        return False
    lefts = sorted(round(min(w.x0 for w in ws)) for ws in own)
    best = max(sum(1 for x in lefts if a <= x <= a + 3) for a in lefts)
    return best >= 0.6 * len(own)


def _banner(r: Region, inside: list[Word], lines: list[list[Word]]) -> bool:
    """A title drawn in a shape ("DÉDICACE" in a blue scroll, "CHAPITRE I : …" in a banner): one to three short
    lines in the middle of a filled shape. A chart or a map has its labels spread out, a photo none."""
    own = [ws for ws in lines if all(r.holds(w.cx, w.cy) for w in ws)]
    # filled, or only an outline wide and low ("SERMENT DE PROBITÉ" in a rounded frame): a chart is neither
    framed = r.fill >= 0.3 or r.w >= 2 * r.h
    if not framed or not 1 <= len(own) <= 3 or sum(len(w.text) + 1 for ws in own for w in ws) > 160:
        return False
    if len(inside) != sum(len(ws) for ws in own):
        return False  # words of other lines (labels) inside
    x0, x1 = min(w.x0 for w in inside), max(w.x1 for w in inside)
    y0, y1 = min(w.y0 for w in inside), max(w.y1 for w in inside)
    return abs((x0 + x1) / 2 - (r.x + r.w / 2)) < 0.2 * r.w and abs((y0 + y1) / 2 - (r.y + r.h / 2)) < 0.3 * r.h


def _words(xml: str) -> dict[int, list[list[list[list[Word]]]]]:
    """pdftotext -bbox-layout: page -> flows -> blocks -> lines -> words, in pdftotext's reading order."""
    xml = re.sub(r"<!DOCTYPE[^>]*>", "", xml)
    root = ET.fromstring(xml)
    ns = {"h": "http://www.w3.org/1999/xhtml"}
    pages = {}
    for p, page in enumerate(root.iter("{http://www.w3.org/1999/xhtml}page"), 1):
        flows = []
        for flow in page.findall("h:flow", ns):
            blocks = []
            for block in flow.findall("h:block", ns):
                lines = []
                for line in block.findall("h:line", ns):
                    ws = [Word(w.text or "", *(float(w.get(k)) for k in ("xMin", "yMin", "xMax", "yMax"))) for w in line.findall("h:word", ns)]
                    if ws:
                        lines.append(ws)
                blocks.append(lines)
            flows.append(blocks)
        pages[p] = flows
    return pages


def _table_rows(r: Region, words: list[Word]) -> list[list[str]]:
    xs = sorted(r.vlines)
    if xs[0] - r.x > 10:
        xs = [r.x] + xs  # tables drawn without side borders
    if r.x + r.w - xs[-1] > 10:
        xs.append(r.x + r.w)
    ys = sorted(r.hlines)
    if ys[0] - r.y > 10:
        ys = [r.y] + ys
    if r.y + r.h - ys[-1] > 10:
        ys.append(r.y + r.h)
    cells: dict[tuple[int, int], list[Word]] = {}
    for w in words:
        if not r.holds(w.cx, w.cy):
            continue
        row = next((k for k in range(len(ys) - 1) if w.cy <= ys[k + 1]), len(ys) - 2)
        col = next((k for k in range(len(xs) - 1) if w.cx <= xs[k + 1]), len(xs) - 2)
        cells.setdefault((row, col), []).append(w)
    rows = []
    for k in range(len(ys) - 1):
        row = []
        for c in range(len(xs) - 1):
            ws = sorted(cells.get((k, c), []), key=lambda w: (round(w.cy / 4), w.x0))
            row.append(" ".join(w.text for w in ws))
        if any(row):
            rows.append(row)
    return rows


def _gs_pages(pdf: Path, pages: list[int], out: str, args: list[str], timeout: int) -> dict[int, str]:
    """Draws the given pages with Ghostscript, split over the processor's cores (gs draws one page at a time):
    {page: image file}. `out` is the file prefix; each part numbers its own outputs."""
    parts = max(1, min(os.cpu_count() or 1, 4, len(pages) // 4 or 1))
    chunks = [pages[k::parts] for k in range(parts)]
    procs = []
    for n, chunk in enumerate(chunks):
        cmd = ["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-dUseCropBox", *args, f"-sPageList={','.join(map(str, chunk))}",
               "-o", f"{out}-{n}-%04d", str(pdf)]
        procs.append(subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    try:
        for proc in procs:
            if proc.wait(timeout=timeout) != 0:
                raise subprocess.CalledProcessError(proc.returncode, "gs")
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.kill()
    return {page: f"{out}-{n}-{k:04d}" for n, chunk in enumerate(chunks) for k, page in enumerate(chunk, 1)}


def _cut_all(pdf: Path, cuts: list[tuple[int, Region, str]], images_dir: Path) -> set[str]:
    """The patches, text included, cut out of their pages at a printable resolution. The pages are drawn in one
    pass (reading a big PDF once per picture took minutes). Returns the names really saved."""
    pages = sorted({p for p, _, _ in cuts})
    s = CUT_DPI / 72
    m = 3  # a little margin: frames drawn on the edge stay whole
    saved = set()
    with tempfile.TemporaryDirectory() as tmp:
        files = _gs_pages(pdf, pages, f"{tmp}/c", ["-sDEVICE=ppmraw", f"-r{CUT_DPI}", "-dTextAlphaBits=4", "-dGraphicsAlphaBits=4"], 300)
        for page in pages:
            img = cv2.imread(files[page])
            if img is None:
                continue
            H, W = img.shape[:2]
            for p, r, name in cuts:
                if p != page:
                    continue
                x0, y0 = max(0, int((r.x - m) * s)), max(0, int((r.y - m) * s))
                x1, y1 = min(W, int((r.x + r.w + m) * s)), min(H, int((r.y + r.h + m) * s))
                if x1 > x0 and y1 > y0 and cv2.imwrite(str(images_dir / name), img[y0:y1, x0:x1]):
                    saved.add(name)
    return saved


def _page_text(text: str, lines: list[list[Word]], regions: list[Region], marks: list[tuple[Region, str]]) -> str:
    """pdftotext's own page, left as it is (its order of lines, lists and columns), minus the lines that sit
    inside kept regions, with a marker line where each region is. pdftotext's boxes and its text come from the
    same reading: line k of the boxes is the next raw line with the same words."""
    raw = text.split("\n")
    at: list[int | None] = []  # raw line of each box line
    ptr = 0
    for ws in lines:
        s = " ".join(w.text for w in ws)
        j = next((k for k in range(ptr, min(len(raw), ptr + 40)) if raw[k].strip() == s), None)
        at.append(j)
        if j is not None:
            ptr = j + 1
    drop: set[int] = set()
    anchor: dict[int, int] = {}  # raw line -> index of the mark that goes before it
    for n, (r, _) in enumerate(marks):
        first = None
        for ws, j in zip(lines, at):
            if j is None:
                continue
            if all(r.holds(w.cx, w.cy) for w in ws):
                drop.add(j)
                first = j if first is None else min(first, j)
        if first is None:  # a picture without words: before the first line under it, in its column
            first = next((j for ws, j in zip(lines, at) if j is not None and min(w.y0 for w in ws) >= r.y
                          and r.x < max(w.x1 for w in ws) and min(w.x0 for w in ws) < r.x + r.w), len(raw))
        anchor.setdefault(first, n)
    out: list[str] = []
    placed = set()
    for k in range(len(raw) + 1):
        for n, (_, m) in enumerate(marks):
            if n not in placed and anchor.get(k) == n:
                out += ["", m, ""]
                placed.add(n)
        if k < len(raw) and k not in drop:
            out.append(raw[k])
    out += [m for n, (_, m) in enumerate(marks) if n not in placed]
    return "\n".join(out)


def _scanned_pages(pdf: Path, sizes: dict[int, tuple[int, int]]) -> set[int]:
    """Pages that are one big picture (a scan, with or without a hidden text layer): every blot of ink on them
    would look like a figure. pdfimages lists the pictures without decoding them."""
    try:
        listing = subprocess.run(["pdfimages", "-list", str(pdf)], capture_output=True, text=True, timeout=60, check=True).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return set()
    out = set()
    for row in listing.splitlines()[2:]:
        f = row.split()
        try:
            page, w, h, xppi, yppi = int(f[0]), int(f[3]), int(f[4]), float(f[12]), float(f[13])
        except (IndexError, ValueError):
            continue
        H, W = sizes.get(page, (0, 0))
        if W and xppi and yppi and w * 72 / xppi * h * 72 / yppi > 0.6 * W * H:
            out.add(page)
    return out


def layout(pdf: Path, pages_text: list[str], images_dir: Path) -> tuple[list[str], dict[str, list[list[str]]]]:
    """pdftotext's pages with pictures and tables put back: (pages, {marker: table rows, or [] for a picture}).
    Only these markers count: the same characters typed in the PDF's own text stay text. Any failure: the text as it was."""
    tables: dict[str, list[list[str]]] = {}
    if len(pages_text) > MAX_PAGES:
        return pages_text, tables
    try:
        info = subprocess.run(["pdfinfo", "-f", "1", "-l", str(len(pages_text)), str(pdf)], capture_output=True, text=True, timeout=60).stdout
        sizes = {int(m[1]): (round(float(m[3])), round(float(m[2]))) for m in re.finditer(r"^Page\s+(\d+) size:\s+([\d.]+) x ([\d.]+)", info, re.M)}
        scanned = _scanned_pages(pdf, sizes)
        if sizes and scanned >= set(sizes):
            return pages_text, tables  # a scanned document: nothing to find in its graphics
        todo = [p for p in (sorted(sizes) or range(1, len(pages_text) + 1)) if p not in scanned]
        with tempfile.TemporaryDirectory() as tmp:
            # only the pages that are not scans; gs numbers its outputs 1, 2, 3… in the order of the list
            files = _gs_pages(pdf, todo, f"{tmp}/p", ["-dFILTERTEXT", "-sDEVICE=pgmraw", "-r72"], 180)  # raw: 2.5× faster than PNG

            def look(page: int) -> list[Region]:
                gray = cv2.imread(files[page], cv2.IMREAD_GRAYSCALE)
                return _graphics(gray) if gray is not None else []

            with ThreadPoolExecutor(min(4, os.cpu_count() or 1)) as pool:  # OpenCV works outside the GIL
                graphics = {page: found for page, found in zip(todo, pool.map(look, todo)) if found}
        if not any(r.kind != "text" for rs in graphics.values() for r in rs):
            return pages_text, tables
        xml = subprocess.run(["pdftotext", "-enc", "UTF-8", "-bbox-layout", str(pdf), "-"], capture_output=True, timeout=120, check=True).stdout
        words = _words(xml.decode("utf-8", "replace"))
    except (subprocess.SubprocessError, FileNotFoundError, ET.ParseError, cv2.error):
        return pages_text, tables
    images_dir.mkdir(parents=True, exist_ok=True)
    out = list(pages_text)
    cuts: list[tuple[int, Region, str]] = []
    for page, regions in graphics.items():
        flows = words.get(page)
        if flows is None or page > len(out):
            continue
        all_lines = [ws for blocks in flows for lines in blocks for ws in lines]
        all_words = [w for ws in all_lines for w in ws]
        for r in regions:
            _classify(r, all_words, all_lines, page)
        kept = _merge([r for r in regions if r.kind != "text"])  # a frame taken for a table holds the picture inside
        if not kept or len(kept) > MAX_PER_PAGE:
            continue  # nothing / a page whose text is drawn in a way we do not understand: left as text
        marks = []
        for r in kept:
            if r.kind == "table" and (rows := _table_rows(r, all_words)) and len(rows) >= 2:
                mark = f"⟦pdftab:{uuid.uuid4().hex[:12]}⟧"
                tables[mark] = rows
            else:
                name = f"{uuid.uuid4().hex}.png"
                mark = f"⟦pdfimg:{name}⟧"
                cuts.append((page, r, name))
            marks.append((r, mark))
        out[page - 1] = _page_text(out[page - 1], all_lines, kept, marks)
    if cuts:
        try:
            saved = _cut_all(pdf, cuts, images_dir)
        except (subprocess.SubprocessError, FileNotFoundError, cv2.error):
            saved = set()
        # a picture that could not be cut leaves only its marker, which from_pdf drops
        tables.update({f"⟦pdfimg:{name}⟧": [] for _, _, name in cuts if name in saved})
    return out, tables
