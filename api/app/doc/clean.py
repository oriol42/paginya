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

from .extract import junk_rate

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
générale général généraux dédicace résumé théorique théoriques méthodologique méthodologiques méthodologie méthode méthodes
résultat résultats étude études littérature matériel réalisation déroulement présentations définition définitions problématique
hypothèse hypothèses stratégie stratégies système systèmes modèle modèles schéma schémas critère critères caractéristiques
activité activités entité entités sécurité propriété propriétés spécification spécifications spécificités détaillée détaillé
épigraphe abréviations abréviation réseaux implémentation déploiement modélisation synthèse analyse généralité intégré
""".split()
ACCENTS = {unicodedata.normalize("NFD", w).encode("ascii", "ignore").decode(): w for w in _ACCENTED}

ROMAN = re.compile(r"^[IVXLC]+$")
ABBR = {"etc", "cf", "p", "pp", "vol", "art", "n°", "no", "m", "mme", "mlle", "dr", "pr", "ex", "env", "fig", "tab", "i.e", "e.g", "av", "j.-c", "st", "ste"}
PLACES = {"cameroun", "douala", "yaoundé", "yaounde", "bafoussam", "garoua", "bamenda", "ngaoundéré", "ngaoundere", "kribi", "limbé", "limbe",
          "bertoua", "ebolowa", "maroua", "buea", "afrique", "france", "europe", "chine", "nigeria", "gabon", "tchad", "congo"}
WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿŒœÆæŸ][A-Za-zÀ-ÖØ-öø-ÿŒœÆæŸ'’\-]*")  # Œ: "PAR CŒUR" → "par cœur", not "par CŒur"
END = re.compile(r"[.!?:;»)\]…]\s*$")


def _upper_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if len(letters) >= 4 else 0.0


# Small words typed in capitals inside a title ("ACCOMPAGNEMENT DES CONSEILLERS") are not acronyms.
SMALL = set("""de des du la le les un une et ou en au aux a à par pour sur dans avec sans sous vers chez entre que qui dont ce ces cet cette
se sa son ses leur leurs notre nos votre vos mon ma mes est sont the of and in on at to for by an or with from is are as""".split())


def vocabulary(texts: list[str]) -> tuple[set[str], set[str]]:
    """Acronyms (MTN, ENEO…) and proper nouns seen in normally-typed text of the document."""
    acr: set[str] = set()
    proper: set[str] = set()
    for t in texts:
        if _upper_ratio(t) > 0.6:
            continue
        words = list(WORD.finditer(t))
        # words of a phrase typed in capitals ("VOIR LA CORRECTION complète") are no acronyms
        phrase = {k for k in range(len(words) - 1) if words[k].group(0).isupper() and words[k + 1].group(0).isupper()
                  and len(words[k].group(0)) + len(words[k + 1].group(0)) >= 6 and (words[k].group(0).lower() in SMALL or words[k + 1].group(0).lower() in SMALL)}
        phrase |= {k + 1 for k in phrase}
        for i, m in enumerate(words):
            w = m.group(0)
            if len(w) >= 2 and w.isupper() and not ROMAN.match(w) and w.lower() not in SMALL and i not in phrase:
                acr.add(w)
            elif (i > 0 and w[:1].isupper() and w[1:].islower() and t[max(0, m.start() - 2):m.start()].strip() not in (".", "!", "?", ":", "«", '"', "·", "•", "|", "—", "–", "(")
                  and w.lower() not in SMALL):
                proper.add(w.lower())  # never "De" or "Un" ("De Morgan", "« Un switch… »"): "PUISSANCES DE 2" stays "puissances de 2"
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


def upper_title(text: str) -> str:
    """"Conclusion generale" → "CONCLUSION GÉNÉRALE": capitals, with the accents a keyboard in capitals often loses."""
    def one(m: re.Match) -> str:
        low = m.group(0).lower()
        base = unicodedata.normalize("NFD", low).encode("ascii", "ignore").decode()
        return (ACCENTS.get(base, low) if base == low else low).upper()

    return WORD.sub(one, text)


def harmonise_tops(items: list[dict]) -> int:
    """The big titles (special pages, parts, chapters) are written the same way: when most are in capitals, all are."""
    tops = [it for it in items if it.get("type") == "heading" and it.get("kind") in ("special", "partie", "chapitre") and not it.get("hidden")]
    if len(tops) < 2 or sum(_upper_ratio(it["text"]) > 0.85 for it in tops) * 2 < len(tops):
        return 0
    n = 0
    for it in tops:
        new = upper_title(it["text"])
        if new != it["text"]:
            it["text"] = new
            n += 1
    return n


# A line of code or a formula keeps its letters as typed: "SELECT … FROM", "p + l = 17", "x > 0 FAIRE"
CODE_WORDS = re.compile(r"^\s*((SELECT|FROM|WHERE|JOIN|GROUP BY|ORDER BY|HAVING|INSERT INTO|VALUES|UPDATE|DELETE FROM|DELIMITER|BEGIN|END|DECLARE|"
                        r"FOR EACH ROW|CALL|USE|CREATE (OR REPLACE )?(TABLE|TRIGGER|PROCEDURE|FUNCTION|VIEW|INDEX|DATABASE|USER)|ALTER TABLE|DROP (TABLE|TRIGGER|PROCEDURE))\b(?!\s+[a-zA-Zà-ÿ]{3,}\s+[a-zA-Zà-ÿ]{3,})"
                        r"|(TANT QUE|POUR|SI|SINON|FIN|FAIRE|ALORS|AFFICHER|LIRE|[ÉE]CRIRE|RETOURNER)\b.*([<>=←]|\b[a-z]\b)"  # pseudo-code: with a variable
                        r"|(int|float|char|void|return|printf|scanf|for|while|if|else|def|print)\b\s*[(\w]|<[a-z!/][^>]*>)")
FORMULA = re.compile(r"^\s*[(\[]?[A-Za-zΑ-ω0-9][\w′'²³ⁿ̄]{0,3}\s*[(\[]?\s*[=+−×·<>≤≥≠⇒→⊕∧∨]|[=⇒⊕≤≥≠]\s*\S+\s*[=+\-−×·⇒→]")


CODE_LINE = re.compile(r"^\s*([{}]\s*;?|#include\b.*|.*\)\s*\{|.*\w\(.*\)\s*;|</?[a-zA-Z][\w-]*(\s[^>]*)?>.*)\s*$")
SCHEMA = re.compile(r"^[A-Z_]{2,}\s*\([^)]*,[^)]*\)")  # "EMP(ENO, ENOM, SAL)": a table of a relational schema


def is_code_or_formula(text: str) -> bool:
    return bool(CODE_WORDS.match(text) or FORMULA.search(text) or CODE_LINE.match(text) or SCHEMA.match(text))


def fix_caps(text: str) -> tuple[str, int]:
    """Capital at the start and after a full stop (not after abbreviations, decimals, ellipses or links)."""
    n = 0
    if is_code_or_formula(text):
        return text, 0
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
        if prev in ABBR or len(prev) == 1 or m.group(1).endswith(".."):  # "(« si... alors... »)": an ellipsis goes on
            return m.group(0)
        n += 1
        return m.group(0)[:-1] + m.group(0)[-1].upper()

    s = re.sub(r"(\b[\wÀ-ÿ.°-]+)[.!?]\s+([a-zà-ÿ])", up, s)
    return s, n


# ----------------------------------------------------------------- structure fixes

_LETTERED = re.compile(r"^[a-z]{1,4}\s?[)\-.°/]\s")  # "a) ", "b- ", "iv. ": a real lettered heading


def _tail(b: dict) -> bool:
    """A paragraph's last words left alone by a page break of the PDF ("en entreprise", "manières :") and taken
    for a heading: it starts in lower case and is no lettered heading."""
    return (b.get("type") == "heading" and not b.get("_explicit") and b.get("kind") not in ("special", "partie", "chapitre")
            and not str(b.get("kind", "")).startswith(("letter", "style"))
            and ((b["text"][:1].islower() and not _LETTERED.match(b["text"])) or _CLOSING.match(b["text"].strip())))


# "PACS).", "(Bts, hnd).": the end of a sentence cut by the page, read as a short title
_CLOSING = re.compile(r"^(\([^()]{1,40}\)|[^()]{1,30}\))[.;,]?$")


def merge_broken(items: list[dict]) -> int:
    """"… une institution de" ¶ "microfinance créée en 2007." → one paragraph."""
    n = 0
    i = 0
    while i + 1 < len(items):
        a, b = items[i], items[i + 1]
        if a.get("type") == "paragraph" and a["text"].strip() in ("-", "–", "•", "*", "o") and b.get("type") in ("paragraph", "heading") and not b.get("_explicit"):
            # a bullet left alone on its line by the PDF: it belongs to the next line
            b.update({"type": "list", "ordered": False, "level": 0})
            b.pop("kind", None)
            del items[i]
            n += 1
            continue
        if (
            a.get("type") == "paragraph" and (b.get("type") == "paragraph" or _tail(b)) and not b.get("_explicit")
            and "sigle" not in (a.get("role"), b.get("role"))  # "z : Niveau de confiance" is a symbol of its own, not the end of a sentence
            and not (STRONG_END if _tail(b) else END).search(a["text"]) and (len(a["text"]) > 30 or _tail(b))
            and b["text"][:1].islower()
        ):
            a["text"] = a["text"].rstrip() + " " + b["text"].lstrip()
            del items[i + 1]
            n += 1
            continue
        if _tail(b) or (b.get("type") == "heading" and not b.get("_explicit") and b.get("kind") != "special" and junk_rate(b["text"]) > 0.5):
            # a title never starts in lower case, and unreadable text (a PDF font read wrongly) is no title
            b["type"] = "paragraph"
            b.pop("level", None)
            b.pop("kind", None)
            n += 1
        i += 1
    return n


STRONG_END = re.compile(r"[.!?:;»]$")  # "(02)" does not end a sentence


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
                if len(t) > 110 or len(t.split()) > 14 or t.endswith(":") or "⟦eq" in t or items[j].get("kind", "").startswith(("style", "dec", "roman", "letter", "section")):
                    break  # a real sentence, a new intro, an equation or a numbered/styled heading ends the enumeration
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


_EMPTY_BULLET = re.compile(r"^[\s•◦▪●○■□➢►▸✓\-–—*·]*[.;,:]?\s*$")


def orphan_bullets(items: list[dict]) -> int:
    """A PDF whose bullets sit in their own column gives "•", "•", "•" then the texts as plain paragraphs:
    the empty items are dropped and the lines that follow them become the list's items again."""
    n = 0
    i = 0
    while i < len(items):
        it = items[i]
        if it.get("type") not in ("list", "paragraph") or it.get("hidden") or not _EMPTY_BULLET.match(it.get("text", "")) or not it.get("text", "").strip():
            i += 1
            continue
        j = i
        while j < len(items) and items[j].get("type") in ("list", "paragraph") and items[j].get("text", "").strip() and _EMPTY_BULLET.match(items[j]["text"]):
            j += 1
        empties = j - i
        level = it.get("level", 0) if it.get("type") == "list" else 0
        del items[i:j]
        n += empties
        # the texts of these bullets: the next lines (a list item, then plain paragraphs), up to a heading or a table
        k, taken = i, 0
        while k < len(items) and taken < empties + 1 and items[k].get("type") in ("list", "paragraph") and len(items[k].get("text", "")) < 600:
            if items[k]["type"] == "paragraph":
                items[k].update({"type": "list", "ordered": False, "level": level})
            k += 1
            taken += 1
        i = k
    return n


