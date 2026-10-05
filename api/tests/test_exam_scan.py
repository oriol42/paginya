"""Photos of exam papers -> header fields + exercises for /epreuve, and the AI provider fallback."""
import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import config, db, fapshi
from app.doc import scan
from app.doc.exam_scan import EXAM_PROMPT, blocks_to_text, finalize, raws_to_text, split_reply
from app.doc.extract import Raw
from app.forms.exam import parse, total_points

AI_REPLY = """ENTETE
ecole: Lycée Bilingue de Biyem-Assi
ministere: MINISTÈRE DES ENSEIGNEMENTS SECONDAIRES
annee: 2025-2026
evaluation: Évaluation de la 2e séquence
matiere: Mathématiques
classe: Terminale C
duree: 3 heures
coefficient: 5
examinateur:
consignes: Calculatrice non autorisée
CONTENU
Exercice 1 (5 pts)
1) Résoudre dans ℝ l'équation x² - 5x + 6 = 0. (2 pts)
2) En déduire le signe de x² - 5x + 6. (3 pts)

Exercice 2 : QCM (5 pts)
1) La dérivée de x³ est :
A) 3x²
B) x²
"""

PRINTED = """RÉPUBLIQUE DU CAMEROUN
Paix - Travail - Patrie
********
MINISTÈRE DES ENSEIGNEMENTS
SECONDAIRES
LYCÉE DE NKOLBISSON
ÉPREUVE DE PHYSIQUE
Classe : Première D    Durée : 2 h    Coef : 2
Année scolaire 2025-2026
Les candidats traiteront les deux exercices.
EXERCICE 1 (8 pts)
1) Énoncer la loi d'Ohm. (2 pts)
"""


def test_split_reply_reads_the_header_and_skips_empty_values():
    fields, content = split_reply(AI_REPLY)
    assert fields["school"] == "Lycée Bilingue de Biyem-Assi"
    assert fields["class"] == "Terminale C"
    assert fields["duration"] == "3 heures"
    assert fields["coef"] == "5"
    assert fields["instructions"] == "Calculatrice non autorisée"
    assert "teacher" not in fields  # "examinateur:" was left empty
    assert content.startswith("Exercice 1 (5 pts)")


def test_split_reply_survives_markdown_and_missing_markers():
    fields, content = split_reply("```\n**ENTETE**\n- classe: 3e A\nExercice 1 (4 pts)\n1) Calculer.\n```")
    assert fields == {"class": "3e A"}
    assert content == "Exercice 1 (4 pts)\n1) Calculer."
    assert split_reply("Exercice 1 (4 pts)\n1) Calculer.") == ({}, "Exercice 1 (4 pts)\n1) Calculer.")
    # page 2: no header at all
    assert split_reply("ENTETE\nCONTENU\nExercice 3 (4 pts)") == ({}, "Exercice 3 (4 pts)")


def test_content_goes_straight_into_the_exam_builder():
    out = finalize(AI_REPLY)
    items = parse(out["content"])
    assert [i["kind"] for i in items][:4] == ["section", "question", "question", "section"]
    assert total_points(items) == 10.0


def test_printed_header_is_moved_to_fields_and_unknown_lines_are_kept():
    out = finalize(PRINTED)
    f = out["fields"]
    assert f["school"] == "LYCÉE DE NKOLBISSON"
    assert f["subject"] == "PHYSIQUE"
    assert f["class"] == "Première D" and f["duration"] == "2 h" and f["coef"] == "2"
    assert f["year"] == "2025-2026"
    assert f["ministry"].startswith("MINISTÈRE")
    lines = out["content"].split("\n")
    assert lines[0] == "Les candidats traiteront les deux exercices."  # not understood -> kept
    assert lines[1] == "EXERCICE 1 (8 pts)"
    assert "RÉPUBLIQUE" not in out["content"] and "****" not in out["content"] and "SECONDAIRES" not in out["content"]


def test_lines_after_the_first_exercise_are_never_touched():
    text = "Exercice 1 (4 pts)\nClasse : on note ici que la classe est calme.\nLycée de la Paix"
    out = finalize(text)
    assert out["content"] == text and out["fields"] == {}


def test_ai_fields_win_over_what_the_text_rules_find():
    out = finalize("ENTETE\nclasse: Terminale C\nCONTENU\nClasse : Seconde A\nExercice 1 (4 pts)")
    assert out["fields"]["class"] == "Terminale C"


# --- Route -------------------------------------------------------------------

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


def white_page() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (600, 800), "white").save(buf, "JPEG")
    return base64.b64encode(buf.getvalue()).decode()


