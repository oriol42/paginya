import json

import pytest

from app.doc import spelling
from tests.test_documents import client  # noqa: F401  (fixture)


def test_only_real_small_fixes_are_kept():
    ok = spelling.acceptable
    assert ok("Les étudiant ont présenter leur rapport.", "Les étudiants ont présenté leur rapport.")
    assert ok("The student have submit his report.", "The student has submitted his report.")
    assert not ok("Les étudiant ont présenter leur rapport.", "Les élèves ont remis leur travail.")  # rephrased
    assert not ok("Le budget est de 1500 FCFA.", "Le budget est de 1 500 FCFA.")  # a number changed
    assert not ok("Soit ⟦eq12⟧ la solution.", "Soit la solution.")  # an equation lost
    assert not ok("Bonjour.", "Bonjour.")


def test_proposals_come_back_per_block_and_bad_ones_are_dropped(monkeypatch):
    blocks = [{"type": "heading", "level": 1, "text": "INTRODUCTION GENERALE"},
              {"type": "paragraph", "text": "Les étudiant ont présenter leur rapport hier."},
              {"type": "figure", "image": "x.png"},
              {"type": "paragraph", "text": "Ce paragraphe est juste."}]
    def fake(payload):
        sent = [json.loads(line) for line in payload.splitlines()]
        assert [s["i"] for s in sent] == [0, 1, 3]  # no figure
        return json.dumps({"fixes": [{"i": 1, "t": "Les étudiants ont présenté leur rapport hier."},
                                     {"i": 3, "t": "Un texte complètement différent ici."}]}), "gemini"
    monkeypatch.setattr(spelling, "ask", fake)
    fixes = spelling.propose(blocks)
    assert fixes == [{"block": 1, "before": blocks[1]["text"], "after": "Les étudiants ont présenté leur rapport hier."}]


def test_the_route_asks_for_consent_and_reports_an_outage(client, monkeypatch):  # noqa: F811
    v = client.post("/documents", json={"text": "INTRODUCTION\n\nLes étudiant ont présenter leur rapport devant le jury hier matin."}).json()
    assert client.post(f"/documents/{v['id']}/spelling", json={}).status_code == 400
    monkeypatch.setattr(spelling, "ask", lambda payload: (_ for _ in ()).throw(spelling.SpellError("pas dispo")))
    r = client.post(f"/documents/{v['id']}/spelling", json={"consent": True})
    assert r.status_code == 503 and r.json()["detail"] == "pas dispo"
    monkeypatch.setattr(spelling, "ask", lambda payload: (json.dumps({"fixes": [{"i": 1, "t": "Les étudiants ont présenté leur rapport devant le jury hier matin."}]}), "groq"))
    fixes = client.post(f"/documents/{v['id']}/spelling", json={"consent": True}).json()["fixes"]
    assert len(fixes) == 1 and fixes[0]["after"].startswith("Les étudiants ont présenté")
