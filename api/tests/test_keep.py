"""A Word file that already has its cover page / sommaire / numbers is kept; only what is missing is added."""
import base64
import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app import config, db, fapshi
from app.doc import keep


def cover_docx(tmp_path, numbered=False, toc=False):
    doc = Document()
    for line in ("RÉPUBLIQUE DU CAMEROUN", "UNIVERSITÉ D'EBOLOWA", "RAPPORT DE STAGE", "Par : Jean Dupont", "Matricule : 22X0070",
                 "Année académique : 2026-2027"):
        doc.add_paragraph(line)
    doc.add_page_break()
    if toc:
        doc.add_paragraph("Sommaire")
    doc.add_heading("Introduction", 1)
    doc.add_paragraph("Texte de l'introduction. " * 20)
    doc.add_heading("Conclusion", 1)
    doc.add_paragraph("Texte de la conclusion.")
    if numbered:
        keep_field = doc.sections[0].footer.paragraphs[0]
        from app.doc.render import _field
        _field(keep_field, "PAGE")
    path = tmp_path / "in.docx"
    doc.save(path)
    return path


def test_inspect_sees_the_cover_and_what_is_missing(tmp_path):
    info = keep.inspect(cover_docx(tmp_path))
    assert info["cover"] is True and info["page_numbers"] is False and info["toc"] is False and info["headings"] == 2


def test_inspect_sees_existing_numbers(tmp_path):
    assert keep.inspect(cover_docx(tmp_path, numbered=True))["page_numbers"] is True


def test_touch_adds_numbers_and_leaves_the_cover_alone(tmp_path):
    src = cover_docx(tmp_path)
    out = tmp_path / "out.docx"
    assert keep.touch(src, out, page_numbers=True) == ["numéros de page"]
    after = Document(str(out))
    assert [p.text for p in after.paragraphs[:6]] == [p.text for p in Document(str(src)).paragraphs[:6]]
    section = after.sections[0]
    assert section.different_first_page_header_footer is True  # the cover page stays blank
    assert keep.inspect(out)["page_numbers"] is True
    assert keep.touch(out, tmp_path / "again.docx", page_numbers=True) == []  # nothing to add the second time


def test_existing_footer_text_is_never_overwritten(tmp_path):
    doc = Document()
    doc.add_paragraph("Texte")
    doc.sections[0].footer.paragraphs[0].text = "Confidentiel"
    src = tmp_path / "f.docx"
    doc.save(src)
    keep.touch(src, tmp_path / "o.docx", page_numbers=True)
    assert Document(str(tmp_path / "o.docx")).sections[0].footer.paragraphs[0].text == "Confidentiel"


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


def test_import_keeps_a_file_that_already_has_a_cover_and_the_render_keeps_it(client, tmp_path):
    data = base64.b64encode(cover_docx(tmp_path).read_bytes()).decode()
    doc = client.post("/documents", json={"filename": "r.docx", "data": data}).json()
    assert doc["mode"] == "keep" and doc["keep"] == {"page_numbers": True, "toc": False}
    assert doc["meta"]["existing"]["cover"] is True
    rendered = client.post(f"/documents/{doc['id']}/render").json()
    assert rendered["render"]["pages"] >= 2
    word = client.get(f"/documents/{doc['id']}")  # still readable
    assert word.status_code == 200
    # the user can switch to the full Paginya layout, and back
    assert client.put(f"/documents/{doc['id']}", json={"mode": "rebuild"}).json()["mode"] == "rebuild"
    assert client.put(f"/documents/{doc['id']}", json={"mode": "keep", "keep": {"page_numbers": False, "toc": True}}).json()["keep"] == {"page_numbers": False, "toc": True}


def test_plain_file_without_cover_still_gets_the_normal_layout(client, tmp_path):
    doc = Document()
    doc.add_heading("Titre", 1)
    doc.add_paragraph("Un texte simple.")
    path = tmp_path / "p.docx"
    doc.save(path)
    data = base64.b64encode(path.read_bytes()).decode()
    made = client.post("/documents", json={"filename": "p.docx", "data": data}).json()
    assert made["mode"] == "rebuild"
