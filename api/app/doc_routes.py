"""Document formatting endpoints. A document is an order whose payload holds {"doc": ...}."""
from __future__ import annotations

import base64
import binascii
import io
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from docx import Document as DocxDocument
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel

from . import config, db, learn, pricing, storage
from .doc import office
from .doc.detect import detect
from .doc.extract import ExtractError, from_docx, from_markdown, from_pdf, from_text, looks_like_markdown
from .doc.render import DEFAULT_OPTIONS, KINDS, THEMES, build_docx, options_for
from . import render as cover_render
from .doc import analysis, art, keep
from .doc.cover_info import split_header_lines
from .forms.letter_parse import parse_letter
from .doc import spelling as spell
from .doc.exam_scan import AUTO_PROMPT, EXAM_PROMPT, blocks_to_text, exam_signals, raws_to_text, split_type
from .doc.exam_scan import finalize as finalize_exam
from .doc.scan import ScanError, ocr_local, read_text, read_text_with_engine, straighten
from .doc import deck as deck_ai
from .doc.slides import DEFAULT_MOTION, DEFAULT_THEME, MOTIONS, THEMES as SLIDE_THEMES, build_pptx, choose_theme, frame_deck, show_plan, title_info
from .svg_safe import UnsafeSvg, sanitize_svg

router = APIRouter(prefix="/documents")

MAX_UPLOAD = 15 * 1024 * 1024
MAX_TEXT = 1_500_000
MAX_DECK_RUNS = 6  # each one is an AI call on a free quota
TIERS = ["document_court", "rapport", "memoire"]
CONVERTIBLE = (".docx", ".pdf")
log = logging.getLogger("paginya.docs")
_LAYOUT_POOL = ThreadPoolExecutor(2)
OLD_WORD = (".doc", ".odt", ".rtf")  # opened by LibreOffice and saved as .docx on arrival
BLOCK_TYPES = {"heading", "paragraph", "list", "table", "figure", "caption", "source", "quote", "code", "title"}
BLOCK_KEYS = {"id", "type", "text", "level", "ordered", "rows", "image", "of", "special", "role",
              "term", "definition", "part", "hidden", "sub"}


def doc_dir(order_id: str) -> Path:
    return config.DATA_DIR / "docs" / order_id


# --- durable inputs (Hugging Face disk is a cache: see storage.py) ------------

def _persist_inputs(order_id: str) -> None:
    """The original file and its images can't be rebuilt: keep them in durable storage. Sent in the background,
    several at a time (the local copy is already there: the customer does not wait for the upload)."""
    folder = doc_dir(order_id)
    paths = [p for p in [*folder.glob("source.*"), *(folder / "images").glob("*")] if p.is_file()]

    def send(path: Path) -> None:
        try:
            storage.put(f"docs/{order_id}/{path.relative_to(folder)}", path.read_bytes())
        except Exception:  # noqa: BLE001 — a failed upload must not break the document; the local copy stays
            log.exception("upload failed: %s", path.name)

    def run() -> None:
        with ThreadPoolExecutor(6) as pool:
            list(pool.map(send, paths))

    if storage.REMOTE:
        threading.Thread(target=run, daemon=True).start()
    else:
        run()


