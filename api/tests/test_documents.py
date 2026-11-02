import base64
import io
import shutil
import zipfile
from pathlib import Path

import pytest
from docx import Document
from docx.shared import Pt
from fastapi.testclient import TestClient
from PIL import Image

from app import config, db, fapshi
from app.doc.detect import detect
from app.doc.extract import from_docx, from_text

FIXTURE = Path(__file__).parent / "fixtures" / "rapport_brut.txt"


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


def headings(blocks):
    return [(b["text"], b["level"]) for b in blocks if b["type"] == "heading"]


def test_plain_text_structure():
    res = detect(from_text(FIXTURE.read_text()))
    h = dict(headings(res["blocks"]))
    assert h["PREMIÈRE PARTIE : PRÉSENTATION DE LA STRUCTURE D'ACCUEIL"] == 1
    assert h["CHAPITRE I : HISTORIQUE ET MISSIONS"] == 2
    assert h["I. Historique"] == 3
    assert h["1.1 Tri et classement des archives"] == 3  # same depth as "I." in another chapter
    types = [b["type"] for b in res["blocks"]]
    assert "SOMMAIRE" not in [b.get("text") for b in res["blocks"]]  # old TOC is dropped
    # Table caption moved above its table, table rebuilt from tab-separated lines
    i = types.index("table")
    assert res["blocks"][i - 1]["type"] == "caption" and res["blocks"][i - 1]["of"] == "table"
    assert res["blocks"][i]["rows"][0] == ["Poste", "Effectif", "Rôle"]
    lists = [b for b in res["blocks"] if b["type"] == "list"]
    assert sum(b["ordered"] for b in lists) == 3 and sum(not b["ordered"] for b in lists) == 6
    assert any(b.get("role") == "sigle" and b["term"] == "COBAC" for b in res["blocks"])
    assert any(b.get("role") == "dedicace" for b in res["blocks"])


def test_numbered_line_alone_is_a_heading_but_a_run_is_a_list():
    text = "1. Contexte de l'étude\nLe Cameroun compte dix régions et une grande diversité culturelle qui influence fortement les pratiques documentaires des institutions publiques et privées.\n\n1. Premier point\n2. Deuxième point\n"
    blocks = detect(from_text(text))["blocks"]
    assert blocks[0]["type"] == "heading"
    assert [b["type"] for b in blocks[2:]] == ["list", "list"]


def make_docx(path: Path) -> None:
    d = Document()
    d.add_heading("Introduction", level=1)
    d.add_paragraph("Texte de l'introduction assez long pour être un paragraphe normal du document.")
    d.add_heading("Méthodologie", level=1)
    p = d.add_paragraph()
    r = p.add_run("Collecte des données")
    r.bold = True
    d.add_paragraph("Premier élément", style="List Number")
    d.add_paragraph("Second élément", style="List Number")
    d.add_paragraph("Une puce", style="List Bullet")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Région", "Effectif"
    t.cell(1, 0).text, t.cell(1, 1).text = "Centre", "120"
    buf = io.BytesIO()
    Image.new("RGB", (400, 200), "#0E9F6E").save(buf, format="PNG")
    buf.seek(0)
    d.add_picture(buf)
    d.add_paragraph("Figure 1 : Carte de la région")
    for par in d.paragraphs:
        for run in par.runs:
            run.font.size = run.font.size or Pt(12)
    d.save(path)


def test_docx_extraction(tmp_path):
    src = tmp_path / "in.docx"
    make_docx(src)
    raws = from_docx(src, tmp_path / "img")
    blocks = detect(raws)["blocks"]
    kinds = [(b["type"], b.get("text", "")[:20]) for b in blocks]
    assert ("heading", "Introduction") in kinds
    assert ("heading", "Collecte des données") in kinds  # bold short line
    lists = [b for b in blocks if b["type"] == "list"]
    assert [b["ordered"] for b in lists] == [True, True, False]
    assert any(b["type"] == "table" for b in blocks)
    fig = next(b for b in blocks if b["type"] == "figure")
    assert (tmp_path / "img" / fig["image"]).is_file()
    # figure caption stays below the figure
    i = blocks.index(fig)
    assert blocks[i + 1]["type"] == "caption" and blocks[i + 1]["of"] == "figure"


