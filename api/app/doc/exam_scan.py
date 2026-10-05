"""Photo of an exam paper (épreuve) -> header fields + exercises, ready for /epreuve.

The AI is asked for a small fixed layout (ENTETE / CONTENU) so the school, class,
duration... can fill the exam form. Whatever comes back (an AI that ignored the
layout, or Tesseract on a printed page), `finalize` still tidies the top of the
page with simple rules, and never throws away a line it does not recognise.
"""
from __future__ import annotations

import re
import unicodedata

from ..forms.exam import SECTION

# key written by the AI -> field of the exam form (web/src/components/forms/ExamForm.tsx)
KEYS = {
    "ministere": "ministry",
    "delegation": "delegation",
    "ecole": "school",
    "departement": "department",
    "annee": "year",
    "evaluation": "exam",
    "matiere": "subject",
    "classe": "class",
    "duree": "duration",
    "coefficient": "coef",
    "examinateur": "teacher",
    "consignes": "instructions",
}

EXAM_PROMPT = (
    "Tu es un outil de transcription d'épreuves d'examen camerounaises (collège, lycée, BEPC, Probatoire, "
    "Baccalauréat). La page est une épreuve imprimée ou écrite à la main, en français ou en anglais. "
    "Recopie-la EXACTEMENT, sans corriger les fautes, sans résoudre les exercices, sans commentaire, "
    "dans ce format précis :\n\n"
    "ENTETE\n"
    "ecole: nom de l'établissement\n"
    "ministere: ministère, s'il est écrit\n"
    "delegation: délégation régionale ou départementale, si elle est écrite\n"
    "departement: département ou cellule, s'il est écrit\n"
    "annee: année scolaire (ex. 2025-2026)\n"
    "evaluation: nom de l'évaluation (ex. Évaluation de la 2e séquence, Probatoire blanc, BEPC)\n"
    "matiere: matière (ex. Mathématiques)\n"
    "classe: classe (ex. Terminale C)\n"
    "duree: durée (ex. 2 heures)\n"
    "coefficient: coefficient\n"
    "examinateur: nom de l'enseignant\n"
    "consignes: consignes générales (ex. Calculatrice non autorisée)\n"
    "CONTENU\n"
    "(les exercices)\n\n"
    "Règles :\n"
    "- Dans ENTETE, n'écris que les lignes réellement présentes sur la page. N'invente rien. "
    "Si la page n'a pas d'en-tête (page 2, 3…), écris ENTETE puis directement CONTENU.\n"
    "- Chaque exercice sur sa propre ligne : « Exercice 1 (5 pts) ». Transforme « /5 », « 5 points », « 5 pts » "
    "en « (5 pts) ». De même « Partie A : titre (x pts) », « Problème (x pts) », « Situation problème (x pts) ».\n"
    "- Questions numérotées « 1) … », sous-questions « a) … », choix de QCM « A) … », chacune sur sa ligne. "
    "Si une question a un barème, mets-le à la fin : « (2 pts) ».\n"
    "- Formules en texte simple avec des symboles Unicode (x², √, ≤, ≥, ≠, ∈, ℝ, π, ∞, →, H₂O), "
    "fraction « a/b », jamais de LaTeX.\n"
    "- Tableau : une ligne par rangée, cellules séparées par une tabulation. "
    "Dessin ou figure : écris [figure] à sa place.\n"
    "- Un mot illisible : [illisible].\n"
    "Réponds uniquement avec ce format, sans bloc de code."
)

_MARK = re.compile(r"^[\s*#`>_-]*(entete|contenu)\b[\s*:`_-]*$")
_EMPTY = {"", "-", "?", "inconnu", "n/a", "aucun", "aucune", "non precise", "non precisee", "neant"}


def _norm(text: str) -> str:
    """Lower-case without accents, to compare words written in different ways."""
    folded = unicodedata.normalize("NFD", text)
    return "".join(c for c in folded if unicodedata.category(c) != "Mn").lower().strip()


def split_reply(text: str) -> tuple[dict, str]:
    """AI reply -> (form fields, exercises text). Without ENTETE/CONTENU markers everything is exercises."""
    fields: dict[str, str] = {}
    body: list[str] = []
    mode = None
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip().startswith("```"):
            continue
        mark = _MARK.match(_norm(line))
        if mark:
            mode = "head" if mark.group(1) == "entete" else "body"
            continue
        if mode == "head":
            key, sep, value = line.partition(":")
            name = _norm(key).strip(" *-•_")
            if sep and name in KEYS:
                value = value.strip(" *_")
                if _norm(value) not in _EMPTY:
                    fields[KEYS[name]] = value[:200]
                continue
            if not line.strip():
                continue
            mode = "body"  # a line that is not a header line: the header is over
        body.append(line)
    return fields, "\n".join(body).strip()


# --- Tidy the top of the page (printed exams read by Tesseract, or an AI that ignored the layout) ----

