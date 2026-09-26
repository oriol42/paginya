import pytest
from fastapi.testclient import TestClient

from app import config, db, fapshi
from app.doc.detect import detect
from app.doc.extract import from_markdown, looks_like_markdown
from app.doc.render import build_docx, inline_spans, options_for

MD = """# Cours de SQL
### Licence 2

Intro avec **gras** et *italique*.

---

## 1. Les bases
### Jointures
1. **Identifier** les tables
2. Écrire la jointure
- un point
  - un sous-point

| Clause | Rôle |
|---|---|
| WHERE | **avant** le groupement |

```sql
SELECT * FROM t
WHERE a = 1;
```

> débit = 1/T
"""


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


def test_markdown_structure():
    r = detect(from_markdown(MD))
    types = [(b["type"], b.get("level")) for b in r["blocks"]]
    assert types[:2] == [("title", None), ("title", None)]
    heads = [(b["text"], b["level"]) for b in r["blocks"] if b["type"] == "heading"]
    assert heads == [("1. Les bases", 1), ("Jointures", 2)]
    lists = [b for b in r["blocks"] if b["type"] == "list"]
    assert [b["ordered"] for b in lists] == [True, True, False, False]
    assert lists[3]["level"] == 1
    assert "**Identifier**" in lists[0]["text"]
    code = next(b for b in r["blocks"] if b["type"] == "code")
    assert code["text"] == "SELECT * FROM t\nWHERE a = 1;"
    table = next(b for b in r["blocks"] if b["type"] == "table")
    assert table["rows"] == [["Clause", "Rôle"], ["WHERE", "**avant** le groupement"]]
    assert any(b["type"] == "quote" for b in r["blocks"])
    assert not any("---" in b.get("text", "") or b.get("text", "").startswith("#") for b in r["blocks"])
    assert r["meta"]["kind"] == "cours" and r["meta"]["title"] == "Cours de SQL"


def test_course_gets_no_generated_pages():
    opts = options_for("cours", 5000)
    assert not opts["toc"] and not opts["toc_end"] and not opts["cover"] and not opts["chapter_pages"]
    assert options_for("memoire")["toc"]


def test_inline_spans():
    assert inline_spans("a **b** *c* `d` ***e***") == [("a ", ""), ("b", "b"), (" ", ""), ("c", "i"), (" ", ""), ("d", "c"), (" ", ""), ("e", "bi")]
    assert inline_spans("2 * 3 * 4") == [("2 * 3 * 4", "")]


def test_markdown_renders(tmp_path):
    r = detect(from_markdown(MD))
    data = build_docx({"blocks": r["blocks"], "meta": r["meta"], "style": {"theme": "simple"}, "options": options_for("cours")}, tmp_path)
    assert data[:2] == b"PK"


def test_looks_like_markdown():
    assert looks_like_markdown(MD)
    assert not looks_like_markdown("Bonjour,\n\nJe vous écris pour une demande de stage.")


def test_letterhead_and_kind_via_api(client):
    r = client.post("/documents", json={"text": MD})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["meta"]["kind"] == "cours" and not d["options"]["toc"]
    logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    lh = {"fr": [["RÉPUBLIQUE DU CAMEROUN", "Paix – Travail – Patrie"], ["UNIVERSITÉ DE DOUALA"]], "en": [["REPUBLIC OF CAMEROON"]], "logo": logo, "institutionId": "udo"}
    r = client.put(f"/documents/{d['id']}", json={"letterhead": lh, "options": {**d["options"], "letterhead": True}})
    assert r.json()["letterhead"]["fr"][1] == ["UNIVERSITÉ DE DOUALA"] and r.json()["options"]["letterhead"]
    r = client.put(f"/documents/{d['id']}", json={"kind": "memoire"})
    o = r.json()["options"]
    assert r.json()["meta"]["kind"] == "memoire" and o["toc"] and o["chapter_pages"] and o["letterhead"]
    r = client.put(f"/documents/{d['id']}", json={"letterhead": {"fr": "x", "logo": "javascript:alert(1)"}})
    assert r.json()["letterhead"]["logo"] is None and r.json()["letterhead"]["fr"] == []


def test_real_report_patterns():
    """Cases found in real internship reports (Memoire Online corpus, docs/ETUDE-DOCUMENTS.md)."""
    from app.doc.extract import Raw
    raws = [Raw(text=t, source="docx") for t in [
        "SOMMAIRE",
        "A- Etude de la population d'Amoutivé P.03",
        "B- Les habitats et installations domestiques P.05",
        "SECTION I : HISTORIQUE ET PLACE DE LA SGBC DANS L'ÉCONOMIE NATIONALE",
        "La banque a été créée en 1963 et compte aujourd'hui plusieurs agences dans tout le pays, avec un réseau dense.",
        "3. LES ABONNES INTERMEDIAIRES : sont ceux qui utilisent l'eau pour l'usage domestique et commercial",
    ]]
    r = detect(raws, trace=True)
    tr = r["trace"]
    assert tr[1]["type"] == "toc" and tr[2]["type"] == "toc"
    assert tr[3]["type"] == "heading"
    assert tr[5]["type"] != "heading"


def test_very_messy_numbering_and_bullets():
    """The careless student: odd numbering, "=>" bullets, no space after "-", titles ending with ":"."""
    from app.doc.extract import Raw
    texts = [
        "Chapitre1 PRESENTATION DE LA STRUCTURE",
        "1- Historique :",
        "La structure a été créée en 1998 par un groupe d'entrepreneurs et compte aujourd'hui plus de cent agents répartis.",
        "2°) Missions",
        "Elle a pour missions principales les suivantes :",
        "=> accueillir les usagers",
        "-orienter les clients",
        "+ suivre les dossiers",
        "Elle contribue aussi à 10.000 emplois et à 1-2 projets par an dans la région du Littoral et au-delà.",
    ]
    tr = detect([Raw(text=t, source="docx") for t in texts], trace=True)["trace"]
    kinds = [tr[i]["type"] for i in range(len(texts))]
    assert kinds[0] == "heading" and kinds[1] == "heading" and kinds[3] == "heading"
    assert kinds[5:8] == ["list", "list", "list"]
    assert kinds[8] == "paragraph"
