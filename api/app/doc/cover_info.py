"""Reads the student's own cover page (the lines before the first heading) into cover fields.

Cameroonian school covers follow one pattern: a bilingual header (République du Cameroun,
ministry, university, faculty, department), the document type, the title ("Thème : ..."),
"Présenté par" + names, "Sous la direction de / Encadreur" + names, the academic year.
When the region looks like such a cover, its lines are returned as fields and hidden from
the text: Paginya's cover page replaces them (the user can show them again in the Plan).
"""
from __future__ import annotations

import re
import unicodedata

HEADER = re.compile(
    r"^(the\s+)?(r[ée]publique|republic|paix|peace|minist[èe]re|ministry|universit[ée]|university|facult[ée]|faculty|"
    r"[ée]cole|school|institut|institute|d[ée]partement|department|division|centre|college|lyc[ée]e|high school|"
    r"\*{3,}|-{3,})",
    re.I,
)
ENGLISH = re.compile(r"\b(republic|peace|work|fatherland|ministry|university|faculty|school|department|institute|higher|of the|high school|college)\b", re.I)
DOC_LABEL = re.compile(
    r"^(rapport (de|du) stage|rapport de fin|rapport d'?activit|rapport de projet|m[ée]moire|th[èe]se|projet tutor[ée]|"
    r"expos[ée]|travaux pratiques|dossier|projet de fin|rapport)\b",
    re.I,
)
THEME = re.compile(r"^(th[èe]me|sujet|intitul[ée]|titre)\s*[:\-–]\s*(.*)$", re.I)
AUTHORS = re.compile(r"^(pr[ée]sent[ée]e?s?|r[ée]dig[ée]e?s?|r[ée]alis[ée]e?s?|[ée]labor[ée]e?s?|soutenue?s?|fait)\s+(par)\b\s*[:\-–]?\s*(.*)$|^(par|auteurs?|[ée]tudiants?|membres du groupe|groupe)\s*[:\-–]\s*(.*)$", re.I)
SUPERVISORS = re.compile(
    r"^(sous la (direction|supervision|co-?direction)( de)?|encadr(eur|ant|ement|[ée]e? par)[^:]*|superviseur|"
    r"directeur de (m[ée]moire|th[èe]se)|ma[îi]tre de stage|tuteur[^:]*|rapporteur|co-?directeur)\s*[:\-–]?\s*(.*)$",
    re.I,
)
MATRICULE = re.compile(r"\bmatricule\s*[:\-–]?\s*([A-Z0-9]{5,12})\b", re.I)
YEAR = re.compile(r"(ann[ée]e (acad[ée]mique|scolaire|universitaire)|academic year)?\s*[:\-–]?\s*((19|20)\d{2}\s*[-/–]\s*(19|20)\d{2})", re.I)
DEGREE = re.compile(r"(en vue de l'?obtention d[ue]s?|pour l'?obtention d[ue]s?|dans le cadre d[ue]s?)\s+(.+)$", re.I)
SPECIALTY = re.compile(r"^(fili[èe]re|option|sp[ée]cialit[ée]|parcours|mention|niveau|cycle)\s*[:\-–]\s*(.+)$", re.I)
STRUCTURE = re.compile(r"(effectu[ée] |r[ée]alis[ée] |stage )?(au sein d[eu]s?|chez|à la soci[ée]t[ée]|à l'entreprise)\s+(.+)$", re.I)
PERIOD = re.compile(r"(p[ée]riode\s*[:\-–]?\s*)?(du\s+\d{1,2}(er)?\s+\w+(\s+\d{4})?\s+au\s+\d{1,2}(er)?\s+\w+\s+\d{4})", re.I)
TITLE_ROLE = re.compile(r"^((pr|dr|m|mme|mlle|mr)\.?|professeur|docteur|ing[ée]nieur|monsieur|madame)\s", re.I)


def _plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


START = re.compile(r"^(introduction|chapitre|partie|avant[- ]propos|sommaire|table des mati|r[ée]sum[ée]|abstract|d[ée]dicace|remerciements|[ée]pigraphe|liste des)\b|^(I|1)\s*[.\-–)]\s+\S", re.I)


def _lines(raws) -> tuple[list[tuple[int, str]], int]:
    """(raw index, line) for the lines before the body starts (first special page or chapter), table cells included."""
    out, end = [], 0
    for i, r in enumerate(raws[:60]):
        text = (r.text or "").strip()
        if r.rows:
            for row in r.rows:
                for cell in row:
                    out.extend((i, ln.strip()) for ln in str(cell).split("\n") if ln.strip())
            end = i + 1
            continue
        if r.image:
            end = i + 1  # the school logos of the old cover
            continue
        if START.match(text) or r.style.startswith("toc") or len(text) > 400:
            break
        out.extend((i, ln.strip()) for ln in text.split("\n") if ln.strip())
        end = i + 1
    return out, end