def _ensure_inputs(order_id: str) -> None:
    """After a restart the local copy is gone: bring the original and images back."""
    folder = doc_dir(order_id)
    if any(folder.glob("source.*")):
        return
    for key in storage.list_keys(f"docs/{order_id}"):
        data = storage.get(key)
        if data is not None:
            path = folder / key.removeprefix(f"docs/{order_id}/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)


def _forget(order_id: str) -> None:
    shutil.rmtree(doc_dir(order_id), ignore_errors=True)
    storage.delete_prefix(f"docs/{order_id}")


def _discard(order_id: str | None) -> None:
    if not order_id:
        return
    _forget(order_id)
    with db.connect() as c:
        c.execute("DELETE FROM orders WHERE id = ?", (order_id,))


def tier_for(pages: int) -> str:
    if pages <= 15:
        return "document_court"
    if pages <= 40:
        return "rapport"
    return "memoire"


class DocIn(BaseModel):
    text: str | None = None
    filename: str | None = None
    data: str | None = None  # base64 file content
    convert: bool = False  # only change the format (Word -> PDF, PDF -> Word): nothing is added or restyled
    to: str = ""  # "pptx": the Word or PDF file becomes a presentation written by the AI (with convert)
    slides: int = deck_ai.DEFAULT_SLIDES  # how many, chosen by the user
    theme: str = "auto"
    school: bool = True  # a school work: the slides open and close like the report (logos, establishment, supervisors)
    consent: bool = False  # the text is sent to an AI service: the user agreed


class DocPatch(BaseModel):
    blocks: list[dict] | None = None
    style: dict | None = None
    options: dict | None = None
    letterhead: dict | None = None  # {"fr": [[lines]], "en": [[lines]], "logo": "data:image/png;base64,..."}
    kind: str | None = None  # user's choice of document type: resets the automatic pages to that type's
    cover_svg: str | None = None
    remove_cover: bool = False
    mode: str | None = None  # "keep": the user's own Word file, element by element; "rebuild": Paginya's layout
    plan: dict | None = None  # {"cover"|"toc"|"numbers": "keep"|"add"|"redo"|"none"}
    confirm: bool = False  # the user has seen the analysis and chose: nothing is rendered before that


def _load(order_id: str) -> dict:
    order = db.get_order(order_id)
    if order is None or "doc" not in order["payload"] or order["payload"]["doc"].get("deleted"):
        raise HTTPException(404, "Document introuvable ou supprimé")
    return order


def view(order: dict) -> dict:
    doc = order["payload"]["doc"]
    paid_at = order.get("paid_at") or 0
    return {
        "id": order["id"],
        "status": order["status"],
        "product": order["product"],
        "label": pricing.LABELS[order["product"]],
        "amount": order["amount"],
        "editable": order["status"] != "PAID" or time.time() - paid_at < config.ORDER_VALIDITY_DAYS * 86400,
        "blocks": doc["blocks"],
        "meta": doc["meta"],
        "style": doc["style"],
        "options": doc["options"],
        "has_cover": bool(doc.get("cover_svg")),
        "letterhead": doc.get("letterhead"),
        "render": doc.get("render"),
        "mode": doc.get("mode", "rebuild"),
        "plan": plan_of(doc),
        "analysis": doc.get("analysis"),
        "confirmed": doc.get("confirmed", True),  # documents made before the analysis screen existed
        "convert": doc.get("convert"),  # "pdf" | "docx" | "pptx" when the order is a plain conversion
        "deck": {"slides": deck_ai.total(doc["deck"]), "theme": doc.get("deck_theme", DEFAULT_THEME),
                 "max": deck_ai.max_slides(doc["meta"].get("words", 0)), "file": doc.get("deck_file", ""), "school": doc.get("deck_school", True), "moving": doc.get("deck_moving", True), "motion": doc.get("deck_motion", DEFAULT_MOTION), "click": doc.get("deck_click", False),
                 "colors": doc.get("deck_colors") or {}, "font": doc.get("deck_font") or "", "content": doc["deck"]["slides"]} if doc.get("deck") else None,
        "help": bool(doc.get("help")),  # « J'aide Paginya à s'améliorer » (app/learn.py)
    }


def plan_of(doc: dict) -> dict:
    """The element-by-element plan; older documents only had {"page_numbers", "toc"} (add what was missing)."""
    if doc.get("plan"):
        return doc["plan"]
    legacy = doc.get("keep") or {}
    return {"cover": "keep", "toc": "add" if legacy.get("toc") else "keep", "numbers": "add" if legacy.get("page_numbers") else "keep"}


@router.post("/upload")
async def upload(request: Request, filename: str, convert: bool = False, to: str = "", slides: int = deck_ai.DEFAULT_SLIDES,
                 theme: str = "auto", consent: bool = False, school: bool = True) -> dict:
    """The file sent as it is (no base64): a third less to send on a slow 3G line than /documents."""
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_UPLOAD:
            raise HTTPException(413, "Fichier trop lourd (15 Mo maximum)")
    if not raw:
        raise HTTPException(400, "Fichier vide")
    body = DocIn(filename=filename[:200], data=base64.b64encode(raw).decode(), convert=convert, to=to, slides=slides, theme=theme, consent=consent, school=school)
    return await run_in_threadpool(create, body)  # the heavy work stays off the event loop, like /documents


@router.post("")
def create(body: DocIn) -> dict:
    tmp_id = None
    early_layout = None
    if body.to == "pptx" and not body.consent:
        raise HTTPException(400, "Accepte l'envoi du texte à l'IA pour préparer la présentation")
    if body.data and body.filename:
        try:
            raw_bytes = base64.b64decode(body.data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(400, "Fichier illisible") from exc
        if len(raw_bytes) > MAX_UPLOAD:
            raise HTTPException(413, "Fichier trop lourd (15 Mo maximum)")
        ext = Path(body.filename).suffix.lower()
        order_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": {}})
        tmp_id = order_id
        folder = doc_dir(order_id)
        folder.mkdir(parents=True, exist_ok=True)
        src = folder / f"source{ext}"
        src.write_bytes(raw_bytes)
        try:
            if ext in OLD_WORD:  # .doc, .odt, .rtf: LibreOffice saves it as .docx, then it is a Word file like any other
                upload = src.rename(folder / f"upload{ext}")
                src, ext = folder / "source.docx", ".docx"
                try:
                    office.to_docx(upload, src)
                except office.OfficeError as exc:
                    raise ExtractError("Ce fichier est illisible. Enregistre-le en .docx (Fichier > Enregistrer sous) puis réessaie.") from exc
                finally:
                    upload.unlink(missing_ok=True)
            if ext == ".docx":
                # LibreOffice lays the original out (the "Avant" view, its cover page) while we read it: ~half the wait on big files
                (folder / "before").mkdir(exist_ok=True)
                early_layout = _LAYOUT_POOL.submit(office.layout, src, folder / "layout.json", folder / "before" / "before.pdf")
                raws = from_docx(src, folder / "images")
            elif ext == ".pdf":
                raws = from_pdf(src, folder / "images", keep_toc=body.convert and body.to != "pptx")  # a sommaire has no place on slides
            elif ext in (".txt", ".md", ".markdown"):
                content = raw_bytes.decode("utf-8", "replace")
                raws = from_markdown(content) if ext != ".txt" or looks_like_markdown(content) else from_text(content)
            else:
                raise ExtractError("Format non pris en charge. Utilise un fichier Word (.docx), PDF ou texte.")
        except ExtractError as exc:
            _discard(order_id)
            raise HTTPException(400, str(exc)) from exc
    elif body.text and body.text.strip():
        if len(body.text) > MAX_TEXT:
            raise HTTPException(413, "Texte trop long")
        raws = from_markdown(body.text) if looks_like_markdown(body.text) else from_text(body.text)
        order_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": {}})
        tmp_id = order_id
        doc_dir(order_id).mkdir(parents=True, exist_ok=True)
        (doc_dir(order_id) / "source.txt").write_text(body.text, encoding="utf-8")
    else:
        raise HTTPException(400, "Colle ton texte ou importe un fichier")

    result = detect(raws, trace=True)
    trace = result.pop("trace")
    if not result["blocks"]:
        _discard(tmp_id)
        raise HTTPException(400, "Aucun texte trouvé dans ce document")
    theme = "academique" if result["meta"]["kind"] in ("memoire", "rapport_stage", "rapport") else "simple"
    doc = {
        "blocks": result["blocks"],
        "meta": result["meta"],
        "style": {"theme": theme, "color": "#0E9F6E"},
        "options": options_for(result["meta"]["kind"], result["meta"]["words"], result["meta"].get("typed_plan", False), result["meta"].get("slots")),
        "cover_svg": None,
        "render": None,
    }
    existing = None
    is_docx = bool(body.data and body.filename and Path(body.filename).suffix.lower() in (".docx", *OLD_WORD))
    if is_docx:
        # What the Word file already has (cover page, sommaire, page numbers): shown to the user, kept unless they say otherwise.
        (folder / "before").mkdir(exist_ok=True)
        try:
            # the real pages, as LibreOffice lays the file out (its PDF is the "Avant" view, made once)
            existing = keep.inspect(src, early_layout.result() if early_layout else office.layout(src, folder / "layout.json", folder / "before" / "before.pdf"))
        except Exception:  # an odd file python-docx cannot read: the normal flow still works
            existing = None
        if existing:
            # Titles only made to look like titles (bold, capitals, numbers typed by hand) instead of Word's styles:
            # the file has no real structure, so it is rebuilt by default (keeping it would keep its disorder).
            styled = sum(1 for r in raws if re.match(r"^(heading|titre)\s*\d", r.style) and r.text.strip())
            found = doc["meta"].get("headings", 0)
            existing["styled"] = styled
            existing["handmade"] = not existing["toc"] and found >= 3 and styled < 0.6 * found
            doc["meta"]["existing"] = existing
            cover_info = doc["meta"].get("cover")
            if cover_info is not None and not cover_info.get("header_fr"):
                try:  # the printed letterhead of a cover sits in the Word header, not in the text
                    fr, en = split_header_lines(keep.header_lines(src))
                except Exception:
                    fr, en = [], []
                if fr:
                    cover_info["header_fr"] = fr
                if en and not cover_info.get("header_en"):
                    cover_info["header_en"] = en
    report = analysis.analyze(result["meta"]["kind"], doc["meta"], doc["blocks"], doc["options"], existing, is_docx)
    doc["analysis"] = report
    doc["plan"] = report["plan"]
    doc["confirmed"] = False
    if existing and (existing["cover"] or existing["toc"] or existing["page_numbers"] or existing["own_layout"]) and not existing.get("handmade"):
        doc["mode"] = "keep"  # rebuilding would lose what only this file has (its cover, text boxes, letterhead…)
    # A file formatted by hand (titles in bold, no Word styles) is rebuilt: keeping it would keep its disorder.
    if body.convert:
        ext = Path(body.filename or "").suffix.lower()
        if ext not in CONVERTIBLE:
            _discard(tmp_id)
            raise HTTPException(400, "La conversion prend un fichier Word (.docx) ou PDF")
        doc["confirmed"] = True  # nothing to choose: the file is shown converted straight away
        if body.to == "pptx":  # the content of the file as slides to edit: only what it says, cut into slides
            doc.pop("mode", None)
            doc.update(convert="pptx", plan={"cover": "none", "toc": "none", "numbers": "none"}, deck_theme=_theme(body.theme, doc), deck_file=(body.filename or "")[:200], deck_school=body.school)
            try:
                _write_deck(doc, body.slides, folder / "images")
            except deck_ai.DeckError as exc:
                db.bump("ia_echec")
                _discard(tmp_id)
                raise HTTPException(503, str(exc)) from exc
        elif ext == ".docx":  # the Word file exactly as it is, printed to PDF
            doc.update(convert="pdf", mode="keep", plan={"cover": "keep", "toc": "keep", "numbers": "keep"})
        else:  # the text, titles, lists, tables and pictures of the PDF in a Word file to edit, with no page added
            if any(b.get("hidden") for b in result["blocks"]) or result["meta"].get("cover"):
                # its own cover (logos, frames, layout) can't be rebuilt from its words: kept as a picture of the page
                try:
                    (folder / "images").mkdir(parents=True, exist_ok=True)
                    subprocess.run(["pdftoppm", "-r", "150", "-png", "-f", "1", "-l", "1", "-singlefile", str(src), str(folder / "images" / "own-cover")],
                                   capture_output=True, timeout=60, check=True)
                    doc["cover_png"] = "own-cover.png"
                except (subprocess.SubprocessError, FileNotFoundError):
                    pass
            doc["blocks"] = _with_toc_lines(doc["blocks"], trace, raws)  # a conversion keeps the author's own sommaire
            doc.pop("mode", None)
            doc["meta"]["kind"] = "document"
            doc.update(convert="docx", options={k: False for k in DEFAULT_OPTIONS}, style={"theme": "simple", "color": "#0E9F6E"},
                       plan={"cover": "none", "toc": "none", "numbers": "none"})
    if tmp_id is None:
        order_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": doc})
    else:
        db.update_payload(order_id, {"doc": doc})
    _persist_inputs(order_id)
    learn.snapshot_later(order_id, raws, result, trace, doc_dir(order_id))
    return view(db.get_order(order_id))


def _theme(name: str, doc: dict | None = None) -> str:
    if name in SLIDE_THEMES:
        return name
    return choose_theme(doc) if doc else DEFAULT_THEME


def _write_deck(doc: dict, wanted: int, images: Path | None = None) -> None:
    most = deck_ai.max_slides(doc["meta"].get("words", 0))
    count = max(deck_ai.MIN_SLIDES, min(wanted, most))
    doc["deck"] = deck_ai.write(doc, count, on_call=lambda provider: db.bump(f"ia:presentation-{provider}"))
    doc["deck_runs"] = doc.get("deck_runs", 0) + 1
    if images is not None:
        art.illustrate(doc["deck"], images)


def _with_toc_lines(blocks: list[dict], trace: dict, raws: list) -> list[dict]:
    """The lines Paginya sets aside when it rebuilds a document (a sommaire typed by hand, a list of figures), put back
    where they were, as plain text: a conversion changes the format, never the content."""
    pos = {b["id"]: k for k, b in enumerate(blocks)}
    before: dict[int, list[dict]] = {}
    pending: list[dict] = []
    for i in sorted(trace):
        it = trace[i]
        if it.get("type") == "toc" and i < len(raws) and raws[i].text.strip():
            pending.append({"type": "paragraph", "text": raws[i].text.strip()})
        elif pending and it.get("id") in pos:
            before.setdefault(pos[it["id"]], []).extend(pending)
            pending = []
    out = []
    for k, b in enumerate(blocks):
        out.extend(before.get(k, []))
        out.append(b)
    out.extend(pending)
    for n, b in enumerate(out, 1):
        b["id"] = n
    return out


@router.get("/{order_id}")
def get(order_id: str) -> dict:
    return view(_load(order_id))


class HelpIn(BaseModel):
    on: bool


@router.post("/{order_id}/help")
def help_paginya(order_id: str, body: HelpIn) -> dict:
    """« J'aide Paginya à s'améliorer »: the customer lets us keep this file (12 months at most) to fix what went wrong."""
    order = _load(order_id)
    db.update_payload(order_id, {"doc": {**order["payload"]["doc"], "help": body.on}})
    if not body.on:
        shutil.rmtree(learn.files_dir() / order_id, ignore_errors=True)
        db.flag_doc(order_id, has_file=0)
    return {"help": body.on}


def _clean_blocks(blocks: list[dict]) -> list[dict]:
    out = []
    for i, b in enumerate(blocks[:6000]):
        if b.get("type") not in BLOCK_TYPES:
            continue
        clean = {k: v for k, v in b.items() if k in BLOCK_KEYS}
        clean["id"] = i + 1
        if "text" in clean:
            clean["text"] = str(clean["text"])[:20000]
        if "level" in clean:
            clean["level"] = max(0, min(int(clean["level"]), 4))
        if "rows" in clean:
            clean["rows"] = [[str(c)[:2000] for c in row][:30] for row in clean["rows"][:500]]
        if clean.get("type") == "figure" and not str(clean.get("image", "")).replace(".", "").isalnum():
            continue
        out.append(clean)
    return out


def _clean_letterhead(h: dict) -> dict:
    def groups(v) -> list[list[str]]:
        if not isinstance(v, list):
            return []
        out = []
        for g in v[:6]:
            lines = [str(x).strip()[:160] for x in (g if isinstance(g, list) else [g])[:4] if str(x).strip()]
            if lines:
                out.append(lines)
        return out

    logo = h.get("logo")
    ok_logo = isinstance(logo, str) and len(logo) < 900_000 and logo.startswith(("data:image/png;base64,", "data:image/jpeg;base64,", "data:image/webp;base64,"))
    inst = re.sub(r"[^a-z0-9-]", "", str(h.get("institutionId", "")))[:40]
    return {"fr": groups(h.get("fr")), "en": groups(h.get("en")), "logo": logo if ok_logo else None, "institutionId": inst}


@router.put("/{order_id}")
def update(order_id: str, body: DocPatch) -> dict:
    order = _load(order_id)
    info = view(order)
    if order["status"] == "PENDING":
        raise HTTPException(409, "Paiement en cours, réessaie dans un instant")
    if not info["editable"]:
        raise HTTPException(403, "La période de modification gratuite (7 jours) est terminée")
    doc = order["payload"]["doc"]
    if body.blocks is not None:
        doc["blocks"] = _clean_blocks(body.blocks)
    if body.style is not None:
        allowed = {"theme", "font", "size", "line", "justify", "margins", "color"}
        style = {k: v for k, v in body.style.items() if k in allowed}
        if style.get("theme") not in THEMES:
            style["theme"] = doc["style"].get("theme", "academique")
        doc["style"] = style
    if body.kind is not None and body.kind in KINDS:
        doc["meta"]["kind"] = body.kind
        doc["options"] = {**options_for(body.kind, doc["meta"].get("words", 0), doc["meta"].get("typed_plan", False), doc["meta"].get("slots")), "letterhead": doc["options"].get("letterhead", False)}
        doc["plan"] = analysis.default_plan(body.kind, doc["meta"].get("existing"), doc["options"])
    if body.options is not None:
        doc["options"] = {k: bool(body.options.get(k, v)) for k, v in DEFAULT_OPTIONS.items()}
    if body.letterhead is not None:
        doc["letterhead"] = _clean_letterhead(body.letterhead)
    if body.mode in ("keep", "rebuild"):
        _ensure_inputs(order_id)
        if body.mode == "keep" and not next(doc_dir(order_id).glob("source.docx"), None):
            raise HTTPException(400, "Le fichier Word d'origine n'est plus disponible")
        doc["mode"] = body.mode
    if body.plan is not None:
        doc["plan"] = analysis.clean_plan(body.plan, plan_of(doc))
        if doc.get("mode", "rebuild") == "rebuild":  # Paginya's own layout: the plan is "which pages to make"
            doc["options"] = {**doc["options"], "cover": doc["plan"]["cover"] != "none", "toc": doc["plan"]["toc"] != "none",
                              "page_numbers": doc["plan"]["numbers"] != "none"}
    if body.confirm:
        doc["confirmed"] = True
    if body.remove_cover:
        doc["cover_svg"] = None
    elif body.cover_svg:
        try:
            doc["cover_svg"] = sanitize_svg(body.cover_svg)
        except UnsafeSvg as exc:
            raise HTTPException(400, str(exc)) from exc
        only_cover = all(v is None for v in (body.blocks, body.style, body.options, body.letterhead, body.kind))
        if only_cover and doc.get("render"):
            # The app shows the new cover itself: no full LibreOffice pass now, the files are rebuilt at download.
            doc["render"]["stale"] = True
    db.update_payload(order_id, {"doc": doc})
    return view(db.get_order(order_id))


def _save_logo(order_id: str, data: str) -> str:
    try:
        raw = base64.b64decode(data.split(",")[-1], validate=True)
        if len(raw) > 3 * 1024 * 1024:
            raise HTTPException(413, "Logo trop lourd (3 Mo maximum)")
        with Image.open(io.BytesIO(raw)) as img:
            img.thumbnail((800, 800))
            folder = doc_dir(order_id) / "images"
            folder.mkdir(parents=True, exist_ok=True)
            img.convert("RGBA").save(folder / "deck-logo.png", "PNG")
    except (binascii.Error, ValueError, OSError) as exc:
        raise HTTPException(400, "Image illisible : choisis un logo en PNG ou JPEG") from exc
    _persist_inputs(order_id)
    return "deck-logo.png"


class PresentIn(BaseModel):
    slides: int = deck_ai.DEFAULT_SLIDES
    theme: str = "auto"
    school: bool = True
    consent: bool = False  # the text is sent to an AI service: the user agreed


@router.post("/{order_id}/present")
def present(order_id: str, body: PresentIn) -> dict:
    """A document already formatted becomes a presentation, with the user's corrections, without sending the file again.
    It is a new order: the presentation is a second file, sold like any other document."""
    if not body.consent:
        raise HTTPException(400, "Accepte l'envoi du texte à l'IA pour préparer la présentation")
    source = _load(order_id)["payload"]["doc"]
    if source.get("convert") == "pptx":
        raise HTTPException(400, "Ce document est déjà une présentation")
    _ensure_inputs(order_id)
    new_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": {}})
    folder, origin = doc_dir(new_id), doc_dir(order_id)
    folder.mkdir(parents=True, exist_ok=True)
    if (origin / "images").is_dir():
        shutil.copytree(origin / "images", folder / "images")
    for path in origin.glob("source.*"):
        shutil.copy(path, folder / path.name)
    meta = source["meta"]
    doc = {"blocks": source["blocks"], "meta": meta, "style": source["style"], "options": source["options"], "cover_svg": None, "render": None, "analysis": None,
           "confirmed": True, "convert": "pptx", "plan": {"cover": "none", "toc": "none", "numbers": "none"}, "deck_theme": "",
           "deck_file": str((meta.get("cover") or {}).get("title") or meta.get("title") or "Ton document")[:200], "deck_school": body.school}
    doc["deck_theme"] = _theme(body.theme, doc)
    try:
        _write_deck(doc, body.slides, folder / "images")
    except deck_ai.DeckError as exc:
        db.bump("ia_echec")
        _discard(new_id)
        raise HTTPException(503, str(exc)) from exc
    db.update_payload(new_id, {"doc": doc})
    _persist_inputs(new_id)
    return view(db.get_order(new_id))


DECK_TYPES = {"liste", "grille", "panneau", "schema", "chronologie", "etapes", "comparaison", "chiffres", "graphique", "encadre", "grand", "figure", "tableau", "section"}
_TEXT_KEYS = ("title", "notes", "part", "highlight", "takeaway", "key", "label", "text", "value", "caption", "chart", "icon", "visual", "art", "motion")


def _clean_edited(slides: list[dict]) -> list[dict]:
    """What comes back from the editor: the user writes what they want, but the shape of a slide stays ours."""
    def line(value, limit: int = 300) -> str:
        return str(value or "").strip()[:limit]

    def items(values, most: int) -> list[dict]:
        out = [{"head": line(v.get("head"), 60), "text": line(v.get("text")), "icon": line(v.get("icon"), 30)} for v in (values if isinstance(values, list) else []) if isinstance(v, dict)]
        return [v for v in out if v["head"] or v["text"]][:most]

    out = []
    for s in slides[:40]:
        kind = s.get("type") if isinstance(s, dict) else None
        if kind not in DECK_TYPES or not line(s.get("title")):
            continue
        clean = {k: line(s[k], 1500 if k == "notes" else 300) for k in _TEXT_KEYS if s.get(k)}
        clean["type"] = kind
        if kind in ("liste", "grille", "panneau", "schema", "chronologie", "etapes"):
            clean["items"] = items(s.get("items"), 6)
            if not clean["items"]:
                continue
            if kind == "chronologie" and len(clean["items"]) < 2 or kind in ("liste", "etapes") and len(clean["items"]) > 5 or kind == "panneau" and len(clean["items"]) > 4:
                clean["type"] = "grille"
        elif kind == "chiffres":
            clean["stats"] = [{"value": line(v.get("value"), 20), "label": line(v.get("label"), 90), "icon": line(v.get("icon"), 30)} for v in (s.get("stats") or [])[:4] if isinstance(v, dict) and v.get("value")]
            if not clean["stats"]:
                continue
        elif kind == "comparaison":
            for side in ("left", "right"):
                part = s.get(side) if isinstance(s.get(side), dict) else {}
                clean[side] = {"title": line(part.get("title"), 40), "points": [line(p, 120) for p in (part.get("points") or [])[:5] if line(p)]}
            if not clean["left"]["points"] or not clean["right"]["points"]:
                continue
        elif kind == "graphique":
            clean["series"] = [{"label": line(v.get("label"), 40), "value": float(v["value"])} for v in (s.get("series") or [])[:6] if isinstance(v, dict) and isinstance(v.get("value"), (int, float))]
            if len(clean["series"]) < 2:
                continue
        elif kind == "figure":
            if not str(s.get("image", "")).replace(".", "").replace("-", "").isalnum():
                continue
            clean["image"] = str(s["image"])
            clean["points"] = [line(p, 120) for p in (s.get("points") or [])[:3] if line(p)]
        elif kind == "tableau":
            clean["rows"] = [[line(c, 200) for c in r][:6] for r in (s.get("rows") or [])[:9] if isinstance(r, list)]
            if len(clean["rows"]) < 2:
                continue
        elif kind in ("encadre", "grand") and not clean.get("text" if kind == "encadre" else "value"):
            continue
        out.append(clean)
    if not out:
        raise HTTPException(400, "Garde au moins une diapositive")
    return out


class DeckIn(BaseModel):
    slides: int | None = None  # a new number: the AI writes the slides again
    theme: str | None = None  # a new look: same words, nothing sent to the AI
    logo: str | None = None  # the school's or company's logo, base64
    school: bool | None = None  # a school work (cover like the report) or a plain presentation: no AI needed
    moving: bool | None = None  # transitions and animations: some juries prefer none
    motion: str | None = None  # how things appear on every slide (a slide can have its own)
    click: bool | None = None  # things appear at each click of the presenter, not on their own
    colors: dict | None = None  # {"accent": "RRGGBB", "second": "RRGGBB"}; {} goes back to the style's own colours
    font: str | None = None  # font of the titles: Calibri, Cambria or Arial; "" for the style's own
    edited: list[dict] | None = None  # the slides as the user changed them: words, order, layout, removals


@router.post("/{order_id}/deck")
def change_deck(order_id: str, body: DeckIn) -> dict:
    order = _load(order_id)
    doc = order["payload"]["doc"]
    if doc.get("convert") != "pptx" or not doc.get("deck"):
        raise HTTPException(400, "Ce document n'est pas une présentation")
    if not view(order)["editable"]:
        raise HTTPException(403, "La période de modification gratuite (7 jours) est terminée")
    if body.theme:
        doc["deck_theme"] = _theme(body.theme)
    if body.school is not None:
        doc["deck_school"] = body.school
    if body.moving is not None:
        doc["deck_moving"] = body.moving
    if body.motion in MOTIONS:
        doc["deck_motion"] = body.motion
    if body.click is not None:
        doc["deck_click"] = body.click
    if body.colors is not None:
        doc["deck_colors"] = {k: str(v).lstrip("#").upper() for k, v in body.colors.items() if k in ("accent", "second") and re.fullmatch(r"#?[0-9a-fA-F]{6}", str(v))}
    if body.font is not None:
        doc["deck_font"] = body.font if body.font in ("Calibri", "Cambria", "Arial") else ""
    if body.edited is not None:
        doc["deck"]["slides"] = _clean_edited(body.edited)
        doc["deck"]["parts"] = list(dict.fromkeys(s["part"] for s in doc["deck"]["slides"] if s.get("part")))
    if body.logo:
        _ensure_inputs(order_id)
        doc["deck_logo"] = _save_logo(order_id, body.logo)
    if body.slides is not None:
        if doc.get("deck_runs", 0) >= MAX_DECK_RUNS:
            raise HTTPException(429, "Tu as refait cette présentation plusieurs fois : garde celle-ci ou importe à nouveau ton fichier.")
        try:
            _write_deck(doc, body.slides, doc_dir(order_id) / "images")
        except deck_ai.DeckError as exc:
            db.bump("ia_echec")
            raise HTTPException(503, str(exc)) from exc
    db.update_payload(order_id, {"doc": doc})
    _persist_inputs(order_id)
    return render(order_id)


SHOW_DPI = 80
_SHOW_LOCK = threading.Lock()  # two calls at once (a double click) must not draw in the same folder


@router.post("/{order_id}/show")
def show(order_id: str) -> dict:
    """The slideshow on the site: each slide as its things appear, so the customer sees it move before paying."""
    with _SHOW_LOCK:
        return _prepare_show(order_id)


def _prepare_show(order_id: str) -> dict:
    order = _load(order_id)
    doc = order["payload"]["doc"]
    build = doc_dir(order_id) / "build"
    if doc.get("convert") != "pptx" or not doc.get("render"):
        raise HTTPException(400, "Prépare d'abord la présentation")
    if not (build / "final.pptx").is_file():
        render(order_id)
    folder = build / "show"
    version = str(doc["render"]["version"]) + str(order["status"])
    plan = show_plan(build / "final.pptx")
    if (folder / "version").is_file() and (folder / "version").read_text() == version:
        return {"slides": plan, "version": version}
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    watermark = order["status"] != "PAID"

    def picture(pdf: Path, page: int, name: str) -> None:
        subprocess.run(["pdftoppm", "-r", str(SHOW_DPI), "-f", str(page), "-l", str(page), "-singlefile", str(pdf), str(folder / "raw")], check=True, capture_output=True, timeout=60)
        raw = folder / "raw.ppm"
        with Image.open(raw) as img:
            page_img = img.convert("RGB")
        if watermark:
            page_img = Image.alpha_composite(page_img.convert("RGBA"), office._watermark_layer(page_img.size)).convert("RGB")
        page_img.save(folder / f"{name}.webp", "WEBP", quality=78, method=2)
        raw.unlink()

    try:
        for frame in range(max(s["frames"] for s in plan) - 1):
            stage = folder / f"stage{frame}.pptx"
            stage.write_bytes(frame_deck(build / "final.pptx", frame))
            office.slides_to_pdf(stage, folder / f"stage{frame}.pdf")
            for n, slide in enumerate(plan, 1):
                if frame < slide["frames"] - 1:
                    picture(folder / f"stage{frame}.pdf", n, f"{n}-{frame}")
            stage.unlink()
            (folder / f"stage{frame}.pdf").unlink()
        for n, slide in enumerate(plan, 1):
            picture(build / "final.pdf", n, f"{n}-{slide['frames'] - 1}")
    except (office.OfficeError, subprocess.SubprocessError, OSError) as exc:
        raise HTTPException(500, "Le diaporama n'a pas pu être préparé, réessaie") from exc
    (folder / "version").write_text(version)
    return {"slides": plan, "version": version}


@router.get("/{order_id}/show/{slide}-{frame}.webp")
def show_frame(order_id: str, slide: int, frame: int) -> FileResponse:
    _load(order_id)
    path = doc_dir(order_id) / "build" / "show" / f"{slide}-{frame}.webp"
    if not path.is_file():
        raise HTTPException(404, "Image introuvable")
    return FileResponse(path, media_type="image/webp")


@router.post("/{order_id}/exam")
def to_exam(order_id: str) -> dict:
    """The document as an exam paper (the user picked "Épreuve"): header fields + exercises for /epreuve.

    Built from the original text or file when we still have it, so "1)", "a)", "Exercice 1 (5 pts)"
    stay exactly as written; otherwise from the editor's blocks.
    """
    order = _load(order_id)
    _ensure_inputs(order_id)
    folder = doc_dir(order_id)
    source = next((p for p in folder.glob("source.*")), None)
    text = None
    try:
        if source is not None and source.suffix in (".txt", ".md", ".markdown"):
            text = source.read_text(encoding="utf-8", errors="replace")
        elif source is not None and source.suffix == ".docx":
            text = raws_to_text(from_docx(source, folder / "images"))
        elif source is not None and source.suffix == ".pdf":
            text = raws_to_text(from_pdf(source))
    except ExtractError:
        text = None
    if not text or not text.strip():
        text = blocks_to_text(order["payload"]["doc"]["blocks"])
    exam = finalize_exam(text[:MAX_TEXT])
    return {"fields": exam["fields"], "content": exam["content"]}


class SpellIn(BaseModel):
    school: bool = True  # a school work: the slides open and close like the report (logos, establishment, supervisors)
    consent: bool = False  # the text is sent to an AI service: the user agreed


@router.post("/{order_id}/spelling")
def spelling(order_id: str, body: SpellIn) -> dict:
    """Spelling fixes proposed by the AI; nothing changes until the user applies the ones they keep (PUT blocks)."""
    if not body.consent:
        raise HTTPException(400, "Accepte l'envoi du texte au service de correction")
    order = _load(order_id)
    try:
        fixes = spell.propose(order["payload"]["doc"].get("blocks", []), on_call=lambda provider: db.bump(f"ia:orthographe-{provider}"))
    except spell.SpellError as exc:
        db.bump("ia_echec")
        raise HTTPException(503, str(exc)) from exc
    return {"fixes": fixes}


@router.post("/{order_id}/letter")
def to_letter(order_id: str) -> dict:
    """The document as a letter (the user agreed it is one): the fields of /lettre, read from the original text."""
    order = _load(order_id)
    _ensure_inputs(order_id)
    folder = doc_dir(order_id)
    source = next((p for p in folder.glob("source.*")), None)
    text = None
    try:
        if source is not None and source.suffix in (".txt", ".md", ".markdown"):
            text = source.read_text(encoding="utf-8", errors="replace")
        elif source is not None and source.suffix == ".docx":
            text = "\n\n".join(r.text for r in from_docx(source, folder / "images") if r.text)
        elif source is not None and source.suffix == ".pdf":
            text = "\n\n".join(r.text for r in from_pdf(source) if r.text)
    except ExtractError:
        text = None
    if not text or not text.strip():
        text = "\n\n".join(str(b.get("text") or "") for b in order["payload"]["doc"]["blocks"] if b.get("text"))
    return parse_letter(text[:MAX_TEXT])


@router.post("/{order_id}/render")
def render(order_id: str) -> dict:
    order = _load(order_id)
    doc = order["payload"]["doc"]
    _ensure_inputs(order_id)
    folder = doc_dir(order_id)
    build = folder / "build"
    build.mkdir(parents=True, exist_ok=True)
    source_docx = folder / "source.docx"
    if doc.get("convert") == "pptx":
        (build / "final.pptx").write_bytes(build_pptx(doc["deck"], title_info(doc, folder / "images"), doc.get("deck_theme", DEFAULT_THEME), folder / "images", doc.get("deck_moving", True), motion=doc.get("deck_motion", DEFAULT_MOTION), click=doc.get("deck_click", False), colors=doc.get("deck_colors"), font=doc.get("deck_font")))
        try:
            office.slides_to_pdf(build / "final.pptx", build / "final.pdf")
        except office.OfficeError as exc:
            raise HTTPException(500, "La création des diapositives a échoué, réessaie") from exc
    elif doc.get("convert") == "pdf" and source_docx.is_file():
        shutil.copy(source_docx, build / "raw.docx")  # a conversion never edits the file
    elif doc.get("mode") == "keep" and source_docx.is_file():
        plan = plan_of(doc)
        cover_png = None
        if plan["cover"] in ("redo", "add") and doc.get("cover_svg"):
            cover_png = cover_render.svg_to_png(doc["cover_svg"], 200)
        keep.touch(source_docx, build / "raw.docx", numbers=plan["numbers"], toc=plan["toc"],
                   cover=plan["cover"] if cover_png else "keep", cover_png=cover_png,
                   layout=office.layout(source_docx, folder / "layout.json"))
    else:
        (build / "raw.docx").write_bytes(build_docx(doc, folder / "images"))
    if doc.get("convert") != "pptx":
        (build / "final.docx").unlink(missing_ok=True)  # made again from raw.docx when downloaded
        try:
            office.finalize(build / "raw.docx", None, build / "final.pdf")
        except office.OfficeError as exc:
            raise HTTPException(500, "La mise en page a échoué, réessaie") from exc
    pages = office.page_count(build / "final.pdf")
    db.bump("rendu")

    tier = tier_for(pages)
    fresh = db.get_order(order_id)
    if fresh["status"] == "PAID":
        # same price whatever the length, but a paid document is not a blank page for other documents
        base = doc.get("paid_pages") or (doc.get("render") or {}).get("pages") or pages
        if pages > max(2 * base, base + 15):
            raise HTTPException(402, "Ton document a beaucoup grossi : il faut le traiter comme un nouveau document.")
        doc["paid_pages"] = base
    elif fresh["status"] != "PENDING":
        db.set_product(order_id, tier, pricing.price_for(tier))

    office.previews(build / "final.pdf", build / "pages", watermark=fresh["status"] != "PAID", pages=pages)
    doc["render"] = {"pages": pages, "version": int(time.time() * 1000)}
    db.update_payload(order_id, {"doc": doc})
    return view(db.get_order(order_id))


@router.get("/{order_id}/pages/{n}.{ext}")
def page(order_id: str, n: int, ext: str) -> FileResponse:
    order = _load(order_id)
    pages_dir = doc_dir(order_id) / "build" / "pages"
    path = office.wait_for_page(pages_dir, n)
    if path is None and order["payload"]["doc"].get("render") and not (doc_dir(order_id) / "build" / "final.pdf").is_file():
        render(order_id)  # the server restarted: rebuild the pages once
        path = office.wait_for_page(pages_dir, n)
    if ext not in ("png", "webp") or path is None:
        raise HTTPException(404, "Page introuvable")
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "no-cache"})


