"""Turn an uploaded file or pasted text into a flat list of raw paragraphs.

A raw paragraph carries the text plus whatever formatting hints the source
gives us (Word styles, bold, font size, list numbering, indentation). The
detector then decides what each paragraph *is*.
"""
from __future__ import annotations

import re
import subprocess
import uuid
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


@dataclass
class Raw:
    text: str = ""
    style: str = ""          # lowercased Word style name ("heading 1", "titre 2", "list bullet"...)
    bold: bool = False       # every visible run is bold
    size: float = 0.0        # largest font size in points (0 = unknown)
    centered: bool = False
    indent: int = 0          # list level or indentation level
    list_kind: str = ""      # "", "bullet" or "number" (from Word numbering)
    rows: list[list[str]] = field(default_factory=list)  # table
    image: str = ""          # stored image file name (figure)
    source: str = "text"     # text | docx | pdf | md
    explicit: bool = False   # structure given by the source (Markdown): never guessed over


class ExtractError(ValueError):
    pass


# --- Plain text / PDF ------------------------------------------------------

_END = re.compile(r"[.:;!?»\"')\]]$")


_CONNECT = re.compile(r"(?:^|\s)(de|du|des|la|le|les|l['’]|d['’]|et|à|en|pour|par|au|aux|sur|dans|un|une|avec|qui|que|ou|son|sa|ses|leur|leurs|ce|cette|notre|nos|of|the|and)$", re.I)
_STARTS_BLOCK = re.compile(r"^([-–—•*➢►▪❖◆■●○➤]|\d+(\.\d+)*[.)\-–]\s|[IVX]+[.)\-–]\s|[a-z][.)]\s|chapitre|partie|section)", re.I)


def _cut(prev: str, nxt: str, strict: bool = False) -> bool:
    """PDF hard wrap: the sentence of `prev` goes on in `nxt`.
    strict (across an empty line): only when `prev` visibly stops mid-sentence."""
    if not prev or not nxt or _END.search(prev) or _STARTS_BLOCK.match(nxt) or (nxt.isupper() and len(nxt) > 3):
        return False
    if _CONNECT.search(prev):
        return True  # "… des Sciences et" / "Techniques …"
    if strict:
        return nxt[:1].islower() and len(prev) > 20
    return (len(prev) > 45 and (nxt[:1].islower() or nxt[:1].isdigit())) or len(prev) >= 78  # full justified line


def from_text(text: str, source: str = "text") -> list[Raw]:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lines = [ln.rstrip() for ln in text.split("\n")]
    paras: list[Raw] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            joined = " ".join(s.strip() for s in buf)
            paras.append(Raw(text=re.sub(r"[ \t]+", " ", joined).strip(), indent=_indent(buf[0]), source=source))
            buf.clear()

    def next_text(i: int) -> str:
        for ln in lines[i + 1:i + 4]:
            if ln.strip():
                return ln.strip()
        return ""

    for i, line in enumerate(lines):
        if not line.strip():
            # PDF: a sentence cut around a picture continues after an empty line ("… l'effervescence du" / "mouvement")
            if source == "pdf" and buf and _cut(buf[-1].strip(), next_text(i), strict=True):
                continue
            flush()
            continue
        if "\t" in line.strip() or " | " in line:
            flush()
            paras.append(Raw(text=line.strip(), indent=_indent(line), source=source))
            continue
        if buf:
            prev = buf[-1].strip()
            # PDF-style hard wraps: previous line long, unfinished, next starts lowercase.
            wrapped = source == "pdf" and _cut(prev, line.strip())
            if wrapped:
                buf.append(line)
                continue
            flush()
        buf.append(line)
    flush()
    return [p for p in paras if p.text]


# --- Markdown ----------------------------------------------------------------

_MD_HEAD = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_MD_ITEM = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])\s+(.*)$")
_MD_RULE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
_MD_FENCE = re.compile(r"^\s{0,3}(```|~~~)")
_MD_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
_MD_HINTS = [re.compile(p, re.M) for p in (r"^#{1,6}\s+\S", r"\*\*[^*\n]+\*\*", r"^```", r"^\|.*\|\s*$", r"^>\s")]


