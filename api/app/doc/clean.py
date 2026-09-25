"""Text clean-up after structure detection: what a careful secretary fixes by hand.

- paragraphs cut in two by an Enter in the middle of a sentence are glued back;
- enumerations typed without bullets ("… les suivantes :" + short lines) become real lists;
- lists are harmonised (French rule: fragments → lowercase + « ; », last « . »; sentences → capital + « . »);
- capitals: paragraph starts, after a full stop, texts and section titles typed ALL IN CAPITALS
  (acronyms like MTN or ENEO and proper nouns are kept, accents are restored: PRESENTATION → Présentation);
- French typography (spaces, no-break spaces before : ; ! ?, « guillemets ») is applied when writing the file.
"""
from __future__ import annotations

import re
import unicodedata

# ----------------------------------------------------------------- accents lost in capitals

_ACCENTED = """
présentation générale général généraux générales stratégie stratégique études étude résultats résultat société sociétés activités activité
élément éléments système systèmes méthodologie méthode méthodes théorique théoriques théorie problématique hypothèse hypothèses
intérêt intérêts réalité qualité quantité capacité capacités sécurité santé société économie économique économiques développement
évolution évaluation réalisation créé créée création opération opérations procédure procédures procédés données déroulement
difficultés difficulté expérience expériences stagiaire stagiaires année années première premier deuxième troisième quatrième
dernière dernier élève élèves étudiant étudiants université universités école écoles supérieure supérieur ministère république
région régions régional régionale département départements différents différentes différent différente spécifique spécifiques
période périodes matériel matériels matériaux véhicule véhicules électrique électricité énergie énergies réseau réseaux intégration
présenté présentée présentés présentées réalisé réalisée réalisés réalisées effectué effectuée effectués effectuées réparties répartis
rôle rôles contrôle contrôles tâche tâches fonctionnalité fonctionnalités technique techniques technologie technologies publique publiques
médecine médical médicale pédagogique pédagogie littérature mémoire mémoires thèse thèses bibliographie références référence
comptabilité financière financier financières bénéfice bénéfices dépense dépenses intérieur extérieur extérieure privée privé
créances crédit crédits épargne clientèle célèbre équipe équipes équipement équipements accès succès progrès procès
déjà très après près là-bas âge âgé âgée mètre mètres kilomètre kilomètres télécommunications téléphone téléphonie
numérique numérisation informatique réalisée gérer gestion géré gérée générer réseaux égalité égal égale également
conclusion introduction généralités recommandations suggestions perspectives acquis limites présentation organisation
""".split()
ACCENTS = {unicodedata.normalize("NFD", w).encode("ascii", "ignore").decode(): w for w in _ACCENTED}

ROMAN = re.compile(r"^[IVXLC]+$")
ABBR = {"etc", "cf", "p", "pp", "vol", "art", "n°", "no", "m", "mme", "mlle", "dr", "pr", "ex", "env", "fig", "tab", "i.e", "e.g", "av", "j.-c", "st", "ste"}
PLACES = {"cameroun", "douala", "yaoundé", "yaounde", "bafoussam", "garoua", "bamenda", "ngaoundéré", "ngaoundere", "kribi", "limbé", "limbe",
          "bertoua", "ebolowa", "maroua", "buea", "afrique", "france", "europe", "chine", "nigeria", "gabon", "tchad", "congo"}
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ'’\-]*")
END = re.compile(r"[.!?:;»)\]…]\s*$")


def _upper_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if len(letters) >= 4 else 0.0


def vocabulary(texts: list[str]) -> tuple[set[str], set[str]]:
    """Acronyms (MTN, ENEO…) and proper nouns seen in normally-typed text of the document."""
    acr: set[str] = set()
    proper: set[str] = set()
    for t in texts:
        if _upper_ratio(t) > 0.6:
            continue
        for i, m in enumerate(WORD.finditer(t)):
            w = m.group(0)
            if len(w) >= 2 and w.isupper() and not ROMAN.match(w):
                acr.add(w)
            elif i > 0 and w[:1].isupper() and w[1:].islower() and t[max(0, m.start() - 2):m.start()].strip() not in (".", "!", "?"):
                proper.add(w.lower())
    return acr, proper


