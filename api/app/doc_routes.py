"""Document formatting endpoints. A document is an order whose payload holds {"doc": ...}."""
from __future__ import annotations

import base64
import binascii
import os
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from docx import Document as DocxDocument
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db, pricing
from .doc import office
from .doc.detect import detect
from .doc.extract import ExtractError, from_docx, from_pdf, from_text
from .doc.render import DEFAULT_OPTIONS, THEMES, build_docx
from .doc.scan import ScanError, ocr_local, read_text, straighten
from .svg_safe import UnsafeSvg, sanitize_svg

router = APIRouter(prefix="/documents")

MAX_UPLOAD = 15 * 1024 * 1024
MAX_TEXT = 1_500_000
TIERS = ["document_court", "rapport", "memoire"]
BLOCK_TYPES = {"heading", "paragraph", "list", "table", "figure", "caption", "source", "quote"}
BLOCK_KEYS = {"id", "type", "text", "level", "ordered", "rows", "image", "of", "special", "role",
              "term", "definition", "part", "hidden"}


def doc_dir(order_id: str) -> Path:
    return config.DATA_DIR / "docs" / order_id


def _discard(order_id: str | None) -> None:
    if not order_id:
        return
    shutil.rmtree(doc_dir(order_id), ignore_errors=True)
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
    cover_svg: str | None = None
    remove_cover: bool = False


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
        "render": doc.get("render"),
    }


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
            elif ext in (".txt", ".md"):
                raws = from_text(raw_bytes.decode("utf-8", "replace"))
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
        raws = from_text(body.text)
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
        "options": dict(DEFAULT_OPTIONS),
        "cover_svg": None,
        "render": None,
    }
    if tmp_id is None:
        order_id = db.create_order("document_court", pricing.price_for("document_court"), {"doc": doc})
    else:
        db.update_payload(order_id, {"doc": doc})
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
    if body.options is not None:
        doc["options"] = {k: bool(body.options.get(k, v)) for k, v in DEFAULT_OPTIONS.items()}
    if body.remove_cover:
        doc["cover_svg"] = None
    elif body.cover_svg:
        try:
            doc["cover_svg"] = sanitize_svg(body.cover_svg)
        except UnsafeSvg as exc:
            raise HTTPException(400, str(exc)) from exc
    db.update_payload(order_id, {"doc": doc})
    return view(db.get_order(order_id))


@router.post("/{order_id}/render")
def render(order_id: str) -> dict:
    order = _load(order_id)
    doc = order["payload"]["doc"]
    folder = doc_dir(order_id)
    build = folder / "build"
    build.mkdir(parents=True, exist_ok=True)
    (build / "raw.docx").write_bytes(build_docx(doc, folder / "images"))
    try:
        office.finalize(build / "raw.docx", build / "final.docx", build / "final.pdf")
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

    office.previews(build / "final.pdf", build / "pages", watermark=fresh["status"] != "PAID")
    doc["render"] = {"pages": pages, "version": int(time.time() * 1000)}
    db.update_payload(order_id, {"doc": doc})
    return view(db.get_order(order_id))


@router.get("/{order_id}/pages/{n}.png")
def page(order_id: str, n: int) -> FileResponse:
    _load(order_id)
    path = doc_dir(order_id) / "build" / "pages" / f"{n}.png"
    if not path.is_file():
        raise HTTPException(404, "Page introuvable")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})


@router.get("/{order_id}/images/{name}")
def image(order_id: str, name: str) -> FileResponse:
    _load(order_id)
    if not name.replace(".", "").isalnum():
        raise HTTPException(404, "Image introuvable")
    path = doc_dir(order_id) / "images" / name
    if not path.is_file():
        raise HTTPException(404, "Image introuvable")
    return FileResponse(path)


def final_file(order_id: str, fmt: str) -> Path:
    path = doc_dir(order_id) / "build" / f"final.{fmt}"
    if fmt not in ("pdf", "docx") or not path.is_file():
        raise HTTPException(409, "Lance d'abord la mise en page")
    return path


# --- "Avant" view: the original document as the user gave it ------------------

@router.post("/{order_id}/before")
def before(order_id: str) -> dict:
    _load(order_id)
    folder = doc_dir(order_id)
    out = folder / "before"
    pages_dir = out / "pages"
    if pages_dir.is_dir() and any(pages_dir.iterdir()):
        return {"pages": len(list(pages_dir.glob("*.png")))}
    out.mkdir(parents=True, exist_ok=True)
    source = next((p for p in folder.glob("source.*")), None)
    if source is None:
        raise HTTPException(404, "Document d'origine indisponible")
    pdf = out / "before.pdf"
    if source.suffix == ".pdf":
        shutil.copy(source, pdf)
    else:
        docx = source
        if source.suffix in (".txt", ".md"):
            docx = out / "plain.docx"
            plain = DocxDocument()
            for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
                plain.add_paragraph(line)
            plain.save(docx)
        try:
            office.finalize(docx, out / "before.docx", pdf)
        except office.OfficeError as exc:
            raise HTTPException(500, "Aperçu de l'original indisponible") from exc
    return {"pages": office.previews(pdf, pages_dir, watermark=False)}


@router.get("/{order_id}/before/{n}.png")
def before_page(order_id: str, n: int) -> FileResponse:
    _load(order_id)
    path = doc_dir(order_id) / "before" / "pages" / f"{n}.png"
    if not path.is_file():
        raise HTTPException(404, "Page introuvable")
    return FileResponse(path, media_type="image/png")


# --- Deletion (right to erasure) and automatic cleanup ------------------------

@router.delete("/{order_id}")
def delete(order_id: str) -> dict:
    order = _load(order_id)
    shutil.rmtree(doc_dir(order_id), ignore_errors=True)
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
            shutil.rmtree(doc_dir(row["id"]), ignore_errors=True)
            shutil.rmtree(config.DATA_DIR / "forms" / row["id"], ignore_errors=True)
            with db.connect() as c:
                c.execute("DELETE FROM orders WHERE id = ?", (row["id"],))
            continue
        if now - ref < limit or row["status"] == "PENDING":
            continue
        folder = doc_dir(row["id"])
        forms_folder = config.DATA_DIR / "forms" / row["id"]
        if folder.exists() or forms_folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
            shutil.rmtree(forms_folder, ignore_errors=True)
            removed += 1
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
    try:
        jpeg, found = straighten(raw)
        if body.handwriting:
            text, engine, confidence = read_text(jpeg), "gemini", 90.0
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
    return {"id": scan_id, "text": text, "straightened": found, "engine": engine, "confidence": round(confidence)}


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
