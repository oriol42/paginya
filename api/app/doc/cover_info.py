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
    r"advanced|higher|national|facult[yé]|"
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
AUTHORS = re.compile(r"^(pr[ée]sent[ée]e?s?|r[ée]dig[ée]e?s?|r[ée]alis[ée]e?s?|[ée]labor[ée]e?s?|soutenue?s?|fait)(\s+et\s+\w+)?\s+(par)\b\s*[:\-–]?\s*(.*)$|^(par|auteurs?|[ée]tudiants?|membres du groupe|groupe)\s*[:\-–]\s*(.*)$", re.I)
SUPERVISORS = re.compile(
    r"^(co-?encadr\w*|sous l['’]encadrement( \w+)?( de)?|sous la (direction|supervision|co-?direction)( \w+)?( de)?|encadr(eur|ant|ement|[ée]e? par)[^:]*|superviseur|"
    r"directeur de (m[ée]moire|th[èe]se)|ma[îi]tre de stage|tuteur[^:]*|rapporteur|co-?directeur)\s*[:\-–]?\s*(?P<rest>.*)$",
    re.I,
)
MATRICULE = re.compile(r"\bmatricule\s*[:\-–]?\s*([A-Z0-9]{5,12})\b", re.I)
YEAR = re.compile(r"(ann[ée]e (acad[ée]mique|scolaire|universitaire)|academic year)?\s*[:\-–]?\s*((19|20)\d{2}\s*[-/–]\s*(19|20)\d{2})", re.I)
DEGREE = re.compile(r"(en vue de l'?obtention d[ue]s?|pour l'?obtention d[ue]s?|dans le cadre d[ue]s?)\s+(.+)$", re.I)
SPECIALTY = re.compile(r"^(fili[èe]re|formation|option|sp[ée]cialit[ée]|parcours|mention|niveau|cycle)\s*[:\-–]\s*(.+)$", re.I)
STRUCTURE = re.compile(r"(effectu[ée] |r[ée]alis[ée] |stage )?(au sein d[eu]s?|chez|à la soci[ée]t[ée]|à l'entreprise)\s+(.+)$", re.I)
PERIOD = re.compile(r"(p[ée]riode\s*[:\-–]?\s*)?(du\s+\d{1,2}(er)?\s+\w+(\s+\d{4})?\s+au\s+\d{1,2}(er)?\s+\w+\s+\d{4})", re.I)
TITLE_ROLE = re.compile(r"^((pr|dr|m|mme|mlle|mr)\.?|professeur|docteur|ing[ée]nieur|monsieur|madame)\s", re.I)


