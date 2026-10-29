"""Learning from paid documents (app/learn.py): what the customer corrected becomes an example; odd results are flagged."""
import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app import config, db, fapshi, learn

FIXTURE = Path(__file__).parent / "fixtures" / "rapport_brut.txt"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    for mod in (config, db):
        monkeypatch.setattr(mod, "DATA_DIR", tmp_path)
        monkeypatch.setattr(mod, "DB_PATH", tmp_path / "t.sqlite3")
    monkeypatch.setattr(config, "FAPSHI_MODE", "mock")
    monkeypatch.setattr(fapshi, "MOCK_DELAY_S", 0)
    monkeypatch.setattr(learn, "snapshot_later", learn.snapshot)  # synchronous in tests
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_correction_becomes_example(client, tmp_path):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    folder = tmp_path / "docs" / doc["id"]
    assert (folder / "learn.npz").exists() and (folder / "learn.json").exists()
    blocks = doc["blocks"]
    k = next(i for i, b in enumerate(blocks) if b["type"] == "heading" and b.get("level") == 2)
    blocks[k] = {**blocks[k], "type": "paragraph"}  # the customer says: this is no title
    blocks.insert(0, {"type": "paragraph", "text": "Une ligne ajoutée par le client."})  # every id moves
    assert client.put(f"/documents/{doc['id']}", json={"blocks": blocks}).status_code == 200

    assert learn.harvest() == []  # not paid: nothing learned
    client.post(f"/orders/{doc['id']}/pay", json={"phone": "670000000"})
    assert client.get(f"/orders/{doc['id']}").json()["status"] == "PAID"
    done = learn.harvest()
    assert done and done[0]["corrections"] == 1
    with np.load(learn.samples_dir() / f"{doc['id']}.npz") as z:
        assert (z["y"] == learn.PARA).sum() > 0 and ((z["rules"] == 2) & (z["y"] == learn.PARA)).sum() == 1
    assert learn.harvest() == []  # once only


def test_help_keeps_the_file_and_flags(client, tmp_path):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    assert client.post(f"/documents/{doc['id']}/help", json={"on": True}).json() == {"help": True}
    client.post(f"/orders/{doc['id']}/pay", json={"phone": "670000000"})
    client.get(f"/orders/{doc['id']}")
    learn.harvest()
    assert list((learn.files_dir() / doc["id"]).glob("source.*"))
    row = next(r for r in db.flagged_docs() if r["id"] == doc["id"])
    assert row["has_file"] == 1 and row["corrections"] == 0
    client.post(f"/documents/{doc['id']}/help", json={"on": False})
    assert not (learn.files_dir() / doc["id"]).exists()


def test_odd_result_is_flagged(client):
    text = "\n\n".join(f"S = A·B + {i}" for i in range(3)) + "\n\n" + ("Une phrase de texte ordinaire. " * 200)
    doc = client.post("/documents", json={"text": text}).json()
    assert any(r["id"] == doc["id"] for r in db.flagged_docs()) or not [b for b in doc["blocks"] if b["type"] == "heading"]


def test_retrain_waits_for_enough_documents(client):
    res = learn.retrain()
    assert res["accepted"] is False and "il en faut" in res["why"]
    learn._record(res)
    assert json.loads(learn.history_path().read_text())[-1]["accepted"] is False


def test_nightly_backs_up_the_database(client, tmp_path, monkeypatch):
    from app import storage

    monkeypatch.setattr(storage, "REMOTE", False)
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "objects"))
    key = db.backup()
    assert key and (tmp_path / "objects" / key).stat().st_size > 0
