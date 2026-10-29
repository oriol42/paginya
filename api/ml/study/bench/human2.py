"""More student habits, the ones handmade.py does not make, with the expected plan in a sidecar .truth.json.

Usage: python human2.py <out dir>
- pdf2word: a PDF turned into Word by an online converter — one paragraph per printed line, the page number and the
  running header typed between the pages, titles in bold.
- autonum: titles numbered with Word's own numbering put on Normal paragraphs (1. / 1.1 levels), bullets typed.
- web: text pasted from websites and from other students — fonts, sizes and colours change from one paragraph to the
  next, highlighting, a body paragraph in 14 pt, double spaces, titles in plain bold.
- tabs: "1.\tIntroduction", titles indented with tabs, text centred with spaces, lists typed with a tab.
- big: a 250-page mémoire (every habit at once, many tables), to see how far the server goes.
"""
import json, random, sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK, WD_COLOR_INDEX, WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

sys.path.insert(0, str(Path(__file__).parent))
from handmade import S, para  # noqa: E402

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)

CHAPTERS = [
    ("CADRE THÉORIQUE ET CONCEPTUEL", ["Définition des concepts", "Revue de la littérature", "Cadre théorique"],
     {"Revue de la littérature": ["Les travaux sur la microfinance", "Les travaux sur le crédit rural"]}),
    ("MÉTHODOLOGIE DE LA RECHERCHE", ["Type de recherche", "Population et échantillon", "Instruments de collecte"],
     {"Instruments de collecte": ["Le questionnaire", "Le guide d'entretien"]}),
    ("PRÉSENTATION ET ANALYSE DES RÉSULTATS", ["Caractéristiques des enquêtés", "Analyse des données", "Vérification des hypothèses"], {}),
    ("DISCUSSION ET SUGGESTIONS", ["Interprétation des résultats", "Limites de l'étude", "Suggestions"], {}),
]


def plan(rng, chapters=CHAPTERS):
    """[(level, text, kind)] + body between them."""
    out = [(1, "INTRODUCTION GÉNÉRALE", "special")]
    for i, (title, sections, subs) in enumerate(chapters, 1):
        out.append((1, title, "chapitre"))
        for s in sections:
            out.append((2, s, ""))
            for ss in subs.get(s, []):
                out.append((3, ss, ""))
    out.append((1, "CONCLUSION GÉNÉRALE", "special"))
    out.append((1, "BIBLIOGRAPHIE", "special"))
    return out


ROMANS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def numbered(items):
    """Typed numbers: CHAPITRE I : …, 1. …, 1.1. …"""
    out, ch, c2, c3 = [], 0, 0, 0
    for level, text, kind in items:
        if kind == "chapitre":
            ch += 1; c2 = c3 = 0
            out.append((level, f"CHAPITRE {ROMANS[ch - 1]} : {text}", text))
        elif kind == "special":
            out.append((level, text, text))
        elif level == 2:
            c2 += 1; c3 = 0
            out.append((level, f"{c2}.\t{text}", text))
        else:
            c3 += 1
            out.append((level, f"{c2}.{c3}.\t{text}", text))
    return out


def body(rng, doc, add, habit, n=2):
    for _ in range(n):
        text = para(rng, rng.randint(3, 6))
        if habit == "pdf2word":
            words, line = text.split(), []
            for w in words:  # one paragraph per printed line, cut at ~85 characters
                line.append(w)
                if len(" ".join(line)) > 85:
                    add(" ".join(line)); line = []
            if line: add(" ".join(line))
        elif habit == "web":
            p = add(text.replace(". ", ".  "), font=rng.choice(["Calibri", "Arial", "Times New Roman", "Verdana", "Segoe UI"]),
                    size=rng.choice([10, 11, 12, 12, 14]), color=rng.choice([None, None, (0x33, 0x33, 0x33), (0x1F, 0x4E, 0x79)]))
            if rng.random() < 0.15:
                for r in p.runs: r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        elif habit == "tabs":
            add(("\t" if rng.random() < 0.7 else "      ") + text)
        else:
            add(text)
    if rng.random() < 0.3:
        items = ["l'insuffisance des moyens", "le manque de formation", "les retards de paiement", "la lourdeur des procédures"]
        for it in rng.sample(items, 3):
            add(("\t" if habit == "tabs" else "") + rng.choice(["- ", "• ", "➢ ", "* "]) + it + rng.choice([" ;", ";", ""]))


