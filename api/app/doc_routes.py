"""Document formatting endpoints. A document is an order whose payload holds {"doc": ...}."""
from __future__ import annotations

import base64
import binascii
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from docx import Document as DocxDocument
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db, pricing, storage
from .doc import office
from .doc.detect import detect
from .doc.extract import ExtractError, from_docx, from_markdown, from_pdf, from_text, looks_like_markdown
from .doc.render import DEFAULT_OPTIONS, KINDS, THEMES, build_docx, options_for
from . import render as cover_render
from .doc import analysis, keep
from .doc.cover_info import split_header_lines
from .doc.exam_scan import AUTO_PROMPT, EXAM_PROMPT, blocks_to_text, exam_signals, raws_to_text, split_type
from .doc.exam_scan import finalize as finalize_exam
from .doc.scan import ScanError, ocr_local, read_text, read_text_with_engine, straighten
from .svg_safe import UnsafeSvg, sanitize_svg

router = APIRouter(prefix="/documents")

MAX_UPLOAD = 15 * 1024 * 1024
MAX_TEXT = 1_500_000
TIERS = ["document_court", "rapport", "memoire"]
BLOCK_TYPES = {"heading", "paragraph", "list", "table", "figure", "caption", "source", "quote", "code", "title"}
BLOCK_KEYS = {"id", "type", "text", "level", "ordered", "rows", "image", "of", "special", "role",
              "term", "definition", "part", "hidden", "sub"}


def doc_dir(order_id: str) -> Path:
    return config.DATA_DIR / "docs" / order_id


# --- durable inputs (Hugging Face disk is a cache: see storage.py) ------------

def _persist_inputs(order_id: str) -> None:
    """The original file and its images can't be rebuilt: keep them in durable storage."""
    folder = doc_dir(order_id)
    for path in [*folder.glob("source.*"), *(folder / "images").glob("*")]:
        if path.is_file():
            storage.put(f"docs/{order_id}/{path.relative_to(folder)}", path.read_bytes())


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
    }


def plan_of(doc: dict) -> dict:
    """The element-by-element plan; older documents only had {"page_numbers", "toc"} (add what was missing)."""
    if doc.get("plan"):
        return doc["plan"]
    legacy = doc.get("keep") or {}
    return {"cover": "keep", "toc": "add" if legacy.get("toc") else "keep", "numbers": "add" if legacy.get("page_numbers") else "keep"}


@router.post("")
def create(body: DocIn) -> dict:
    tmp_id = None
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
            if ext == ".docx":
                raws = from_docx(src, folder / "images")
            elif ext == ".pdf":
                raws = from_pdf(src)
            elif ext in (".txt", ".md", ".markdown"):
                content = raw_bytes.decode("utf-8", "replace")
                raws = from_markdown(content) if ext != ".txt" or looks_like_markdown(content) else from_text(content)
            elif ext == ".doc":
                raise ExtractError("Ancien format .doc : enregistre-le en .docx (Fichier > Enregistrer sous) puis réessaie.")
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

    result = detect(raws)
    if not result["blocks"]:
        _discard(tmp_id)
        raise HTTPException(400, "Aucun texte trouvé dans ce document")
    theme = "academique" if result["meta"]["kind"] in ("memoire", "rapport_stage", "rapport") else "simple"
    doc = {
        "blocks": result["blocks"],
        "meta": result["meta"],
        "style": {"theme": theme, "color": "#0E9F6E"},
        "options": options_for(result["meta"]["kind"], result["meta"]["words"]),
        "cover_svg": None,
        "render": None,
    }
    existing = None
    is_docx = bool(body.data and body.filename and Path(body.filename).suffix.lower() == ".docx")
    if is_docx:
        # What the Word file already has (cover page, sommaire, page numbers): shown to the user, kept unless they say otherwise.
        try:
            existing = keep.inspect(src)
        except Exception:  # an odd file python-docx cannot read: the normal flow still works
            existing = None
        if existing:
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
    if existing and (existing["cover"] or existing["toc"] or existing["page_numbers"]):
        doc["mode"] = "keep"
    if tmp_id is None:
        order_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": doc})
    else:
        db.update_payload(order_id, {"doc": doc})
    _persist_inputs(order_id)
    return view(db.get_order(order_id))


@router.get("/{order_id}")
def get(order_id: str) -> dict:
    return view(_load(order_id))


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
        doc["options"] = {**options_for(body.kind, doc["meta"].get("words", 0)), "letterhead": doc["options"].get("letterhead", False)}
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


@router.post("/{order_id}/render")
def render(order_id: str) -> dict:
    order = _load(order_id)
    doc = order["payload"]["doc"]
    _ensure_inputs(order_id)
    folder = doc_dir(order_id)
    build = folder / "build"
    build.mkdir(parents=True, exist_ok=True)
    source_docx = folder / "source.docx"
    if doc.get("mode") == "keep" and source_docx.is_file():
        plan = plan_of(doc)
        cover_png = None
        if plan["cover"] in ("redo", "add") and doc.get("cover_svg"):
            cover_png = cover_render.svg_to_png(doc["cover_svg"], 200)
        keep.touch(source_docx, build / "raw.docx", numbers=plan["numbers"], toc=plan["toc"],
                   cover=plan["cover"] if cover_png else "keep", cover_png=cover_png)
    else:
        (build / "raw.docx").write_bytes(build_docx(doc, folder / "images"))
    (build / "final.docx").unlink(missing_ok=True)  # made again from raw.docx when downloaded
    try:
        office.finalize(build / "raw.docx", None, build / "final.pdf")
    except office.OfficeError as exc:
        raise HTTPException(500, "La mise en page a échoué, réessaie") from exc
    pages = office.page_count(build / "final.pdf")

    tier = tier_for(pages)
    fresh = db.get_order(order_id)
    if fresh["status"] == "PAID":
        if TIERS.index(tier) > TIERS.index(fresh["product"]):
            raise HTTPException(402, "Ton document a beaucoup grossi : il faut le traiter comme un nouveau document.")
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
    if fmt in ("pdf", "docx") and doc.get("render") and (not (build / "final.pdf").is_file() or doc["render"].get("stale")):
        render(order_id)  # rebuilt after a restart, or after edits that skipped the full render (cover)
    if fmt == "docx" and not path.is_file() and (build / "raw.docx").is_file() and doc.get("mode") == "keep" and plan_of(doc)["toc"] not in ("add", "redo"):
        shutil.copy(build / "raw.docx", path)  # the user's own file, untouched by LibreOffice, with the numbers added
    if fmt == "docx" and not path.is_file() and (build / "raw.docx").is_file():
        try:
            office.finalize(build / "raw.docx", path, None)
        except office.OfficeError as exc:
            raise HTTPException(500, "La création du fichier Word a échoué, réessaie") from exc
    if fmt not in ("pdf", "docx") or not path.is_file():
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
            text, engine = read_text_with_engine(jpeg, prompt)
            confidence = 95.0 if engine == "mock" else 90.0
            if auto:
                kind_found, text = split_type(text)
        elif os.getenv("OCR_PROVIDER") == "mock":
            text, engine, confidence = read_text(jpeg), "mock", 95.0
        else:
            text, confidence = ocr_local(jpeg)
            engine = "tesseract"
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
