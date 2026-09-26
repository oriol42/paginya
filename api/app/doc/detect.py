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
    "dedicace": ("dedicace", "dedicaces"),
    "epigraphe": ("epigraphe",),
    "remerciements": ("remerciements", "remerciement"),
    "avant_propos": ("avant-propos", "avant propos"),
    "sigles": (
        "sigles", "sigles et abreviations", "liste des sigles", "liste des sigles et abreviations",
        "liste des abreviations", "abreviations", "sigles et acronymes", "sigles, abreviations et acronymes",
        "liste des sigles, abreviations et acronymes", "liste des abreviations et sigles", "acronymes",
        "liste des sigles et acronymes", "list of abbreviations", "abbreviations",
    ),
    "resume": ("resume",),
    "abstract": ("abstract",),
    "introduction": ("introduction", "introduction generale", "general introduction"),
    "conclusion": (
        "conclusion", "conclusion generale", "conclusion et recommandations", "conclusion et perspectives",
        "general conclusion",
    ),
    "bibliographie": (
        "bibliographie", "references", "references bibliographiques", "webographie",
        "bibliographie et webographie", "sources et bibliographie", "bibliography",
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
LINKS = re.compile(r"https?://\S+|(?<![/\w])www\.\S+|[\w.+-]+@[\w-]+\.\w+")
PARTIE = re.compile(
    r"^((premi[eè]re|deuxi[eè]me|troisi[eè]me|quatri[eè]me|cinqui[eè]me|seconde|\d+\s*(e|[eè]me|re))\s+partie"
    r"|partie\s+([ivx]+|\d+|une|deux|trois|quatre|cinq)\b)",
    re.I,
)
CHAPITRE = re.compile(r"^(chapitre|chapter)\s*([ivx]+|\d+|premier|un|une|deux|trois|quatre|cinq|six|one|two|three|four|five)\b", re.I)
# "TERME : définition en minuscules…" after a number
DEFINITION = re.compile(r"^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s+[^:]{2,60}\s:\s+[a-zàâçéèêëîïôûù]\S*\s+\S+\s+\S+")
SECTION = re.compile(r"^(section|sous[- ]section|paragraphe)\s+([ivx]+|\d+|premi[eè]re?|unique)\b", re.I)
DECIMAL = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s+(\S.*)$")
# "1. ", "1) ", "1- ", "1°) ", "1-Texte" (no space) — but not "1-2 fois" or "10.000 F"
SINGLE_NUM = re.compile(r"^(\d{1,2})\s*(?:°\)|[.)°]\s|-)\s*(?=[^\d\s])(\S.*)$")
NUM_NODOT = re.compile(r"^(\d{1,2})\s+([A-ZÀ-Ý][^\d].*)$")  # "1 Historique" (number without a dot)
ROMAN = re.compile(r"^([IVX]{1,5})\s*[.\-–—)/]\s*(\S.*)$")
LETTER = re.compile(r"^([A-H])\s*[.\-–—)/]\s+(\S.*)$")
LOWER_ITEM = re.compile(r"^([a-z])\s*[.)]\s+(\S.*)$")
BULLET = re.compile(r"^\s*(=>|->|-->|\+(?=\s*[A-Za-zÀ-ÿ])|[-–—•*➢►▪▫◦✓✔→>§]|||||o(?=\s))\s*(\S.*)$")


def _special_of(text: str) -> str | None:
    if len(text) > 70:
        return None
    t = re.sub(r"^([ivx]+|\d+)\s*[.\-–)]\s*", "", plain(text).rstrip(" :"))
    return SPECIAL_LOOKUP.get(t)


def _is_title_like(text: str, limit: int = 120) -> bool:
    return 2 <= len(text) <= limit and not ENDS_SENTENCE.search(text.strip())


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

    for idx, r in enumerate(raws):
        nxt = raws[idx + 1] if idx + 1 < len(raws) else None
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
            if TOC_ENTRY.match(text) or (len(text) < 120 and re.search(r"\s\d{1,3}$", text)):
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

    items = _text_tables(items)
    items = _resolve_numbered(items)
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
    stats["typed_lists"] = sum(1 for it in items if it.pop("_typed", False))
    stats["text_tables"] = sum(1 for it in items if it.pop("_from_text", False))
    blocks = []
    for i, it in enumerate(items):
        if it.get("kind") == "partie":
            it["part"] = True
        it.pop("kind", None)
        it["id"] = i + 1
        blocks.append(it)
    meta = _meta(blocks)
    meta["title"] = _guess_title(blocks)
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

    if PARTIE.match(text) and len(text) < 160:
        return {"type": "heading", "kind": "partie", "text": text}
    if CHAPITRE.match(text) and len(text) < 160:
        return {"type": "heading", "kind": "chapitre", "text": text}

    m = re.match(r"^(heading|titre|title)\s*(\d)?$", r.style)
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

    if PARTIE.match(text) and len(text) < 160:
        return {"type": "heading", "kind": "partie", "text": text}
    if CHAPITRE.match(text) and len(text) < 160:
        return {"type": "heading", "kind": "chapitre", "text": text}

    if SECTION.match(text) and len(text) < 180 and not ENDS_SENTENCE.search(text):
        return {"type": "heading", "kind": "section", "text": text}
    if DEFINITION.match(text):  # "3. LES ABONNÉS : sont ceux qui…" is an item, not a title
        m = SINGLE_NUM.match(text) or DECIMAL.match(text)
        if m:
            return {"type": "list", "ordered": True, "level": min(r.indent, 2), "text": m.group(2), "_typed": True}
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


def _resolve_numbered(items: list[dict]) -> list[dict]:
    """'1. xxx' lines: a run of them is a numbered list; an isolated short one is a heading."""
    out = []
    for i, it in enumerate(items):
        if it.get("type") != "numcand":
            out.append(it)
            continue
        prev_c = i > 0 and items[i - 1].get("type") in ("numcand", "list")
        next_c = i + 1 < len(items) and items[i + 1].get("type") in ("numcand", "list")
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
    for it in items:
        if it.get("type") != "heading":
            continue
        if it["kind"] == "special":
            # Behaves like a chapter: closed by any part/chapter, parent of sections.
            stack = [rank["chapitre"]]
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
    if "memoire" in plain(text_head) or "mémoire" in text_head:
        kind = "memoire"
    elif re.search(r"rapport de stage|stage acad|stage professionnel", text_head):
        kind = "rapport_stage"
    elif words < 1500 and ADMIN.search(text_head):
        kind = "administratif"
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