@router.get("/{order_id}/images/{name}")
def image(order_id: str, name: str) -> FileResponse:
    _load(order_id)
    if not name.replace(".", "").isalnum():
        raise HTTPException(404, "Image introuvable")
    _ensure_inputs(order_id)
    path = doc_dir(order_id) / "images" / name
    if not path.is_file():
        raise HTTPException(404, "Image introuvable")
    return FileResponse(path)


def final_file(order_id: str, fmt: str) -> Path:
    build = doc_dir(order_id) / "build"
    path = build / f"final.{fmt}"
    doc = _load(order_id)["payload"]["doc"]
    if fmt in ("pdf", "docx", "pptx") and doc.get("render") and (not (build / "final.pdf").is_file() or doc["render"].get("stale")):
        render(order_id)  # rebuilt after a restart, or after edits that skipped the full render (cover)
    if fmt == "docx" and not path.is_file() and (build / "raw.docx").is_file() and doc.get("mode") == "keep" and plan_of(doc)["toc"] not in ("add", "redo"):
        shutil.copy(build / "raw.docx", path)  # the user's own file, untouched by LibreOffice, with the numbers added
    if fmt == "docx" and not path.is_file() and (build / "raw.docx").is_file():
        try:
            office.finalize(build / "raw.docx", path, None)
        except office.OfficeError as exc:
            raise HTTPException(500, "La création du fichier Word a échoué, réessaie") from exc
    if fmt not in ("pdf", "docx", "pptx") or not path.is_file():
        raise HTTPException(409, "Lance d'abord la mise en page")
    return path


