"""Pages the author planned: where they are, and what to do when they were left empty.

A student often prepares the pages of the front matter before writing them: a "SOMMAIRE" title on a page of its
own, "LISTE DES TABLEAUX", "LISTE DES SIGLES ET ABRÉVIATIONS", "DÉDICACE"… with nothing under. Paginya:

- builds the sommaire and the lists of tables and figures exactly where the author put their title (after the
  remerciements, before the résumé…), with the author's own title ("Table des matières", "Contents");
- fills an empty list of acronyms with the acronyms the text itself explains ("Banque des États de l'Afrique
  centrale (BEAC)"), and an empty list of appendices with the appendices of the document;
- removes the planned pages that stay empty (a dedication never written), so no blank page is printed.

`note` is called by the detection when it meets such a title; `settle` runs once the structure is known.
"""
from __future__ import annotations

import re
import unicodedata

# Pages before the introduction (roman numbers). Kept in sync with render.PRELIM_SPECIALS, which imports it.
PRELIM = {"dedicace", "epigraphe", "remerciements", "avant_propos", "sigles", "resume", "abstract", "glossaire", "liste_annexes"}
BODY_START = {"introduction", "conclusion", "bibliographie", "annexes"}
DETAILED_TOC = re.compile(r"(?i)^\W*(table\s+des\s+mati[eè]res|contents|table\s+of\s+contents)\W*$")
NAMES = {
    "dedicace": "Dédicace", "epigraphe": "Épigraphe", "remerciements": "Remerciements", "avant_propos": "Avant-propos",
    "sigles": "Liste des sigles", "resume": "Résumé", "abstract": "Abstract", "glossaire": "Glossaire", "liste_annexes": "Liste des annexes",
}
AFTER_WORDS = {
    "": "au début", "dedicace": "après la dédicace", "epigraphe": "après l'épigraphe", "remerciements": "après les remerciements",
    "avant_propos": "après l'avant-propos", "sigles": "après la liste des sigles", "resume": "après le résumé",
    "abstract": "après l'abstract", "glossaire": "après le glossaire", "liste_annexes": "après la liste des annexes",
}


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower().strip()


def kinds_of(title: str) -> list[str]:
    """"Sommaire" → toc; "Liste des tableaux" → lot; "Liste des figures et tableaux" → lot + lof."""
    t = _plain(title)
    if re.search(r"table des matieres|table of contents|^\W*contents\W*$|sommaire", t):
        return ["toc"]
    tables = bool(re.search(r"tableaux|\btables\b", t))
    figures = bool(re.search(r"figures|illustrations|graphiques|images|schemas|graphs", t))
    if tables or figures:
        return (["lot"] if tables else []) + (["lof"] if figures else [])
    return ["toc"]


def note(stats: dict, title: str, src: int) -> None:
    """A planned sommaire or list met at raw paragraph `src` (its title is dropped: Paginya writes its own)."""
    stats.setdefault("slots_seen", []).append({"title": re.sub(r"\s+", " ", title.strip()).rstrip(" :"), "src": src})


def in_front_matter(items: list[dict]) -> bool:
    """Still before the body: no introduction, chapter or part yet (used for "Liste des annexes")."""
    return not any(
        not it.get("hidden") and it.get("type") == "heading" and (it.get("special") in BODY_START or it.get("kind") in ("chapitre", "partie"))
        for it in items
    )


def _anchor(items: list[dict], src: int, total: int) -> str | None:
    """The preliminary page the planned one follows ("" at the very start), or None once the body has started."""
    words, last = 0, ""
    for it in items:
        s = it.get("_src")
        if s is not None and s >= src:
            break
        if it.get("hidden"):
            continue
        words += len(str(it.get("text") or "").split())
        if it.get("type") != "heading":
            continue
        sp = it.get("special")
        if sp in PRELIM:
            last = sp
        elif sp in BODY_START or it.get("kind") in ("chapitre", "partie") or it.get("part"):
            return None
    if total and words > 0.4 * total:
        return None
    return last


def _next_special(items: list[dict], src: int) -> str:
    """The special page right after the planned one, when it is a special one (the annexes…)."""
    for it in items:
        s = it.get("_src")
        if s is None or s <= src or it.get("hidden"):
            continue
        if it.get("type") == "heading":
            return it.get("special") or ""
    return ""