def table(rng, doc, add, n):
    add(f"Tableau {n} : Répartition des enquêtés selon le niveau d'étude", bold=True, center=True)
    rows = [["Niveau", "Effectif", "Pourcentage"]] + [[lv, str(e), f"{e * 2.5:.1f} %"] for lv, e in
                                                      zip(["Primaire", "Secondaire", "Supérieur", "Aucun"], rng.sample(range(3, 20), 4))]
    t = doc.add_table(rows=len(rows), cols=3); t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row): t.cell(i, j).text = cell
    add("Source : nos enquêtes, 2025", italic=True)


def autonum(doc, p, level):
    """Word's own numbering on a Normal paragraph (numId 1 of the template's list, ilvl = depth)."""
    ppr = p._p.get_or_add_pPr()
    numpr = OxmlElement("w:numPr")
    ilvl = OxmlElement("w:ilvl"); ilvl.set(qn("w:val"), str(level))
    num = OxmlElement("w:numId"); num.set(qn("w:val"), "1")
    numpr.append(ilvl); numpr.append(num); ppr.append(numpr)


def build(name, habit, seed, chapters=CHAPTERS, repeat=1):
    rng = random.Random(seed)
    doc = Document()
    doc.styles["Normal"].font.name = rng.choice(["Times New Roman", "Calibri", "Arial"])
    doc.styles["Normal"].font.size = Pt(12)
    page = [0]

    def add(text, bold=False, center=False, size=None, color=None, italic=False, font=None, underline=False):
        p = doc.add_paragraph()
        r = p.add_run(text)
        r.bold = bold or None; r.italic = italic or None; r.underline = underline or None
        if size: r.font.size = Pt(size)
        if font: r.font.name = font
        if color: r.font.color.rgb = RGBColor(*color)
        if center: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return p

    def newpage():
        page[0] += 1
        if habit == "pdf2word":  # the converter keeps the page number and the running header as text
            add(str(page[0]), center=True)
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            add("Mémoire de Master — Université de Douala — 2025", italic=True, size=9)
        elif habit == "tabs":
            for _ in range(rng.randint(5, 12)): doc.add_paragraph("")
        else:
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # a cover of the usual kind
    for line in ["RÉPUBLIQUE DU CAMEROUN", "Paix – Travail – Patrie", "UNIVERSITÉ DE DOUALA", "FACULTÉ DES SCIENCES ÉCONOMIQUES ET DE GESTION"]:
        add(line, bold=True, center=True, size=11)
    add("MÉMOIRE DE MASTER", bold=True, center=True, size=18)
    add("L'ACCÈS AU CRÉDIT DES PETITES ENTREPRISES DANS LA VILLE DE DOUALA", bold=True, center=True, size=16)
    add("Présenté par : EBANDA Paul Hervé", center=True)
    add("Sous la direction du Pr NKOA Jean", center=True)
    add("Année académique 2024-2025", bold=True, center=True)
    newpage()

    truth = []
    tn = 0
    for rep in range(repeat):
        items = numbered(plan(rng, chapters))
        for level, text, clean in items:
            kind = "chapitre" if text.startswith("CHAPITRE") else "special" if level == 1 else ""
            if level == 1 and (rep or kind != "special" or clean != "INTRODUCTION GÉNÉRALE"):
                newpage()
            if habit == "autonum" and kind == "":
                p = doc.add_paragraph(style="List Number" if level == 2 else "List Number 2")  # Word draws the number
                p.add_run(clean).bold = True
            elif habit == "web":
                add(text.replace("\t", " "), bold=True, size=rng.choice([None, 13, 14]), color=rng.choice([None, (0xC0, 0x39, 0x2B)]))
            elif habit == "tabs":
                add(("\t" * (level - 1)) + text, bold=level <= 2, center=level == 1)
            else:  # pdf2word, big
                add(text.replace("\t", " "), bold=True, size=14 if level == 1 else None, center=level == 1)
            truth.append((level, clean if habit == "autonum" else text.replace("\t", " ")))
            body(rng, doc, add, habit if habit != "big" else rng.choice(["pdf2word", "web", "tabs", "plain"]), n=rng.randint(2, 4) if repeat == 1 else rng.randint(6, 10))
            if level >= 2 and rng.random() < (0.25 if repeat == 1 else 0.6):
                tn += 1
                table(rng, doc, add, tn)
    if habit == "pdf2word":
        newpage()
    fname = f"hm2_{name}"
    doc.save(OUT / f"{fname}.docx")
    (OUT / f"{fname}.docx.truth.json").write_text(json.dumps(truth, ensure_ascii=False))
    return fname


for i, h in enumerate(["pdf2word", "autonum", "web", "tabs"]):
    build(f"memoire_{h}", h, 300 + i)
# 250 pages: the whole plan written 7 times over (7 × 4 chapters), every habit mixed
build("memoire_250_pages", "big", 400, repeat=7)
print("ok:", sorted(p.name for p in OUT.glob("hm2_*.docx")))