def test_full_flow_text_to_paid_download(client):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    assert doc["meta"]["kind"] == "rapport_stage"
    r = client.post(f"/documents/{doc['id']}/render")
    assert r.status_code == 200, r.text
    info = r.json()
    assert info["render"]["pages"] >= 10
    assert info["product"] == "document_court" and info["amount"] == 550
    assert client.get(f"/documents/{doc['id']}/pages/1.webp").content[8:12] == b"WEBP"
    assert client.get(f"/orders/{doc['id']}/file.pdf").status_code == 402

    client.post(f"/orders/{doc['id']}/pay", json={"phone": "670000000"})
    assert client.get(f"/orders/{doc['id']}").json()["status"] == "PAID"
    pdf = client.get(f"/orders/{doc['id']}/file.pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    docx = client.get(f"/orders/{doc['id']}/file.docx")
    xml = zipfile.ZipFile(io.BytesIO(docx.content)).read("word/document.xml").decode()
    assert "Répartition du personnel" in xml and "[[TOC" not in xml  # markers replaced by real indexes


def test_edit_blocks_and_style(client):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    blocks = doc["blocks"]
    blocks[0]["hidden"] = True
    r = client.put(f"/documents/{doc['id']}", json={"blocks": blocks, "style": {"theme": "moderne", "color": "#1E3A8A"}})
    assert r.status_code == 200
    assert r.json()["style"]["theme"] == "moderne" and r.json()["blocks"][0]["hidden"] is True
    bad = client.put(f"/documents/{doc['id']}", json={"style": {"theme": "hack"}})
    assert bad.json()["style"]["theme"] == "moderne"


def test_upload_docx(client, tmp_path):
    src = tmp_path / "in.docx"
    make_docx(src)
    r = client.post("/documents", json={"filename": "rapport.docx", "data": base64.b64encode(src.read_bytes()).decode()})
    assert r.status_code == 200, r.text
    assert any(b["type"] == "figure" for b in r.json()["blocks"])
    assert client.post(f"/documents/{r.json()['id']}/render").status_code == 200


def test_old_word_formats_are_converted(client, tmp_path):
    """.doc / .odt / .rtf: LibreOffice saves them as .docx on arrival, then they are Word files like any other."""
    rtf = (r"{\rtf1\ansi\deff0 {\fonttbl{\f0 Times New Roman;}}\f0\fs24 "
           r"{\b INTRODUCTION}\par Ce rapport pr\'e9sente le stage effectu\'e9 \'e0 Douala pendant trois mois.\par "
           r"{\b I- Pr\'e9sentation de l'entreprise}\par L'entreprise a \'e9t\'e9 cr\'e9\'e9e en 2004 et compte cent employ\'e9s.\par }").encode()
    r = client.post("/documents", json={"filename": "rapport.rtf", "data": base64.b64encode(rtf).decode()})
    assert r.status_code == 200, r.text
    doc = r.json()
    assert [b["text"] for b in doc["blocks"] if b["type"] == "heading"][:2] == ["INTRODUCTION", "I- Présentation de l'entreprise"]
    assert doc["analysis"]["docx"] is True


def photo_of_page(tmp_path) -> bytes:
    """A white page with text, photographed at an angle on a dark table."""
    import cv2
    import numpy as np
    from PIL import ImageDraw
    from PIL import ImageFont
    page = Image.new("RGB", (600, 850), "white")
    d = ImageDraw.Draw(page)
    font = ImageFont.truetype(str(Path(__file__).parent.parent / "fonts" / "tinos-400.ttf"), 26)
    d.text((50, 50), "CHAPITRE I : PRÉSENTATION", fill="black", font=font)
    for i in range(10):
        d.text((50, 120 + i * 60), f"Ligne de texte numéro {i + 1} du rapport", fill="black", font=font)
    src = np.array(page)[:, :, ::-1]
    table = np.full((1200, 1000, 3), (40, 50, 60), np.uint8)
    corners = np.float32([[0, 0], [599, 0], [599, 849], [0, 849]])
    target = np.float32([[180, 150], [800, 210], [760, 1080], [130, 1010]])
    warped = cv2.warpPerspective(src, cv2.getPerspectiveTransform(corners, target), (1000, 1200),
                                 dst=table, borderMode=cv2.BORDER_TRANSPARENT)
    ok, jpg = cv2.imencode(".jpg", warped)
    return jpg.tobytes()


def test_straighten_finds_the_sheet(tmp_path):
    from app.doc.scan import straighten
    jpeg, found = straighten(photo_of_page(tmp_path))
    assert found
    img = Image.open(io.BytesIO(jpeg))
    assert 0.6 < img.width / img.height < 0.8  # upright A4-ish page, table cropped away


def test_handwriting_requires_consent(client, monkeypatch, tmp_path):
    monkeypatch.setenv("OCR_PROVIDER", "mock")
    data = base64.b64encode(photo_of_page(tmp_path)).decode()
    assert client.post("/scans", json={"data": data, "handwriting": True}).status_code == 400
    r = client.post("/scans", json={"data": data, "handwriting": True, "consent": True})
    assert r.status_code == 200 and r.json()["straightened"] is True
    assert client.get(f"/scans/{r.json()['id']}.jpg").status_code == 200


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract not installed")
def test_printed_page_read_locally_with_tesseract(client, tmp_path):
    data = base64.b64encode(photo_of_page(tmp_path)).decode()
    r = client.post("/scans", json={"data": data})  # no consent needed: stays on our server
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["engine"] == "tesseract"
    assert "CHAPITRE I" in body["text"] and "numéro 7" in body["text"] and body["confidence"] > 80


def test_ocr_rejoins_wrapped_lines():
    from app.doc.scan import _tsv_to_text
    rows = ["level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext"]
    def w(line, left, width, text, par=1):
        rows.append(f"5\t1\t1\t{par}\t{line}\t1\t{left}\t{line * 30}\t{width}\t20\t95\t{text}")
    w(1, 100, 300, "INTRODUCTION")  # short title line
    w(2, 100, 890, "Comme le disait le philosophe, la théorie sans")  # reaches the right margin
    w(3, 100, 400, "pratique est inutile.")
    text, conf = _tsv_to_text("\n".join(rows))
    assert text == "INTRODUCTION\n\nComme le disait le philosophe, la théorie sans pratique est inutile."


def test_before_view_and_delete(client):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    assert client.post(f"/documents/{doc['id']}/before").json()["pages"] >= 1
    assert client.get(f"/documents/{doc['id']}/before/1.png").status_code == 200
    assert doc["meta"]["changes"]
    assert client.delete(f"/documents/{doc['id']}").json()["deleted"] is True
    assert client.get(f"/documents/{doc['id']}").status_code == 404


def test_new_themes_render(client):
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    for theme in ("universitaire", "elegant", "corporate"):
        client.put(f"/documents/{doc['id']}", json={"style": {"theme": theme}})
        assert client.post(f"/documents/{doc['id']}/render").status_code == 200


def test_cleanup_after_7_days_and_purge_after_a_year(client):
    import time as _t
    from app.doc_routes import cleanup, doc_dir
    doc = client.post("/documents", json={"text": FIXTURE.read_text()}).json()
    assert doc_dir(doc["id"]).exists()
    cleanup(now=_t.time() + 8 * 86400)
    assert not doc_dir(doc["id"]).exists()
    assert client.get(f"/documents/{doc['id']}").status_code == 404
    cleanup(now=_t.time() + 400 * 86400)
    assert db.get_order(doc["id"]) is None


def test_survives_a_server_restart(client, tmp_path):
    """Hugging Face wipes the disk at every restart: the original, its images and the renders must come back."""
    src = tmp_path / "in.docx"
    make_docx(src)
    doc = client.post("/documents", json={"filename": "rapport.docx", "data": base64.b64encode(src.read_bytes()).decode()}).json()
    client.post(f"/documents/{doc['id']}/render")
    client.post(f"/orders/{doc['id']}/pay", json={"phone": "670000000"})
    assert client.get(f"/orders/{doc['id']}").json()["status"] == "PAID"

    shutil.rmtree(tmp_path / "docs")  # the restart: only the database and durable storage are left
    assert client.get(f"/documents/{doc['id']}/pages/1.webp").content[8:12] == b"WEBP"
    fig = next(b for b in doc["blocks"] if b["type"] == "figure")
    assert client.get(f"/documents/{doc['id']}/images/{fig['image']}").status_code == 200

    shutil.rmtree(tmp_path / "docs")
    assert client.get(f"/orders/{doc['id']}/file.pdf").content.startswith(b"%PDF")
    assert client.post(f"/documents/{doc['id']}/before").json()["pages"] >= 1

    client.delete(f"/documents/{doc['id']}")
    assert not [p for p in (tmp_path / "objects").rglob("*") if p.is_file()]  # right to erasure: durable copies deleted too


def test_form_survives_a_server_restart(client, tmp_path):
    from tests.test_forms import LETTER  # noqa: PLC0415

    f = client.post("/forms", json={"kind": "lettre", "data": LETTER}).json()
    shutil.rmtree(tmp_path / "forms")
    assert client.get(f"/forms/{f['id']}/pages/1.webp").content[8:12] == b"WEBP"


def test_a_conversion_changes_the_format_and_nothing_else(client, tmp_path):
    import base64
    from docx import Document

    d = Document()
    d.add_paragraph("Mon titre")
    d.add_paragraph("Un paragraphe de texte. " * 10)
    path = tmp_path / "c.docx"
    d.save(path)
    data = base64.b64encode(path.read_bytes()).decode()
    view = client.post("/documents", json={"filename": "c.docx", "data": data, "convert": True}).json()
    assert view["convert"] == "pdf" and view["confirmed"] is True and view["mode"] == "keep"
    assert view["plan"] == {"cover": "keep", "toc": "keep", "numbers": "keep"}
    assert client.post("/documents", json={"filename": "c.txt", "data": data, "convert": True}).status_code == 400


def test_pdf_becomes_an_editable_word_with_its_sommaire(client, tmp_path):
    """PDF -> Word: the text, titles and the author's own sommaire come back in a Word file; nothing is added."""
    import base64
    import subprocess
    from docx import Document

    long = "Cette structure occupe une place importante dans le tissu économique de la région du Centre. " * 4
    d = Document()
    d.add_paragraph("SOMMAIRE")
    d.add_paragraph("INTRODUCTION ......................................... 1")
    d.add_paragraph("CHAPITRE I : PRÉSENTATION ............................. 2")
    d.add_page_break()
    for t in ("INTRODUCTION", "CHAPITRE I : PRÉSENTATION"):
        d.add_paragraph().add_run(t).bold = True
        d.add_paragraph(long)
    d.save(tmp_path / "p.docx")
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(tmp_path / "p.docx")], capture_output=True, timeout=120)
    data = base64.b64encode((tmp_path / "p.pdf").read_bytes()).decode()
    view = client.post("/documents", json={"filename": "p.pdf", "data": data, "convert": True}).json()
    assert view["convert"] == "docx" and view["confirmed"] is True
    texts = [b.get("text", "") for b in view["blocks"]]
    assert any(t.startswith("CHAPITRE I : PRÉSENTATION") and "2" in t for t in texts)  # the old sommaire line is kept
    assert any(b["type"] == "heading" and b["text"].startswith("CHAPITRE I") for b in view["blocks"])