def looks_like_markdown(text: str) -> bool:
    """Pasted text written in Markdown (from ChatGPT, Notion, GitHub...): at least two different signs."""
    return sum(bool(p.search(text)) for p in _MD_HINTS) >= 2


def strip_inline(text: str) -> str:
    """Text without Markdown emphasis markers (for headings, titles, table of contents)."""
    text = re.sub(r"(\*\*|__)(.+?)\1", r"\2", text)
    text = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"\1", text)
    return re.sub(r"`([^`]+)`", r"\1", text).strip()


def from_markdown(text: str) -> list[Raw]:
    """Markdown keeps its structure as written: # headings, lists, tables, code blocks, quotes.

    Inline **bold**, *italic* and `code` stay in the text; the renderer turns them into real formatting.
    A single leading "# Title" becomes the document title (and a heading right under it, its subtitle).
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ").split("\n")
    out: list[Raw] = []
    buf: list[str] = []
    quote: list[str] = []

    def raw(**kw) -> Raw:
        return Raw(source="md", explicit=True, **kw)

    def flush() -> None:
        if buf:
            out.append(raw(text=re.sub(r"[ \t]+", " ", " ".join(s.strip() for s in buf)).strip()))
            buf.clear()
        if quote:
            out.append(raw(text=" ".join(quote).strip(), style="quote"))
            quote.clear()

    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if not s:
            flush()
            i += 1
            continue
        if _MD_FENCE.match(line):
            flush()
            fence = _MD_FENCE.match(line).group(1)
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith(fence):
                code.append(lines[i].rstrip())
                i += 1
            i += 1
            while code and not code[-1].strip():
                code.pop()
            if code:
                out.append(raw(text="\n".join(code), style="code"))
            continue
        if _MD_RULE.match(line):
            flush()
            i += 1
            continue
        m = _MD_HEAD.match(s)
        if m:
            flush()
            if m.group(2):
                out.append(raw(text=strip_inline(m.group(2)), style=f"heading {len(m.group(1))}"))
            i += 1
            continue
        if s.startswith("|") and i + 1 < len(lines) and _MD_TABLE_SEP.match(lines[i + 1]):
            flush()
            rows = [_md_cells(s)]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_md_cells(lines[i].strip()))
                i += 1
            out.append(raw(rows=rows))
            continue
        if s.startswith(">"):
            if buf:
                flush()
            quote.append(s.lstrip(">").strip())
            i += 1
            continue
        m = _MD_ITEM.match(line)
        if m:
            flush()
            depth = len(m.group(1).replace("\t", "    ")) // 2
            out.append(raw(text=m.group(3).strip(), list_kind="number" if m.group(2)[0].isdigit() else "bullet", indent=min(depth, 2)))
            i += 1
            continue
        if out and out[-1].list_kind and not buf and line[:1] in (" ", "\t"):
            out[-1].text += " " + s  # continuation of a list item
            i += 1
            continue
        if quote:
            flush()
        buf.append(s)
        if line.endswith("  ") or line.endswith("\\"):
            flush()  # explicit line break
        i += 1
    flush()
    return _md_title(out)


def _md_cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def _md_title(raws: list[Raw]) -> list[Raw]:
    """One "# Title" at the top = the document's title; the other levels move up to fill the gap."""
    heads = [r for r in raws if r.style.startswith("heading ")]
    if not heads:
        return raws
    levels = sorted({int(r.style[-1]) for r in heads})
    first = raws[0]
    if first.style == "heading 1" and sum(r.style == "heading 1" for r in heads) == 1 and len(heads) > 1:
        first.style = "doctitle"
        if len(raws) > 1 and raws[1].style.startswith("heading ") and int(raws[1].style[-1]) > min(
                (int(r.style[-1]) for r in heads[1:] if r is not raws[1]), default=9):
            raws[1].style = "docsubtitle"  # "### ENSPD — Préparation concours" right under the title
        levels = sorted({int(r.style[-1]) for r in raws if r.style.startswith("heading ")})
    remap = {lvl: min(i + 1, 4) for i, lvl in enumerate(levels)}
    for r in raws:
        if r.style.startswith("heading "):
            r.style = f"heading {remap[int(r.style[-1])]}"
    return raws


