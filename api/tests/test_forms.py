import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import config, db, fapshi
from app.forms.exam import parse, split_points, total_points

LETTER = {
    "type": "emploi",
    "sender": {"name": "MBALLA Junior", "address": "BP 1234 Yaoundé", "phone": "670000000", "email": "junior@mail.cm"},
    "place": "Yaoundé", "date": "23 septembre 2026",
    "recipient": {"civility": "Monsieur", "title": "le Directeur Général", "org": "de ENEO Cameroun", "city": "Douala"},
    "via": "Monsieur le Chef du personnel",
    "subject": "Demande d'emploi",
    "attachments": ["Curriculum vitae", "Copie du diplôme"],
    "body": "J'ai l'honneur de venir très respectueusement solliciter un emploi.\n\nDans l'attente d'une suite favorable, veuillez agréer, Monsieur le Directeur Général, l'expression de ma haute considération.",
    "stamp": True,
}

EXAM = {
    "school": "Lycée de Biyem-Assi", "department": "Département de Mathématiques", "year": "2025-2026",
    "exam": "Évaluation de la 1ère séquence", "subject": "Mathématiques", "class": "Terminale C",
    "duration": "3 heures", "coef": "7",
    "content": "Exercice 1 (5 pts)\n1) Résoudre l'équation x² - 4 = 0. (2 pts)\n2) Calculer la limite. (3 pts)\n"
               "Exercice 2 : QCM (5 points)\n1. Quelle est la dérivée de x² ?\nA) 2x\nB) x\n"
               "Problème (10 pts)\nPartie A\na) Étudier la fonction f.\nb) Tracer la courbe.",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    for mod in (config, db):
        monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(mod, "DB_PATH", tmp_path / "t.sqlite3")
    monkeypatch.setattr(config, "FAPSHI_MODE", "mock")
    monkeypatch.setattr(fapshi, "MOCK_DELAY_S", 0)
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_exam_parsing_and_total():
    items = parse(EXAM["content"])
    kinds = [i["kind"] for i in items]
    assert kinds[:3] == ["section", "question", "question"]
    assert items[1]["points"] == "2 pts" and items[1]["text"].endswith("= 0.")
    assert "option" in kinds and "sub" in kinds
    assert total_points(items) == 20
    assert split_points("Question (0,5 pt)") == ("Question", "0.5 pt")


def test_letter_flow_render_pay_download(client):
    r = client.post("/forms", json={"kind": "lettre", "data": LETTER})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert doc["amount"] == 350 and doc["render"]["pages"] == 1
    assert client.get(f"/forms/{doc["id"]}/pages/1.webp").content[8:12] == b"WEBP"
    assert client.get(f"/orders/{doc['id']}/file.pdf").status_code == 402
    client.post(f"/orders/{doc['id']}/pay", json={"phone": "670000000"})
    assert client.get(f"/orders/{doc['id']}").json()["status"] == "PAID"
    docx = client.get(f"/orders/{doc['id']}/file.docx")
    xml = zipfile.ZipFile(io.BytesIO(docx.content)).read("word/document.xml").decode()
    assert "Monsieur le Directeur Général," in xml and "Timbre fiscal" in xml and "ENEO" in xml


def test_exam_flow_and_edit(client):
    doc = client.post("/forms", json={"kind": "epreuve", "data": EXAM}).json()
    assert doc["amount"] == 550 and doc["total_points"] == 20
    changed = dict(EXAM, content=EXAM["content"] + "\nExercice 3 (4 pts)\n1) Bonus.")
    r = client.put(f"/forms/{doc['id']}", json={"data": changed})
    assert r.status_code == 200 and r.json()["total_points"] == 24


def test_unknown_kind_rejected(client):
    assert client.post("/forms", json={"kind": "virus", "data": {}}).status_code == 400