# --- "Avant" view: the original document as the user gave it ------------------

@router.post("/{order_id}/before")
def before(order_id: str) -> dict:
    _load(order_id)
    _ensure_inputs(order_id)
    folder = doc_dir(order_id)
    out = folder / "before"
    pages_dir = out / "pages"
    if pages_dir.is_dir() and any(pages_dir.glob("*.webp")):
        pdf = out / "before.pdf"
        return {"pages": office.page_count(pdf) if pdf.is_file() else len(list(pages_dir.glob("*.webp")))}
    out.mkdir(parents=True, exist_ok=True)
    source = next((p for p in folder.glob("source.*")), None)
    if source is None:
        raise HTTPException(404, "Document d'origine indisponible")
    pdf = out / "before.pdf"
    if source.suffix == ".pdf":
        shutil.copy(source, pdf)
    else:
        docx = source
        if source.suffix in (".txt", ".md", ".markdown"):
            docx = out / "plain.docx"
            plain = DocxDocument()
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                plain.add_paragraph(line)
            plain.save(docx)
        try:
            if not pdf.is_file() or docx != source:
                office.finalize(docx, None, pdf)
        except office.OfficeError as exc:
            raise HTTPException(500, "Aperçu de l'original indisponible") from exc
    return {"pages": office.previews(pdf, pages_dir, watermark=False)}


