import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import config, db, fapshi
from app.svg_safe import UnsafeSvg, sanitize_svg

SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="595.28" height="841.89" viewBox="0 0 595.28 841.89">'
    '<rect width="595.28" height="841.89" fill="#fff"/>'
    '<text x="60" y="400" font-family="Poppins" font-weight="800" font-size="30">RAPPORT DE STAGE</text>'
    "</svg>"
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "t.sqlite3")
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.sqlite3")
    monkeypatch.setattr(config, "FAPSHI_MODE", "mock")
    monkeypatch.setattr(fapshi, "MOCK_DELAY_S", 0)
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_sanitizer_strips_scripts_handlers_and_external_links():
    dirty = (
        '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>'
        '<rect width="10" height="10" onclick="x()"/>'
        '<image href="http://evil/x.png"/><image href="data:image/png;base64,AAAA"/></svg>'
    )
    clean = sanitize_svg(dirty)
    assert "script" not in clean and "onclick" not in clean and "evil" not in clean
    assert "data:image/png;base64,AAAA" in clean


def test_sanitizer_rejects_entities():
    with pytest.raises(UnsafeSvg):
        sanitize_svg('<!DOCTYPE svg [<!ENTITY x "y">]><svg xmlns="http://www.w3.org/2000/svg"/>')


def test_price_is_set_by_server(client):
    r = client.post("/orders", json={"product": "page_de_garde", "svg": SVG, "amount": 1})
    assert r.status_code == 200
    assert r.json()["amount"] == 300


def test_download_requires_payment(client):
    order = client.post("/orders", json={"svg": SVG}).json()
    assert client.get(f"/orders/{order['id']}/file.pdf").status_code == 402


def test_successful_mock_payment_unlocks_all_formats(client):
    order = client.post("/orders", json={"svg": SVG}).json()
    r = client.post(f"/orders/{order['id']}/pay", json={"phone": "670000000"})
    assert r.json()["status"] == "PENDING"
    assert client.get(f"/orders/{order['id']}").json()["status"] == "PAID"

    pdf = client.get(f"/orders/{order['id']}/file.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    png = client.get(f"/orders/{order['id']}/file.png")
    assert png.content.startswith(b"\x89PNG")
    docx = client.get(f"/orders/{order['id']}/file.docx")
    assert "word/document.xml" in zipfile.ZipFile(io.BytesIO(docx.content)).namelist()


def test_failed_payment_can_be_retried(client):
    order = client.post("/orders", json={"svg": SVG}).json()
    client.post(f"/orders/{order['id']}/pay", json={"phone": "670000001"})
    assert client.get(f"/orders/{order['id']}").json()["status"] == "FAILED"
    assert client.post(f"/orders/{order['id']}/retry").json()["status"] == "DRAFT"


def test_invalid_phone_is_rejected(client):
    order = client.post("/orders", json={"svg": SVG}).json()
    r = client.post(f"/orders/{order['id']}/pay", json={"phone": "12345"})
    assert r.status_code == 400


def test_settle_is_idempotent(client):
    order = client.post("/orders", json={"svg": SVG}).json()
    client.post(f"/orders/{order['id']}/pay", json={"phone": "670000000"})
    assert db.settle(order["id"], "PAID") is True
    assert db.settle(order["id"], "PAID") is False


def test_webhook_requires_secret(client, monkeypatch):
    monkeypatch.setattr(config, "FAPSHI_WEBHOOK_SECRET", "s3cret")
    assert client.post("/webhooks/fapshi", json={}).status_code == 401
    r = client.post("/webhooks/fapshi", json={"externalId": "none"}, headers={"x-wh-secret": "s3cret"})
    assert r.status_code == 200


def test_edit_after_payment_within_7_days(client, monkeypatch):
    order = client.post("/orders", json={"svg": SVG}).json()
    client.post(f"/orders/{order['id']}/pay", json={"phone": "670000000"})
    client.get(f"/orders/{order['id']}")
    assert client.put(f"/orders/{order['id']}", json={"svg": SVG}).status_code == 200
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 8 * 86400)
    assert client.put(f"/orders/{order['id']}", json={"svg": SVG}).status_code == 403