def test_numbered_titles_keep_one_level_per_numbering():
    """"I) / 1) / 2)": the items under a roman title all sit one level below it (the model must not move them).
    Without chapters, "I)" is a sibling of the Introduction (level 1), as in an exposé."""
    long = "Cette structure occupe une place importante dans le tissu économique de la région du Centre. " * 3
    text = "\n\n".join(["Introduction", long, "I) Les causes lointaines", "1) Les rivalités coloniales", long, "2) La course aux armements", long,
                         "II) Les causes immédiates", "1) L'attentat de Sarajevo", long, "2) L'engrenage des alliances", long, "Conclusion", long])
    h = dict(headings(detect(from_text(text))["blocks"]))
    assert h["I) Les causes lointaines"] == h["II) Les causes immédiates"] == h["Introduction"] == 1
    assert {h[k] for k in h if k[0].isdigit()} == {2}


def test_body_is_never_hidden_as_a_cover_page(tmp_path):
    """A cover followed by titles the engine does not know by name ("A/ Objectif du TP") used to be read as one
    long cover page: every short line of the document was hidden."""
    doc = Document()
    for line in ("RÉPUBLIQUE DU CAMEROUN", "INSTITUT UNIVERSITAIRE DE TECHNOLOGIE", "COMPTE RENDU DE TP", "Rédigé et présenté par :",
                 "MBIDA Kevin", "Sous la supervision de :", "M. TAKAM", "Année académique 2025-2026"):
        doc.add_paragraph(line)
    for title in ("A/ Objectif du TP", "B/ Matériel utilisé", "C/ Manipulations"):
        doc.add_paragraph(title).runs[0].bold = True
        doc.add_paragraph("Nous avons configuré le réseau local de la salle avec trois commutateurs et un routeur.")
    path = tmp_path / "tp.docx"
    doc.save(path)
    blocks = detect(from_docx(path, tmp_path / "img"))["blocks"]
    shown = [b["text"] for b in blocks if not b.get("hidden") and b.get("text")]
    assert [t for t in shown if t[1:2] == "/"] == ["A/ Objectif du TP", "B/ Matériel utilisé", "C/ Manipulations"]
    assert sum("Nous avons configuré" in t for t in shown) == 3
    assert all(b.get("hidden") for b in blocks if b.get("text") in ("MBIDA Kevin", "COMPTE RENDU DE TP"))


def test_announced_chapters_are_a_list_and_typed_lines_are_cleaned():
    long = "Le service dispose de cinq ordinateurs, de deux imprimantes et d'une connexion internet instable. " * 3
    text = "\n\n".join(["INTRODUCTION", "Ce rapport s'articule autour de trois chapitres :", "Chapitre 1 : Présentation", "Chapitre 2 : Déroulement",
                         "Chapitre 3 : Bilan", "__________________________", "CHAPITRE 1 : PRESENTATION", long, "Plan du chapitre……………………",
                         "CHAPITRE 2 : DEROULEMENT", long, "CHAPITRE 3 : BILAN", long])
    blocks = detect(from_text(text))["blocks"]
    chapters = [b["text"] for b in blocks if b["type"] == "heading" and b["text"].upper().startswith("CHAPITRE")]
    assert chapters == ["CHAPITRE 1 : PRÉSENTATION", "CHAPITRE 2 : DÉROULEMENT", "CHAPITRE 3 : BILAN"]  # capitals, accents restored
    assert sum(b["type"] == "list" for b in blocks) == 3
    assert not any("____" in (b.get("text") or "") or "……" in (b.get("text") or "") for b in blocks)