def sentence_case(text: str, acr: set[str], proper: set[str]) -> str:
    """"LES TÂCHES DE LA CNPS À DOUALA" → "Les tâches de la CNPS à Douala"."""
    out = []
    pos = 0
    first = True
    for m in WORD.finditer(text):
        out.append(text[pos:m.start()])
        w = m.group(0)
        low = w.lower()
        if w in acr or ROMAN.match(w) and len(w) <= 4:
            new = w
        else:
            base = unicodedata.normalize("NFD", low).encode("ascii", "ignore").decode()
            new = ACCENTS.get(base, low) if base == low else low  # restore lost accents only when none are left
            if low == "a" and not first:
                nxt = text[m.end():].lstrip()[:12].lower()
                if re.match(r"(la|le|les|l['’]|un|une|travers|partir|cause|compter)\b", nxt) or nxt.split(" ")[0].strip(".,;") in PLACES:
                    new = "à"  # "A DOUALA", "A LA" in capitals: the preposition, not the verb
            if first or low in proper or low in PLACES:
                new = new[:1].upper() + new[1:]
        out.append(new)
        first = False
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def fix_caps(text: str) -> tuple[str, int]:
    """Capital at the start and after a full stop (not after abbreviations, decimals or links)."""
    n = 0
    chars = list(text)
    for i, ch in enumerate(chars):
        if not ch.isalpha():
            continue
        if i == 0 or not "".join(chars[:i]).strip(" «\"'(“"):
            if ch.islower():
                chars[i] = ch.upper()
                n += 1
            break
    s = "".join(chars)

    def up(m: re.Match) -> str:
        nonlocal n
        prev = m.group(1).lower().rstrip(".")
        if prev in ABBR or len(prev) == 1:
            return m.group(0)
        n += 1
        return m.group(0)[:-1] + m.group(0)[-1].upper()

    s = re.sub(r"(\b[\wÀ-ÿ.°-]+)[.!?]\s+([a-zà-ÿ])", up, s)
    return s, n


# ----------------------------------------------------------------- structure fixes

def merge_broken(items: list[dict]) -> int:
    """"… une institution de" ¶ "microfinance créée en 2007." → one paragraph."""
    n = 0
    i = 0
    while i + 1 < len(items):
        a, b = items[i], items[i + 1]
        if (
            a.get("type") == "paragraph" and b.get("type") == "paragraph" and not b.get("_explicit")
            and not END.search(a["text"]) and len(a["text"]) > 30
            and b["text"][:1].islower()
        ):
            a["text"] = a["text"].rstrip() + " " + b["text"].lstrip()
            del items[i + 1]
            n += 1
            continue
        i += 1
    return n


def unmarked_lists(items: list[dict]) -> int:
    """"Les missions sont les suivantes :" followed by short lines without bullets → a real list.

    The intro may have been taken for a heading ("LES OBJECTIFS SONT :" in capitals): a sentence
    ending with ":" that introduces short lines is turned back into a paragraph.
    """
    made = 0
    i = 0
    while i < len(items):
        it = items[i]
        intro = not it.get("_explicit") and it.get("type") in ("paragraph", "heading") and it.get("text", "").rstrip().endswith(":") \
            and it.get("kind") not in ("special", "partie", "chapitre") and len(it.get("text", "").split()) >= 3
        if intro:
            j = i + 1
            run = []
            while j < len(items) and not items[j].get("_explicit") and items[j].get("type") in ("paragraph", "heading") and items[j].get("kind") not in ("special", "partie", "chapitre"):
                t = items[j]["text"].strip()
                if len(t) > 110 or len(t.split()) > 14 or t.endswith(":") or items[j].get("kind", "").startswith(("style", "dec", "roman", "letter", "section")):
                    break  # a real sentence, a new intro or a numbered/styled heading ends the enumeration
                run.append(j)
                j += 1
            if len(run) >= 2:
                if it["type"] == "heading":
                    it.update({"type": "paragraph"})
                    it.pop("level", None)
                    it.pop("kind", None)
                for k in run:
                    items[k].update({"type": "list", "ordered": False, "level": 0, "_nomark": True})
                    items[k].pop("kind", None)
                made += 1
                i = j
                continue
        i += 1
    return made