def _indent(line: str) -> int:
    expanded = line.replace("\t", "    ")
    return (len(expanded) - len(expanded.lstrip(" "))) // 3


# Word PDFs whose embedded fonts lack a character map come out shifted: "6WDJH HIIHFWXp" for "Stage effectué".
# ASCII glyphs sit 29 below their letter; accented ones follow the Mac glyph order, one place off.
_MAC_ACCENTS = "ÄÅÇÉÑÖÜáàâäãåçéèêëíìîïñóòôöõúùûü"  # Mac standard glyph order, from index 97
_SPECIAL = {"¶": "’", "³": "«", "´": "»", "\x10": "-", "\x03": " "}
_FUNC = set("le la les de des du et en un une pour par dans au aux sur est que qui à ou ce cette son sa ses avec".split())
_WORD = re.compile(r"^[A-ZÀ-Ý]?[a-zà-ÿ'’\-]+[.,;:]?$")


def _unshift(line: str) -> str:
    out = []
    for ch in line:
        o = ord(ch)
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
        elif ch == " ":
            out.append(ch)  # real spaces come from the text positions, not from the font
        elif 3 <= o <= 93:
            out.append(chr(o + 29))
        elif 98 <= o < 98 + len(_MAC_ACCENTS):
            out.append(_MAC_ACCENTS[o - 98])
        else:
            out.append(ch)
    return "".join(out)


def _readability(line: str) -> int:
    words = line.split()
    return sum(1 for w in words if _WORD.match(w) and re.search(r"[aeiouyéèêàâîôû]", w.lower())) + 3 * sum(1 for w in words if w.lower().strip(".,;:") in _FUNC)


def fix_shifted_fonts(text: str) -> tuple[str, int]:
    """Decodes the lines that read far better shifted back (line by line: other fonts of the page are fine)."""
    fixed, lines = 0, []
    for line in text.split("\n"):
        if line.strip() and not line.isascii() or re.search(r"[A-Z]{2,}[a-z]?[A-Z]|[0-9][A-Z]{2}", line):
            dec = _unshift(line)
            if _readability(dec) > _readability(line) + 1:
                lines.append(dec)
                fixed += 1
                continue
        lines.append(line)
    return "\n".join(lines), fixed


_LEADERS = re.compile(r"(\.\s?){6,}\s*([0-9ivxlc]+)?\s*$|…{3,}\s*\d*\s*$", re.I)
_LABEL = re.compile(r"^(\d+(\.\d+)*|[a-zA-Z]|[ivxlcIVXLC]{1,6})\s*[.)\-–]$")
_PAGE_NO = re.compile(r"^(page\s*)?[-–]?\s*([0-9]{1,3}|[ivxlc]{1,6})\s*[-–]?$", re.I)


def pdf_cleanup(text: str) -> str:
    """What a PDF adds around the text: running headers/footers, page numbers, the old typed table of
    contents (dot leaders), numbering labels put on their own line. Pages are separated by form feeds."""
    pages = [p.split("\n") for p in text.split("\f")]
    norm = lambda s: re.sub(r"\d+", "#", s.strip().lower())  # noqa: E731
    # 1. running headers / footers: the same line at the top or bottom of many pages
    edges = Counter()
    for lines in pages:
        body = [ln for ln in lines if ln.strip()]
        for ln in {norm(x) for x in body[:3] + body[-3:]}:
            edges[ln] += 1
    repeated = {ln for ln, n in edges.items() if n >= max(3, len(pages) * 0.3) and len(ln) < 160}
    out: list[str] = []
    for lines in pages:
        body_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        edge = set(body_idx[:3] + body_idx[-3:])
        for i, ln in enumerate(lines):
            if i in edge and (norm(ln) in repeated or _PAGE_NO.match(ln.strip())):
                continue
            out.append(ln)
        out.append("")
    # 2. the old table of contents: runs of dot-leader lines, with the pieces between them
    leader = [i for i, ln in enumerate(out) if _LEADERS.search(ln)]
    drop: set[int] = set()
    for a, b in zip(leader, leader[1:]):
        if b - a <= 6:
            drop.update(range(a, b + 1))
    for i in leader:
        drop.add(i)
        j = i - 1  # an entry wrapped on two lines: its first half sits just above the leader line
        while j >= 0 and not out[j].strip():
            j -= 1
        if j >= 0 and j not in drop and len(out[j]) < 120 and not _LEADERS.search(out[j]) and (j - 1 in drop or _LABEL.match(out[j].strip()) or re.search(r"\b(sommaire|table des mati)", out[j], re.I)):
            drop.add(j)
    lines = [ln for i, ln in enumerate(out) if i not in drop]
    # 3. "2." alone on its line, the title on the next one
    merged: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if _LABEL.match(ln.strip()):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and not _LABEL.match(lines[j].strip()) and len(lines[j].strip()) > 1:
                merged.append(f"{ln.strip()} {lines[j].strip()}")
                i = j + 1
                continue
        merged.append(ln)
        i += 1
    # 4. the words of a diagram (organigram boxes) come out as a burst of tiny lines: keep them, on one line,
    #    rather than letting each become a fake heading
    frag = lambda s: 0 < len(s.strip()) <= 22 and len(s.split()) <= 3 and not s.strip().endswith((":", ".", ";")) and not _LABEL.match(s.strip()) and not _STARTS_BLOCK.match(s.strip())  # noqa: E731
    final: list[str] = []
    run: list[str] = []

    def flush() -> None:
        if len(run) >= 6:
            final.append(" · ".join(x.strip() for x in run))
        else:
            final.extend(run)
        run.clear()

    for ln in merged:
        if frag(ln):
            run.append(ln)
        elif not ln.strip() and run:
            continue
        else:
            flush()
            final.append(ln)
    flush()
    return "\n".join(final)


