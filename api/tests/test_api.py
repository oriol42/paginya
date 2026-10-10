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
    assert r.json()["amount"] == 350


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


def test_the_team_signs_in_with_google_and_unlocks_an_order_nobody_else_does(client, monkeypatch):
    from app import admin

    order = client.post("/orders", json={"svg": SVG, "form": {}}).json()
    assert client.get("/admin/config").json() == {"client_id": ""}  # nothing set: off
    assert client.post(f"/orders/{order['id']}/admin", json={"token": "x"}).status_code == 403
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "abc.apps.googleusercontent.com")
    monkeypatch.setattr(config, "ADMIN_EMAILS", {"chef@gmail.com"})
    monkeypatch.setattr(config, "ADMIN_SECRET", "s3cret")
    monkeypatch.setattr(admin, "google_email", lambda credential: credential)  # Google is not called in tests
    assert client.post("/admin/login", json={"credential": "intrus@gmail.com"}).status_code == 403
    token = client.post("/admin/login", json={"credential": "chef@gmail.com"}).json()["token"]
    assert admin.email_of(token) == "chef@gmail.com"
    assert admin.email_of(token, now=time.time() + 31 * 86400) is None  # the pass expires
    assert admin.email_of(admin.issue("chef@gmail.com")[:-4] + "AAAA") is None  # and cannot be forged
    assert client.post(f"/orders/{order['id']}/admin", json={"token": "faux"}).status_code == 403
    assert client.post(f"/orders/{order['id']}/admin", json={"token": token}).json()["status"] == "PAID"
    assert client.get(f"/orders/{order['id']}/file.pdf").status_code == 200
