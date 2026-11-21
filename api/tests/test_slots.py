"""Pages planned by the author (sommaire, lists, sigles…): built where they are, filled, or removed when left empty."""
import shutil
import subprocess

import pytest
from docx import Document

from app.doc import keep, office, slots
from app.doc.detect import detect
from app.doc.extract import from_text
from app.doc.render import build_docx, options_for

PLANNED = """RAPPORT DE STAGE ACADÉMIQUE

DÉDICACE

REMERCIEMENTS

Je remercie toute l'équipe de la Banque des États de l'Afrique centrale (BEAC) pour son accueil pendant ces trois mois.

SOMMAIRE

LISTE DES SIGLES ET ABRÉVIATIONS

LISTE DES TABLEAUX

LISTE DES FIGURES

LISTE DES ANNEXES

RÉSUMÉ

Ce rapport présente le stage effectué à Yaoundé. Mots-clés : stage, banque.

INTRODUCTION GÉNÉRALE

Le stage s'est déroulé à la direction informatique. Les Technologies de l'Information et de la Communication (TIC) y occupent une place centrale. L'École nationale supérieure polytechnique (ENSP) forme les ingénieurs.

CHAPITRE I : PRÉSENTATION DE LA STRUCTURE

1.1 Historique

La structure a été créée en 1972 et compte aujourd'hui plusieurs centaines d'employés répartis dans six pays.

Tableau 1 : Effectifs par service

1.2 Missions

Elle émet la monnaie et veille à la stabilité du système bancaire de la sous-région.

CONCLUSION GÉNÉRALE

Ce stage a été très enrichissant pour ma formation et mon projet professionnel.

BIBLIOGRAPHIE

Dupont, J. (2020). La banque centrale. Paris : Economica.

TABLE DES MATIÈRES

ANNEXES

Annexe 1 : Organigramme de la structure

Annexe 2 : Questionnaire
"""


def planned():
    out = detect(from_text(PLANNED))
    return out, [b for b in out["blocks"] if not b.get("hidden")]


def test_planned_pages_are_found_where_the_author_put_them():
    out, blocks = planned()
    assert out["meta"]["slots"] == {
        "toc": {"after": "remerciements", "title": "SOMMAIRE"},
        "lot": {"after": "sigles", "title": "LISTE DES TABLEAUX"},
        "lof": {"after": "sigles", "title": "LISTE DES FIGURES"},
        "toc_end": {"title": "TABLE DES MATIÈRES", "before": "annexes"},
    }
    assert blocks[0] == {**blocks[0], "type": "title", "text": "RAPPORT DE STAGE ACADÉMIQUE"}  # not a chapter: the front matter stays roman
    changes = out["meta"]["changes"]
    assert "Sommaire placé à l'endroit que tu avais prévu (après les remerciements)" in changes
    assert "Table des matières placée avant les annexes, comme tu l'avais prévu" in changes
    assert "Page « Liste des figures » retirée : ton document n'a pas de figure légendé" in changes


def test_empty_pages_are_filled_from_the_text_or_removed():
    out, blocks = planned()
    specials = [b.get("special") for b in blocks if b["type"] == "heading" and b.get("special")]
    assert "dedicace" not in specials  # never written: removed, no blank page
    sigles = [(b["term"], b["definition"]) for b in blocks if b.get("role") == "sigle"]
    assert sigles == [
        ("BEAC", "Banque des États de l'Afrique centrale"),
        ("ENSP", "École nationale supérieure polytechnique"),
        ("TIC", "Technologies de l'Information et de la Communication"),
    ]
    i = next(i for i, b in enumerate(blocks) if b.get("special") == "liste_annexes")
    assert [b["text"] for b in blocks[i + 1:i + 3]] == ["Annexe 1 : Organigramme de la structure", "Annexe 2 : Questionnaire"]
    changes = out["meta"]["changes"]
    assert "Liste des sigles remplie avec les 3 sigles expliqués dans ton texte" in changes
    assert "Page laissée vide retirée : « Dédicace »" in changes
    assert not any(k.startswith("_") for b in out["blocks"] for k in b)  # no working key left in the saved document


def test_the_word_file_follows_the_authors_plan(tmp_path):
    out, _ = planned()
    meta = out["meta"]
    opts = options_for(meta["kind"], meta["words"], False, meta.get("slots"))
    data = build_docx({"blocks": out["blocks"], "meta": meta, "style": {"theme": "academique"}, "options": opts}, tmp_path)
    (tmp_path / "d.docx").write_bytes(data)
    texts = [p.text.strip() for p in Document(str(tmp_path / "d.docx")).paragraphs if p.text.strip()]
    order = [t for t in texts if t.isupper() or t.startswith("[[")]
    assert order[:9] == ["RAPPORT DE STAGE ACADÉMIQUE", "REMERCIEMENTS", "SOMMAIRE", "[[TOC:2]]", "LISTE DES SIGLES ET ABRÉVIATIONS",
                         "LISTE DES TABLEAUX", "[[LOT]]", "LISTE DES ANNEXES", "RÉSUMÉ"]
    assert "LISTE DES FIGURES" not in texts  # no figure: the planned page is not printed
    end = texts.index("TABLE DES MATIÈRES")
    assert texts[end + 1] == "[[TOC:4]]" and texts[end + 2] == "ANNEXES"


