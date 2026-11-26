"""Pictures made by the AI (FLUX.2 klein on Cloudflare Workers AI), for presentations and Word documents. No network here."""
import base64
import io
import threading

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from pptx import Presentation

from app import config, db, fapshi
from app.doc import art
from app.doc.slides import build_pptx, title_info


def png() -> str:
    out = io.BytesIO()
    Image.new("RGB", (1280, 720), (200, 90, 40)).save(out, "PNG")
    return base64.b64encode(out.getvalue()).decode()


class Answer:
    def __init__(self, status: int, body: dict | None = None, text: str = ""):
        self.status_code, self._body, self.text = status, body or {}, text

    def json(self):
        return self._body


@pytest.fixture()
def cloudflare(monkeypatch):
    """Cloudflare set up and answering; `sent` keeps what each call asked."""
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "acc")
    monkeypatch.setenv("CLOUDFLARE_AI_TOKEN", "tok")
    monkeypatch.setattr(art, "_spent_until", 0.0)
    sent: list[dict] = []
    state = {"answer": Answer(200, {"result": {"image": png()}, "success": True})}

    def post(url, headers=None, files=None, timeout=None):
        sent.append({"url": url, "auth": headers["Authorization"], "form": {k: v[1] for k, v in files.items()}})
        return state["answer"]
    monkeypatch.setattr(art.httpx, "post", post)
    return sent, state