def _pdftotext(path: Path) -> str:
    out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=60, check=True)
    return out.stdout.decode("utf-8", "replace")


def from_pdf(path: Path) -> list[Raw]:
    try:
        raw = _pdftotext(path)
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        # Damaged or cut-off PDF (WhatsApp transfers...): Ghostscript rebuilds what it can read.
        repaired = path.with_name(path.stem + ".repaired.pdf")
        try:
            subprocess.run(["gs", "-q", "-o", str(repaired), "-sDEVICE=pdfwrite", str(path)], capture_output=True, timeout=120)
            raw = _pdftotext(repaired)
        except (subprocess.SubprocessError, FileNotFoundError):
            raise ExtractError("Impossible de lire ce PDF : il est peut-être abîmé. Réessaie avec le fichier Word.") from exc
    text, _ = fix_shifted_fonts(raw)
    text = pdf_cleanup(text)
    if len(text.strip()) < 20:
        text = _ocr_pdf(path)  # a scanned document: read its pages like photos
    return from_text(text, source="pdf")


OCR_MAX_PAGES = 25  # the free server reads ~1 page every few seconds


def _ocr_pdf(path: Path) -> str:
    """Scanned PDF (only pictures of pages): each page rasterised then read by Tesseract, pages kept apart."""
    import tempfile

    from .scan import ScanError, ocr_local

    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(["pdftoppm", "-r", "200", "-gray", "-jpeg", "-l", str(OCR_MAX_PAGES), str(path), f"{tmp}/p"],
                           capture_output=True, timeout=300, check=True)
        except (subprocess.SubprocessError, FileNotFoundError) as exc:
            raise ExtractError("Impossible de lire ce PDF : il est peut-être abîmé. Réessaie avec le fichier Word.") from exc
        pages = []
        for jpg in sorted(Path(tmp).glob("p-*.jpg")):
            try:
                pages.append(ocr_local(jpg.read_bytes())[0])
            except ScanError:
                continue
    text = "\n\n".join(p for p in pages if p.strip())
    if len(text.strip()) < 20:
        raise ExtractError("Ce PDF ne contient pas de texte lisible. Prends plutôt tes pages en photo, bien à plat.")
    return text


# --- Word ------------------------------------------------------------------