def test_shift_enter_lines_become_their_own_paragraphs(tmp_path):
    doc = Document()
    p = doc.add_paragraph()
    for k, line in enumerate(["- Absence de tableaux de bord", "", "2.2 Limites de l'existant", "Cette situation générait plusieurs problèmes pour",
                               "les équipes du terrain chaque fin de mois."]):
        run = p.add_run(line)
        if k < 4:
            run.add_break()
    path = tmp_path / "soft.docx"
    doc.save(path)
    texts = [r.text for r in from_docx(path, tmp_path / "img")]
    assert texts == ["- Absence de tableaux de bord", "2.2 Limites de l'existant", "Cette situation générait plusieurs problèmes pour les équipes du terrain chaque fin de mois."]


def test_control_characters_from_a_pdf_never_break_the_word_file(tmp_path):
    from app.doc.render import build_docx
    doc = {"blocks": [{"type": "heading", "level": 1, "text": "Chapitre\x01 un"}, {"type": "paragraph", "text": "Texte\x0b avec\x00 des codes\x1f."}], "meta": {}}
    data = build_docx(doc, tmp_path)
    assert data[:2] == b"PK"


def test_junk_rate_spots_a_bad_ocr_layer():
    from app.doc.extract import junk_rate
    assert junk_rate("Analysez ce sujet en faisant ressortir la thèse de l'auteur (2 pts) ; 1) Le domaine.") < 0.05
    assert junk_rate("~,,~ __ ~~ Comtnente~~ ut dtJ cOlTespond faisantres50rtir ~.~ .,-':;~--") > 0.5


def test_word_equations_survive_the_rebuild(tmp_path):
    from docx import Document
    from docx.oxml import parse_xml
    from app.doc.extract import from_docx
    from app.doc.render import build_docx
    import io, zipfile
    m = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
    d = Document()
    d.add_paragraph("On considère l'équation suivante :")
    p = d.add_paragraph(); p._p.append(parse_xml(f'<m:oMathPara {m}><m:oMath><m:r><m:t>ax²+bx+c=0</m:t></m:r></m:oMath></m:oMathPara>'))
    p = d.add_paragraph("Le discriminant vaut "); p._p.append(parse_xml(f'<m:oMath {m}><m:r><m:t>Δ=b²−4ac</m:t></m:r></m:oMath>')); p.add_run(" ici.")
    d.save(tmp_path / "maths.docx")
    raws = from_docx(tmp_path / "maths.docx", tmp_path / "images")
    texts = [r.text for r in raws]
    assert texts[1].startswith("⟦eq") and texts[2].startswith("Le discriminant vaut ⟦eq") and texts[2].endswith(" ici.")
    blocks = [{"type": "paragraph", "text": t} for t in texts] + [{"type": "heading", "level": 1, "text": "Titre " + texts[1]}]
    data = build_docx({"blocks": blocks, "meta": {}}, tmp_path / "images")
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()
    assert xml.count("<m:oMath") >= 2 and "Δ=b²−4ac" in xml and "⟦" not in xml  # real equations; the title gets plain text


def test_a_file_sent_as_it_is_is_imported_like_a_base64_one(client):
    from docx import Document
    import io
    d = Document()
    d.add_heading("INTRODUCTION", 1)
    d.add_paragraph("Le présent rapport décrit le stage effectué au sein de l'entreprise pendant trois mois. " * 5)
    buf = io.BytesIO(); d.save(buf)
    r = client.post("/documents/upload?filename=rapport.docx", content=buf.getvalue(), headers={"Content-Type": "application/octet-stream"})
    assert r.status_code == 200 and any(b["text"] == "INTRODUCTION" for b in r.json()["blocks"])
    assert client.post("/documents/upload?filename=vide.docx", content=b"").status_code == 400


def test_typed_plan_without_page_numbers_is_dropped():
    """A plan typed at the start ("I. Introduction", "II. …", "Conclusion") is the old sommaire, not a run of titles."""
    long = "L'imagerie médicale regroupe les techniques qui permettent d'obtenir des images de l'intérieur du corps humain. " * 3
    text = "\n\n".join(["PLAN", "Introduction", "I. Les différentes lois en imagerie médicale", "II. L'organisation en imagerie médicale",
                         "Conclusion", "INTRODUCTION", long, "I. LES DIFFÉRENTES LOIS EN IMAGERIE MÉDICALE", long,
                         "II. L'ORGANISATION EN IMAGERIE MÉDICALE", long, "CONCLUSION", long])
    heads = headings(detect(from_text(text))["blocks"])
    assert [t.upper()[:12] for t, _ in heads] == ["INTRODUCTION", "I. LES DIFFÉ", "II. L'ORGANI", "CONCLUSION"]
    assert {lv for _, lv in heads} == {1}


ITEMS = [{"head": "Stock", "text": "Suivi quotidien", "icon": "layers"}, {"head": "Livraisons", "text": "Tournées", "icon": "truck"}, {"head": "Clients", "text": "Accueil", "icon": "pas-une-icone"}]
DECK_ANSWER = {"notes": "Bonjour à tous.", "thanks": "Merci de votre attention", "slides": [
    {"type": "points", "title": "Le contexte", "points": ["Un stage à Douala", "Trois mois en logistique"], "notes": "Je commence par le contexte."},
    {"type": "liste", "title": "Les missions", "items": ITEMS, "notes": ""},
    {"type": "chiffres", "title": "Inventé", "stats": [{"value": "87 %", "label": "pas dans le document"}, {"value": "1200", "label": "non plus"}]},
    {"type": "chiffres", "title": "Vrai", "stats": [{"value": "3", "label": "mois", "icon": "clock"}, {"value": "2026", "label": "année"}]},
    {"type": "graphique", "title": "Faux", "chart": "donut", "series": [{"label": "A", "value": 77}, {"label": "B", "value": 88}]},
    {"type": "etapes", "title": "La démarche", "items": ITEMS},
    {"type": "comparaison", "title": "Avant et après", "left": {"title": "Avant", "points": ["Papier"]}, "right": {"title": "Après", "points": ["Tableur"]}},
    {"type": "figure", "title": "Image inconnue", "figure": "F9", "points": []},
    {"type": "inconnu", "title": "Conclusion", "points": ["Un stage enrichissant", "Fait en 3 mois", "Soit 999 clients"]},
]}


def stage_docx(path: Path) -> None:
    d = Document()
    d.add_heading("Introduction", 1)
    d.add_paragraph("Le stage s'est déroulé à Douala pendant 3 mois en 2026 dans une entreprise de logistique, au service des stocks et des livraisons. " * 12)
    d.add_heading("Conclusion", 1)
    d.add_paragraph("Ce stage a été très enrichissant pour la suite de ma formation professionnelle dans la gestion des entreprises. " * 12)
    d.save(path)