@router.get("/{order_id}/before/{n}.{ext}")
def before_page(order_id: str, n: int, ext: str) -> FileResponse:
    _load(order_id)
    path = office.wait_for_page(doc_dir(order_id) / "before" / "pages", n)
    if ext not in ("png", "webp") or path is None:
        raise HTTPException(404, "Page introuvable")
    return FileResponse(path, media_type="image/webp")


# --- Deletion (right to erasure) and automatic cleanup ------------------------

@router.delete("/{order_id}")
def delete(order_id: str) -> dict:
    order = _load(order_id)
    _forget(order_id)
    if order["status"] in ("PAID", "PENDING"):
        # Keep the payment record (accounting), drop every piece of content.
        db.update_payload(order_id, {"doc": {"deleted": True, "blocks": [], "meta": {}, "style": {}, "options": {}}})
    else:
        with db.connect() as c:
            c.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    return {"deleted": True}


def cleanup(now: float | None = None) -> int:
    """Delete document contents 7 days after payment (or creation if never paid)."""
    now = now or time.time()
    limit = config.ORDER_VALIDITY_DAYS * 86400
    removed = 0
    with db.connect() as c:
        rows = c.execute("SELECT id, status, created_at, paid_at FROM orders").fetchall()
    for row in rows:
        ref = row["paid_at"] or row["created_at"]
        if now - ref > 365 * 86400:  # payment proof kept 12 months, then everything goes
            _forget(row["id"])
            shutil.rmtree(config.DATA_DIR / "forms" / row["id"], ignore_errors=True)
            with db.connect() as c:
                c.execute("DELETE FROM orders WHERE id = ?", (row["id"],))
            continue
        if now - ref < limit or row["status"] == "PENDING":
            continue
        folder = doc_dir(row["id"])
        forms_folder = config.DATA_DIR / "forms" / row["id"]
        if folder.exists() or forms_folder.exists():
            shutil.rmtree(forms_folder, ignore_errors=True)
            removed += 1
        order_row = db.get_order(row["id"])
        if order_row and "doc" in order_row["payload"] and not order_row["payload"]["doc"].get("deleted"):
            _forget(row["id"])
        order = db.get_order(row["id"])
        if order and "doc" in order["payload"] and not order["payload"]["doc"].get("deleted"):
            db.update_payload(row["id"], {"doc": {"deleted": True, "blocks": [], "meta": {}, "style": {}, "options": {}}})
        elif order and "form_doc" in order["payload"] and not order["payload"]["form_doc"].get("deleted"):
            db.update_payload(row["id"], {"form_doc": {"deleted": True}})
        elif order and "svg" in order["payload"]:
            db.update_payload(row["id"], {"svg": "", "form": {}, "deleted": True})
    return removed