_LABELS = {
    "class": r"classe|class|niveau",
    "duration": r"dur[ée]e|duration|temps",
    "coef": r"coef(?:ficient)?\.?|coeff?\.?",
    "year": r"ann[ée]e\s+(?:scolaire|acad[ée]mique)|session",
    "subject": r"mati[èe]re|discipline|subject",
    "teacher": r"examinateur|professeur|enseignant|prof\.?",
}
_ANY_LABEL = "|".join(f"(?:{rx})" for rx in _LABELS.values())
_PAIR = re.compile(rf"(?i)\b({_ANY_LABEL})\s*:\s*(.+?)(?=\s{{2,}}|\s+(?:{_ANY_LABEL})\s*:|$)")
_LETTERHEAD = re.compile(
    r"^(republique du cameroun|republic of cameroon|paix\W+travail\W+patrie|peace\W+work\W+fatherland"
    r"|(des )?enseignements? secondaires?|secondary education|secondaires?)$"
)
_MINISTRY = re.compile(r"^(ministere|ministry)\b")
_DELEGATION = re.compile(r"^(delegation|regional delegation)\b")
_SCHOOL = re.compile(
    r"^(lycee|college|cetic|ces|ceg|gbhs|ghs|gtc|gts|institut|complexe scolaire|ecole|government)\b"
)
_EXAM_NAME = re.compile(r"^(sequence|evaluation|composition|examen|devoir|probatoire|baccalaureat|bepc|brevet)\b")
_SUBJECT_LINE = re.compile(r"^epreuve\s+(?:de|d['’]|du|des)\s*(.+)$")
_YEAR_LINE = re.compile(r"^(?:annee\s+(?:scolaire|academique)\s*:?\s*)?(\d{4}\s*[-/–]\s*\d{4})$")


def _field_for(label: str) -> str:
    for field, rx in _LABELS.items():
        if re.fullmatch(rx, label.strip(), re.I):
            return field
    return ""


def tidy_top(content: str, fields: dict[str, str]) -> tuple[str, dict[str, str]]:
    """Moves letterhead and "Classe : … Durée : …" lines out of the exercises into form fields.

    Only the part before the first "Exercice / Partie / Problème" is looked at, and a line is only
    removed when it is fully understood: anything else stays in the text.
    """
    lines = content.split("\n")
    end = next((i for i, ln in enumerate(lines[:30]) if SECTION.match(ln.strip())), min(len(lines), 12))
    kept: list[str] = []
    for i, raw in enumerate(lines):
        line = raw.strip()
        if i >= end or not line:
            kept.append(raw)
            continue
        norm = _norm(line)
        if re.fullmatch(r"[\W_]{3,}", line) or _LETTERHEAD.match(norm):
            continue
        if _MINISTRY.match(norm):
            fields.setdefault("ministry", line)
            continue
        if _DELEGATION.match(norm):
            fields.setdefault("delegation", line)
            continue
        subject = _SUBJECT_LINE.match(norm)
        if subject:
            fields.setdefault("subject", line[len(line) - len(subject.group(1)):].strip(" :.-–"))
            continue
        year = _YEAR_LINE.match(norm)
        if year:
            fields.setdefault("year", year.group(1).replace(" ", ""))
            continue
        pairs = list(_PAIR.finditer(line))
        if pairs and not re.search(r"[^\W\d_]", _PAIR.sub("", line)):
            for pair in pairs:
                fields.setdefault(_field_for(pair.group(1)), pair.group(2).strip())
            continue
        if _SCHOOL.match(norm) and "school" not in fields:
            fields["school"] = line
            continue
        if _EXAM_NAME.match(norm) and len(line) < 80 and "exam" not in fields:
            fields["exam"] = line
            continue
        kept.append(raw)
    fields.pop("", None)
    return "\n".join(kept).strip(), fields


# --- A document already imported (Word, PDF, pasted text) turned into an exam ---------------------

def _numbered(counters: dict[int, int], level: int) -> str:
    """"1)", "2)"… at the top level, "a)", "b)"… one level down; deeper counters start again."""
    counters[level] = counters.get(level, 0) + 1
    for deeper in [k for k in counters if k > level]:
        del counters[deeper]
    n = counters[level]
    return f"{n})" if level == 0 else f"{chr(96 + min(n, 26))})"


def raws_to_text(raws) -> str:
    """Word/PDF paragraphs as plain lines for the exam form.

    Word's automatic numbering is not part of the text, so it is put back ("1)", "2)", and "a)", "b)"
    one level down) for the questions to be recognised. Tables: one line per row, cells split by tabs.
    """
    lines: list[str] = []
    counters: dict[int, int] = {}
    for r in raws:
        if r.rows:
            counters.clear()
            lines += ["\t".join(cell.strip() for cell in row) for row in r.rows]
            continue
        text = r.text.strip()
        if not text:
            continue
        if r.list_kind == "number":
            lines.append(f"{_numbered(counters, min(r.indent, 1))} {text}")
        else:
            counters.clear()
            lines.append(("- " if r.list_kind == "bullet" else "") + text)
    return "\n".join(lines)


def blocks_to_text(blocks: list[dict]) -> str:
    """Same thing from the editor's blocks (when the original file is gone)."""
    lines: list[str] = []
    counters: dict[int, int] = {}
    for b in blocks:
        kind = b.get("type")
        if kind == "table":
            counters.clear()
            lines += ["\t".join(str(cell).strip() for cell in row) for row in b.get("rows") or []]
            continue
        text = str(b.get("text") or "").strip()
        if kind in ("figure", "code") or not text:
            continue
        if kind == "list" and b.get("ordered"):
            lines.append(f"{_numbered(counters, min(int(b.get('level') or 0), 1))} {text}")
        else:
            counters.clear()
            lines.append(("- " if kind == "list" else "") + text)
    return "\n".join(lines)


def finalize(text: str) -> dict:
    """What /scans returns for an exam page: {"fields": {...form fields}, "content": "exercises"}."""
    fields, content = split_reply(text)
    content, fields = tidy_top(content, fields)
    return {"fields": fields, "content": content}
