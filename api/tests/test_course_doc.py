"""A revision course (concours ENSPD, sent by a customer on 28/10/2026): typed sommaire, "CHAPITRE N" on its own
line, boxes labelled "MÉTHODE" / "EXEMPLE RÉSOLU" again and again, formulas and SQL between the paragraphs."""
from app.doc.clean import fix_caps, sentence_case, vocabulary
from app.doc.detect import detect
from app.doc.extract import Raw, fix_shifted_fonts

BODY = "Ce paragraphe explique la méthode en détail, avec assez de mots pour être un vrai paragraphe du cours."


def _raws(lines: list[str]) -> list[Raw]:
    return [Raw(text=t, source="pdf", new_page=t.startswith("CHAPITRE") or t == "Sommaire") for t in lines]


COURSE = [
    "P R É PA R AT I O N I N T E N S I V E", "Concours ENSPD", "Sommaire",
    "Chapitre 1 — Logique et raisonnement", "1.1 Mise en équation · 1.2 Problèmes têtes & pattes · 1.3 Suites",
    "Chapitre 2 — Bases de données", "2.1 Schéma relationnel · 2.2 Requêtes SQL",
    "CHAPITRE 1", "Logique et raisonnement", BODY,
    "1.1 — Mise en équation des énigmes", BODY,
    "MÉTHODE EN 4 ÉTAPES", "1. Identifier l'inconnue.", "2. Découper l'énoncé.", "3. Poser l'équation.",
    "EXEMPLE RÉSOLU", BODY, "12 + 8 + 8 + 4x = 44 → 4x = 16 → x = 4", BODY,
    "1.2 — Problèmes de comptage", BODY, "ASTUCE MNÉMOTECHNIQUE", BODY, "EXEMPLE RÉSOLU", BODY, "VOIR LA CORRECTION", BODY,
    "1.3 — Suites numériques", BODY, "PIÈGE À ÉVITER", BODY, "EXEMPLE RÉSOLU", BODY, "VOIR LA CORRECTION", BODY,
    "CHAPITRE 2", "Bases de données", BODY,
    "2.1 — Schéma relationnel", BODY, "EMP(ENO, ENOM, SAL, DNO)", BODY,
    "2.2 — Requêtes SQL", BODY, "VOIR LA CORRECTION", "SELECT EMP.ENOM, DEPT.DNOM", "FROM EMP", "JOIN DEPT ON EMP.DNO = DEPT.DNO;", BODY,
]


def test_course_structure():
    d = detect(_raws(COURSE))
    heads = [(b["level"], b["text"]) for b in d["blocks"] if b["type"] == "heading" and not b.get("hidden")]
    texts = [t for _, t in heads]
    assert d["meta"]["title"] == "PRÉPARATION INTENSIVE"  # spaced letters glued back, cut into words
    assert d["meta"].get("typed_plan")  # the typed sommaire is gone
    assert heads[0] == (1, "CHAPITRE 1 : Logique et raisonnement")  # "CHAPITRE 1" and its name are one title
    assert (2, "1.1 — Mise en équation des énigmes") in heads
    assert ("Exemple résolu" not in texts and "Voir la correction" not in texts
            and "EXEMPLE RÉSOLU" not in texts and "VOIR LA CORRECTION" not in texts)  # labels of boxes, not sections
    labels = [b["text"] for b in d["blocks"] if b.get("role") == "label"]
    assert labels.count("Exemple résolu") == 3
    assert not any("=" in t or "EMP(" in t for t in texts)  # formulas never titles
    # the small title of a box sits under its numbered section
    assert dict((t, lv) for lv, t in heads)["Méthode en 4 étapes"] == 3
    code = [b["text"] for b in d["blocks"] if b["type"] == "code"]
    assert code == ["SELECT EMP.ENOM, DEPT.DNOM\nFROM EMP\nJOIN DEPT ON EMP.DNO = DEPT.DNO;"]
    steps = [b["text"] for b in d["blocks"] if b["type"] == "list" and b.get("ordered")]
    assert steps[:3] == ["Identifier l'inconnue.", "Découper l'énoncé.", "Poser l'équation."]


def test_formulas_are_not_shifted_fonts():
    for line in ["4×70 000 + 5×30 + 10×2 = 280 000 + 150 + 20 = 280 170 dm³", "Compléter : 2, 6, 12, 20, 30, ?"]:
        assert fix_shifted_fonts(line) == (line, 0)


def test_capitals():
    acr, proper = vocabulary(["Les lois de De Morgan sont utiles.", "Lis « Un switch » attentivement."])
    assert sentence_case("FORMULE À CONNAÎTRE PAR CŒUR", acr, proper) == "Formule à connaître par cœur"
    assert sentence_case("CONVERTIR LES PUISSANCES DE 2", acr, proper) == "Convertir les puissances de 2"
    assert fix_caps("p + l = 17 et 2p + 4l = 52")[0] == "p + l = 17 et 2p + 4l = 52"
    assert fix_caps('des implications ("si... alors...") sans piège.')[0] == 'Des implications ("si... alors...") sans piège.'
