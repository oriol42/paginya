"""Rule-based structure detection (no AI needed for the common cases).

Every raw paragraph becomes a typed block: heading (with level), paragraph,
list item, table, figure, caption, source, quote. Rules come from real
Cameroonian reports (see docs/NORMES-CAMEROUN.md): "PREMIÈRE PARTIE",
"CHAPITRE II", "I.", "A.", "1.1", hand-typed bullets, "Tableau 3 :", etc.
"""
from __future__ import annotations

import re
import unicodedata

from .extract import Raw, body_size

# --- helpers ---------------------------------------------------------------

def plain(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9 ,'-]+", " ", s).strip()


def upper_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if len(letters) >= 3 else 0.0


ENDS_SENTENCE = re.compile(r"[.;,!?]$")

SPECIALS: dict[str, tuple[str, ...]] = {
    "dedicace": ("dedicace", "dedicaces", "dedication", "dedications"),
    "epigraphe": ("epigraphe",),
    "remerciements": ("remerciements", "remerciement", "acknowledgements", "acknowledgement", "acknowledgments", "acknowledgment"),
    "avant_propos": ("avant-propos", "avant propos", "foreword", "preface"),
    "sigles": (
        "sigles", "sigles et abreviations", "liste des sigles", "liste des sigles et abreviations",
        "liste des abreviations", "abreviations", "sigles et acronymes", "sigles, abreviations et acronymes",
        "liste des sigles, abreviations et acronymes", "liste des abreviations et sigles", "acronymes",
        "liste des sigles et acronymes", "list of abbreviations", "abbreviations",
    ),
    "resume": ("resume", "summary", "executive summary"),
    "abstract": ("abstract",),
    "glossaire": ("glossaire", "glossary", "lexique"),
    "introduction": ("introduction", "introduction generale", "general introduction"),
    "conclusion": (
        "conclusion", "conclusion generale", "conclusion et recommandations", "conclusion et perspectives",
        "general conclusion", "conclusion and recommendations", "conclusion et suggestions", "conclusion partielle",
    ),
    "bibliographie": (
        "bibliographie", "references", "references bibliographiques", "webographie",
        "bibliographie et webographie", "sources et bibliographie", "bibliography", "references bibliographiques et webographiques",
        "sources", "sitographie", "list of references",
    ),
    "annexes": ("annexes", "annexe", "liste des annexes", "appendices", "appendix"),
    "toc": (
        "sommaire", "table des matieres", "liste des tableaux", "liste des figures", "liste des illustrations",
        "liste des graphiques", "table des illustrations", "table of contents", "contents", "list of tables",
        "list of figures",
    ),
}
SPECIAL_LOOKUP = {v: k for k, vals in SPECIALS.items() for v in vals}

TOC_ENTRY = re.compile(r"^(.{2,}?)(?:[\s.…_·-]{3,}\s*|\s+(?:p\.?|pp\.?|page)\s*)([ivxlcdm]+|\d+)\s*$", re.I)
CAPTION = re.compile(
    r"^(tableau|table|tab\.|figure|fig\.?|graphique|graphe|graph\.|image|photo|sch[ée]ma|carte|illustration|diagramme)"
    r"\s*(n\s*[°o]\s*)?(\d+(?:[.\-]\d+)?)\s*[:.\-–—]\s*(.*)$",
    re.I,
)
SOURCE = re.compile(r"^(source|sources)\s*:", re.I)
RULE_LINE = re.compile(r"^[\s_*=\-–—~#.·•❖◆■\uf000-\uf0ff]{5,}$")
PAGE_ONLY = re.compile(r"^(page\s*)?[-–]?\s*\d{1,3}\s*(/\s*\d{1,3})?\s*[-–]?$", re.I)
LEADERS_END = re.compile(r"\s*(?:\.{6,}|…{2,}|(?:\. ){5,})[.…\s]*$")
LINKS = re.compile(r"https?://\S+|(?<![/\w])www\.\S+|[\w.+-]+@[\w-]+\.\w+")
PARTIE = re.compile(
    r"^((premi[eè]re|deuxi[eè]me|troisi[eè]me|quatri[eè]me|cinqui[eè]me|seconde|\d+\s*(e|[eè]me|re))\s+partie"
    r"|partie\s+([ivx]+|\d+|une|deux|trois|quatre|cinq)\b)",
    re.I,
)
CHAPITRE = re.compile(r"^(chapitre|chapter)\s*([ivx]+|\d+|premier|un|une|deux|trois|quatre|cinq|six|one|two|three|four|five)\b", re.I)
# "TERME : définition en minuscules…" after a number
DEFINITION = re.compile(r"^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s+[^:]{2,60}\s:\s+[a-zàâçéèêëîïôûù]\S*\s+\S+\s+\S+")
ARTICLE = re.compile(r"^(article|art\.)\s*(\d+|premier|unique)\s*[.:\-–]\s*\S", re.I)
ALINEA = re.compile(r"^(alin[ée]a)\s*(\d+(?:\.\d+)*)\s*[.:\-–]?\s*\S", re.I)
OFFICIAL_LINE = re.compile(r"^[-–—*\s]*(the\s+)?(r[ée]publique|republic|paix|peace|minist[èe]re|ministry|universit[ée]|university|facult[ée]|faculty|b\.?\s?p\b|p\.?\s?o\.?\s?box)\b", re.I)
SECTION = re.compile(r"^(section|sous[- ]section|paragraphe)\s+([ivx]+|\d+|premi[eè]re?|unique)\b", re.I)
DECIMAL = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s+(\S.*)$")
# "1. ", "1) ", "1- ", "1°) ", "1-Texte" (no space) — but not "1-2 fois" or "10.000 F"
SINGLE_NUM = re.compile(r"^(\d{1,2})\s*(?:°\)|[.)°/]\s|-)\s*(?=[^\d\s])(\S.*)$")
NUM_NODOT = re.compile(r"^(\d{1,2})\s+([A-ZÀ-Ý][^\d].*)$")  # "1 Historique" (number without a dot)
ROMAN = re.compile(r"^([IVX]{1,5}|I(?:ii|v|x)|V(?:i|ii|iii))\s*[.\-–—)/]\s*(\S.*)$")  # "Iii-", "Iv-": Word put a capital on "iii"
LETTER = re.compile(r"^([A-H])\s*[.\-–—)/]\s+(\S.*)$")
LOWER_ITEM = re.compile(r"^([a-z])\s*[.)]\s+(\S.*)$")
BULLET = re.compile(r"^\s*(=>|->|-->|\+(?=\s*[A-Za-zÀ-ÿ])|\*(?!\*)|[-–—•➢►▪▫◦✓✔→>§❖◆◇■□●○➤➔⇒✗✘☐☑✪★☆♦·]|||||o(?=\s))\s*(\S.*)$")


MATRICULE_RE = re.compile(r"\b\d{2}[A-Z]{1,4}[0-9O]{3,4}[A-Z]{0,3}\b")  # "25SB025FS", "25RIOO4FS"
# "Superviseur : Mme NKE", "NOMS, prénoms et matricules des participants": the people of a cover, never a title
PEOPLE_LINE = re.compile(r"^(noms?\s*(,|et)\s*pr[ée]noms?|superviseur|encadr(eur|ant)e?s?\s*:|examinat(eur|rice)|membres du groupe|pr[ée]sent[ée]e?s? par|r[ée]alis[ée]e?s? par|sous la (direction|supervision))", re.I)
FORM_FIELD = re.compile(r"^(noms?|pr[ée]noms?|statut|t[ée]l[ée]phone|t[ée]l|adresse|e-?mail|date|signature|[âa]ge|sexe|profession|matricule|fonction|qualit[ée]|lieu)\s*:\s*\S", re.I)
FENCE = re.compile(r"^`{3,}\s*\w*$")
WHOLE_BOLD = re.compile(r"^(?:\*\*|__)(?=\S)([^*]+?)(?<=\S)(?:\*\*|__)\s*[.:;]?$")


def _special_of(text: str) -> str | None:
    if len(text) > 70:
        return None
    t = re.sub(r"^([ivx]+|\d+)\s*[.\-–)]\s*", "", plain(text).rstrip(" :"))
    t = re.sub(r"\s+", " ", t)
    if re.match(r"^(liste|table|index)s? des (figures|tableaux|illustrations|graphiques|images|schemas)\b", t):
        return "toc"  # "Liste des figures & tableaux", "Liste des tableaux et figures"…: rebuilt automatically
    if re.match(r"^(liste des |table des )?(sigles|abreviations|acronymes|symboles|notations)\b[\w ,/&-]*$", t) and len(t) < 70:
        return "sigles"  # "Liste des abréviations, sigles et acronymes" in any order, "Liste des symboles et unités"
    return SPECIAL_LOOKUP.get(t)


def _is_title_like(text: str, limit: int = 120) -> bool:
    return 2 <= len(text) <= limit and not ENDS_SENTENCE.search(text.strip())


# A reference typed in a footnote or the bibliography starts like a lettered heading: initial(s), surname, comma.
REFERENCE = re.compile(r"^(?:[A-Z]\.\s?-?){1,3}\s*[A-ZÀ-Ý][\w'’\-]+(?:\s[A-ZÀ-Ý][\w'’\-]+)?\s?,\s")
REF_DETAIL = re.compile(r"\b(1[5-9]|20)\d\d\b|\bpp?\.\s?\d|\b(op\.\s?cit|ibid|[ée]d\.|[ée]dition|vol\.)", re.I)


def _numbered_title_like(text: str, limit: int, body: str) -> bool:
    """A numbered line is a title even when its author ended it with ":" or "." ("2- Les missions :"),
    as long as what follows the number is one short phrase (no other sentence inside)."""
    if _is_title_like(text, limit):
        return True
    core = re.sub(r"\s*[:.]\s*$", "", body.strip())
    return _is_title_like(core, limit) and not re.search(r"[.!?]\s", core) and len(core.split()) <= 14


# Order used to turn heading "kinds" into levels (first present = level 1).
RANK = [
    "partie", "chapitre", "style1", "section", "roman", "upper", "style2", "letter", "dec1", "big",
    "bold", "style3", "dec2", "short", "style4", "dec3", "dec4",
]


# --- main ------------------------------------------------------------------

def detect(raws: list[Raw], trace: bool = False, refine: bool = True) -> dict:
    """`trace`: also return, for each raw paragraph index, what it became (used to measure accuracy).
    `refine`: let the learned model correct the rules where it is confident (app/doc/ml.py)."""
    base = body_size(raws)
    items: list[dict] = []
    dropped: list[int] = []
    skip_toc = False
    stats = {"toc_lines": 0, "captions_moved": 0}
    from .cover_info import extract as cover_fields

    _unflatten_styles(raws)
    cover, old_cover = cover_fields(raws)  # the student's own cover page: read, then kept hidden
    stats["cover_lines"] = len(old_cover)

    for idx, r in enumerate(raws):
        nxt = raws[idx + 1] if idx + 1 < len(raws) else None
        if idx in old_cover:
            if r.rows:
                items.append({"type": "table", "rows": r.rows, "hidden": True, "_explicit": True})
            elif r.image:
                items.append({"type": "figure", "image": r.image, "hidden": True, "_explicit": True})
                if cover is not None and len(cover.setdefault("logos", [])) < 3:
                    cover["logos"].append(r.image)  # the school's logos printed on the student's own cover
            elif r.text.strip():
                items.append({"type": "paragraph", "text": r.text.strip(), "hidden": True, "_explicit": True, "_src": idx})
            continue
        if r.rows:
            skip_toc = False
            items.append({"type": "table", "rows": r.rows})
            continue
        if r.image:
            skip_toc = False
            items.append({"type": "figure", "image": r.image})
            if r.text:
                items.append(_classify_text(r, nxt, base))
            continue

        text = r.text.strip()
        if r.style.startswith("toc") or r.style.startswith("table of figures"):
            continue
        if RULE_LINE.match(text) or (r.source == "pdf" and PAGE_ONLY.match(text)) or FENCE.match(text):
            dropped.append(idx)  # a line drawn with the keyboard (_____, *****), a page number left by the PDF, a ``` pasted from a chatbot
            continue
        if (m := WHOLE_BOLD.match(text)) and not r.explicit:
            # "**Gestion des visites :**" pasted from a chatbot: the stars are its bold, not a bullet
            r.text, r.bold, text = m.group(1).strip(), True, m.group(1).strip()
        if LEADERS_END.search(text) and len(text) < 200:
            text = LEADERS_END.sub("", text).strip()  # "Présentation du projet…………": the dots of a plan typed by hand
            r.text = text
            if not text:
                dropped.append(idx)
                continue
        if r.style == "code":
            items.append({"type": "code", "text": r.text, "_src": idx})
            continue
        if r.style in ("doctitle", "docsubtitle"):
            items.append({"type": "title", "sub": r.style == "docsubtitle", "text": text, "_src": idx})
            continue
        if r.explicit:  # Markdown: the author already said what each line is
            item = _classify_explicit(r)
            if item:
                items.append({**item, "_src": idx, "_explicit": True})
                continue
        special = _special_of(text)
        if special == "toc":
            skip_toc = True
            stats["toc_lines"] += 1
            dropped.append(idx)
            continue
        if skip_toc:
            # a typed list of figures often has no page numbers: "Figure 1 : Architecture générale"
            if TOC_ENTRY.match(text) or (len(text) < 120 and re.search(r"\s\d{1,3}$", text)) or (len(text) < 200 and CAPTION.match(text)):
                stats["toc_lines"] += 1
                dropped.append(idx)
                continue
            skip_toc = False
        if TOC_ENTRY.match(text) and len(text) < 160:
            stats["toc_lines"] += 1
            dropped.append(idx)
            continue  # stray table-of-contents line

        if special:
            items.append({"type": "heading", "kind": "special", "special": special, "text": _clean_special(text), "_src": idx})
            continue
        items.append({**_classify_text(r, nxt, base), "_src": idx})

    items = _drop_typed_plan(items, dropped, stats)
    items = _text_tables(items)
    _announced_chapters(items)
    items = _resolve_numbered(items)
    _join_cut_titles(items)
    _assign_levels(items)
    _roles_in_sections(items)
    items, stats["captions_moved"] = _fix_caption_positions(items)

    traced = {it["_src"]: it for it in items if "_src" in it}
    from .clean import unmarked_lists

    stats["lists"] = unmarked_lists(items)  # before the model: it must not turn these lines into headings
    if refine:
        from . import ml

        full = {**{i: {"type": "toc"} for i in dropped}, **traced}
        m = ml.model()
        stats["ml_fixes"] = ml.refine(raws, full, base, float(m.p.get("threshold", 0.9)) if m else 0.9)
    from .clean import clean

    stats.update(clean(items))
    stats["not_titles"] = _not_titles(items)
    stats["typed_lists"] = sum(1 for it in items if it.pop("_typed", False))
    stats["text_tables"] = sum(1 for it in items if it.pop("_from_text", False))
    blocks = []
    for i, it in enumerate(items):
        if it.get("kind") == "partie":
            it["part"] = True
        it.pop("kind", None)
        it["id"] = i + 1
        blocks.append(it)
    meta = _meta(blocks)  # the old cover says best what the document is ("Rapport de stage", "Mémoire")
    if meta["kind"] == "document" and meta["words"] >= 500 and meta["headings"] >= 3:
        # an official cover, a group with student numbers ("25SB025FS") or "Groupe 3": schoolwork, not a plain text
        every = " ".join(b.get("text", "") for b in blocks)
        if (cover and cover.get("header_fr")) or len(MATRICULE_RE.findall(every)) >= 2 or re.search(r"(?i)\b(groupe\s*(n°|no)?\s*\d|membres du groupe)", every):
            meta["kind"] = "expose" if meta["words"] < 6000 else "rapport"
    meta["title"] = cover.get("title") or _guess_title([b for b in blocks if not b.get("hidden")])
    if cover:
        meta["cover"] = cover
    if stats.get("typed_plan"):
        meta["typed_plan"] = True  # replaced by a real sommaire (render.options_for)
    meta["changes"] = _changes(blocks, stats)
    out = {"blocks": blocks, "meta": meta}
    if trace:
        out["trace"] = {**{i: {"type": "toc"} for i in dropped}, **{i: dict(it) for i, it in traced.items()}}
    for it in blocks:
        it.pop("_src", None)
        it.pop("_full", None)
        it.pop("_nomark", None)
        it.pop("_explicit", None)
    return out


BIBLIO = re.compile(r",\s*(?:\d{1,2}\s*(?:e|ème)?\s*éd\.?,\s*)?[^,]{0,40},\s*(?:19|20)\d{2}\b|\b(?:L['’]Harmattan|Éditions|Editions|Press|PUF|Karthala)\b.*\b(?:19|20)\d{2}\b")


_PLAN_TITLE = re.compile(r"^(sommaire|table des mati[eè]res?|tableau des? mati[eè]res?|plan( de l['’ ]?expos[ée]| du travail)?|contents|table of contents)\b\s*[:.]?\s*", re.I)


def _plan_key(text: str) -> str:
    """"II. Notions fondamentales (définitions…)", "★CONCLUSION", "PARTIE I : NOTIONS…" → "notions fondamentales"."""
    t = plain(_PLAN_TITLE.sub("", text.strip()))
    t = re.sub(r"\([^)]*\)", " ", t)
    t = re.sub(r"^[^a-z0-9]*((partie|chapitre)\s+)?(([ivxl]+|\d+(\.\d+)*|[a-h])(?![a-z0-9]))?\s*[\W_]*\s*", "", t)
    return " ".join(re.findall(r"[a-z0-9]+", t))


_OPEN_END = re.compile(r"(?:^|\s)(de|du|des|la|le|les|l['’]|d['’]|et|à|aux|au|en|pour|par|sur|dans|avec|of|the|and)$", re.I)


def _join_cut_titles(items: list[dict]) -> None:
    """"2. Les lois relatives aux" / "Droits du patient": a title cut in two lines by the PDF ends on a small word."""
    i = 0
    while i + 1 < len(items):
        a, b = items[i], items[i + 1]
        if (a.get("type") == "heading" and not a.get("hidden") and _OPEN_END.search(a.get("text", "").rstrip())
                and b.get("type") in ("heading", "paragraph") and not b.get("hidden") and len(b.get("text", "")) < 80
                and not re.search(r"[.;:!?]$", b.get("text", "").rstrip()) and not b.get("special")
                and not re.match(r"(?i)^(d[ée]dicace|[ée]pigraphe|remerciements?|introduction|conclusion|sommaire|r[ée]sum[ée]|abstract|annexes?|bibliographie)\b", b.get("text", "").strip())
                and not re.match(r"^\s*([IVXLivxl]+|\d+(\.\d+)*|[A-Ha-h])\s*[.\-–)/:]", b.get("text", ""))):
            a["text"] = a["text"].rstrip() + " " + b["text"].strip()
            del items[i + 1]
            continue
        i += 1


def _drop_typed_plan(items: list[dict], dropped: list[int], stats: dict) -> list[dict]:
    """A plan typed at the start without page numbers ("I. Introduction", "II. Notions…", "Conclusion") reads as a
    run of titles with no text between them, and its titles come back further down: it is the old sommaire
    (Paginya writes a real one), so it goes."""
    visible = [k for k, it in enumerate(items) if not it.get("hidden")]
    for n, start in enumerate(visible[:25]):
        # at the very start of the text, or right under a "Plan" / "Sommaire" title
        after_title = n > 0 and _PLAN_TITLE.match(items[visible[n - 1]].get("text", "")) and len(items[visible[n - 1]].get("text", "")) < 40
        if n > 3 and not after_title and not _PLAN_TITLE.match(items[start].get("text", "")):
            continue
        if items[start].get("type") not in ("heading", "paragraph", "list", "numcand") or len(items[start].get("text", "")) > 160:
            continue
        if any(items[k].get("type") == "paragraph" and len(items[k].get("text", "")) > 160 for k in visible if k < start):
            break  # a plan comes before the text, never after a real paragraph
        seen: list[str] = []
        end = start
        while end < len(items):
            it = items[end]
            text = it.get("text", "")
            if it.get("hidden") or it.get("type") not in ("heading", "paragraph", "list", "numcand") or len(text) > 160:
                break
            words = len(text.split())
            if it.get("type") in ("paragraph", "list") and (re.search(r"[.:;!?]$", text.rstrip()) or words > (24 if it["type"] == "list" else 10) or text.count(",") > 2):
                break  # a sentence ("Ce rapport s'articule autour de trois chapitres :") is text, never a line of a plan
            key = _plan_key(text)
            nxt = next((x for x in items[end + 1:] if not x.get("hidden")), None)
            if (key and key in seen) or (nxt and nxt.get("type") == "paragraph" and len(nxt.get("text", "")) > 160):
                break  # the same title again, or a title followed by its text: the document has begun
            if key:
                seen.append(key)
            end += 1
        short = lambda k: " ".join(k.split()[:2])
        later = {short(_plan_key(it.get("text", ""))) for it in items[end:] if it.get("type") in ("heading", "numcand")}
        found = sum(1 for k in seen if short(k) in later)
        # the lines of a plan are numbered ("I.", "1-", "A.") or are the Introduction and the Conclusion
        bare = lambda t: _PLAN_TITLE.sub("", t).lstrip("★➢•*- ")
        labelled = sum(1 for it in items[start:end] if it.get("type") in ("numcand", "list") or it.get("special")
                       or re.match(r"^\s*([IVXLivxl]+|\d+(\.\d+)*|[A-Ha-h])\s*[.\-–—)_/:]", bare(it.get("text", "")))
                       or re.match(r"(?i)^(introduction|conclusion|bibliographie|r[ée]f[ée]rences|sources|annexes?)\b", bare(it.get("text", ""))))
        # right after a plan the document starts again from its beginning: its Introduction or its first title
        restart = end < len(items) and (_plan_key(items[end].get("text", "")) in seen[:2] or _plan_key(items[end].get("text", "")).startswith("introduction"))
        if end - start >= 4 and found >= 2 and found * 3 >= len(seen) and labelled * 2 >= end - start and restart:
            for it in items[start:end]:
                if "_src" in it:
                    dropped.append(it["_src"])
            stats["toc_lines"] += end - start
            stats["typed_plan"] = True
            return items[:start] + items[end:]
    return items


def _not_titles(items: list[dict]) -> int:
    """Last look at the titles, whatever made them: a quotation from an interview, a reference of the
    bibliography or a whole sentence is never a title (each would be a long, ugly line of the sommaire)."""
    n = 0
    # A block of header lines (a model cover in the annexes: university, faculty, department, laboratory, one
    # line each, nothing between them) is no run of titles
    header_like = re.compile(r"^[-–—*\s]*(the\s+)?(r[ée]publique|republic|paix|peace|minist[èe]re|ministry|universit|facult|d[ée]partement|department|"
                             r"laboratoire|laboratory|unit[ée] de formation|doctoral|[ée]cole|school|institut|b\.?\s?p\b|p\.?\s?o\.?\s?box)", re.I)
    i = 0
    while i < len(items):
        j = i
        while j < len(items) and items[j].get("type") == "heading" and not items[j].get("special") and not items[j].get("_explicit"):
            j += 1
        if j - i >= 3 and sum(bool(header_like.match(items[k].get("text", ""))) for k in range(i, j)) * 3 >= j - i:
            for k in range(i, j):
                for key in ("level", "number", "part", "kind", "numbered"):
                    items[k].pop(key, None)
                items[k]["type"] = "paragraph"
                n += 1
        i = max(j, i + 1)
    for it in items:
        if it.get("type") != "heading" or it.get("special") or it.get("_explicit"):
            continue
        text = it.get("text", "").strip()
        # "[Emplacement de la figure]", "[Insérer le tableau ici]": a note left in the text, never a title;
        # "Nom : MENDOGO", "Statut : Étudiante": a filled field of a form (annexes), never a title either
        # "UNIVERSITÉ D'EBOLOWA", "-----FACULTÉ DES SCIENCES": the header of a model cover in the annexes, not a title
        if (text[:1] in "«“\"" and len(text) > 40) or (text[:1] == "[" and text[-1:] == "]") or FORM_FIELD.match(text) or OFFICIAL_LINE.match(text) or PEOPLE_LINE.match(text) or REFERENCE.match(text) or BIBLIO.search(text) or len(text) > 160 \
                or (len(text) > 100 and ENDS_SENTENCE.search(text)):
            for k in ("level", "number", "part", "kind", "special", "numbered"):
                it.pop(k, None)
            it["type"] = "paragraph"
            n += 1
    return n


def _label_family(text: str) -> str | None:
    """Which numbering a title line carries: "I-" and "II." are one family, "1)" another, "a/" another."""
    t = text.strip()
    if CHAPITRE.match(t) or PARTIE.match(t):
        return "chapitre"
    if DECIMAL.match(t):
        return "decimal"
    if ROMAN.match(t):
        return "roman"
    if LETTER.match(t):
        return "letter"
    if SINGLE_NUM.match(t):
        return "digit"
    if LOWER_ITEM.match(t):
        return "lower"
    return None


def _unflatten_styles(raws: list[Raw]) -> None:
    """A file where every title uses the same Word style ("Titre 1" for chapters and sub-sections alike)
    says nothing about depth; when those titles are numbered in at least two ways, the numbering does.
    Their style is then ignored, so the usual numbering rules decide the level."""
    styled = [r for r in raws if re.match(r"^(heading|titre|title)\s*\d?$", r.style) and r.text.strip()]
    if len(styled) < 5 or len({r.style for r in styled}) != 1:
        return
    families = {f for r in styled if (f := _label_family(r.text)) and f != "chapitre"}
    if len(families) < 2:
        return
    for r in styled:
        if _label_family(r.text):
            r.style, r.bold = "normal", True


def _guess_title(blocks: list[dict]) -> str:
    """A short first line before any section heading is usually the document title."""
    for b in blocks[:3]:
        if b["type"] == "title" and not b.get("sub"):
            return b["text"]
        if b.get("special"):
            return ""
        text = b.get("text", "")
        if b["type"] in ("heading", "paragraph") and 8 <= len(text) <= 160 and not ENDS_SENTENCE.search(text):
            return text
    return ""


def _changes(blocks: list[dict], stats: dict) -> list[str]:
    """Human summary of what Paginya did (shown to the user as 'before/after')."""
    out = []
    headings = [b for b in blocks if b["type"] == "heading"]
    levels = len({b.get("level") for b in headings})
    if headings:
        out.append(f"{len(headings)} titres structurés sur {levels} niveau{'x' if levels > 1 else ''}")
    if stats["typed_lists"]:
        out.append(f"{stats['typed_lists']} tirets ou numéros tapés à la main transformés en vraies listes")
    if stats.get("lists"):
        out.append(f"{stats['lists']} énumération{'s' if stats['lists'] > 1 else ''} sans puces transformée{'s' if stats['lists'] > 1 else ''} en liste")
    if stats.get("merged"):
        out.append(f"{stats['merged']} paragraphe{'s' if stats['merged'] > 1 else ''} coupé{'s' if stats['merged'] > 1 else ''} en deux recollé{'s' if stats['merged'] > 1 else ''}")
    if stats.get("caps"):
        out.append(f"{stats['caps']} majuscule{'s' if stats['caps'] > 1 else ''} corrigée{'s' if stats['caps'] > 1 else ''} (débuts de phrase, textes tout en capitales, accents)")
    if stats.get("lists_harmonised"):
        out.append("Listes harmonisées (ponctuation « ; » et « . », majuscules)")
    if stats["text_tables"]:
        out.append(f"{stats['text_tables']} tableau{'x' if stats['text_tables'] > 1 else ''} reconstruit{'s' if stats['text_tables'] > 1 else ''} à partir du texte")
    captions = sum(b["type"] == "caption" for b in blocks)
    if captions:
        out.append(f"{captions} légende{'s' if captions > 1 else ''} numérotée{'s' if captions > 1 else ''} automatiquement")
    if stats["captions_moved"]:
        out.append(f"{stats['captions_moved']} légende{'s' if stats['captions_moved'] > 1 else ''} replacée{'s' if stats['captions_moved'] > 1 else ''} selon les normes")
    sigles = sum(b.get("role") == "sigle" for b in blocks)
    if sigles:
        out.append(f"Liste de {sigles} sigles mise en tableau")
    if stats["toc_lines"]:
        out.append("Ancien sommaire tapé à la main remplacé par un sommaire automatique")
    if stats.get("cover_lines"):
        out.append("Ta page de garde lue : école, titre, noms et année remplis automatiquement")
    links = sum(len(LINKS.findall(b.get("text", ""))) for b in blocks)
    if links:
        out.append(f"{links} lien{'s' if links > 1 else ''} rendu{'s' if links > 1 else ''} cliquable{'s' if links > 1 else ''}")
    out.append("Texte justifié et typographie française (espaces, « guillemets »)")
    return out


def _clean_special(text: str) -> str:
    return re.sub(r"^([IVX]+|\d+)\s*[.\-–)]\s*", "", text.strip()).rstrip(" :")


def _classify_explicit(r: Raw) -> dict | None:
    """Markdown blocks: headings, lists and quotes are what they say; plain paragraphs still get
    the special-section checks (Introduction, Bibliographie...) through the normal path."""
    m = re.match(r"^heading (\d)$", r.style)
    if m:
        special = _special_of(r.text)
        if special and special != "toc" and m.group(1) == "1":
            return {"type": "heading", "kind": "special", "special": special, "text": _clean_special(r.text)}
        return {"type": "heading", "kind": f"style{m.group(1)}", "text": r.text.strip()}
    if r.list_kind:
        return {"type": "list", "ordered": r.list_kind == "number", "level": r.indent, "text": r.text.strip()}
    if r.style == "quote":
        return {"type": "quote", "text": r.text.strip()}
    return {"type": "paragraph", "text": r.text.strip()}


def _classify_text(r: Raw, nxt: Raw | None, base: float) -> dict:
    text = r.text.strip()

    # (a line Word shows with a bullet is an item, even when it reads "Chapitre 1 : …": the plan announced in the introduction)
    if PARTIE.match(text) and len(text) < 160 and r.list_kind != "bullet":
        return {"type": "heading", "kind": "partie", "text": text}
    if CHAPITRE.match(text) and len(text) < 160 and r.list_kind != "bullet":
        return {"type": "heading", "kind": "chapitre", "text": text}
    # a charter or a regulation: "Article 3. Encadrement" is its chapter, "Alinéa 1.2. Rédaction" its section
    if ARTICLE.match(text) and len(text) < 140 and not re.search(r"[.;]$", text):
        return {"type": "heading", "kind": "chapitre", "text": text}
    if (m := ALINEA.match(text)) and len(text) < 140 and not re.search(r"[.;]$", text):
        return {"type": "heading", "kind": ("section", "dec1", "big")[min(m.group(2).count("."), 2)], "text": text}

    m = re.match(r"^(heading|titre|title)\s*(\d)?$", r.style)
    if m and not m.group(2) and _label_family(text):
        m = None  # the Word style "Titre" (no level) put on every title: "II-", "1-", "a-" tell the levels, not the style
    if m and text:
        level = int(m.group(2) or 1)
        return {"type": "heading", "kind": f"style{min(level, 4)}", "text": text}

    m = CAPTION.match(text)
    if m and len(text) < 220:
        target = "table" if m.group(1).lower().startswith("tab") else "figure"
        label = m.group(4).strip() or text
        return {"type": "caption", "of": target, "text": label[:1].upper() + label[1:]}
    if SOURCE.match(text):
        return {"type": "source", "text": text}

    if r.list_kind:
        body = BULLET.match(text)
        clean = body.group(2) if body else text
        return {"type": "list", "ordered": r.list_kind == "number", "level": min(r.indent, 2), "text": clean}

    if SECTION.match(text) and len(text) < 180 and not ENDS_SENTENCE.search(text):
        return {"type": "heading", "kind": "section", "text": text}
    if DEFINITION.match(text):  # "3. LES ABONNÉS : sont ceux qui…" is an item, not a title
        m = SINGLE_NUM.match(text) or DECIMAL.match(text)
        if m:
            return {"type": "list", "ordered": True, "level": min(r.indent, 2), "text": m.group(2), "_typed": True}
    if REFERENCE.match(text) and REF_DETAIL.search(text):
        return {"type": "paragraph", "text": text}  # "E. Tawil, Les relations…, 2013, p. 5.": a footnote, not heading E.
    m = DECIMAL.match(text)
    if m and _numbered_title_like(text, 140, m.group(2)):
        depth = min(m.group(1).count(".") + 1, 4)
        return {"type": "heading", "kind": f"dec{depth}", "text": text}
    m = ROMAN.match(text)
    if m and _numbered_title_like(text, 140, m.group(2)):
        return {"type": "heading", "kind": "roman", "text": text}
    m = LETTER.match(text)
    if m and _numbered_title_like(text, 110, m.group(2)):
        return {"type": "heading", "kind": "letter", "text": text}

    m = BULLET.match(text)
    if m and not text.startswith("--"):
        return {"type": "list", "ordered": False, "level": min(r.indent, 2), "text": m.group(2), "_typed": True}
    m = SINGLE_NUM.match(text)
    if m:
        return {"type": "numcand", "text": text, "body": m.group(2), "title_like": _numbered_title_like(text, 90, m.group(2)), "level": min(r.indent, 2), "bold": r.bold}
    m = NUM_NODOT.match(text)
    if m and _is_title_like(text, 90):
        return {"type": "numcand", "text": text, "body": m.group(2), "title_like": True, "level": min(r.indent, 2), "bold": r.bold, "nodot": True}
    m = LOWER_ITEM.match(text)
    if m and len(text) < 400:
        return {"type": "list", "ordered": True, "level": min(r.indent, 2) or 1, "text": m.group(2), "_typed": True}

    if r.source == "docx" and _is_title_like(text, 120):
        if base and r.size >= base + 1.5:
            return {"type": "heading", "kind": "big", "text": text}
        if r.bold:
            return {"type": "heading", "kind": "bold", "text": text}
    if upper_ratio(text) >= 0.8 and _is_title_like(text, 90):
        return {"type": "heading", "kind": "upper", "text": text}
    if (text.startswith(("«", "“", '"')) and len(text) > 80) or r.style in ("quote", "citation", "intense quote"):
        return {"type": "quote", "text": text}
    if (
        r.source != "docx" and _is_title_like(text, 70) and text[:1].isupper()
        and nxt is not None and len(nxt.text) > 120 and not nxt.rows
    ):
        return {"type": "heading", "kind": "short", "text": text}
    return {"type": "paragraph", "text": text}


def _text_tables(items: list[dict]) -> list[dict]:
    """Consecutive tab/pipe separated lines become one table."""
    out: list[dict] = []
    i = 0
    while i < len(items):
        run: list[list[str]] = []
        j = i
        while j < len(items) and items[j].get("type") == "paragraph" and not items[j].get("_explicit") and (cells := _cells(items[j]["text"])):
            run.append(cells)
            j += 1
        if len(run) >= 2:
            out.append({"type": "table", "rows": run, "_from_text": True})
            i = j
        else:
            out.append(items[i])
            i += 1
    return out


def _cells(text: str) -> list[str] | None:
    if "\t" in text:
        cells = [c.strip() for c in re.split(r"\t+", text)]
    elif text.count("|") >= 1 and " | " in text:
        cells = [c.strip() for c in text.strip().strip("|").split("|")]
    else:
        return None
    return cells if len(cells) >= 2 else None


def _announced_chapters(items: list[dict]) -> None:
    """"Ce rapport s'articule autour de six chapitres : / Chapitre 1 : … / Chapitre 2 : …": chapters announced one
    under the other in the introduction are a list, not six titles (each would get a page of its own).
    They are recognised as a run of chapter lines with nothing between them, whose chapters come again later."""
    def number(it: dict) -> str:
        m = CHAPITRE.match(it["text"]) or PARTIE.match(it["text"])
        return plain(m.group(0)) if m else ""

    i = 0
    while i < len(items):
        j = i
        seen: set[str] = set()
        while j < len(items) and items[j].get("type") == "heading" and items[j].get("kind") in ("chapitre", "partie"):
            if number(items[j]) in seen:
                break  # "Chapitre 1" again: the real chapter starts right after the announced ones
            seen.add(number(items[j]))
            j += 1
        if j - i >= 2:
            later = {number(it) for it in items[j:] if it.get("type") == "heading" and it.get("kind") in ("chapitre", "partie")}
            run = items[i:j] if j < len(items) else []
            again = sum(number(it) in later for it in run)
            # three chapter lines in a row with no text between them are never three chapters; two must come again later
            if run and later and (len(run) >= 3 and again >= 1 or again == len(run)):
                for it in run:
                    it.pop("kind", None)
                    it.update({"type": "list", "ordered": False, "level": 0, "_nomark": True})
        i = max(j, i + 1)


def _resolve_numbered(items: list[dict]) -> list[dict]:
    """'1. xxx' lines: a run of them is a numbered list; an isolated short one is a heading."""
    out = []
    for i, it in enumerate(items):
        if it.get("type") != "numcand":
            out.append(it)
            continue
        prev_c = i > 0 and items[i - 1].get("type") in ("numcand", "list")
        next_c = i + 1 < len(items) and items[i + 1].get("type") in ("numcand", "list")
        if next_c and items[i + 1].get("type") == "list" and not items[i + 1].get("ordered") and not prev_c:
            next_c = False  # "2. Matériel utilisé" then bullets: a title and its list, not a numbered list
        # after a *bullet* list, a short "2. Xxx" followed by text is the next section, not a list item
        after_bullets = i > 0 and items[i - 1].get("type") == "list" and not items[i - 1].get("ordered")
        if it["title_like"] and not next_c and (not prev_c or after_bullets or it.get("bold") or it.get("nodot")):
            out.append({"type": "heading", "kind": "dec1", "text": it["text"], "_src": it.get("_src")})
        else:
            out.append({"type": "list", "ordered": True, "level": it["level"], "text": it["body"], "_typed": True, "_src": it.get("_src"), "_full": it["text"]})
    return out


def _assign_levels(items: list[dict]) -> None:
    """Relative levels: a heading closes every open heading of the same or lower rank.

    So "1.1" right under "CHAPITRE III" gets the same level as "I." under
    "CHAPITRE I", whatever numbering style each chapter uses.
    """
    rank = {k: i for i, k in enumerate(RANK)}
    stack: list[int] = []
    # Without chapters or parts (an exposé: Introduction, I., II., Conclusion), "I." is a sibling of the
    # Introduction, not a section under it
    chapters = any(it.get("type") == "heading" and it.get("kind") in ("chapitre", "partie") for it in items)
    for it in items:
        if it.get("type") != "heading":
            continue
        if it["kind"] == "special":
            # Behaves like a chapter: closed by any part/chapter, parent of sections.
            stack = [rank["chapitre"]] if chapters else []
            it["level"] = 1
            continue
        r = rank.get(it["kind"], len(RANK))
        while stack and stack[-1] >= r:
            stack.pop()
        stack.append(r)
        it["level"] = min(len(stack), 4)


def _roles_in_sections(items: list[dict]) -> None:
    """Paragraph roles depend on the section they are in (dedication, acronyms, bibliography)."""
    section = None
    for it in items:
        if it.get("type") == "heading":
            if section in ("dedicace", "epigraphe") and it.get("kind") not in ("special", "partie", "chapitre"):
                # a poem's short lines ("Je", "Ont") are not titles
                it.update({"type": "paragraph", "role": "dedicace"})
                it.pop("level", None)
                continue
            section = it.get("special") if it["level"] == 1 else section
            continue
        if it.get("type") not in ("paragraph", "list"):
            continue
        if section == "dedicace":
            it["type"], it["role"] = "paragraph", "dedicace"
        elif section == "sigles":
            m = re.match(r"^([^:–—=]{1,40}?)\s*[:–—=]\s+(.+)$", it["text"])
            if m:
                it.update({"type": "paragraph", "role": "sigle", "term": m.group(1).strip(), "definition": m.group(2).strip()})
        elif section == "bibliographie" and it.get("type") == "paragraph":
            it["role"] = "biblio"
        elif section in ("resume", "abstract") and it.get("type") == "paragraph" and re.match(r"^(mots[- ]cl[ée]s|key ?words)\s*:", it["text"], re.I):
            it["role"] = "keywords"


def _fix_caption_positions(items: list[dict]) -> tuple[list[dict], int]:
    """Norms: table caption ABOVE the table, figure caption BELOW the figure."""
    out = list(items)
    moved = 0
    i = 0
    while i < len(out) - 1:
        a, b = out[i], out[i + 1]
        if a.get("type") == "table" and b.get("type") == "caption" and b.get("of") == "table":
            if i == 0 or out[i - 1].get("type") != "caption":
                out[i], out[i + 1] = b, a
                moved += 1
        elif a.get("type") == "caption" and a.get("of") == "figure" and b.get("type") == "figure":
            if i + 2 >= len(out) or out[i + 2].get("type") != "caption":
                out[i], out[i + 1] = b, a
                moved += 1
        i += 1
    return out, moved


ADMIN = re.compile(r"\bobjet\s*:|veuillez agr[ée]er|je soussign|certifie que|attestation|note de service|proc[èe]s[- ]verbal|"
                   r"d[ée]cision n|communiqu[ée]|monsieur le |madame la ", re.I)
COURSE = re.compile(r"\b(cours|le[çc]on|chapitre|exercices?|td|tp|fiche|r[ée]vision|notes?|module|corrig[ée])\b", re.I)


def _meta(blocks: list[dict]) -> dict:
    words = sum(len(b.get("text", "").split()) for b in blocks)
    text_head = " ".join(b.get("text", "") for b in blocks[:40]).lower()
    headings = [b for b in blocks if b["type"] == "heading"]
    titles = " ".join(b.get("text", "") for b in blocks[:3] if b["type"] in ("title", "heading"))
    head = plain(text_head)
    letter = words < 700 and len(headings) <= 2 and re.search(r"\bobjet\s*:|veuillez agreer|je vous prie d.agreer|je soussign", head)
    if letter:
        kind = "administratif"  # "Objet : demande de stage académique" is a letter, not an internship report
    elif re.search(r"\bmemoire\b|\bthese\b|\bdissertation\b|\bthesis\b", head):
        kind = "memoire"
    elif re.search(r"rapport de stage|stage acad|stage professionnel|stage effectue|internship report|stage de (participation|perfectionnement|fin)", head):
        kind = "rapport_stage"
    elif words < 1500 and ADMIN.search(text_head):
        kind = "administratif"
    elif re.search(r"\bexpose\b", head) and words < 6000:
        kind = "expose"
    elif re.search(r"rapport d[e'’ ]\s?(projet|activit|etude|mission|synthese|tp|travaux)|projet (tutore|de fin|tuteure)|cahier des charges|\breport\b", head):
        kind = "rapport"
    elif COURSE.search(titles):
        kind = "cours"
    elif words >= 2500 and len(headings) >= 5:
        kind = "rapport"
    else:
        kind = "document"
    return {
        "kind": kind,
        "words": words,
        "headings": len(headings),
        "tables": sum(b["type"] == "table" for b in blocks),
        "figures": sum(b["type"] == "figure" for b in blocks),
        "lists": sum(b["type"] == "list" for b in blocks),
    }