def clean(items: list[dict]) -> dict:
    """Runs every fix on the detected items (in place). Returns counters for the "what changed" card."""
    stats = {"orphan_bullets": orphan_bullets(items), "merged": merge_broken(items)}  # unmarked_lists runs earlier, before the model (see detect)
    texts = [it.get("text", "") for it in items if it.get("type") in ("paragraph", "list")]
    acr, proper = vocabulary(texts)
    caps = 0
    for it in items:
        t = it.get("type")
        text = it.get("text", "")
        if not text:
            continue
        if is_code_or_formula(text):
            continue
        if t == "heading" and it.get("level", 1) >= 2 and it.get("kind") not in ("partie", "chapitre", "special") and _upper_ratio(text) > 0.85 and len(text) > 6:
            # "I. LES LOIS" → "I. Les lois": the first word after the number keeps its capital
            it["text"] = re.sub(r"^(\s*(?:[IVXLivxl]+|\d+(?:\.\d+)*|[A-Ha-h])\s*[.\-–)_/:]+\s*)([a-zà-ÿ])", lambda m: m.group(1) + m.group(2).upper(), sentence_case(text, acr, proper))
            caps += 1
        elif it.get("role") == "label":
            if _upper_ratio(text) > 0.85:
                it["text"] = sentence_case(text, acr, proper)  # "EXEMPLE RÉSOLU" → "Exemple résolu"
                caps += 1
        elif t in ("paragraph", "list", "quote") and it.get("role") not in ("sigle", "biblio"):
            if _upper_ratio(text) > 0.85 and len(text) > 30:
                it["text"] = sentence_case(text, acr, proper)
                caps += 1
            it["text"], n = fix_caps(it["text"])
            caps += n
    caps += harmonise_tops(items)
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
