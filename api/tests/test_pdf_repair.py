"""Real student PDFs: fonts without a character map, damaged files."""
from app.doc.extract import fix_shifted_fonts


def test_shifted_font_lines_are_decoded_and_normal_lines_kept():
    text = "6WDJH HIIHFWXp j /¶+DUP\nRédigé par :\nRAPPORT DE STAGE\nUY1 ENSP IUT\n6RXV O¶HQFDGUHPHQW"
    fixed, n = fix_shifted_fonts(text)
    assert fixed.split("\n") == ["Stage effectué à L’Harm", "Rédigé par :", "RAPPORT DE STAGE", "UY1 ENSP IUT", "Sous l’encadrement"]
    assert n == 2