def place(items: list[dict], stats: dict) -> dict:
    """meta["slots"]: {"toc": {"after", "title"}, "lot"/"lof": {"after"} or {"end": True}, "toc_end": {"title", "before"}}."""
    seen = stats.get("slots_seen") or []
    if not seen:
        return {}
    total = sum(len(str(it.get("text") or "").split()) for it in items if not it.get("hidden"))
    out: dict = {}
    for s in seen:
        after = _anchor(items, s["src"], total)
        for kind in kinds_of(s["title"]):
            if kind == "toc":
                if after is None:
                    out.setdefault("toc_end", {"title": s["title"], "before": _next_special(items, s["src"])})
                else:
                    out.setdefault("toc", {"after": after, "title": s["title"]})
            elif after is None:
                out.setdefault(kind, {"end": True})
            else:
                out.setdefault(kind, {"after": after, "title": s["title"] if len(kinds_of(s["title"])) == 1 else ""})
    return out


# --- planned pages left empty ---------------------------------------------------------------------

_STOP = {
    "de", "des", "du", "d", "la", "le", "les", "l", "et", "en", "a", "au", "aux", "pour", "par", "sur", "dans", "un", "une",
    "of", "the", "and", "for", "in", "on", "to",
}
_ACR_AFTER = re.compile(r"\(\s*([A-Z][A-Za-z0-9&]{1,11}(?:-[A-Z0-9]{1,5})?)\s*\)")  # Banque centrale (BEAC)
_ACR_BEFORE = re.compile(r"\b([A-Z][A-Z0-9&]{1,11})\s*\(\s*([^()]{6,110}?)\s*\)")  # BEAC (Banque centrale…)
_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][\w’'\-]*")


def _significant(word: str) -> str:
    w = re.sub(r"^(?:[ldjmnst]|qu)['’]", "", word, flags=re.I)  # l'Information → Information
    return "" if _plain(w) in _STOP else w


def _initials(words: list[str]) -> str:
    return "".join(_plain(w)[0] for w in words if w)


def _long_form(words: list[str], acr: str) -> str | None:
    """The shortest run of words at the end of `words` whose meaningful words start with the acronym's letters."""
    letters = _plain("".join(c for c in acr if c.isalpha()))
    if len(letters) < 2:
        return None
    for start in range(len(words) - 1, max(-1, len(words) - 3 * len(letters) - 3), -1):
        run = words[start:]
        sig = [_significant(w) for w in run]
        if not sig[0]:
            continue  # never start on "de", "la"…
        got = _initials([w for w in sig if w])
        if got == letters:
            return " ".join([sig[0], *run[1:]])  # "L'École normale…" → "École normale…"
        if len(got) > len(letters):
            break
    return None


def acronyms(items: list[dict]) -> list[tuple[str, str]]:
    """Acronyms the text explains, in alphabetical order: [("BEAC", "Banque des États de l'Afrique centrale")]."""
    found: dict[str, str] = {}
    for it in items:
        if it.get("hidden") or it.get("type") not in ("paragraph", "list", "quote") or it.get("role") in ("sigle", "biblio"):
            continue
        text = str(it.get("text") or "")
        for m in _ACR_AFTER.finditer(text):
            acr = m.group(1)
            if sum(c.isupper() for c in acr) < 2 or acr in found:
                continue
            long = _long_form(_WORD.findall(text[: m.start()])[-40:], acr)
            if long:
                found[acr] = long
        for m in _ACR_BEFORE.finditer(text):
            acr, inside = m.group(1), m.group(2)
            if acr in found or sum(c.isupper() for c in acr) < 2:
                continue
            words = _WORD.findall(inside)
            if words and _initials([w for w in map(_significant, words) if w]) == _plain(acr):
                found[acr] = " ".join(words)
    return sorted(((k, v[0].upper() + v[1:]) for k, v in found.items()), key=lambda kv: _plain(kv[0]))


_ANNEX = re.compile(r"(?i)^\s*(annexe|appendix|appendice)\s*(n\s*[°o]\s*)?([ivxlc]+|\d{1,2}|[a-h])\b\s*[:.\-–—]?\s*(.*)$")


def annex_titles(items: list[dict]) -> list[str]:
    """"Annexe 1 : Questionnaire", "Annexe 2 : Organigramme"… found after the "Annexes" title of the document."""
    out: list[str] = []
    started = False
    for it in items:
        if it.get("hidden"):
            continue
        if it.get("type") == "heading" and it.get("special") == "annexes":
            started = True
            continue
        if not started or it.get("type") not in ("heading", "paragraph", "caption"):
            continue
        text = re.sub(r"\s+", " ", str(it.get("text") or "")).strip()
        if _ANNEX.match(text) and len(text) <= 160 and text not in out:
            out.append(text)
    return out


def _is_empty_page(items: list[dict], i: int) -> bool:
    for it in items[i + 1:]:
        if it.get("hidden"):
            continue
        return it.get("type") == "heading"
    return True


def titles_before_front_matter(items: list[dict]) -> int:
    """"RAPPORT DE STAGE ACADÉMIQUE" typed above the "DÉDICACE" (no cover was recognised): the document's title, not
    a chapter, else the dedication, the thanks and the sommaire would fall in the body (arabic page numbers)."""
    visible = [it for it in items if not it.get("hidden")]
    run = []
    for it in visible:
        if it.get("type") == "heading" and not it.get("special") and not it.get("part") and it.get("kind") not in ("chapitre", "partie"):
            run.append(it)
            continue
        break
    nxt = visible[len(run)] if len(run) < len(visible) else None
    if not run or len(run) > 3 or nxt is None or nxt.get("type") != "heading" or nxt.get("special") not in PRELIM:
        return 0
    for i, it in enumerate(run):
        it.update({"type": "title", "sub": i > 0})
        it.pop("level", None)
    return len(run)


def settle_empty_pages(items: list[dict]) -> tuple[list[dict], list[str]]:
    """Fills or removes the front-matter pages left empty. Returns the new items and what was done, in words."""
    changes: list[str] = []
    out: list[dict] = []
    removed: list[str] = []
    for i, it in enumerate(items):
        sp = it.get("special")
        if it.get("hidden") or it.get("type") != "heading" or sp not in PRELIM or not _is_empty_page(items, i):
            out.append(it)
            continue
        if sp == "sigles":
            found = acronyms(items)
            if len(found) >= 2:
                out.append(it)
                out.extend({"type": "paragraph", "role": "sigle", "term": k, "definition": v, "text": f"{k} : {v}", "_filled": True} for k, v in found)
                changes.append(f"Liste des sigles remplie avec les {len(found)} sigles expliqués dans ton texte")
                continue
        if sp == "liste_annexes":
            found = annex_titles(items)
            if found:
                out.append(it)
                out.extend({"type": "paragraph", "text": t, "_filled": True} for t in found)
                changes.append(f"Liste des annexes remplie ({len(found)} annexe{'s' if len(found) > 1 else ''})")
                continue
        removed.append(NAMES.get(sp, it.get("text", "")))
    if removed:
        names = ", ".join(f"« {n} »" for n in removed)
        changes.append(f"Page{'s' if len(removed) > 1 else ''} laissée{'s' if len(removed) > 1 else ''} vide{'s' if len(removed) > 1 else ''} retirée{'s' if len(removed) > 1 else ''} : {names}")
    return out, changes


def options(opts: dict, slots: dict | None) -> dict:
    """The planned pages switch on what they ask for (a sommaire, the lists) whatever the kind of document."""
    if not slots:
        return opts
    out = dict(opts)
    if "toc" in slots:
        out["toc"] = True
        if DETAILED_TOC.match(slots["toc"].get("title", "")) and "toc_end" not in slots:
            out["toc_end"] = False  # the author's "Table des matières" is at the start: no second one at the end
    if "toc_end" in slots:
        out["toc_end"] = True
    if "lot" in slots or "lof" in slots:
        out["lists"] = True
    return out


def words_for(slots: dict, blocks: list[dict] | None = None) -> list[str]:
    """What the user is told: "Sommaire placé à l'endroit que tu avais prévu (après les remerciements)"."""
    out = []
    has = {b.get("of") for b in blocks or [] if b.get("type") == "caption" and not b.get("hidden")}
    for k, of, name, what in (("lot", "table", "Liste des tableaux", "de tableau"), ("lof", "figure", "Liste des figures", "de figure")):
        if k in slots and of not in has:
            out.append(f"Page « {name} » retirée : ton document n'a pas {what} légendé")
            slots = {**slots, k: {}}
    toc = slots.get("toc")
    if toc and toc.get("after"):
        out.append(f"{_label(toc.get('title'), 'Sommaire')} placé à l'endroit que tu avais prévu ({AFTER_WORDS.get(toc['after'], 'à sa place')})")
    for k, name in (("lot", "Liste des tableaux"), ("lof", "Liste des figures")):
        s = slots.get(k)
        if s and (s.get("after") or s.get("end")):
            out.append(f"{name} placée à l'endroit que tu avais prévu ({'à la fin' if s.get('end') else AFTER_WORDS.get(s['after'], 'à sa place')})")
    end = slots.get("toc_end")
    if end and end.get("before") == "annexes":
        out.append("Table des matières placée avant les annexes, comme tu l'avais prévu")
    return out


def _label(title: str | None, default: str) -> str:
    t = (title or "").strip()
    return t[0].upper() + t[1:].lower() if t else default