def harmonise_lists(items: list[dict]) -> int:
    """French list rule, applied consistently inside each list."""
    changed = 0
    i = 0
    while i < len(items):
        if items[i].get("type") != "list":
            i += 1
            continue
        j = i
        while j < len(items) and items[j].get("type") == "list" and items[j].get("ordered") == items[i].get("ordered") and items[j].get("level", 0) == items[i].get("level", 0):
            j += 1
        run = items[i:j]
        intro = items[i - 1]["text"].rstrip() if i > 0 and items[i - 1].get("type") == "paragraph" else ""
        texts = [r["text"].strip() for r in run]
        full = sum(1 for t in texts if len(t) > 100 or re.search(r"[.!?]\s+[A-ZÀ-Ý]", t))
        for k, (r, t) in enumerate(zip(run, texts)):
            core = re.sub(r"[\s;,.]+$", "", t)
            if not core:
                continue
            if intro.endswith(":") and full == 0:
                first = core.split()[0]
                if first[:1].isupper() and first[1:].islower() and first.lower() not in PLACES:
                    core = core[:1].lower() + core[1:]
                new = core + (" ;" if k < len(run) - 1 else ".")
            else:
                new = core[:1].upper() + core[1:] + ("." if not core.endswith(("!", "?", "»")) else "")
            if new != t:
                r["text"] = new
                changed += 1
        i = j
    return changed


def clean(items: list[dict]) -> dict:
    """Runs every fix on the detected items (in place). Returns counters for the "what changed" card."""
    stats = {"merged": merge_broken(items)}  # unmarked_lists runs earlier, before the model (see detect)
    texts = [it.get("text", "") for it in items if it.get("type") in ("paragraph", "list")]
    acr, proper = vocabulary(texts)
    caps = 0
    for it in items:
        t = it.get("type")
        text = it.get("text", "")
        if not text:
            continue
        if t == "heading" and it.get("level", 1) >= 2 and it.get("kind") not in ("partie", "chapitre", "special") and _upper_ratio(text) > 0.85 and len(text) > 6:
            it["text"] = sentence_case(text, acr, proper)
            caps += 1
        elif t in ("paragraph", "list", "quote") and it.get("role") not in ("sigle", "biblio"):
            if _upper_ratio(text) > 0.85 and len(text) > 30:
                it["text"] = sentence_case(text, acr, proper)
                caps += 1
            it["text"], n = fix_caps(it["text"])
            caps += n
    stats["lists_harmonised"] = harmonise_lists(items)
    stats["caps"] = caps
    return stats


# ----------------------------------------------------------------- typography (applied when writing)

_NBSP, _NNBSP = " ", " "


def typo_fr(text: str) -> str:
    """French typography on plain text (links and e-mails must be removed before calling)."""
    t = re.sub(r"[ \t]{2,}", " ", text)
    t = re.sub(r"\s+([,.])(?!\d)", r"\1", t)                      # "mot ," → "mot,"
    t = re.sub(r",(?=[A-Za-zÀ-ÿ])", ", ", t)                        # "a,b" → "a, b" (not 1,5)
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r"\s*([;!?])(?=\s|$)", _NNBSP + r"\1", t)             # thin no-break space before ; ! ?
    t = re.sub(r"(?<=[\wÀ-ÿ)»%])\s*:(?=\s|$)", _NBSP + ":", t)       # no-break space before : (not 10:30)
    t = re.sub(r'"([^"\n]{1,200})"', "«" + _NNBSP + r"\1" + _NNBSP + "»", t)  # "texte" → « texte »
    t = re.sub(r"«\s*", "«" + _NNBSP, t)
    t = re.sub(r"\s*»", _NNBSP + "»", t)
    return t