def test_a_table_des_matieres_at_the_start_is_detailed_and_not_repeated_at_the_end():
    text = PLANNED.replace("SOMMAIRE\n", "TABLE DES MATIÈRES\n", 1).replace("\nTABLE DES MATIÈRES\n\nANNEXES", "\nANNEXES")
    out = detect(from_text(text))
    meta = out["meta"]
    assert meta["slots"]["toc"]["title"] == "TABLE DES MATIÈRES" and "toc_end" not in meta["slots"]
    opts = options_for("memoire", meta["words"], False, meta["slots"])
    assert opts["toc"] is True and opts["toc_end"] is False


def test_a_short_text_with_a_planned_sommaire_gets_one():
    text = "SOMMAIRE\n\nINTRODUCTION\n\n" + "Le texte de l'exposé. " * 30 + "\n\nI. Les causes\n\nLe texte. \n\nII. Les conséquences\n\nLe texte.\n\nCONCLUSION\n\nFin."
    meta = detect(from_text(text))["meta"]
    assert options_for("expose", meta["words"], False, meta.get("slots"))["toc"] is True


@pytest.mark.parametrize("text, expected", [
    ("Le Fonds monétaire international (FMI) prête.", [("FMI", "Fonds monétaire international")]),
    ("La CEMAC (Communauté économique et monétaire de l'Afrique centrale) regroupe six pays.",
     [("CEMAC", "Communauté économique et monétaire de l'Afrique centrale")]),
    ("Les données (voir annexe) et le chiffre (2020) ne sont pas des sigles. Il est parti (OK).", []),
])
def test_acronyms_explained_in_the_text(text, expected):
    assert slots.acronyms([{"type": "paragraph", "text": text}]) == expected


# --- the user's own Word file, kept -------------------------------------------------------------

def _seq_caption(doc, label, n, text):
    """A Word caption "Tableau 1 : …" with its real number field (SEQ Tableau), as Word's Insert caption makes it."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    p = doc.add_paragraph(f"{label} ")
    for kind, value in (("begin", None), (None, f" SEQ {label} \\* ARABIC "), ("separate", None)):
        run = OxmlElement("w:r")
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            run.append(fc)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = value
            run.append(it)
        p._p.append(run)
    p.add_run(str(n))
    end = OxmlElement("w:r")
    fc = OxmlElement("w:fldChar")
    fc.set(qn("w:fldCharType"), "end")
    end.append(fc)
    p._p.append(end)
    p.add_run(f" : {text}")


def planned_docx(tmp_path):
    doc = Document()
    for line in ("RÉPUBLIQUE DU CAMEROUN", "UNIVERSITÉ DE YAOUNDÉ I", "RAPPORT DE STAGE", "Par : Jean Dupont", "Année académique : 2026-2027"):
        doc.add_paragraph(line)
    doc.add_page_break()
    doc.add_paragraph("SOMMAIRE")
    doc.add_paragraph("")
    doc.add_page_break()
    doc.add_paragraph("LISTE DES TABLEAUX")
    doc.add_page_break()
    doc.add_heading("Introduction", 1)
    doc.add_paragraph("Texte de l'introduction. " * 20)
    doc.add_heading("Chapitre 1 : La structure", 1)
    _seq_caption(doc, "Tableau", 1, "Effectifs par service")
    doc.add_paragraph("Texte du chapitre. " * 20)
    _seq_caption(doc, "Tableau", 2, "Budget annuel")
    doc.add_heading("Conclusion", 1)
    doc.add_paragraph("Texte de la conclusion.")
    doc.add_page_break()
    doc.add_paragraph("TABLE DES MATIÈRES")
    path = tmp_path / "planned.docx"
    doc.save(path)
    return path


def test_kept_word_file_gets_its_empty_pages_filled(tmp_path):
    out = tmp_path / "out.docx"
    done = keep.touch(planned_docx(tmp_path), out, numbers="none", toc="add")
    assert done == ["sommaire", "liste des tableaux"]
    texts = [p.text for p in Document(str(out)).paragraphs if p.text.strip()]
    assert texts[texts.index("SOMMAIRE") + 1] == "[[TOC:2]]"
    assert texts[texts.index("LISTE DES TABLEAUX") + 1] == "[[LOI:Tableau]]"
    assert texts[texts.index("TABLE DES MATIÈRES") + 1] == "[[TOC:4]]"  # after the introduction: every level


def test_kept_word_file_without_captions_keeps_its_list_page_as_it_is(tmp_path):
    doc = Document()
    doc.add_paragraph("LISTE DES FIGURES")
    doc.add_page_break()
    doc.add_heading("Introduction", 1)
    doc.add_paragraph("Texte.")
    src = tmp_path / "nofig.docx"
    doc.save(src)
    assert keep.touch(src, tmp_path / "o.docx", numbers="none", toc="keep") == []  # nothing to list it from


@pytest.mark.skipif(not shutil.which("soffice") or not shutil.which("pdftotext"), reason="LibreOffice et poppler nécessaires")
def test_libreoffice_builds_the_list_from_the_authors_captions(tmp_path):
    touched = tmp_path / "touched.docx"
    keep.touch(planned_docx(tmp_path), touched, numbers="none", toc="add")
    office.finalize(touched, None, tmp_path / "out.pdf")
    text = subprocess.run(["pdftotext", str(tmp_path / "out.pdf"), "-"], capture_output=True, text=True).stdout
    page = text.split("\f")[2]  # cover, sommaire, then the list of tables
    assert "LISTE DES TABLEAUX" in page and "Effectifs par service" in page and "Budget annuel" in page
    assert "[[" not in text