def test_the_ai_never_gets_to_invent_a_number(monkeypatch):
    """Whatever it answers: unknown types become points, unknown pictures go, a number not in the document goes."""
    import json
    from app.doc import deck
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(DECK_ANSWER), "gemini"))
    document = {"blocks": [{"type": "paragraph", "text": "Stage de 3 mois à Douala en 2026."}]}
    made = deck.write(document, 9, None)
    slides = made["slides"]
    assert len(made["parts"]) >= 2 and all(s["part"] in made["parts"] for s in slides)  # the plan and the progress bar
    assert [s["title"] for s in slides] == ["Le contexte", "Les missions", "Vrai", "La démarche", "Avant et après", "Conclusion"]
    assert [x["head"] for x in slides[-1]["items"]] == ["Un stage enrichissant", "Fait en 3 mois"]
    assert slides[1]["items"][2]["icon"] == "circle-check"  # an icon we do not have
    types = [s["type"] for s in slides]
    assert all(a != b for a, b in zip(types, types[1:]))  # never the same page twice in a row
    assert deck.total(deck.write(document, 5, None)) == 5  # the number chosen by the user wins
    assert deck.max_slides(100) == 5 and deck.max_slides(600) == 24 and deck.max_slides(90_000) == 30


def test_the_plan_reads_well_however_the_ai_names_its_parts():
    from app.doc.deck import _label, _with_parts
    slides = [{"title": t, "part": p} for t, p in (("A", 1), ("B", "1"), ("C", 2), ("D", None))]
    assert _with_parts(slides, ["Contexte", "Résultats"]) == ["Contexte", "Résultats"]
    assert [s["part"] for s in slides] == ["Contexte", "Contexte", "Résultats", "Résultats"]
    assert _label("Architecture générale de la plateforme") == "Architecture générale"


def test_school_slides_open_and_close_like_the_report_and_a_plain_one_does_not(tmp_path):
    from pptx import Presentation
    from app.doc.slides import build_pptx, title_info
    Image.new("RGB", (80, 80), "blue").save(tmp_path / "logo.png")
    cover = {"title": "Mon rapport", "doc_label": "Rapport", "logos": ["logo.png"], "header_fr": ["RÉPUBLIQUE DU CAMEROUN", "*****"], "header_en": ["REPUBLIC OF CAMEROON"],
             "authors": [{"name": "KAMGA Paul", "info": "23I0080FS"}], "supervisors": [{"name": "Dr. NKE", "role": "ENCADREUR"}]}
    school = title_info({"blocks": [], "meta": {"cover": cover}}, tmp_path)
    assert school["logos"] == ["logo.png"] and school["header"] == ["RÉPUBLIQUE DU CAMEROUN"] and school["author_lines"] == ["KAMGA Paul (23I0080FS)"]
    plain = title_info({"deck_school": False, "blocks": [], "meta": {"cover": cover}}, tmp_path)
    assert plain["logos"] == [] and plain["header"] == [] and plain["supervisors"] == [] and plain["authors"] == ["KAMGA Paul"]
    deck = {"slides": [{"type": "liste", "title": "A", "items": [{"head": "x", "text": "y", "icon": "users"}]}], "parts": ["A"]}

    def pictures(info, index):
        path = tmp_path / "s.pptx"
        path.write_bytes(build_pptx(deck, info, "academique", tmp_path))
        return sum(1 for shape in Presentation(path).slides[index].shapes if shape.name.startswith("Picture"))

    assert pictures(school, 0) == 1 and pictures(school, -1) == 1  # the logos on the first page and the last
    assert pictures(plain, 0) == 0 and pictures(plain, -1) == 0


def test_title_mark_and_big_number_are_checked_too(monkeypatch):
    import json
    from app.doc import deck
    answer = {"slides": [
        {"type": "grand", "title": "Trois mois sur place", "highlight": "Trois mois", "value": "3 mois", "text": "À Douala", "takeaway": "Un vrai terrain"},
        {"type": "grand", "title": "Inventé", "value": "99 %", "text": "Faux"},
        {"type": "liste", "title": "Le stage", "highlight": "absent du titre", "items": ITEMS},
        {"type": "grille", "title": "Les tâches", "items": ITEMS}]}
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(answer), "gemini"))
    slides = deck.write({"blocks": [{"type": "paragraph", "text": "Stage de 3 mois à Douala."}]}, 7)["slides"]
    assert [s["title"] for s in slides] == ["Trois mois sur place", "Le stage", "Les tâches"]
    assert slides[0]["highlight"] == "Trois mois" and slides[0]["takeaway"] == "Un vrai terrain" and not slides[1]["highlight"]


def test_chart_values_must_be_in_the_document():
    from app.doc.deck import _number
    assert _number("40", {"40"}) == 40 and _number("40 %", {"40"}) == 40 and _number("12,5", {"12,5"}) == 12.5
    assert _number("41", {"40"}) is None and _number("beaucoup", {"40"}) is None


def test_big_tables_are_left_to_the_ai_to_tell():
    from app.doc.deck import _source
    small = [["Année", "Ventes"], ["2020", "10"]]
    huge = [["Terme", "Définition"], *[[f"Mot {i}", "une très longue définition " * 6] for i in range(4)]]
    _, _, tables = _source([{"type": "table", "rows": small}, {"type": "table", "rows": huge}])
    assert [t["rows"] for t in tables.values()] == [small]