def test_scan_route_returns_exam_fields_for_handwriting(client, monkeypatch):
    seen = {}

    def fake(jpeg, key, prompt):
        seen["prompt"] = prompt
        return AI_REPLY

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setitem(scan.PROVIDERS, "gemini", ("GEMINI_API_KEY", fake))
    r = client.post("/scans", json={"data": white_page(), "handwriting": True, "consent": True, "kind": "epreuve"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert seen["prompt"] == EXAM_PROMPT
    assert body["exam"]["school"] == "Lycée Bilingue de Biyem-Assi"
    assert body["text"].startswith("Exercice 1 (5 pts)")  # header block is not repeated in the text


def test_scan_route_without_kind_is_unchanged(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setitem(scan.PROVIDERS, "gemini", ("GEMINI_API_KEY", lambda j, k, p: "Un texte"))
    r = client.post("/scans", json={"data": white_page(), "handwriting": True, "consent": True})
    assert r.status_code == 200
    assert r.json()["text"] == "Un texte" and "exam" not in r.json()


# --- Provider fallback ---------------------------------------------------------

def _clear_keys(monkeypatch):
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "OCR_PROVIDER", "OCR_PROVIDERS"):
        monkeypatch.delenv(name, raising=False)


def test_fallback_goes_to_the_next_provider(monkeypatch):
    _clear_keys(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "a")
    monkeypatch.setenv("GROQ_API_KEY", "b")

    def boom(jpeg, key, prompt):
        raise scan.ScanError("quota")

    monkeypatch.setitem(scan.PROVIDERS, "gemini", ("GEMINI_API_KEY", boom))
    monkeypatch.setitem(scan.PROVIDERS, "groq", ("GROQ_API_KEY", lambda j, k, p: "texte groq"))
    assert scan.read_text_with_engine(b"x") == ("texte groq", "groq")


def test_fallback_skips_providers_without_a_key_and_reports_the_last_error(monkeypatch):
    _clear_keys(monkeypatch)
    with pytest.raises(scan.OcrUnavailable):
        scan.read_text_with_engine(b"x")

    def boom(jpeg, key, prompt):
        raise scan.ScanError("Trop de pages lues aujourd'hui, réessaie dans un moment")

    monkeypatch.setenv("GROQ_API_KEY", "b")
    monkeypatch.setitem(scan.PROVIDERS, "groq", ("GROQ_API_KEY", boom))
    with pytest.raises(scan.ScanError, match="Trop de pages"):
        scan.read_text_with_engine(b"x")


# --- "Épreuve" chosen in the editor: an imported document becomes an exam ---------------------

def test_word_numbering_is_put_back():
    raws = [
        Raw(text="Exercice 1 (5 pts)"),
        Raw(text="Résoudre x² = 4", list_kind="number"),
        Raw(text="Calculer", list_kind="number"),
        Raw(text="Justifier", list_kind="number", indent=1),
        Raw(text="Conclure", list_kind="number", indent=1),
        Raw(text="Exercice 2 (5 pts)"),
        Raw(text="Tracer", list_kind="number"),
        Raw(rows=[["x", "1", "2"], ["y", "3", "4"]]),
    ]
    assert raws_to_text(raws) == (
        "Exercice 1 (5 pts)\n1) Résoudre x² = 4\n2) Calculer\na) Justifier\nb) Conclure\n"
        "Exercice 2 (5 pts)\n1) Tracer\nx\t1\t2\ny\t3\t4"
    )


def test_blocks_give_the_same_kind_of_text():
    blocks = [
        {"type": "heading", "text": "Exercice 1 (5 pts)"},
        {"type": "list", "ordered": True, "level": 0, "text": "Calculer."},
        {"type": "list", "ordered": True, "level": 0, "text": "Justifier."},
        {"type": "figure", "image": "a1"},
        {"type": "list", "ordered": False, "text": "un point"},
    ]
    assert blocks_to_text(blocks) == "Exercice 1 (5 pts)\n1) Calculer.\n2) Justifier.\n- un point"


def test_document_can_become_an_exam(client):
    doc = client.post("/documents", json={"text": PRINTED + "2) Calculer la résistance. (3 pts)\n"}).json()
    r = client.post(f"/documents/{doc['id']}/exam")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["fields"]["school"] == "LYCÉE DE NKOLBISSON" and body["fields"]["class"] == "Première D"
    assert body["content"].split("\n")[-1] == "2) Calculer la résistance. (3 pts)"  # numbering kept as typed
    assert client.post("/documents/inconnu/exam").status_code == 404