# --- Photos / scans -----------------------------------------------------------

scan_router = APIRouter(prefix="/scans")
SCAN_MAX = 12 * 1024 * 1024


class ScanIn(BaseModel):
    data: str  # base64 image
    handwriting: bool = False  # handwritten pages need the external AI (Gemini)
    consent: bool = False  # required only for handwriting: the page leaves our server
    kind: str = "auto"  # "auto": Paginya decides if the page is an exam paper; "epreuve" / "document" force it


def scans_dir() -> Path:
    return config.DATA_DIR / "scans"


@scan_router.post("")
def scan_page(body: ScanIn) -> dict:
    """One page at a time, so the app can show progress page by page."""
    if body.handwriting and not body.consent:
        raise HTTPException(400, "Accepte la lecture par l'IA pour les pages écrites à la main")
    try:
        raw = base64.b64decode(body.data, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(400, "Image illisible") from exc
    if len(raw) > SCAN_MAX:
        raise HTTPException(413, "Photo trop lourde (12 Mo maximum)")
    auto = body.kind == "auto"
    exam_mode = body.kind == "epreuve"
    kind_found = ""
    try:
        jpeg, found = straighten(raw)
        if body.handwriting:
            prompt = AUTO_PROMPT if auto else EXAM_PROMPT if exam_mode else None
            try:
                text, engine = read_text_with_engine(jpeg, prompt)
            except ScanError:
                db.bump("ia_echec")
                raise
            db.bump(f"ia:{engine}")
            confidence = 95.0 if engine == "mock" else 90.0
            if auto:
                kind_found, text = split_type(text)
        elif os.getenv("OCR_PROVIDER") == "mock":
            text, engine, confidence = read_text(jpeg), "mock", 95.0
        else:
            text, confidence = ocr_local(jpeg)
            engine = "tesseract"
            db.bump("ocr")
    except ScanError as exc:
        raise HTTPException(422, str(exc)) from exc
    scan_id = uuid.uuid4().hex
    scans_dir().mkdir(parents=True, exist_ok=True)
    (scans_dir() / f"{scan_id}.jpg").write_bytes(jpeg)
    is_exam = exam_mode or (auto and (kind_found == "epreuve" or (not kind_found and exam_signals(text)["likely"])))
    result = {"id": scan_id, "text": text, "straightened": found, "engine": engine, "confidence": round(confidence), "is_exam": is_exam}
    if is_exam:
        exam = finalize_exam(text)
        result["raw"] = "\n".join(ln for ln in text.splitlines() if ln.strip().lower().strip("*# ") not in ("entete", "contenu"))
        result["text"], result["exam"] = exam["content"], exam["fields"]
    return result


@scan_router.get("/{scan_id}.jpg")
def scan_image(scan_id: str) -> FileResponse:
    if not scan_id.isalnum():
        raise HTTPException(404, "Image introuvable")
    path = scans_dir() / f"{scan_id}.jpg"
    if not path.is_file():
        raise HTTPException(404, "Image introuvable")
    return FileResponse(path, media_type="image/jpeg")


def cleanup_scans(now: float | None = None) -> None:
    """Photos are only needed for proofreading: deleted after 24 h."""
    now = now or time.time()
    for path in scans_dir().glob("*.jpg") if scans_dir().exists() else []:
        if now - path.stat().st_mtime > 86400:
            path.unlink(missing_ok=True)
