"""Letters (lettre) and exam papers (epreuve): form -> Word/PDF, live preview."""
from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import config, db, pricing
from .doc import office
from .forms.exam import build_exam, parse, total_points
from .forms.letter import build_letter

router = APIRouter(prefix="/forms")
BUILDERS = {"lettre": build_letter, "epreuve": build_exam}


def form_dir(order_id: str) -> Path:
    return config.DATA_DIR / "forms" / order_id


class FormIn(BaseModel):
    kind: str
    data: dict


class FormPatch(BaseModel):
    data: dict


def _load(order_id: str) -> dict:
    order = db.get_order(order_id)
    if order is None or "form_doc" not in order["payload"] or order["payload"]["form_doc"].get("deleted"):
        raise HTTPException(404, "Document introuvable")
    return order


def _editable(order: dict) -> bool:
    return order["status"] != "PAID" or time.time() - (order["paid_at"] or 0) < config.ORDER_VALIDITY_DAYS * 86400


def view(order: dict) -> dict:
    fd = order["payload"]["form_doc"]
    out = {
        "id": order["id"], "kind": fd["kind"], "status": order["status"], "amount": order["amount"],
        "label": pricing.LABELS[order["product"]], "editable": _editable(order),
        "data": fd["data"], "render": fd.get("render"),
    }
    if fd["kind"] == "epreuve":
        out["total_points"] = total_points(parse(str(fd["data"].get("content") or "")))
    return out


def _render(order_id: str, kind: str, data: dict, paid: bool) -> dict:
    folder = form_dir(order_id)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "raw.docx").write_bytes(BUILDERS[kind](data))
    try:
        office.finalize(folder / "raw.docx", folder / "final.docx", folder / "final.pdf")
    except office.OfficeError as exc:
        raise HTTPException(500, "La mise en page a échoué, réessaie") from exc
    pages = office.previews(folder / "final.pdf", folder / "pages", watermark=not paid, dpi=96)
    return {"pages": pages, "version": int(time.time() * 1000)}


@router.post("")
def create(body: FormIn) -> dict:
    if body.kind not in BUILDERS:
        raise HTTPException(400, "Type de document inconnu")
    order_id = db.create_order(body.kind, pricing.price_for(body.kind), {"form_doc": {"kind": body.kind, "data": body.data}})
    render = _render(order_id, body.kind, body.data, paid=False)
    db.update_payload(order_id, {"form_doc": {"kind": body.kind, "data": body.data, "render": render}})
    return view(db.get_order(order_id))


@router.get("/{order_id}")
def get(order_id: str) -> dict:
    return view(_load(order_id))


@router.put("/{order_id}")
def update(order_id: str, body: FormPatch) -> dict:
    order = _load(order_id)
    if order["status"] == "PENDING":
        raise HTTPException(409, "Paiement en cours, réessaie dans un instant")
    if not _editable(order):
        raise HTTPException(403, "La période de modification gratuite (7 jours) est terminée")
    kind = order["payload"]["form_doc"]["kind"]
    render = _render(order_id, kind, body.data, paid=order["status"] == "PAID")
    db.update_payload(order_id, {"form_doc": {"kind": kind, "data": body.data, "render": render}})
    return view(db.get_order(order_id))


@router.post("/{order_id}/refresh")
def refresh(order_id: str) -> dict:
    """Re-render (e.g. right after payment, to drop the watermark from the previews)."""
    order = _load(order_id)
    fd = order["payload"]["form_doc"]
    fd["render"] = _render(order_id, fd["kind"], fd["data"], paid=order["status"] == "PAID")
    db.update_payload(order_id, {"form_doc": fd})
    return view(db.get_order(order_id))


def _rebuild_if_lost(order_id: str) -> None:
    """The server's disk is a cache (restarts wipe it): everything is rebuilt from the saved form data."""
    order = _load(order_id)
    fd = order["payload"]["form_doc"]
    if fd.get("render") and not (form_dir(order_id) / "final.pdf").is_file():
        _render(order_id, fd["kind"], fd["data"], paid=order["status"] == "PAID")


@router.get("/{order_id}/pages/{n}.png")
def page(order_id: str, n: int) -> FileResponse:
    _rebuild_if_lost(order_id)
    path = form_dir(order_id) / "pages" / f"{n}.png"
    if not path.is_file():
        raise HTTPException(404, "Page introuvable")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})


def final_file(order_id: str, fmt: str) -> Path:
    _rebuild_if_lost(order_id)
    path = form_dir(order_id) / f"final.{fmt}"
    if fmt not in ("pdf", "docx") or not path.is_file():
        raise HTTPException(409, "Document pas encore prêt")
    return path
