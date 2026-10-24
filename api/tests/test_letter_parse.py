from app.forms.letter_parse import letter_signals, parse_letter

EMPLOI = """TCHOUMI KAMGA Paul
BP 1234 Douala
Tél. 699 87 65 43

                                                    Douala, le 03 mars 2026

                                    A Monsieur le Directeur Général
                                    de la Société Camerounaise des Eaux
                                    DOUALA

OBJET : DEMANDE D'EMPLOI

Monsieur le Directeur Général,

Titulaire d'un BTS en Génie Électrique, j'ai l'honneur de solliciter un emploi d'électricien.

Je reste à votre entière disposition pour un entretien.

Veuillez agréer, Monsieur le Directeur Général, l'expression de mes salutations distinguées.

                                                    TCHOUMI KAMGA Paul
"""

MOTIVATION = """FOTSO Aurélien
fotso.aurelien@yahoo.fr

Dschang, le 20 août 2026

À l'attention de Monsieur le Coordonnateur du Master Professionnel
Faculté d'Agronomie et des Sciences Agricoles
Université de Dschang

Objet : lettre de motivation
P.J. : CV ; relevés de notes

Monsieur le Coordonnateur,

Titulaire d'une Licence, je souhaite intégrer votre Master.

Je vous prie d'agréer, Monsieur le Coordonnateur, l'expression de mes sentiments respectueux.

FOTSO Aurélien
"""


def test_a_typed_request_is_read_back_into_the_letter_fields():
    assert letter_signals(EMPLOI)
    d = parse_letter(EMPLOI)
    assert d["sender"] == {"name": "TCHOUMI KAMGA Paul", "extra": "", "address": "BP 1234 Douala", "phone": "699 87 65 43", "email": ""}
    assert (d["place"], d["date"]) == ("Douala", "03 mars 2026")
    assert d["recipient"] == {"civility": "Monsieur", "title": "le Directeur Général", "org": "de la Société Camerounaise des Eaux", "city": "Douala"}
    assert d["subject"] == "Demande d'emploi" and d["type"] == "emploi"
    assert d["body"].startswith("Titulaire") and d["body"].endswith("salutations distinguées.") and "TCHOUMI" not in d["body"]


def test_attention_line_and_attachments():
    d = parse_letter(MOTIVATION)
    assert d["recipient"]["title"] == "le Coordonnateur du Master Professionnel"
    assert d["recipient"]["org"] == "Faculté d'Agronomie et des Sciences Agricoles Université de Dschang" and d["recipient"]["city"] == ""
    assert d["subject"] == "Lettre de motivation" and d["attachments"] == ["CV", "relevés de notes"]
    assert d["sender"]["email"] == "fotso.aurelien@yahoo.fr"


def test_a_report_is_not_a_letter():
    assert not letter_signals("CHAPITRE 1 : INTRODUCTION\n\nLe présent rapport présente le stage.\n\nObjet : étude\n\nRésultats.")


def test_a_pasted_letter_is_offered_to_the_letter_tool(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app import config, db
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.sqlite3")
    from app.main import app
    with TestClient(app) as c:
        v = c.post("/documents", json={"text": EMPLOI}).json()
        assert v["analysis"]["letter"] is True and v["analysis"]["exam"] is False
        d = c.post(f"/documents/{v['id']}/letter").json()
        assert d["subject"] == "Demande d'emploi" and d["recipient"]["city"] == "Douala"