@pytest.mark.parametrize("theme", ["academique", "sorbonne", "campus", "savane", "ocean", "medical", "royal", "corail", "soleil", "ardoise", "nuit", "neon", "contraste", "vitamine", "terre", "foret", "prairie", "horizon", "azur", "graphite", "ambre", "citron", "halo", "iris", "brume"])
def test_every_theme_draws_every_kind_of_slide(tmp_path, theme):
    from pptx import Presentation
    from app.doc.slides import build_pptx, title_info
    Image.new("RGB", (300, 200), "red").save(tmp_path / "a.webp", "WEBP")
    items = [{"head": "Stock", "text": "Suivi quotidien", "icon": "layers"}, {"head": "Vente", "text": "Par mois", "icon": "coins"}, {"head": "Clients", "text": "Accueil", "icon": "users"}]
    slides = [{"type": kind, "title": "Le contexte", "items": items, "notes": "Dire ceci.", "highlight": "contexte", "takeaway": "À retenir"} for kind in ("liste", "grille", "panneau", "schema", "chronologie", "etapes")]
    slides += [{"type": "grand", "title": "Un chiffre", "value": "3 semaines", "text": "Le délai", "icon": "clock"}]
    slides += [{"type": "grille", "title": "Six", "items": items * 2}, {"type": "grille", "title": "Quatre", "items": [*items, items[0]]}]
    slides += [{"type": "comparaison", "title": "Avant", "left": {"title": "A", "points": ["x"]}, "right": {"title": "B", "points": ["y"]}}]
    slides += [{"type": "graphique", "title": "Parts", "chart": chart, "series": [{"label": "A", "value": 40}, {"label": "B", "value": 60}], "key": "Message", "icon": "chart-pie"} for chart in ("donut", "barres")]
    slides += [{"type": "encadre", "title": "La question", "label": "Problématique", "text": "Comment gérer les stocks ?"}, {"type": "section", "title": "Partie 1"}, {"type": "chiffres", "title": "Vrai", "stats": [{"value": "3", "label": "mois", "icon": "clock"}, {"value": "2026", "label": "année", "icon": "calendar"}]},
               {"type": "figure", "title": "Schéma", "image": "a.webp", "caption": "Le schéma", "points": ["Un point"]},
               {"type": "tableau", "title": "Ventes", "rows": [["A", "B"], ["1", "2"]], "caption": ""}]
    Image.new("RGB", (80, 80), "blue").save(tmp_path / "logo.png")
    info = title_info({"deck_logo": "logo.png", "blocks": [], "meta": {"title": "Mon rapport", "cover": {"doc_label": "Mémoire", "header_fr": ["UNIVERSITÉ DE YAOUNDÉ I"],
                       "authors": [{"name": "KAMGA Paul"}], "supervisors": ["Pr NKE"], "year": "2025-2026"}}}, tmp_path)
    assert info["logos"] == ["logo.png"] and info["authors"] == ["KAMGA Paul"]
    saved = tmp_path / "s.pptx"
    saved.write_bytes(build_pptx({"slides": slides, "parts": ["Contexte"], "notes": "Bonjour", "thanks": "Merci"}, info, theme, tmp_path))
    prs = Presentation(saved)
    assert len(prs.slides) == len(slides) + 3 and prs.slide_width > prs.slide_height
    assert prs.slides[0].shapes.title.text == "Mon rapport" and prs.slides[0].notes_slide.notes_text_frame.text == "Bonjour"
    assert prs.slides[2].shapes.title.text.lower() == "le contexte" and prs.slides[2].notes_slide.notes_text_frame.text == "Dire ceci."
    assert any(shape.has_table for shape in prs.slides[-2].shapes)
    for slide in prs.slides:  # PowerPoint refuses what LibreOffice lets through: one id per shape
        ids = [shape.shape_id for shape in slide.shapes]
        assert len(ids) == len(set(ids))


def test_presentation_needs_consent_and_can_change_look_and_length(client, tmp_path, monkeypatch):
    import json
    import os
    from pptx import Presentation
    from app import doc_routes
    from app.doc import deck

    calls = []
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (calls.append(1), (json.dumps(DECK_ANSWER), "gemini"))[1])
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    body = {"filename": "r.docx", "data": data, "convert": True, "to": "pptx", "slides": 9, "theme": "corail"}
    assert client.post("/documents", json=body).status_code == 400
    view = client.post("/documents", json={**body, "consent": True}).json()
    assert view["convert"] == "pptx" and (view["deck"]["slides"], view["deck"]["theme"], view["deck"]["file"], view["deck"]["school"]) == (9, "corail", "r.docx", True) and len(calls) == 1
    if not (os.getenv("PROPRE_SOFFICE") or shutil.which("simpress")):
        pytest.skip("LibreOffice Impress n'est pas installé")
    done = client.post(f"/documents/{view['id']}/deck", json={"theme": "nuit"}).json()
    assert done["render"]["pages"] == 9 and done["deck"]["theme"] == "nuit" and len(calls) == 1  # a new look costs no AI call
    assert client.post(f"/documents/{view['id']}/deck", json={"school": False}).json()["deck"]["school"] is False and len(calls) == 1
    client.post(f"/documents/{view['id']}/deck", json={"slides": 6})
    assert len(calls) == 2
    assert len(Presentation(doc_routes.final_file(view["id"], "pptx")).slides) == 6


def test_a_formatted_document_becomes_a_presentation_without_sending_it_again(client, tmp_path, monkeypatch):
    import json
    from app.doc import deck
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(DECK_ANSWER), "gemini"))
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    first = client.post("/documents", json={"filename": "r.docx", "data": data}).json()
    assert client.post(f"/documents/{first['id']}/present", json={}).status_code == 400  # no consent
    made = client.post(f"/documents/{first['id']}/present", json={"slides": 9, "theme": "foret", "consent": True}).json()
    assert made["id"] != first["id"] and made["convert"] == "pptx" and made["deck"]["slides"] == 9 and made["deck"]["theme"] == "foret"
    assert client.post(f"/documents/{made['id']}/present", json={"consent": True}).status_code == 400
    assert client.get(f"/documents/{first['id']}").json().get("convert") is None  # the document itself has not moved


def test_a_failed_ai_leaves_nothing_behind(client, tmp_path, monkeypatch):
    from app.doc import deck
    from app.doc.spelling import SpellError

    def down(source, prompt):
        raise SpellError("occupé")
    monkeypatch.setattr(deck, "ask", down)
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    r = client.post("/documents", json={"filename": "r.docx", "data": data, "convert": True, "to": "pptx", "consent": True})
    assert r.status_code == 503 and "IA" in r.json()["detail"]


def audit_slides(path) -> list[str]:
    """Everything that would be seen spilling out of its box or off the slide."""
    from pptx import Presentation
    from pptx.util import Emu
    from app.doc.slides import text_height
    prs = Presentation(path)
    width, height = prs.slide_width, prs.slide_height
    faults = []
    for n, slide in enumerate(prs.slides, 1):
        for shape in slide.shapes:
            if shape.name == "Décor":
                continue
            if shape.left < -1000 or shape.top < -1000 or shape.left + shape.width > width + 1000 or shape.top + shape.height > height + 1000:
                faults.append(f"{n}: {shape.name} hors de la diapo")
            if shape.has_text_frame and shape.text_frame.text.strip():
                used = 0.0
                for p in shape.text_frame.paragraphs:
                    runs = [r for r in p.runs if r.font.size]
                    if runs:
                        indent = 0.32 if p._p.pPr is not None and p._p.pPr.get("marL") else 0
                        size = runs[0].font.size.pt
                        used += text_height("".join(r.text for r in p.runs), size, Emu(shape.width).inches - indent, runs[0].font.name or "Calibri", bool(runs[0].font.bold))
                        used += (p.space_after.pt / 72 if p.space_after else 0)
                if used > Emu(shape.height).inches + 0.2:
                    faults.append(f"{n}: « {shape.text_frame.text[:40]} » {used:.2f} pouces pour {Emu(shape.height).inches:.2f}")
            if shape.has_table if hasattr(shape, "has_table") else False:
                if shape.top + sum(r.height for r in shape.table.rows) > Emu(int(7.05 * 914400)):
                    faults.append(f"{n}: tableau trop haut")
    return faults