def _is_name(line: str) -> bool:
    words = line.replace(",", " ").split()
    return 1 <= len(words) <= 7 and len(line) <= 70 and not re.search(r"[:;?!]", line) and not HEADER.match(line)


def extract(raws) -> tuple[dict, set[int]]:
    """Returns (fields, indexes of the raw paragraphs of the old cover). Empty when there is no cover."""
    lines, end = _lines(raws)
    if len(lines) < 3:
        return {}, set()

    f: dict = {"header_fr": [], "header_en": [], "authors": [], "supervisors": []}
    signals = 0
    mode: str | None = None  # "authors" / "supervisors" while reading the names under a label
    role = ""
    for _, line in lines:
        p = _plain(line)
        if HEADER.match(line) and len(line) < 120:
            if re.match(r"^(\*|-){3,}$", line):
                continue
            (f["header_en"] if ENGLISH.search(line) and not re.search(r"\b(de|du|des|la|le|et)\b", p) else f["header_fr"]).append(line)
            signals += 0.5
            mode = None
            continue
        if m := THEME.match(line):
            f["title"] = m.group(2).strip(" «»\"") or f.get("title", "")
            mode = "title" if not m.group(2).strip() else None
            signals += 1
            continue
        if DOC_LABEL.match(line) and len(line) < 90 and "doc_label" not in f:
            f["doc_label"] = line.rstrip(" :")
            signals += 1
            mode = None
            continue
        if m := AUTHORS.match(line):
            rest = (m.group(3) or m.group(5) or "").strip()
            if rest and _is_name(rest):
                f["authors"].append({"name": rest})
            mode = "authors"
            signals += 1
            continue
        if m := SUPERVISORS.match(line):
            role = re.sub(r"\s*[:\-–]\s*$", "", line[: m.start(5)] if m.group(5) else line).strip()
            role = role[:1].upper() + role[1:] if role else "Encadreur"
            rest = (m.group(5) or "").strip()
            if rest and _is_name(rest):
                f["supervisors"].append({"name": rest, "role": role})
            mode = "supervisors"
            signals += 1
            continue
        if m := MATRICULE.search(line):
            if f["authors"] and not f["authors"][-1].get("info"):
                f["authors"][-1]["info"] = m.group(1)
            else:
                f["matricule"] = m.group(1)
            continue
        if (m := YEAR.search(line)) and len(line) < 60:
            f["year"] = re.sub(r"\s*[-/–]\s*", "-", m.group(3))
            signals += 1 if m.group(1) else 0.5
            mode = None
            continue
        if (m := DEGREE.search(line)) and len(line) < 200:
            f["degree"] = m.group(2).strip(" .")
            mode = None
            continue
        if m := SPECIALTY.match(line):
            f.setdefault("specialty", m.group(2).strip(" ."))
            continue
        if (m := PERIOD.search(line)) and len(line) < 90:
            f["period"] = m.group(2)
            continue
        if (m := STRUCTURE.search(line)) and len(line) < 120 and "structure" not in f:
            f["structure"] = m.group(3).strip(" .")
            continue
        if mode == "title":
            f["title"] = line.strip(" «»\"")
            mode = None
            continue
        if mode in ("authors", "supervisors") and _is_name(line):
            person = {"name": line}
            if mode == "supervisors":
                person["role"] = role
                if f["supervisors"] and not TITLE_ROLE.match(line) and f["supervisors"][-1].get("name") and not f["supervisors"][-1].get("info") and len(line.split()) <= 5 and not line.isupper():
                    f["supervisors"][-1]["info"] = line  # "Chargé de cours, Université de ..." under the name
                    continue
            f[mode].append(person)
            continue
        mode = None
        # Title: a longish line in capitals or the region's explicit title, never a sentence.
        if "title" not in f and 12 <= len(line) <= 200 and not line.endswith(".") and (line.isupper() or len(line.split()) >= 4):
            f["title"] = line.strip(" «»\"")

    for r in raws[:end]:
        if r.style == "doctitle":
            f["title"] = r.text.strip()
            break

    if signals < 2.5 or not (f["header_fr"] or f.get("doc_label")) or not (f["authors"] or f["supervisors"] or f.get("year")):
        return {}, set()
    f["authors"] = f["authors"][:8]
    f["supervisors"] = f["supervisors"][:4]
    # The old cover's lines are hidden; a long paragraph before the body is real text and stays.
    hide = {i for i in range(end) if raws[i].rows or raws[i].image or len((raws[i].text or "").strip()) < 220}
    return {k: v for k, v in f.items() if v}, hide
