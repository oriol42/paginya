"""Keep the user's own Word file and add only what is missing (page numbers, sommaire).

`inspect` looks at a .docx and says what it already has (cover page, sommaire, page numbers),
`touch` writes a copy with the missing parts added, without rebuilding anything: the cover page,
the styles, the sections and the numbering the user made are left exactly as they are.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Pt

from .render import _field

_COVER_WORDS = re.compile(
    r"(?i)\b(par\s*:|présenté|presente|matricule|année\s+(académique|scolaire|universitaire)|encadr|superviseur|"
    r"enseignant|république|republic|université|university|institut|faculté|école|ecole|mémoire|rapport|projet|"
    r"sujet|thème|soutenu|filière|département|niveau|classe|stage|élève|etudiant|étudiant)"
)
_PAGE_FIELD = re.compile(r"(?<![A-Z])PAGE(?![A-Z])")


def _paragraph_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(qn("w:t")))


def _has_page_break(p) -> bool:
    if p.find(".//" + qn("w:pPr") + "/" + qn("w:sectPr")) is not None:
        return True
    if p.find(".//" + qn("w:pPr") + "/" + qn("w:pageBreakBefore")) is not None:
        return True
    return any(br.get(qn("w:type")) == "page" for br in p.iter(qn("w:br")))


def _has_page_field(element) -> bool:
    if element is None:
        return False
    for instr in element.iter(qn("w:instrText")):
        if _PAGE_FIELD.search(instr.text or ""):
            return True
    return any(_PAGE_FIELD.search(f.get(qn("w:instr")) or "") for f in element.iter(qn("w:fldSimple")))


def _section_has_numbers(section) -> bool:
    return any(_has_page_field(part._element) for part in (section.footer, section.first_page_footer, section.header, section.first_page_header))


def _is_heading(paragraph) -> bool:
    name = (paragraph.style.name if paragraph.style is not None else "").lower()
    return name.startswith(("heading", "titre")) and not name.startswith(("titre de", "titre du"))


def _cover_end(doc) -> int | None:
    """Index of the first paragraph after the cover page, or None when the file has no cover page."""
    body = list(doc.element.body.iterchildren(qn("w:p")))[:80]
    lines = 0
    score = 0
    for i, p in enumerate(body):
        text = _paragraph_text(p).strip()
        if text:
            lines += 1
            if _COVER_WORDS.search(text):
                score += 1
        if _has_page_break(p):
            if lines >= 3 and score >= 2 and i < 70:
                return i + 1
            return None
    return None


def inspect(path: Path) -> dict:
    """What the Word file already has: {"cover", "toc", "page_numbers", "sections", "headings"}."""
    doc = Document(str(path))
    body = doc.element.body
    toc = any(re.match(r"\s*TOC\b", i.text or "") for i in body.iter(qn("w:instrText")))
    toc = toc or any((f.get(qn("w:instr")) or "").strip().startswith("TOC") for f in body.iter(qn("w:fldSimple")))
    if not toc:
        toc = any(
            (p.style.name if p.style is not None else "").lower().startswith(("toc", "table des mati", "sommaire"))
            for p in doc.paragraphs
        )
    return {
        "cover": _cover_end(doc) is not None,
        "toc": bool(toc),
        "page_numbers": any(_section_has_numbers(s) for s in doc.sections),
        "sections": len(doc.sections),
        "headings": sum(1 for p in doc.paragraphs if _is_heading(p)),
    }


def touch(src: Path, dst: Path, page_numbers: bool = False, toc: bool = False) -> list[str]:
    """Writes a copy of `src` with page numbers and/or a sommaire added where missing. Returns what was done."""
    doc = Document(str(src))
    done: list[str] = []
    cover_end = _cover_end(doc)

    if page_numbers:
        added = False
        for i, section in enumerate(doc.sections):
            if _section_has_numbers(section):
                continue
            if i == 0 and cover_end is not None:
                if len(doc.sections) > 1:
                    continue  # the cover is a section of its own: it stays without a number
                section.different_first_page_header_footer = True  # one section: the first page (the cover) stays blank
            section.footer.is_linked_to_previous = False
            p = section.footer.paragraphs[0] if section.footer.paragraphs else section.footer.add_paragraph()
            if p.text.strip() and not p.text.strip().isdigit():
                continue  # a footer with its own text: never overwrite it (a bare leftover number is replaced)
            p.text = ""
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _field(p, "PAGE")
            for run in p.runs:
                run.font.size = Pt(10)
            added = True
        if added:
            done.append("numéros de page")

    if toc and not inspect_toc(doc):
        headings = [p for p in doc.paragraphs if _is_heading(p)]
        if headings:
            first = headings[0]
            if cover_end is not None:  # after the cover, before the first heading
                first = next((p for p in headings if p._p.getprevious() is not None), first)
            title = first.insert_paragraph_before("Sommaire")
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in title.runs:
                run.bold = True
                run.font.size = Pt(16)
            marker = first.insert_paragraph_before("[[TOC:2]]")
            marker.paragraph_format.space_after = Pt(12)
            br = first.insert_paragraph_before("")
            br.add_run().add_break(WD_BREAK.PAGE)
            done.append("sommaire")

    dst.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dst))
    return done


def inspect_toc(doc) -> bool:
    body = doc.element.body
    return any(re.match(r"\s*TOC\b", i.text or "") for i in body.iter(qn("w:instrText")))