@pytest.mark.parametrize("theme", ["academique", "sorbonne", "campus", "savane", "ocean", "medical", "royal", "corail", "soleil", "ardoise", "nuit", "neon", "contraste", "vitamine", "terre", "foret", "aurora", "braise", "lagon", "minuit", "perle", "menthe", "prairie", "horizon", "azur", "graphite", "ambre", "citron", "halo", "iris", "brume"])
def test_nothing_overflows_even_with_the_longest_text_allowed(tmp_path, theme):
    """The worst case the AI can send: every limit reached, for every layout."""
    from app.doc.slides import build_pptx, title_info
    long = "Une phrase volontairement très longue qui atteint presque la limite autorisée pour un élément de diapo ici"
    head = "Un titre court mais quand même assez long"
    item = {"head": head, "text": long, "icon": "users"}
    title = "Un titre de diapositive très long qui dit vraiment tout le message de la diapositive en entier"
    slides = [{"type": kind, "title": title, "part": "Contexte", "items": [item] * n, "key": long, "takeaway": long[:90]}
              for kind, n in (("liste", 5), ("grille", 6), ("grille", 4), ("grille", 3), ("grille", 2), ("schema", 3), ("schema", 4), ("schema", 5), ("schema", 6), ("panneau", 4), ("chronologie", 6), ("chronologie", 3), ("etapes", 5), ("etapes", 4), ("etapes", 3))]
    points = [long[:90]] * 4
    rows = [["Colonne un", "Colonne deux", "Colonne trois", "Colonne quatre"], *[["Une cellule assez longue pour tester le retour à la ligne automatique du tableau", "x" * 60, "y y y " * 12, "z"] for _ in range(7)]]
    slides += [{"type": "comparaison", "title": title, "left": {"title": head, "points": points}, "right": {"title": head, "points": points}},
               {"type": "chiffres", "title": title, "stats": [{"value": "1 234 567 FCFA", "label": long[:70], "icon": "coins"}] * 4},
               {"type": "encadre", "title": title, "label": "Problématique", "text": long * 2},
               {"type": "grand", "title": title, "value": "Hétérogénéités", "text": long, "icon": "target"},
               {"type": "tableau", "title": title, "rows": rows, "caption": long},
               {"type": "graphique", "title": title, "chart": "barres", "series": [{"label": "A", "value": 40}, {"label": "B", "value": 60}], "key": long, "icon": "chart-pie"}]
    cover = {"title": title * 2, "doc_label": "Mémoire de fin d'études", "header_fr": ["DÉPARTEMENT DES TECHNOLOGIES DE L'INFORMATION ET DE LA COMMUNICATION"] * 7,
             "header_en": ["DEPARTMENT OF INFORMATION TECHNOLOGIES AND COMMUNICATION OF THE UNIVERSITY"] * 7, "specialty": "TIC · Niveau Licence 3", "year": "2025-2026",
             "authors": [{"name": "ZEUDJO TIYO VARELA ORIOL NOM TRÈS LONG", "info": "23I0080FS"}] * 4, "supervisors": [{"name": "Dr. KENGI OLGA"}] * 3}
    saved = tmp_path / "s.pptx"
    for seed in range(3):  # three documents: each takes other compositions of the layouts
        cover["title"] = f"{title} {seed}" * 2
        saved.write_bytes(build_pptx({"slides": slides * 2, "parts": ["Contexte", "Solution", "Conclusion", "Résultats obtenus", "Perspectives"], "thanks": "Merci"}, title_info({"blocks": [], "meta": {"cover": cover}}, tmp_path), theme, tmp_path))
        assert audit_slides(saved) == []


def test_slides_carry_their_transition_and_animation_in_the_order_powerpoint_wants(tmp_path):
    from pptx import Presentation
    from app.doc.slides import build_pptx, title_info
    items = [{"head": "Stock", "text": "Suivi", "icon": "layers"}, {"head": "Vente", "text": "Mois", "icon": "coins"}]
    deck = {"slides": [{"type": "liste", "title": "Le contexte", "items": items, "part": "A"}], "parts": ["A", "B"]}
    info = title_info({"blocks": [], "meta": {"title": "Mon rapport"}}, tmp_path)
    saved = tmp_path / "s.pptx"
    saved.write_bytes(build_pptx(deck, info, "foret", tmp_path))
    prs = Presentation(saved)
    assert [c.tag.rsplit("}", 1)[1] for c in prs.slides[2]._element] == ["cSld", "clrMapOvr", "transition", "timing"]
    timing = prs.slides[2]._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}timing")
    ids = timing.xpath(".//p:cTn/@id")
    assert len(ids) == len(set(ids))  # every id only once
    shapes = {str(s.shape_id) for s in prs.slides[2].shapes}
    assert set(timing.xpath(".//p:spTgt/@spid")) <= shapes  # only shapes that exist
    saved.write_bytes(build_pptx(deck, info, "foret", tmp_path, moving=False))
    assert [c.tag.rsplit("}", 1)[1] for c in Presentation(saved).slides[2]._element] == ["cSld", "clrMapOvr"]


