"""Real student PDFs: fonts without a character map, damaged files."""
from app.doc.extract import fix_shifted_fonts


def test_shifted_font_lines_are_decoded_and_normal_lines_kept():
    text = "6WDJH HIIHFWXp j /¶+DUP\nRédigé par :\nRAPPORT DE STAGE\nUY1 ENSP IUT\n6RXV O¶HQFDGUHPHQW"
    fixed, n = fix_shifted_fonts(text)
    assert fixed.split("\n") == ["Stage effectué à L’Harm", "Rédigé par :", "RAPPORT DE STAGE", "UY1 ENSP IUT", "Sous l’encadrement"]
    assert n == 2


def test_pdf_cleanup_drops_running_headers_old_toc_and_joins_labels():
    from app.doc.extract import pdf_cleanup

    head = "RAPPORT DE STAGE ASCESE 2022"
    pages = [
        "COVER\nREPUBLIQUE DU\nCAMEROUN",
        f"{head}\nSOMMAIRE ....................\nINTRODUCTION .............. 1\nSECTION 1 : DE LA CREATION\nL’ENTREPRISE ............ 3\n2.\nCadre ........... 4\nOCTOBRE 2022",
        f"{head}\nINTRODUCTION\nLe texte commence ici.\n2.\nCadre de référence\nOCTOBRE 2022",
        f"{head}\nSuite du texte.\n12\nOCTOBRE 2022",
        f"{head}\nFin du texte.\nOCTOBRE 2022",
    ]
    out = [ln for ln in pdf_cleanup("\f".join(pages)).split("\n") if ln.strip()]
    assert head not in out and "OCTOBRE 2022" not in out and "12" not in out
    assert not any("....." in ln for ln in out) and "SECTION 1 : DE LA CREATION" not in out
    assert "2. Cadre de référence" in out and "Le texte commence ici." in out
