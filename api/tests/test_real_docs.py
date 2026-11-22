"""Habits found on real Cameroonian reports and books (bench of 22/11/2026), each reduced to a few lines."""
from app.doc.detect import detect
from app.doc.extract import Raw, from_text, pdf_cleanup


def test_word_bullets_printed_to_pdf_find_their_items_again():
    """Word's bullet is a Symbol-font glyph (\\uf0b7): pdftotext puts all of them first, then the items."""
    text = "Ce service comprend :\n\n\n\nla mise à jour de la base ;\nla vérification des pièces ;\nla formation des stagiaires.\nFin du texte."
    lines = [ln for ln in pdf_cleanup(text).split("\n") if ln.strip()]
    assert lines[1:4] == [" la mise à jour de la base ;", " la vérification des pièces ;", " la formation des stagiaires."]
    blocks = detect(from_text("\n".join(lines)))["blocks"]
    assert [b["type"] for b in blocks] == ["paragraph", "list", "list", "list", "paragraph"]


def test_bullets_all_on_the_first_item_line_are_split():
    lines = [ln for ln in pdf_cleanup("Activités :\n·  ·  ·  le classement ;\nla saisie ;\nles courriers.").split("\n") if ln.strip()]
    assert lines[1:] == ["· le classement ;", "· la saisie ;", "· les courriers."]


def test_a_books_running_header_naming_the_section_is_not_text():
    """Odd pages print the current section at the top: 4 pages out of 10, too few for the usual header rule."""
    pages = []
    for n in range(10):
        head = ["4.5 L'évolution des processus et la gestion du changement", str(110 + n)] if n % 2 else [str(110 + n), "Chapitre 4. La gouvernance des processus"]
        body = [f"Page {n} : le changement demande du temps et l'adhésion de chacun des acteurs, ligne {k}." for k in range(6)]
        if n == 3:
            body.insert(2, "4.5 L'évolution des processus et la gestion du changement")  # the real title, in the page
        pages.append("\n".join(head + body))
    out = pdf_cleanup("\f".join(pages))
    assert out.count("4.5 L'évolution des processus") == 1


def test_a_sommaire_typed_with_a_tab_before_the_page_is_dropped():
    """"DEDICACE<tab>I", "CHAPITRE 1 : INSERTION EN ENTREPRISE<tab>11": an old sommaire, never titles."""
    lines = ["REMERCIEMENTS", "Je remercie toute l'équipe de Devira pour son accueil pendant ce stage de deux mois.", "SOMMAIRE",
             "DEDICACE\tI", "REMERCIEMENTS\tII", "LISTE DES FIGURES\tVI", "INTRODUCTION GÉNÉRALE\t10", "CHAPITRE 1 : INSERTION EN ENTREPRISE\t11",
             "I.  Présentation de Devira\t11", "CONCLUSION GÉNÉRALE\t32", "TABLE DES MATIÈRES\t34",
             "RÉSUMÉ", "Ce rapport présente le développement d'un outil de suivi des clients.", "INTRODUCTION GÉNÉRALE",
             "Le stage s'est déroulé à Ebolowa pendant deux mois au sein de l'équipe technique.", "CHAPITRE 1 : INSERTION EN ENTREPRISE",
             "I.  Présentation de Devira", "Devira est une jeune entreprise du numérique installée à Ebolowa depuis 2021."]
    raws = [Raw(text=t, source="docx") for t in lines]
    out = detect(raws)
    heads = [b["text"] for b in out["blocks"] if b["type"] == "heading" and not b.get("hidden")]
    assert not any("\t" in h for h in heads)
    assert [h.upper() for h in heads] == ["REMERCIEMENTS", "RÉSUMÉ", "INTRODUCTION GÉNÉRALE", "CHAPITRE 1 : INSERTION EN ENTREPRISE", "I.  PRÉSENTATION DE DEVIRA"]
    assert out["meta"]["slots"] == {"toc": {"after": "remerciements", "title": "SOMMAIRE"}}  # an entry of the old sommaire plans nothing
    assert "Ancien sommaire tapé à la main remplacé par un sommaire automatique" in out["meta"]["changes"]


def test_two_entries_of_a_sommaire_on_one_pdf_line_go_too():
    text = ("INTRODUCTION\n\nDédicace ______________________________________________________________________ i remerciements "
            "_______________________________________________________________ ii\n\nLe texte de l'introduction commence ici et continue longtemps.")
    out = detect(from_text(text))
    assert not any("____" in b.get("text", "") for b in out["blocks"])


def test_a_sentence_starting_with_chapitre_is_not_a_chapter():
    text = ("INTRODUCTION\n\nLe texte de l'introduction présente le plan de cet ouvrage, comme on le verra au\n\n"
            "chapitre 5, La dimension humaine d'un projet.\n\nCHAPITRE 1 : LES PROCESSUS\n\nUn processus est un ensemble d'activités.")
    heads = [b["text"] for b in detect(from_text(text))["blocks"] if b["type"] == "heading"]
    assert "chapitre 5, La dimension humaine d'un projet." not in heads and "CHAPITRE 1 : LES PROCESSUS" in heads