@pytest.mark.parametrize("motion", ["fondu", "monter", "glisser", "zoom", "balayer"])
@pytest.mark.parametrize("click", [False, True])
def test_every_animation_is_valid_for_powerpoint_and_can_change_per_slide(tmp_path, motion, click):
    from pptx import Presentation
    from app.doc.slides import MOTIONS, build_pptx, show_plan, title_info
    items = [{"head": "Stock", "text": "Suivi", "icon": "layers"}, {"head": "Vente", "text": "Mois", "icon": "coins"}, {"head": "Clients", "text": "Accueil", "icon": "users"}]
    slides = [{"type": "liste", "title": "Le contexte", "items": items, "part": "A"}, {"type": "liste", "title": "La suite", "items": items, "part": "A", "motion": "aucune"}, {"type": "liste", "title": "Autre", "items": items, "part": "B", "motion": "fondu"}]
    saved = tmp_path / "s.pptx"
    saved.write_bytes(build_pptx({"slides": slides, "parts": ["A", "B"]}, title_info({"blocks": [], "meta": {"title": "Mon rapport"}}, tmp_path), "halo", tmp_path, motion=motion, click=click))
    prs = Presentation(saved)
    timing = prs.slides[2]._element.find("{http://schemas.openxmlformats.org/presentationml/2006/main}timing")
    ids = timing.xpath(".//p:cTn/@id")
    assert len(ids) == len(set(ids)) and set(timing.xpath(".//p:spTgt/@spid")) <= {str(s.shape_id) for s in prs.slides[2].shapes}
    assert timing.xpath(".//p:cTn[@presetID]/@presetID")[0] == str(MOTIONS[motion][0])
    assert ("clickEffect" in timing.xpath(".//p:cTn/@nodeType")) == click
    plan = show_plan(saved)
    assert plan[2]["motion"] == motion and plan[2]["click"] == click and plan[2]["frames"] > 2
    assert [c.tag.rsplit("}", 1)[1] for c in prs.slides[3]._element] == ["cSld", "clrMapOvr"]  # « aucune » on this slide
    assert plan[4]["motion"] == "fondu"


def test_the_style_follows_the_subject():
    from app.doc.slides import choose_theme
    health = {"blocks": [{"text": "Les soins infirmiers en réanimation : patient, hôpital, médicaments."}], "meta": {"kind": "cours"}}
    farm = {"blocks": [{"text": "Agriculture et élevage : la plantation de cacao, agronomie."}], "meta": {"kind": "rapport"}}
    assert choose_theme(health) in ("medical", "brume", "horizon", "menthe") and choose_theme(farm) in ("prairie", "citron", "halo", "horizon", "menthe")


def test_the_user_changes_words_order_colours_and_font(client, tmp_path, monkeypatch):
    import json
    import os
    from pptx import Presentation
    from app import doc_routes
    from app.doc import deck
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(DECK_ANSWER), "gemini"))
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    view = client.post("/documents", json={"filename": "r.docx", "data": data, "convert": True, "to": "pptx", "slides": 9, "theme": "foret", "consent": True}).json()
    if not (os.getenv("PROPRE_SOFFICE") or shutil.which("simpress")):
        pytest.skip("LibreOffice Impress n'est pas installé")
    edited = view["deck"]["content"]
    edited[0]["title"] = "Mon propre titre"
    edited[0]["items"][0]["head"] = "Mes mots à moi"
    edited = [edited[1], edited[0], *edited[2:-1]]  # moved, and the last one removed
    done = client.post(f"/documents/{view['id']}/deck", json={"edited": edited, "colors": {"accent": "#123456", "second": "abcdef", "x": "1"}, "font": "Arial"}).json()
    assert done["deck"]["colors"] == {"accent": "123456", "second": "ABCDEF"} and done["deck"]["font"] == "Arial"
    assert done["deck"]["content"][1]["title"] == "Mon propre titre" and done["deck"]["slides"] == 8
    prs = Presentation(doc_routes.final_file(view["id"], "pptx"))
    assert prs.slides[3].shapes.title.text == "Mon propre titre" and len(prs.slides) == 8
    assert client.post(f"/documents/{view['id']}/deck", json={"edited": [{"type": "liste", "title": ""}]}).status_code == 400


def test_a_slide_without_its_picture_still_works(tmp_path, monkeypatch):
    """The free picture service can be down: the talk must come out all the same."""
    import httpx
    from pptx import Presentation
    from app.doc import art
    from app.doc.slides import build_pptx, title_info

    def down(*args, **kwargs):
        raise httpx.ConnectError("down")
    monkeypatch.setattr(art.httpx, "get", down)
    items = [{"head": "Stock", "text": "Suivi", "icon": "layers"}, {"head": "Vente", "text": "Mois", "icon": "coins"}]
    deck = {"visual": "a warehouse", "slides": [{"type": "panneau", "title": "Le contexte", "items": items, "visual": "a truck", "part": "A"}, {"type": "grand", "title": "Un chiffre", "value": "3", "text": "mois", "part": "B"}], "parts": ["A", "B"]}
    art.illustrate(deck, tmp_path / "images")
    assert deck["art"] == "" and deck["slides"][0]["art"] == ""
    saved = tmp_path / "s.pptx"
    saved.write_bytes(build_pptx(deck, title_info({"blocks": [], "meta": {"title": "Mon rapport"}, "deck_school": False}, tmp_path), "aurora", tmp_path))
    assert len(Presentation(saved).slides) == 5


def test_the_slideshow_on_the_site_builds_up_step_by_step(client, tmp_path, monkeypatch):
    import json
    import os
    from pptx import Presentation
    from app import doc_routes
    from app.doc import deck
    from app.doc.slides import frame_deck, show_plan
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(DECK_ANSWER), "gemini"))
    if not (os.getenv("PROPRE_SOFFICE") or shutil.which("simpress")):
        pytest.skip("LibreOffice Impress n'est pas installé")
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    view = client.post("/documents", json={"filename": "r.docx", "data": data, "convert": True, "to": "pptx", "slides": 9, "theme": "lagon", "school": False, "consent": True}).json()
    client.post(f"/documents/{view['id']}/render")
    final = doc_routes.doc_dir(view["id"]) / "build" / "final.pptx"
    plan = show_plan(final)
    assert plan[0]["frames"] == 1 and max(s["frames"] for s in plan) > 1  # the title page does not build up
    stage = tmp_path / "stage.pptx"
    stage.write_bytes(frame_deck(final, 0))
    moving = next(i for i, s in enumerate(plan) if s["frames"] > 1)
    assert len(Presentation(stage).slides[moving].shapes) < len(Presentation(final).slides[moving].shapes)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(2) as pool:  # a double click: both calls get the slideshow
        answers = list(pool.map(lambda _: client.post(f"/documents/{view['id']}/show"), range(2)))
    assert [r.status_code for r in answers] == [200, 200]
    made = answers[0].json()
    assert len(made["slides"]) == 9
    n, last = moving + 1, plan[moving]["frames"] - 1
    assert client.get(f"/documents/{view['id']}/show/{n}-0.webp").status_code == 200
    assert client.get(f"/documents/{view['id']}/show/{n}-{last}.webp").status_code == 200
