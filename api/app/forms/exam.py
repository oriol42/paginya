"""Teacher's exam paper (épreuve), MINESEC-style header.

The teacher types (or pastes) the exercises as plain text; we recognise:
- "Exercice 1 (5 pts)", "Partie A : …", "Problème (8 points)" -> section titles, points right-aligned
- "1) …", "2. …" -> numbered questions (hanging indent); "(2 pts)" at the end -> points right-aligned
- "a) …" -> sub-questions; "A) …" -> multiple-choice options
"""
from __future__ import annotations

import io
import re

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .common import field, new_document, no_borders, para

SECTION = re.compile(
    r"^(exercice|exercise|partie|part|probl[èe]me|problem|section|situation\s+probl[èe]me)\b\s*([ivx\d]+|[a-e])?\s*[:.\-–]?\s*(.*)$",
    re.I,
)
POINTS = re.compile(r"\(?\s*(\d+(?:[.,]\d+)?)\s*(pts?|points?)\s*\)?\s*\.?$", re.I)
QUESTION = re.compile(r"^(\d{1,2})\s*[).\-]\s+(.*)$")
SUBQ = re.compile(r"^([a-h])\s*[).]\s+(.*)$")
OPTION = re.compile(r"^([A-E])\s*[).]\s+(.*)$")

TEXT_W = Cm(21 - 2 - 2)


def _s(data: dict, key: str, default: str = "") -> str:
    return str(data.get(key) or default).strip()[:400]


def split_points(text: str) -> tuple[str, str]:
    m = POINTS.search(text)
    if not m or m.start() == 0:
        return text, ""
    pts = m.group(1).replace(",", ".")
    return text[: m.start()].rstrip(" -–:,"), f"{pts.rstrip('0').rstrip('.') if '.' in pts else pts} pt{'s' if float(pts) > 1 else ''}"


def parse(content: str) -> list[dict]:
    items = []
    for raw in content.replace("\r\n", "\n").split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = SECTION.match(line)
        if m and len(line) < 140:
            body, pts = split_points(line)
            items.append({"kind": "section", "text": body, "points": pts})
            continue
        for kind, rx in (("question", QUESTION), ("sub", SUBQ), ("option", OPTION)):
            m = rx.match(line)
            if m:
                body, pts = split_points(m.group(2))
                items.append({"kind": kind, "label": m.group(1), "text": body, "points": pts})
                break
        else:
            body, pts = split_points(line)
            items.append({"kind": "text", "text": body, "points": pts})
    return items


def total_points(items: list[dict]) -> float:
    sections = [i for i in items if i["kind"] == "section" and i["points"]]
    source = sections or [i for i in items if i["points"]]
    total = 0.0
    for i in source:
        try:
            total += float(i["points"].split()[0])
        except ValueError:
            pass
    return total


def _shade(cell, hex6: str) -> None:
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex6)
    tcpr.append(shd)


def _with_points(p, text: str, points: str, bold=False) -> None:
    p.paragraph_format.tab_stops.add_tab_stop(TEXT_W, WD_TAB_ALIGNMENT.RIGHT)
    run = p.add_run(text)
    run.bold = bold
    if points:
        pr = p.add_run(f"\t({points})")
        pr.bold = True
        pr.font.size = Pt(10.5)


def build_exam(data: dict) -> bytes:
    doc = new_document("Times New Roman", 12, margins=(1.6, 1.6, 2, 2))
    color = _s(data, "color", "0E9F6E").lstrip("#").upper()

    # Header: school (left) | exam facts (right)
    head = doc.add_table(rows=1, cols=2)
    no_borders(head)
    head.autofit = False
    left, right = head.rows[0].cells
    left.width, right.width = Cm(9.5), Cm(7.5)
    lines = []
    if data.get("country", True):
        lines += [("RÉPUBLIQUE DU CAMEROUN", True, False), ("Paix – Travail – Patrie", False, True)]
    lines += [(_s(data, "ministry", "MINISTÈRE DES ENSEIGNEMENTS SECONDAIRES"), True, False)]
    for key in ("delegation", "school", "department"):
        if _s(data, key):
            lines.append((_s(data, key).upper() if key == "school" else _s(data, key), key == "school", False))
    first = True
    for text, bold, italic in lines:
        p = left.paragraphs[0] if first else left.add_paragraph()
        first = False
        run = p.add_run(text)
        run.bold, run.italic = bold, italic
        run.font.size = Pt(9.5)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    facts = [
        ("Année scolaire", _s(data, "year")),
        ("Classe", _s(data, "class")),
        ("Durée", _s(data, "duration")),
        ("Coefficient", _s(data, "coef")),
        ("Examinateur", _s(data, "teacher")),
    ]
    first = True
    for label, value in facts:
        if not value:
            continue
        p = right.paragraphs[0] if first else right.add_paragraph()
        first = False
        p.add_run(f"{label} : ").font.size = Pt(10)
        v = p.add_run(value)
        v.bold = True
        v.font.size = Pt(10)
        p.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    # Title band
    para(doc, "", space_after=6)
    band = doc.add_table(rows=1, cols=1)
    band.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = band.rows[0].cells[0]
    _shade(cell, color)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(4)
    if _s(data, "exam"):
        r = p.add_run(_s(data, "exam").upper())
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor.from_string("FFFFFF")
        p = cell.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(4)
    r = p.add_run(f"ÉPREUVE DE {_s(data, 'subject', 'MATIÈRE').upper()}")
    r.bold = True
    r.font.size = Pt(14)
    r.font.color.rgb = RGBColor.from_string("FFFFFF")

    if _s(data, "instructions"):
        para(doc, _s(data, "instructions"), italic=True, size=10.5, align="center", space_before=8)

    # Body
    items = parse(str(data.get("content") or "")[:60000])
    for it in items:
        k = it["kind"]
        if k == "section":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            _with_points(p, it["text"].upper(), it["points"], bold=True)
            for run in p.runs[:1]:
                run.font.color.rgb = RGBColor.from_string(color)
            bdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            for key, val in (("w:val", "single"), ("w:sz", "6"), ("w:space", "2"), ("w:color", color)):
                bottom.set(qn(key), val)
            bdr.append(bottom)
            p._p.get_or_add_pPr().append(bdr)
        elif k in ("question", "sub", "option"):
            p = doc.add_paragraph()
            indent = {"question": 0.8, "sub": 1.6, "option": 1.6}[k]
            p.paragraph_format.left_indent = Cm(indent)
            p.paragraph_format.first_line_indent = Cm(-0.7)
            p.paragraph_format.space_after = Pt(4)
            label = {"question": f"{it['label']}.", "sub": f"{it['label']})", "option": f"{it['label']}."}[k]
            lab = p.add_run(f"{label} ")
            lab.bold = k == "question"
            _with_points(p, it["text"], it["points"])
        else:
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(6)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _with_points(p, it["text"], it["points"])

    # Footer: page x / y
    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = footer.add_run(f"{_s(data, 'subject', 'Épreuve')} · {_s(data, 'class')} · Page ")
    run.font.size = Pt(9)
    field(footer, "PAGE")
    footer.add_run(" / ").font.size = Pt(9)
    field(footer, "NUMPAGES")
    for r in footer.runs:
        r.font.size = Pt(9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