def _plain(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


START = re.compile(r"^(introduction|chapitre|partie|avant[- ]propos|sommaire|table des mati|r[ée]sum[ée]|abstract|d[ée]dicace|remerciements|[ée]pigraphe|liste des)\b|^(I|1)\s*[.\-–)]\s+\S", re.I)


_ADDRESS = re.compile(r"^(b\.?\s?p\.?|p\.?\s?o\.?\s?box|t[ée]l|fax|e-?mail|site|www\.)\b", re.I)


def _cell_lines(cell: str) -> list[str]:
    """A header cell flattened by Word: "RÉPUBLIQUE DU CAMEROUN PAIX - TRAVAIL - PATRIE ******* MINISTÈRE …"."""
    parts = []
    for chunk in re.split(r"\s*\*{3,}\s*|\n", cell):
        parts.extend(re.split(r"\s+(?=(?:PAIX|PEACE)\b)", chunk.strip()))
    return [p.strip() for p in parts if p.strip() and not _ADDRESS.match(p.strip())]


_NUMBERED = re.compile(r"^([IVX]{1,4}|[A-H]|\d{1,2})\s*[.\-–)/]\s*(\S.*)$")
_PEOPLE = re.compile(r"(?i)\b(pr[ée]sent|r[ée]dig|r[ée]alis|par\s*:|membres|encadr|supervis|direction de|sous la)")


def _closes_cover(text: str, seen: list[tuple[int, str]]) -> bool:
    """The academic year written under the names is the last line of a Cameroonian cover page."""
    m = YEAR.search(text)
    return bool(m and _academic(m) and len(text) < 60 and len(seen) >= 5 and any(_PEOPLE.search(ln) for _, ln in seen))


def _academic(m: re.Match) -> bool:
    """"Année académique 2025-2026" or "2025/2026"; not a promotion ("Promotion 2023/2026" spans three years)."""
    y1, y2 = (int(y) for y in re.findall(r"\d{4}", m.group(3)))
    return bool(m.group(1)) or y2 - y1 == 1


def _body_starts(r, text: str, seen: int, closed: bool) -> bool:
    """True when this paragraph is no longer the cover page: the text of the document has begun.

    Without this, a document whose first title is not a known word ("A/ Objectif du TP") was read as
    one long cover page and its short lines were hidden.
    """
    if seen < 3:
        return False
    if getattr(r, "new_page", False) or getattr(r, "gap", 0) >= 6:
        return True  # a cover is one page
    if closed:
        return not (YEAR.search(text) or HEADER.match(text) or len(text) < 40 and re.search(r"(?i)\b(19|20)\d{2}\b|^(yaound|douala|dschang|buea|bamenda|maroua|ngaound|bertoua|ebolowa|garoua)", text))
    if re.match(r"^(heading|titre)\s*\d", r.style) and seen >= 5:
        return True  # a real Word title after the cover lines
    m = _NUMBERED.match(text)
    named = re.search(r"\b[A-ZÀ-Ý]{3,}\b", m.group(2)) and len(m.group(2).split()) <= 5 if m else False  # "1- KAMGA Paul"
    if m and not named and len(text) < 120:
        return True  # "A/ Objectif du TP", "II- Historique": a section, not a line of the cover
    return len(text) > 200 and text.rstrip().endswith((".", "!", "?"))  # a real paragraph of text


def _lines(raws) -> tuple[list[tuple[int, str]], int]:
    """(raw index, line) for the lines before the body starts (first special page or chapter), table cells included."""
    out, end = [], 0
    closed = False  # the line that ends a cover ("Année académique 2025-2026" under the names) has been read
    for i, r in enumerate(raws[:60]):
        text = (r.text or "").strip()
        if r.rows:
            # column by column: "ENCADREUR PRINCIPAL" then its name, then the next column
            width = max(len(row) for row in r.rows)
            for c in range(width):
                for row in r.rows:
                    if c < len(row):
                        out.extend((i * 1000 + c, ln) for ln in _cell_lines(str(row[c])))
            end = i + 1
            continue
        if r.image:
            end = i + 1  # the school logos of the old cover
            continue
        if START.match(text) or r.style.startswith("toc") or len(text) > 400:
            break
        if closed and _PEOPLE.search(text):
            closed = False  # the supervisors come after the year on this cover
        if out and _body_starts(r, text, len(out), closed):
            break
        closed = closed or _closes_cover(text, out)
        out.extend((i, ln.strip()) for ln in text.split("\n") if ln.strip())
        end = i + 1
    return _join_wrapped(out), end


_CONNECTOR = re.compile(r"\b(du|de|des|d['’]|et|la|le|l['’]|of|and|the|en|pour)$", re.I)


def _join_wrapped(lines: list[tuple[int, str]]) -> list[tuple[int, str]]:
    """Header lines cut in two by a narrow column: "REPUBLIQUE DU" + "CAMEROUN", "UNIVERSITE DE YAOUNDE" + "II"."""
    out: list[tuple[int, str]] = []
    for idx, ln in lines:
        if out:
            pi, prev = out[-1]
            upper = prev.isupper() and ln.isupper()
            cont = _CONNECTOR.search(prev) or (len(ln.split()) <= 2 and not HEADER.match(ln) and not ln.startswith(("(", "*")))
            # mixed case: "École Supérieure des Sciences" / "et Techniques de" / "l'Information et de la"
            lower_cont = HEADER.match(prev) and not HEADER.match(ln) and not ln.startswith(("(", "*")) and (
                _CONNECTOR.search(prev) or ln[:1].islower() or (len(ln.split()) <= 2 and ln[:1].isalpha() and not re.search(r"[.:;]$", prev)))
            if ((upper and cont) or lower_cont) and not re.match(r"^(\*|-){3,}$", ln) and len(prev) + len(ln) < 110:
                out[-1] = (pi, f"{prev} {ln}")
                continue
        out.append((idx, ln))
    return out


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
    label_at = -1
    loose: list[tuple[int, str]] = []  # lines that are none of the known fields: the subject is among them
    for idx, line in lines:
        p = _plain(line)
        if HEADER.match(line) and len(line) < 120:
            if re.match(r"^(\*|-){3,}$", line):
                continue
            halves = [h.strip() for h in re.split(r"\s+/\s+", line)]
            if len(halves) == 2 and all(halves):
                # "UNIVERSITÉ D'ÉBOLOWA / UNIVERSITY OF EBOLOWA": each half goes to its own column
                fr_half, en_half = halves if ENGLISH.search(halves[1]) else halves[::-1]
                f["header_fr"].append(fr_half)
                f["header_en"].append(en_half)
                signals += 0.5
                mode = None
                continue
            english = (ENGLISH.search(line) and not re.search(r"\b(de|du|des|la|le|et)\b", p)) or p.startswith("the ")
            (f["header_en"] if english else f["header_fr"]).append(line)
            signals += 0.5
            mode = None
            continue
        if m := THEME.match(line):
            f["title"] = m.group(2).strip(" «»\"") or f.get("title", "")
            mode = "title" if not m.group(2).strip() else "title_more"
            signals += 1
            continue
        if mode == "title_more":
            if line.isupper() and not AUTHORS.match(line) and not SUPERVISORS.match(line) and not HEADER.match(line) and len(line) < 120:
                f["title"] = f"{f['title']} {line.strip(' «»\"')}"
                continue
            mode = None
        if DOC_LABEL.match(line) and len(line) < 90 and "doc_label" not in f:
            f["doc_label"] = line.rstrip(" :")
            label_at = idx
            signals += 1
            mode = None
            continue
        if m := AUTHORS.match(line):
            rest = (m.group(4) or m.group(6) or "").strip()
            if rest and _is_name(rest):
                f["authors"].append({"name": rest})
            mode = "authors"
            signals += 1
            continue
        if m := SUPERVISORS.match(line):
            role = re.sub(r"\s*[:\-–]\s*$", "", line[: m.start("rest")] if m.group("rest") else line).strip()
            role = role[:1].upper() + role[1:] if role else "Encadreur"
            rest = (m.group("rest") or "").strip()
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
            if _academic(m) or "year" not in f:
                f["year"] = re.sub(r"\s*[-/–]\s*", "-", m.group(3))
            signals += 1 if m.group(1) else 0.5
            mode = None
            continue
        if (m := DEGREE.search(line)) and len(line) < 200:
            f["degree"] = re.sub(r"(?i)^(la |le |l['’]|du )?dipl[ôo]me d[eu]s?\s+", "", m.group(2).strip(" ."))  # the cover writes "diplôme de" itself
            mode = None
            continue
        if re.match(r"^(fili[èe]re|option|sp[ée]cialit[ée]|parcours|mention)\s*[:\-–]?\s*$", line, re.I):
            mode = "specialty"  # "Filière :" alone, the value on the next line
            continue
        if m := SPECIALTY.match(line):
            if m.group(1).lower() in ("niveau", "cycle"):
                f["level"] = m.group(2).strip(" .")
            else:
                f.setdefault("specialty", m.group(2).strip(" ."))
            continue
        if mode == "specialty":
            f["specialty"] = line.strip(" .")
            mode = None
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
        loose.append((idx, line))
        # Title: a longish line in capitals or the region's explicit title, never a sentence.
        # (only a line in capitals: "Stage effectué à … du 04" is a mention, not a title; no title beats a wrong one)
        if "title" not in f and 12 <= len(line) <= 200 and not line.endswith(".") and line.isupper() and not re.search(r"\d{4}", line) and not DOC_LABEL.match(line):
            f["title"] = line.strip(" «»\"")

    blob = " ".join(ln for _, ln in lines)
    if "period" not in f and (m := PERIOD.search(blob)):
        f["period"] = m.group(2)
    if "structure" not in f and (m := re.search(r"(?:stage|effectu[ée]e?)\s+(?:effectu[ée]e?\s+)?(?:[àa]|au sein d[eu]s?|chez)\s+(.{3,80}?)\s+(?:du|de|p[ée]riode)\s+\d", blob, re.I)):
        f["structure"] = m.group(1).strip(" ,.")
    if "degree" not in f and (m := re.search(r"(?:en vue de|pour) l['’]obtention d[ue]s?\s+(?:la |le |l['’]|du |diplôme d[ue] )?(.{5,120}?)(?=\s+(?:option|fili[èe]re|sp[ée]cialit[ée]|r[ée]dig|pr[ée]sent|par|sous|ann[ée]e)\b|$)", blob, re.I)):
        f["degree"] = m.group(1).strip(" ,.")
    for r in raws[:end]:
        if r.style == "doctitle":
            f["title"] = r.text.strip()
            break

    complete = signals >= 2.5 and (f["header_fr"] or f.get("doc_label")) and (f["authors"] or f["supervisors"] or f.get("year"))
    # A title page with only "RAPPORT DE STAGE" and the subject (no names): still a cover, as long as it is short
    # and the text clearly starts after it (a special page, a chapter, a new page).
    bare = bool(f.get("doc_label")) and len(lines) <= 14 and end < len(raws) and all(len(ln) < 160 for _, ln in lines)
    if not complete and not bare:
        return {}, set()
    if "title" not in f and f.get("doc_label"):
        # The subject in normal case (under "RAPPORT DE STAGE", or under the names): the first line that is none
        # of the known fields, with the line that continues it
        cands = [(i, ln) for i, ln in loose if 12 <= len(ln) <= 200 and re.search(r"[A-Za-zÀ-ÿ]{3}", ln) and not re.search(r"[.;]$", ln) and not _is_name(ln)
                 and not re.match(r"(?i)^(promotion|l[1-3]|m[12]|licence|master|niveau|classe)\b", ln) and not _PEOPLE.search(ln) and not re.search(r"(?i)\b(obtention|soutenu|pr[ée]sent[ée])", ln)]
        after = [c for c in cands if c[0] > label_at]
        cands = after or cands  # the subject is written under "MÉMOIRE", "RAPPORT DE STAGE"
        if cands:
            rest = [cands[0][1]]
            # the line right under it continues the subject ("… en ligne :" / "Comparaison entre …")
            nxt = next((ln for i, ln in loose if i == cands[0][0] + 1 and 12 <= len(ln) <= 200 and not re.search(r"[.;]$|\d{4}", ln)), None)
            if nxt:
                rest.append(nxt)
            f["title"] = " ".join(rest).strip(" :«»\"")
    if level := f.pop("level", None):
        f["specialty"] = f"{f['specialty']} · Niveau {level}" if f.get("specialty") else f"Niveau {level}"
    for k in ("header_fr", "header_en"):
        f[k] = list(dict.fromkeys(f[k]))  # a cover printed twice (cover + inner title page)
    if f.get("title") and f.get("doc_label") and f["title"].strip().lower() == f["doc_label"].strip().lower():
        del f["title"]

    def unique(people: list[dict]) -> list[dict]:
        seen, out = set(), []
        for x in people:
            key = re.sub(r"\W+", "", x["name"].lower())
            if key not in seen:
                seen.add(key)
                out.append(x)
        return out

    f["authors"] = unique(f["authors"])[:8]
    f["supervisors"] = unique(f["supervisors"])[:4]
    # The old cover's lines are hidden; a long paragraph before the body is real text and stays.
    hide = {i for i in range(end) if raws[i].rows or raws[i].image or len((raws[i].text or "").strip()) < 220}
    return {k: v for k, v in f.items() if v}, hide


def split_header_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """Lines of a printed letterhead (Word header) -> (French lines, English lines), like the cover's own header."""
    flat: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        flat.extend((i, part) for part in _cell_lines(line))
    fr: list[str] = []
    en: list[str] = []
    for _, line in _join_wrapped(flat):
        if re.match(r"^(\*|-){3,}$", line) or not HEADER.match(line) or len(line) >= 120:
            continue
        p = _plain(line)
        english = (ENGLISH.search(line) and not re.search(r"\b(de|du|des|la|le|et)\b", p)) or p.startswith("the ")
        (en if english else fr).append(line)
    return list(dict.fromkeys(fr)), list(dict.fromkeys(en))
