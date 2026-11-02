"""The presentation itself: an AI reads the document and writes the slides, for the number the user chose.

The AI only writes the words and picks a slide type; slides.py does all the drawing. What it answers is never
trusted: unknown types and pictures are dropped, and so is any sentence or chart value quoting a number the document does not have.
The text leaves our server (Gemini first, Groq if Gemini is busy), so the user is asked first.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .spelling import SpellError, ask

ICONS = tuple(sorted(p.stem for p in Path(__file__).with_name("icons").glob("*.svg")))
MIN_SLIDES, MAX_SLIDES = 5, 30
DEFAULT_SLIDES = 12
WORDS_PER_SLIDE = 25  # below this a slide has nothing left to say: the AI would fill it with invented text
MAX_SOURCE = 200_000
TABLE_MAX_ROWS, TABLE_MAX_COLS = 8, 6
TABLE_MAX_CELL, TABLE_MAX_CHARS = 90, 520  # beyond this a table is unreadable on a slide: the AI tells what it says instead

PROMPT = (
    "Tu prépares le support PowerPoint d'une présentation orale (soutenance, exposé) à partir du document ci-dessous, "
    "pour un étudiant ou un professionnel camerounais. Comprends le document, garde l'essentiel et reformule : une diapositive "
    "dit une idée, en mots courts, jamais en paragraphes recopiés.\n"
    "LANGUE : tout ce que tu écris (titres, parties, éléments, notes, remerciements) est dans la langue du document : un document en anglais donne une présentation entièrement en anglais, même si ces consignes sont en français.\n"
    "Règles strictes :\n"
    "- N'invente rien : aucun fait, nom, chiffre ou résultat qui ne soit pas dans le document.\n"
    "- Écris exactement {n} diapositives dans \"slides\" : c'est le nombre demandé par l'utilisateur.\n"
    "- Découpe la présentation en 3 à 6 grandes parties, listées dans \"parts\" : des noms de 2 ou 3 mots, 24 caractères au plus "
    "(ils forment le plan et la barre de progression). Chaque diapositive porte \"part\" : le numéro de sa partie, à partir de 1.\n"
    "- Mets la problématique ou la question centrale dans un \"encadre\" si le document en a une.\n"
    "- Suis la logique d'une présentation : contexte et problème, objectifs, démarche, résultats, conclusion et perspectives "
    "(adapte ce plan au document). La dernière diapositive de \"slides\" est la conclusion.\n"
    "- Une présentation belle est variée : utilise au moins 5 types différents, jamais deux fois le même type à la suite. "
    "S'il y a des chiffres qui se comparent (pourcentages, parts, résultats), fais un \"graphique\" ou des \"chiffres\". Une suite "
    "dans le temps est une \"chronologie\" ; une méthode, des \"etapes\" ; deux options, une \"comparaison\". "
    "Utilise les images [F…] et les tableaux [T…] qui prouvent quelque chose, chacun une seule fois, et seulement ceux de la liste.\n"
    "- Titre : 60 caractères au plus, il dit le message de la diapositive, pas juste le sujet (« Le recrutement est cassé. Deux fois. » et non « Le recrutement »). "
    "\"highlight\" (obligatoire sur chaque diapositive) : les 1 à 3 mots du titre à mettre en couleur, copiés tels quels.\n"
    "- Très peu de mots : on doit lire une diapositive en 5 secondes, le détail va dans les notes.\n"
    "- \"takeaway\" (obligatoire sur une diapositive sur trois au moins) : la phrase à retenir, 70 caractères au plus.\n"
    "- Si le document contient un chiffre fort, une diapositive \"grand\" au moins est obligatoire.\n"
    "- Élément (item) : \"head\" 2 à 4 mots, \"text\" 60 caractères au plus. \"icon\" : le mot de cette liste le plus proche du sens : {icons}.\n"
    "- \"visual\" (obligatoire sur chaque diapositive \"grand\" et \"panneau\", et dans le champ général) : une scène à illustrer, en ANGLAIS, 15 mots au plus, concrète et photographiable (lieu, personnes, objets), sans nom propre, sans texte.\n"
    "- \"notes\" : ce que l'orateur dit à l'oral sur cette diapositive, 2 à 4 phrases naturelles.\n"
    "Types possibles (champ \"type\"), avec item = {{\"head\":\"\",\"text\":\"\",\"icon\":\"\"}} :\n"
    "- {{\"type\":\"liste\",\"title\":\"\",\"items\":[item],\"notes\":\"\"}} : 2 à 5 éléments les uns sous les autres\n"
    "- {{\"type\":\"grille\",\"title\":\"\",\"items\":[item],\"notes\":\"\"}} : 2 à 6 idées de même poids en cartes\n"
    "- {{\"type\":\"schema\",\"title\":\"\",\"key\":\"le mot central, 18 caractères au plus\",\"icon\":\"\",\"items\":[item],\"notes\":\"\"}} : un schéma, 3 à 6 idées autour d'une idée centrale (piliers, composantes, acteurs, causes) ; mets-en au moins un dans la présentation\n"
    "- {{\"type\":\"panneau\",\"title\":\"\",\"key\":\"le message à retenir, 90 caractères au plus\",\"icon\":\"\",\"items\":[item],\"notes\":\"\"}} : un message fort et 2 à 4 détails\n"
    "- {{\"type\":\"chronologie\",\"title\":\"\",\"items\":[item],\"notes\":\"\"}} : 3 à 6 moments dans le temps, text de 60 caractères au plus\n"
    "- {{\"type\":\"etapes\",\"title\":\"\",\"items\":[item],\"notes\":\"\"}} : 3 à 5 étapes dans l'ordre, text de 70 caractères au plus\n"
    "- {{\"type\":\"comparaison\",\"title\":\"\",\"left\":{{\"title\":\"\",\"points\":[\"\"]}},\"right\":{{\"title\":\"\",\"points\":[\"\"]}},\"notes\":\"\"}} : deux colonnes\n"
    "- {{\"type\":\"chiffres\",\"title\":\"\",\"stats\":[{{\"value\":\"\",\"label\":\"\",\"icon\":\"\"}}],\"notes\":\"\"}} : 2 à 4 chiffres clés copiés du document\n"
    "- {{\"type\":\"graphique\",\"title\":\"\",\"chart\":\"donut ou barres\",\"series\":[{{\"label\":\"\",\"value\":40}}],\"key\":\"ce que montre le graphique\",\"icon\":\"\",\"notes\":\"\"}} : 2 à 6 valeurs copiées du document\n"
    "- {{\"type\":\"grand\",\"title\":\"\",\"value\":\"3 semaines\",\"text\":\"ce que ça signifie, 80 caractères au plus\",\"icon\":\"\",\"notes\":\"\"}} : un seul chiffre ou mot énorme, copié du document ; mets-en une ou deux dans la présentation s'il y a des chiffres forts\n"
    "- {{\"type\":\"encadre\",\"title\":\"\",\"label\":\"Problématique\",\"text\":\"\",\"notes\":\"\"}} : une phrase forte dans un cadre, text de 180 caractères au plus\n"
    "- {{\"type\":\"figure\",\"title\":\"\",\"figure\":\"F1\",\"points\":[\"\"],\"notes\":\"\"}} : une image et 0 à 3 puces\n"
    "- {{\"type\":\"tableau\",\"title\":\"\",\"table\":\"T1\",\"notes\":\"\"}} : un tableau\n"
    "- {{\"type\":\"section\",\"title\":\"\",\"notes\":\"\"}} : ouvre une grande partie (seulement à partir de 15 diapositives)\n"
    "Réponds avec un objet JSON et rien d'autre : "
    "{{\"visual\":\"scène en anglais pour la couverture\",\"title\":\"le vrai titre du document, tel qu'il y figure ou reformulé fidèlement, 100 caractères au plus\",\"notes\":\"mot d'accueil pour la page de titre\",\"thanks\":\"Merci de votre attention (ces seuls mots, dans la langue du document)\","
    "\"parts\":[\"Contexte\",\"Démarche\",\"Résultats\"],\"slides\":[…]}}\n\n"
    "DOCUMENT :\n"
)


class DeckError(Exception):
    pass


def max_slides(words: int) -> int:
    return max(MIN_SLIDES, min(MAX_SLIDES, words // WORDS_PER_SLIDE))


def _source(blocks: list[dict]) -> tuple[str, dict, dict]:
    """The document as the AI reads it, with the pictures and tables it may show."""
    lines: list[str] = []
    figures: dict[str, dict] = {}
    tables: dict[str, dict] = {}
    shown = [b for b in blocks if not b.get("hidden")]

    def caption(i: int, kind: str) -> str:
        for j in (i + 1, i - 1):
            if 0 <= j < len(shown) and shown[j].get("type") == "caption" and shown[j].get("of", kind) == kind:
                return str(shown[j].get("text") or "").strip()
        return ""

    for i, b in enumerate(shown):
        kind, text = b.get("type"), str(b.get("text") or "").strip()
        if kind == "figure" and b.get("image"):
            key = f"F{len(figures) + 1}"
            figures[key] = {"image": str(b["image"]), "caption": caption(i, "figure")}
            lines.append(f"[{key}] image : {figures[key]['caption'] or 'sans légende'}")
        elif kind == "table":
            rows = [[str(c).strip() for c in r] for r in b.get("rows") or [] if r]
            cols = max((len(r) for r in rows), default=0)
            sizes = [len(c) for r in rows for c in r]
            if 2 <= len(rows) <= TABLE_MAX_ROWS and 2 <= cols <= TABLE_MAX_COLS and max(sizes) <= TABLE_MAX_CELL and sum(sizes) <= TABLE_MAX_CHARS:
                key = f"T{len(tables) + 1}"
                tables[key] = {"rows": [r + [""] * (cols - len(r)) for r in rows], "caption": caption(i, "table")}
                lines.append(f"[{key}] tableau : {tables[key]['caption']}")
                lines.extend(" | ".join(r) for r in rows)
            else:
                lines.extend(" | ".join(str(c) for c in r) for r in (b.get("rows") or [])[:40])
        elif kind == "heading":
            lines.append(f"\n{'#' * max(1, min(int(b.get('level') or 1), 4))} {text}")
        elif kind == "list":
            lines.append(f"- {text}")
        elif text and kind != "caption":
            lines.append(text)
    return "\n".join(lines)[:MAX_SOURCE], figures, tables


_NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _honest(text: str, known: set[str]) -> bool:
    return all(n in known for n in _NUM.findall(text))


def _line(value, limit: int, known: set[str]) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().lstrip("•-– ").strip()
    if not text or not _honest(text, known):
        return ""
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _lines(values, limit: int, known: set[str], most: int) -> list[str]:
    out = [_line(v, limit, known) for v in (values if isinstance(values, list) else [])]
    return [t for t in out if t][:most]


def _icon(value) -> str:
    name = str(value or "").strip().lower()
    return name if name in ICONS else "circle-check"


def _items(values, known: set[str], most: int, limit: int = 110) -> list[dict]:
    out = []
    for v in values if isinstance(values, list) else []:
        if isinstance(v, str):
            v = {"head": v}
        if isinstance(v, dict):
            head, text = _line(v.get("head") or v.get("title"), 44, known), _line(v.get("text"), limit, known)
            if head:
                out.append({"head": head, "text": text, "icon": _icon(v.get("icon"))})
    return out[:most]


def _number(value, known: set[str]) -> float | None:
    text = str(value).strip().rstrip("%").strip()
    if not _NUM.fullmatch(text) or not ({text, text.replace(".", ","), text.replace(",", "."), text.removesuffix(".0")} & known):
        return None
    return float(text.replace(",", "."))


def _clean_slide(s: dict, figures: dict, tables: dict, known: set[str]) -> dict | None:
    kind = {"points": "liste", "cartes": "grille"}.get(s.get("type"), s.get("type"))
    title = _line(s.get("title"), 80, known)
    if not title:
        return None
    out = {"type": kind, "title": title, "notes": str(s.get("notes") or "").strip()[:1500], "part": s.get("part")}
    mark, takeaway = _line(s.get("highlight"), 40, known), _line(s.get("takeaway"), 90, known)
    if mark and mark.lower() in title.lower() and mark.lower() != title.lower():
        out["highlight"] = mark
    if takeaway:
        out["takeaway"] = takeaway
    visual = re.sub(r"[^\w ,'-]", " ", str(s.get("visual") or ""))[:140].strip()
    if visual:
        out["visual"] = visual
    if kind == "section":
        return out
    if kind == "encadre":
        out.update(label=_line(s.get("label"), 34, known), text=_line(s.get("text"), 220, known))
        return out if out["text"] else None
    if kind == "grand":
        out.update(value=_line(s.get("value"), 22, known), text=_line(s.get("text"), 110, known), icon=_icon(s.get("icon")))
        return out if out["value"] else None
    if kind == "chiffres":
        out["stats"] = []
        for v in s.get("stats") if isinstance(s.get("stats"), list) else []:
            if isinstance(v, dict):
                value, label = _line(v.get("value"), 18, known), _line(v.get("label"), 70, known)
                if value and label and _NUM.search(value):
                    out["stats"].append({"value": value, "label": label, "icon": _icon(v.get("icon"))})
        out["stats"] = out["stats"][:4]
        return out if len(out["stats"]) >= 2 else None
    if kind == "graphique":
        series = []
        for v in s.get("series") if isinstance(s.get("series"), list) else []:
            if isinstance(v, dict):
                label, value = _line(v.get("label"), 30, known), _number(v.get("value"), known)
                if label and value is not None:
                    series.append({"label": label, "value": value})
        out.update(series=series[:6], chart="donut" if s.get("chart") == "donut" else "barres", key=_line(s.get("key"), 130, known), icon=_icon(s.get("icon")))
        return out if len(out["series"]) >= 2 else None
    if kind == "etapes":
        out["items"] = _items(s.get("items"), known, 5, 90)
        return out if len(out["items"]) >= 3 else None
    if kind == "schema":
        out.update(items=_items(s.get("items"), known, 6, 60), key=_line(s.get("key"), 22, known), icon=_icon(s.get("icon")))
        return out if len(out["items"]) >= 3 else None
    if kind == "chronologie":
        out["items"] = _items(s.get("items"), known, 6, 70)
        return out if len(out["items"]) >= 3 else None
    if kind == "comparaison":
        for side in ("left", "right"):
            part = s.get(side) if isinstance(s.get(side), dict) else {}
            out[side] = {"title": _line(part.get("title"), 40, known), "points": _lines(part.get("points"), 90, known, 4)}
        return out if out["left"]["points"] and out["right"]["points"] else None
    if kind == "figure":
        figure = figures.get(str(s.get("figure")))
        if figure is None:
            return None
        out.update(image=figure["image"], caption=figure["caption"], points=_lines(s.get("points"), 90, known, 3))
        return out
    if kind == "tableau":
        table = tables.get(str(s.get("table")))
        if table is None:
            return None
        out.update(rows=table["rows"], caption=table["caption"])
        return out
    out["type"] = kind if kind in ("grille", "panneau") else "liste"
    out["items"] = _items(s.get("items") or s.get("points"), known, 6 if kind == "grille" else 5)
    if out["type"] == "panneau":
        out.update(key=_line(s.get("key"), 110, known), icon=_icon(s.get("icon")))
        out["items"] = out["items"][:4]
    return out if out["items"] else None


SMALL = {"de", "du", "des", "la", "le", "les", "et", "à", "au", "aux", "un", "une", "pour", "en", "sur", "dans", "of", "the", "and", "for", "a", "in", "on", "d'", "l'"}


def _highlight(title: str) -> str:
    """The words to colour when the AI gave none: what follows a colon, or the end of the title."""
    if ":" in title:
        after = title.rsplit(":", 1)[1].strip()
        if 0 < len(after.split()) <= 4:
            return after
    words = title.rstrip(" .!?").split(" ")
    if len(words) < 3:
        return ""
    picked = words[-2:]
    while len(picked) > 1 and picked[0].lower() in SMALL:
        picked = picked[1:]
    return " ".join(picked)


def _strengthen(slides: list[dict]) -> None:
    """Every title gets its colour; the strongest figures of a talk get a slide of their own, when none has one."""
    for s in slides:
        s["highlight"] = s.get("highlight") or _highlight(s["title"])
    if len(slides) >= 6 and not any(s["type"] == "grand" for s in slides):
        for s in slides[1:-1]:
            stats = s.get("stats") or []
            if s["type"] == "chiffres" and len(stats) == 2:
                first = stats[0]
                s.update(type="grand", value=first["value"], text=first["label"] if len(stats) < 2 else f"{first['label']} · {stats[1]['value']} {stats[1]['label']}"[:110], icon=first["icon"])
                s.pop("stats")
                return


def _vary(slides: list[dict]) -> None:
    """Never the same page twice in a row, whatever the AI chose: text slides take the layout used least so far."""
    used = {"liste": 0, "grille": 0, "panneau": 0, "schema": 0}
    last = ""
    for s in slides:
        if s["type"] in used:
            n = len(s["items"])
            fits = [k for k, most in (("schema", 6), ("grille", 6), ("panneau", 4), ("liste", 5)) if 2 + (k == "schema") <= n <= most]
            if fits and (s["type"] == last or s["type"] not in fits or used[s["type"]] > min(used[k] for k in fits)):
                s["type"] = min((k for k in fits if k != last), key=lambda k: used[k], default=s["type"])
            s["items"] = s["items"][:{"schema": 6, "grille": 6, "panneau": 4, "liste": 5}[s["type"]]]
            used[s["type"]] += 1
        last = s["type"]


def _clean(answer: dict, figures: dict, tables: dict, known: set[str], count: int) -> list[dict]:
    seen: set[str] = set()
    slides = []
    for s in answer.get("slides") if isinstance(answer.get("slides"), list) else []:
        slide = _clean_slide(s, figures, tables, known) if isinstance(s, dict) else None
        if slide is None:
            continue
        shown = slide.get("image") or (json.dumps(slide["rows"]) if "rows" in slide else "")
        if shown and shown in seen:  # the same picture twice says nothing more
            continue
        seen.add(shown)
        slides.append(slide)
    while len(slides) > count:  # the number is the user's: section openers go first, then the slides just before the end
        spare = next((i for i, s in enumerate(slides) if s["type"] == "section"), len(slides) - 2)
        slides.pop(spare)
    return slides


def _label(text: str) -> str:
    """A part's name for the progress bar: whole words, never ending on « de la »."""
    words = re.sub(r"\s+", " ", str(text or "")).strip().split(" ")
    while len(" ".join(words)) > 26 and len(words) > 1:
        words.pop()
    while len(words) > 1 and words[-1].lower().strip(":,") in ("de", "du", "des", "la", "le", "les", "et", "à", "au", "aux", "d'", "l'", "of", "the", "and", "for"):
        words.pop()
    return " ".join(words).rstrip(" :,;")