def _numbering_formats(doc) -> dict[tuple[str, str], str]:
    """(numId, ilvl) -> numFmt ("bullet", "decimal", "lowerLetter"...)."""
    try:
        numbering = doc.part.numbering_part.element
    except (KeyError, NotImplementedError, AttributeError):
        return {}
    abstract: dict[str, dict[str, str]] = {}
    for an in numbering.findall(qn("w:abstractNum")):
        levels = {}
        for lvl in an.findall(qn("w:lvl")):
            fmt = lvl.find(qn("w:numFmt"))
            levels[lvl.get(qn("w:ilvl"))] = fmt.get(qn("w:val")) if fmt is not None else "decimal"
        abstract[an.get(qn("w:abstractNumId"))] = levels
    result: dict[tuple[str, str], str] = {}
    for num in numbering.findall(qn("w:num")):
        ref = num.find(qn("w:abstractNumId"))
        if ref is None:
            continue
        for ilvl, fmt in abstract.get(ref.get(qn("w:val")), {}).items():
            result[(num.get(qn("w:numId")), ilvl)] = fmt
    return result


def _style_chain_bold(style) -> bool:
    while style is not None:
        if style.font is not None and style.font.bold is not None:
            return bool(style.font.bold)
        style = style.base_style
    return False


def _style_size(style) -> float:
    while style is not None:
        if style.font is not None and style.font.size is not None:
            return style.font.size.pt
        style = style.base_style
    return 0.0


def _paragraph(p: Paragraph, fmts: dict, images_dir: Path, doc) -> Raw:
    style = p.style
    raw = Raw(text=p.text.strip(), style=(style.name or "").lower() if style is not None else "", source="docx")
    runs = [r for r in p.runs if r.text.strip()]
    style_bold = _style_chain_bold(style)
    if runs:
        raw.bold = all((r.bold if r.bold is not None else style_bold) for r in runs)
        sizes = [r.font.size.pt for r in runs if r.font.size is not None]
        raw.size = max(sizes) if sizes else _style_size(style)
    raw.centered = p.alignment is not None and int(p.alignment) == 1  # CENTER

    ppr = p._p.pPr
    num_pr = ppr.numPr if ppr is not None else None
    if num_pr is not None and num_pr.numId is not None and num_pr.numId.val != 0:
        ilvl = str(num_pr.ilvl.val) if num_pr.ilvl is not None else "0"
        fmt = fmts.get((str(num_pr.numId.val), ilvl), "decimal")
        raw.list_kind = "bullet" if fmt == "bullet" else "number"
        raw.indent = int(ilvl)
    elif "list bullet" in raw.style or "liste à puces" in raw.style:
        raw.list_kind = "bullet"
    elif "list number" in raw.style or "liste numéro" in raw.style:
        raw.list_kind = "number"

    for blip in p._p.iter(qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        if not rid or rid not in doc.part.related_parts:
            continue
        part = doc.part.related_parts[rid]
        ext = Path(getattr(part, "partname", "img.png")).suffix.lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp"):
            continue
        name = f"{uuid.uuid4().hex}{ext}"
        (images_dir / name).write_bytes(part.blob)
        raw.image = name
        break
    return raw


def from_docx(path: Path, images_dir: Path) -> list[Raw]:
    try:
        doc = DocxDocument(str(path))
    except Exception as exc:  # python-docx raises many types on corrupt files
        raise ExtractError("Ce fichier Word est illisible ou protégé") from exc
    images_dir.mkdir(parents=True, exist_ok=True)
    fmts = _numbering_formats(doc)
    out: list[Raw] = []
    for el in doc.element.body.iterchildren():
        if el.tag == qn("w:p"):
            raw = _paragraph(Paragraph(el, doc), fmts, images_dir, doc)
            if raw.text or raw.image:
                out.append(raw)
        elif el.tag == qn("w:tbl"):
            table = Table(el, doc)
            rows = []
            for row in table.rows:
                cells = []
                for cell in row.cells:
                    cells.append(" ".join(par.text.strip() for par in cell.paragraphs).strip())
                # merged cells repeat: collapse consecutive duplicates
                dedup = [c for i, c in enumerate(cells) if i == 0 or c != cells[i - 1] or not c]
                rows.append(dedup)
            if rows and any(any(c for c in r) for r in rows):
                out.append(Raw(rows=rows, source="docx"))
    return out


def body_size(raws: list[Raw]) -> float:
    """Most common font size weighted by characters (the body text size)."""
    c: Counter[float] = Counter()
    for r in raws:
        if r.size and r.text:
            c[round(r.size)] += len(r.text)
    return float(c.most_common(1)[0][0]) if c else 0.0
