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

    for i, line in enumerate(lines):
        if not line.strip():
            flush()
            continue
        if "\t" in line.strip() or " | " in line:
            flush()
            paras.append(Raw(text=line.strip(), indent=_indent(line), source=source))
            continue
        if buf:
            prev = buf[-1].strip()
            # PDF-style hard wraps: previous line long, unfinished, next starts lowercase.
            wrapped = (
                source == "pdf" and len(prev) > 45 and not _END.search(prev)
                and (line.strip()[:1].islower() or line.strip()[:1].isdigit())
            )
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


def from_pdf(path: Path) -> list[Raw]:
    try:
        out = subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], capture_output=True, timeout=60, check=True)
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        raise ExtractError("Impossible de lire ce PDF") from exc
    text = out.stdout.decode("utf-8", "replace").replace("\f", "\n\n")
    if len(text.strip()) < 20:
        raise ExtractError("Ce PDF ne contient pas de texte (c'est peut-être un scan). Les photos et scans arrivent bientôt.")
    return from_text(text, source="pdf")


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