def test_nothing_is_drawn_without_the_keys(tmp_path, monkeypatch):
    monkeypatch.delenv("CLOUDFLARE_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("CLOUDFLARE_AI_TOKEN", raising=False)
    monkeypatch.setattr(art.httpx, "post", lambda *a, **k: pytest.fail("no call without keys"))
    assert not art.ai_configured() and art.generate("a market in the morning", tmp_path / "x.jpg") is None


def test_a_picture_is_asked_to_flux_klein_and_saved_with_its_credit(tmp_path, cloudflare):
    sent, _ = cloudflare
    got = art.generate("Students reading in a library", tmp_path / "x.jpg")
    assert got == {"credit": art.AI_CREDIT}
    with Image.open(tmp_path / "x.jpg") as img:
        assert img.format == "JPEG" and img.size == (1280, 720)
    call = sent[0]
    assert call["url"].endswith("/accounts/acc/ai/run/@cf/black-forest-labs/flux-2-klein-4b") and call["auth"] == "Bearer tok"
    assert call["form"]["prompt"].startswith("Students reading in a library. Any people in the picture are Black Africans") and "No text" in call["form"]["prompt"]
    assert (call["form"]["width"], call["form"]["height"]) == ("1280", "720")
    art.generate("A lab bench", tmp_path / "y.jpg", art.FIGURE_SIZE)
    assert (sent[1]["form"]["width"], sent[1]["form"]["height"]) == ("1024", "768")


def test_once_the_free_allowance_is_spent_no_call_until_the_next_day(tmp_path, cloudflare):
    sent, state = cloudflare
    state["answer"] = Answer(429, text='{"errors":[{"code":4006,"message":"you have used up your daily free allocation of 10,000 neurons"}]}')
    assert art.generate("a harbour", tmp_path / "x.jpg") is None and art.ai_spent()
    assert art.generate("a harbour", tmp_path / "x.jpg") is None and len(sent) == 1  # no second call today


def test_people_are_drawn_as_black_africans_unless_the_scene_says_who_they_are():
    assert art.PEOPLE in art.prompt("A team meeting in a bright office")
    assert art.PEOPLE in art.prompt("un tableau noir dans une salle de classe")  # a blackboard says nothing about people
    for told in ("A European tourist taking a photo", "deux femmes blanches au marché", "An Asian engineer at work", "African farmers in a cocoa field"):
        assert art.PEOPLE not in art.prompt(told), told


def test_some_pictures_are_never_drawn_but_ordinary_subjects_are():
    for bad in ("une femme nue", "naked people", "un homme avec une arme", "soldiers with guns", "scène érotique"):
        assert art.UNSAFE.search(bad), bad
    for fine in ("blood test in a hospital", "dépistage du cancer du sein", "l'armée de l'air au défilé", "skills training", "a sextant on a boat"):
        assert not art.UNSAFE.search(fine), fine


def test_a_slide_without_a_photo_gets_an_ai_picture_and_ai_pictures_come_first_when_chosen(tmp_path, cloudflare, monkeypatch):
    sent, _ = cloudflare
    photo = {"credit": "Photo : A, Pexels"}

    def bank(query, seed, path, taken, lock, deadline=40):
        if query == "office team":
            Image.new("RGB", (1600, 900), (20, 120, 200)).save(path)
            return photo
        return None
    monkeypatch.setattr(art, "find_photo", bank)
    deck = {"photo": "office team", "visual": "A team meeting in a bright office",
            "slides": [{"type": "grand", "photo": "cocoa beans", "visual": "Hands sorting cocoa beans on a wooden table"}]}
    art.illustrate(deck, tmp_path)
    assert deck["credit"] == photo["credit"] and deck["slides"][0]["credit"] == art.AI_CREDIT  # no photo of cocoa: drawn
    assert [c["form"]["prompt"].split(".")[0] for c in sent] == ["Hands sorting cocoa beans on a wooden table"]
    art.illustrate(deck, tmp_path, drawn=True)
    assert deck["credit"] == deck["slides"][0]["credit"] == art.AI_CREDIT and len(sent) == 3
    assert all((tmp_path / d["art"]).is_file() for d in (deck, deck["slides"][0]))


def test_drawn_pictures_fall_back_to_real_photos_when_the_ai_cannot_draw(tmp_path, cloudflare, monkeypatch):
    _, state = cloudflare
    state["answer"] = Answer(500, text="busy")
    monkeypatch.setattr(art, "find_photo", lambda query, seed, path, taken, lock, deadline=40: (Image.new("RGB", (1600, 900), (20, 120, 200)).save(path), {"credit": "Photo : A, Pexels"})[1])
    deck = {"photo": "office team", "visual": "A team meeting", "slides": []}
    art.illustrate(deck, tmp_path, drawn=True)
    assert deck["credit"] == "Photo : A, Pexels"


def test_the_last_slide_credits_ai_pictures_as_images(tmp_path):
    Image.new("RGB", (1600, 900), (30, 120, 200)).save(tmp_path / "deck-photo-0.jpg")
    items = [{"head": "Stock", "text": "Suivi quotidien", "icon": ""}, {"head": "Vente", "text": "Par mois", "icon": ""}]
    deck = {"art": "deck-photo-0.jpg", "credit": art.AI_CREDIT, "parts": ["A"], "slides": [{"type": "liste", "title": "Les missions", "items": items, "part": "A"}]}
    info = title_info({"blocks": [], "meta": {"title": "Mon rapport"}, "deck_school": False}, tmp_path)
    (tmp_path / "s.pptx").write_bytes(build_pptx(deck, info, "studio", tmp_path))
    last = list(Presentation(tmp_path / "s.pptx").slides)[-1]
    credits = next(s for s in last.shapes if s.name == "Crédits des photos").text_frame.text
    assert credits == "Images : " + art.AI_CREDIT


# --- the routes ----------------------------------------------------------------------------------

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


TEXT = "Introduction\n\nLe stage s'est déroulé à Douala pendant trois mois dans une entreprise de logistique. " * 3


def test_a_word_document_gets_an_ai_figure_from_the_users_words(client, cloudflare):
    sent, _ = cloudflare
    doc = client.post("/documents", json={"text": TEXT}).json()
    assert doc["ai_images"] is True
    made = client.post(f"/documents/{doc['id']}/image", json={"prompt": "un entrepôt rempli de cartons, vu de haut"})
    assert made.status_code == 200, made.text
    body = made.json()
    assert body["image"].startswith("ia") and body["image"].replace(".", "").isalnum()
    assert body["caption"] == "Un entrepôt rempli de cartons, vu de haut (image générée par IA)"
    assert client.get(f"/documents/{doc['id']}/images/{body['image']}").status_code == 200
    blocks = client.get(f"/documents/{doc['id']}").json()["blocks"]
    blocks += [{"id": 0, "type": "figure", "image": body["image"]}, {"id": 0, "type": "caption", "of": "figure", "text": body["caption"]}]
    saved = client.put(f"/documents/{doc['id']}", json={"blocks": blocks}).json()
    assert [b["type"] for b in saved["blocks"][-2:]] == ["figure", "caption"]  # the figure is kept when the document is saved
    assert client.post(f"/documents/{doc['id']}/image", json={"prompt": "une femme nue"}).status_code == 400
    assert client.post(f"/documents/{doc['id']}/image", json={"prompt": "ok"}).status_code == 400  # too short
    assert len(sent) == 1


def test_a_document_cannot_draw_without_keys_nor_past_its_limit(client, cloudflare, monkeypatch):
    from app import doc_routes
    doc = client.post("/documents", json={"text": TEXT}).json()
    monkeypatch.setattr(doc_routes, "MAX_DRAWN", 1)
    assert client.post(f"/documents/{doc['id']}/image", json={"prompt": "un marché le matin"}).status_code == 200
    assert client.post(f"/documents/{doc['id']}/image", json={"prompt": "un marché le soir"}).status_code == 429
    monkeypatch.delenv("CLOUDFLARE_AI_TOKEN")
    assert client.get(f"/documents/{doc['id']}").json()["ai_images"] is False
    assert client.post(f"/documents/{doc['id']}/image", json={"prompt": "un marché le soir"}).status_code == 503


def test_a_presentation_can_switch_to_ai_pictures_without_writing_its_slides_again(client, cloudflare, tmp_path, monkeypatch):
    import json
    from app import doc_routes
    from app.doc import deck
    from tests.test_documents import DECK_ANSWER, stage_docx
    calls = []
    answer = {**DECK_ANSWER, "visual": "Workers checking boxes in a warehouse", "photo": "warehouse shelves"}
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (calls.append(1), (json.dumps(answer), "gemini"))[1])
    monkeypatch.setattr(art, "find_photo", lambda *a, **k: None)  # no photo bank today
    monkeypatch.setattr(doc_routes, "render", lambda order_id: doc_routes.view(db.get_order(order_id)))  # no LibreOffice here
    stage_docx(tmp_path / "r.docx")
    data = base64.b64encode((tmp_path / "r.docx").read_bytes()).decode()
    view = client.post("/documents", json={"filename": "r.docx", "data": data, "convert": True, "to": "pptx", "slides": 9, "consent": True}).json()
    assert view["deck"]["images"] == "photos"
    drawn_first = len(cloudflare[0])
    assert drawn_first >= 1  # no photo found: the AI drew them
    done = client.post(f"/documents/{view['id']}/deck", json={"images": "ia"}).json()
    assert done["deck"]["images"] == "ia" and len(calls) == 1 and len(cloudflare[0]) == 2 * drawn_first
    order = db.get_order(view["id"])["payload"]["doc"]
    assert order["deck"]["credit"] == art.AI_CREDIT
    assert client.post(f"/documents/{view['id']}/deck", json={"images": "ia"}).json()["deck"]["images"] == "ia" and len(cloudflare[0]) == 2 * drawn_first  # same choice: nothing redone


def test_ai_pictures_can_be_ticked_before_the_slides_are_made(client, cloudflare, tmp_path, monkeypatch):
    import json
    from app.doc import deck
    from tests.test_documents import DECK_ANSWER, stage_docx
    answer = {**DECK_ANSWER, "visual": "Workers checking boxes in a warehouse", "photo": "warehouse shelves"}
    monkeypatch.setattr(deck, "ask", lambda source, prompt: (json.dumps(answer), "gemini"))
    monkeypatch.setattr(art, "find_photo", lambda *a, **k: pytest.fail("ticked: no photo search first"))
    stage_docx(tmp_path / "r.docx")
    data = (tmp_path / "r.docx").read_bytes()
    made = client.post("/documents/upload?filename=r.docx&convert=true&to=pptx&consent=true&slides=9&images=ia", content=data).json()
    assert made["deck"]["images"] == "ia" and cloudflare[0]  # drawn from the start
    first = client.post("/documents", json={"filename": "r.docx", "data": base64.b64encode(data).decode()}).json()
    again = client.post(f"/documents/{first['id']}/present", json={"slides": 9, "consent": True, "images": "ia"}).json()
    assert again["deck"]["images"] == "ia"
