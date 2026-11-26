"""Real photos for the presentations, found on free photo banks; no icons in the Studio family. No network here."""
import io
import threading

from PIL import Image
from pptx import Presentation

from app.doc import art
from app.doc.slides import build_pptx, title_info


def jpeg(colourful: bool = True) -> bytes:
    img = Image.new("RGB", (1600, 900), (40, 120, 220) if colourful else (128, 128, 128))
    out = io.BytesIO()
    img.save(out, "JPEG")
    return out.getvalue()


class Answer:
    def __init__(self, content: bytes):
        self.content = content


def fake_sources(monkeypatch, banks: dict[str, list[dict]], pictures: dict[str, bytes]):
    monkeypatch.setattr(art, "_sources", lambda query: (lambda: banks.get(query, []) for _ in range(1)))
    monkeypatch.setattr(art.httpx, "get", lambda url, **kw: Answer(pictures[url]))


def test_every_wanted_photo_is_found_once_with_its_credit(tmp_path, monkeypatch):
    banks = {"warehouse shelves": [{"url": "u1", "w": 1600, "h": 900, "credit": "Photo : A, CC0, via Openverse"}],
             "office team": [{"url": "u1", "w": 1600, "h": 900, "credit": "Photo : A, CC0, via Openverse"},
                             {"url": "u2", "w": 1600, "h": 900, "credit": "Photo : B, CC BY 2.0, via Openverse"}]}
    fake_sources(monkeypatch, banks, {"u1": jpeg(), "u2": jpeg()})
    deck = {"photo": "office team", "slides": [{"type": "liste", "photo": "warehouse shelves"}, {"type": "grille", "photo": "ignored"}]}
    art.illustrate(deck, tmp_path)
    assert deck["art"] and deck["credit"] in ("Photo : A, CC0, via Openverse", "Photo : B, CC BY 2.0, via Openverse")
    assert deck["slides"][1].get("art") is None  # a grid of cards takes no photo
    names = [d["art"] for d in (deck, deck["slides"][0]) if d.get("art")]
    assert len(names) == len(set(names)) and all((tmp_path / n).is_file() for n in names)


def test_black_and_white_pictures_and_signs_are_left_out(tmp_path, monkeypatch):
    fake_sources(monkeypatch, {"x": [{"url": "grey", "w": 1600, "h": 900, "credit": "c"}]}, {"grey": jpeg(colourful=False)})
    assert art.find_photo("x", 0, tmp_path / "p.jpg", set(), threading.Lock()) is None
    assert art.OFF.search("Warehouse workers protest for safety") and art.OLD.search("Toronto History, circa 1920")
    assert art.keywords("Workers checking boxes on shelves in a large warehouse") == "Workers checking boxes"


def test_studio_shows_the_photos_and_no_icon_and_credits_them(tmp_path):
    for n in range(3):
        Image.new("RGB", (1600, 900), (30 + 60 * n, 120, 200)).save(tmp_path / f"deck-photo-{n}.jpg")
    items = [{"head": "Stock", "text": "Suivi quotidien", "icon": "layers"}, {"head": "Vente", "text": "Par mois", "icon": "coins"}]
    deck = {"art": "deck-photo-0.jpg", "credit": "Photo : A, CC0, via Openverse", "parts": ["A", "B"], "slides": [
        {"type": "section", "title": "Le contexte", "art": "deck-photo-1.jpg", "credit": "Photo : B, CC BY 2.0, via Openverse"},
        {"type": "liste", "title": "Les missions", "items": items, "part": "A", "art": "deck-photo-2.jpg", "credit": "Photo : C, CC0, via Openverse", "notes": "Je présente."},
        {"type": "grille", "title": "Les objectifs", "items": items * 2, "part": "A"},
        {"type": "chiffres", "title": "Les chiffres", "stats": [{"value": "3", "label": "mois", "icon": "clock"}, {"value": "12", "label": "agents", "icon": "users"}], "part": "B"}]}
    info = title_info({"blocks": [], "meta": {"title": "Mon rapport", "cover": {"authors": [{"name": "KAMGA Paul"}]}}}, tmp_path)
    saved = tmp_path / "s.pptx"
    saved.write_bytes(build_pptx(deck, info, "studio", tmp_path))
    prs = Presentation(saved)
    slides = list(prs.slides)
    kinds = lambda slide: {s.name: s.shape_type for s in slide.shapes}  # noqa: E731
    assert kinds(slides[0])["!!Panneau"] == 13  # the cover's panel is a picture (MSO_SHAPE_TYPE.PICTURE)
    assert kinds(slides[2])["!!Panneau"] == 13 and kinds(slides[3])["!!Panneau"] == 13  # part opener, list: the same name, Morph carries the photo
    assert slides[3].notes_slide.notes_text_frame.text == "Je présente.\n\nPhoto : C, CC0, via Openverse"
    assert all(s.name != "Icône" for slide in slides for s in slide.shapes)  # no icon anywhere
    credits = next(s for s in slides[-1].shapes if s.name == "Crédits des photos").text_frame.text
    assert "A, CC0" in credits and "B, CC BY 2.0" in credits and "C, CC0" in credits