def _with_parts(slides: list[dict], names, english: bool = False) -> list[str]:
    """Every slide in a named part, however the AI gave them; none given: the three parts of any talk."""
    names = [_label(n) for n in names if str(n or "").strip()] if isinstance(names, list) else []
    last = ""
    for s in slides:
        part = s.get("part")
        if isinstance(part, str) and part.strip().isdigit():
            part = int(part.strip())
        if isinstance(part, int) and not isinstance(part, bool):
            part = names[part - 1] if 0 < part <= len(names) else ""
        last = s["part"] = _label(part) or last
    if len({s["part"] for s in slides if s["part"]}) < 2:
        names = ("Introduction", "Development", "Conclusion") if english else ("Introduction", "Développement", "Conclusion")
        first, last_one = max(1, len(slides) // 4), max(1, len(slides) // 6)
        for i, s in enumerate(slides):
            s["part"] = names[0] if i < first else names[2] if i >= len(slides) - last_one else names[1]
    for s in slides:
        s["part"] = s["part"] or next(x["part"] for x in slides if x["part"])
    return list(dict.fromkeys(s["part"] for s in slides))


def total(deck: dict) -> int:
    return len(deck["slides"]) + 3  # the title page, the plan and « Merci »


def write(document: dict, count: int, on_call=None) -> dict:
    """The deck of `count` slides in all: the title page + the plan + the AI's slides + « Merci »."""
    blocks = document.get("blocks") or []
    source, figures, tables = _source(blocks)
    if not source.strip():
        raise DeckError("Aucun texte à présenter dans ce document.")
    known = set(_NUM.findall(source))
    middle = count - 3
    best: list[dict] = []
    answer: dict = {}
    for _ in range(2):  # the second try only when the first came back well short of the number asked
        try:
            raw, provider = ask(source, PROMPT.format(n=middle, icons=", ".join(ICONS)))
        except SpellError as exc:
            raise DeckError("L'IA n'est pas disponible pour le moment. Réessaie dans quelques minutes.") from exc
        if on_call:
            on_call(provider)
        try:
            parsed = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        slides = _clean(parsed, figures, tables, known, middle)
        if len(slides) > len(best):
            best, answer = slides, parsed
        if len(best) == middle:
            break
    if len(best) < min(2, middle):
        raise DeckError("L'IA n'a pas réussi à préparer tes diapositives. Réessaie.")
    _vary(best)
    _strengthen(best)
    return {"title": _line(answer.get("title"), 120, known), "visual": re.sub(r"[^\w ,'-]", " ", str(answer.get("visual") or ""))[:140].strip(), "slides": best, "parts": _with_parts(best, answer.get("parts"), not str(answer.get("thanks") or "Merci").lower().startswith("merci")),
            "notes": str(answer.get("notes") or "").strip()[:1500],
            "thanks": re.split(r"(?<=[.!?])\s", _line(answer.get("thanks"), 200, known) or "Merci de votre attention")[0].rstrip(".")}
