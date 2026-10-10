"""Paginya API: orders, cover rendering and Fapshi direct-pay."""
import hmac
import logging
import os
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import admin, config, db, doc_routes, fapshi, forms_routes, guard, pricing, storage
from .render import render_cover
from .svg_safe import UnsafeSvg, sanitize_svg

log = logging.getLogger("propre")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init()
    storage.ensure_bucket(public=False)  # users' documents are private
    stop = threading.Event()

    def janitor() -> None:  # hourly: delete contents older than 7 days
        while not stop.wait(0 if not janitor.started else 3600):
            janitor.started = True
            try:
                doc_routes.cleanup()
                doc_routes.cleanup_scans()
            except Exception:  # never crash the API because of cleanup
                log.exception("cleanup failed")

    janitor.started = False
    threading.Thread(target=janitor, daemon=True).start()
    yield
    stop.set()


app = FastAPI(title="Paginya API", lifespan=lifespan)
guard.LIMITS[:] = [
    ("POST", r"/documents", 30, 3600),  # new documents
    ("POST", r"/documents/[^/]+/render", 150, 3600),
    ("POST", r"/documents/[^/]+/before", 30, 3600),
    ("POST", r"/scans", 80, 3600),  # OCR of photos
    ("POST", r"/orders", 30, 3600),
    ("POST", r"/(orders|documents|forms)/[^/]+/pay", 20, 3600),
    ("POST", r"/forms", 40, 3600),
    ("POST", r"/admin/login|/orders/[^/]+/admin", 20, 3600),
]
app.middleware("http")(guard.middleware)  # before CORS: a refusal still carries the CORS headers
app.include_router(doc_routes.router)
app.include_router(doc_routes.scan_router)
app.include_router(forms_routes.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

MEDIA = {
    "pdf": "application/pdf",
    "png": "image/png",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class CoverIn(BaseModel):
    svg: str
    form: dict = Field(default_factory=dict)


class OrderIn(CoverIn):
    product: str = "page_de_garde"


class PayIn(BaseModel):
    phone: str = ""
    return_url: str = ""  # where Fapshi's payment page sends the customer back


def _return_url(url: str) -> str:
    """Only our own sites (a payment page must never redirect elsewhere)."""
    for origin in config.CORS_ORIGINS:
        if origin and url.startswith(origin.rstrip("/") + "/"):
            return url[:500]
    return config.CORS_ORIGINS[0].rstrip("/") + "/paiement/"


def _clean_svg(svg: str) -> str:
    try:
        return sanitize_svg(svg)
    except UnsafeSvg as exc:
        raise HTTPException(400, str(exc)) from exc


def _order_or_404(order_id: str) -> dict:
    order = db.get_order(order_id)
    if order is None:
        raise HTTPException(404, "Document introuvable")
    return order


def _still_editable(order: dict) -> bool:
    if order["status"] != "PAID":
        return True
    return time.time() - order["paid_at"] < config.ORDER_VALIDITY_DAYS * 86400


def _public(order: dict) -> dict:
    return {
        "id": order["id"],
        "product": order["product"],
        "label": pricing.LABELS[order["product"]],
        "amount": order["amount"],
        "status": order["status"],
        "form": order["payload"].get("form", {}),
        "is_document": "doc" in order["payload"] or "form_doc" in order["payload"],
        "editable": _still_editable(order),
    }


@app.get("/health")
def health() -> dict:
    """Also the keep-alive target (cron every few hours): touches the database so Supabase stays awake too."""
    with db.connect() as c:
        c.execute("SELECT 1").fetchone()
    return {"ok": True, "payments": config.FAPSHI_MODE}


@app.get("/prices")
def prices() -> dict:
    return {k: {"label": pricing.LABELS[k], "amount": v} for k, v in pricing.PRICES_XAF.items()}


@app.post("/preview")
def preview(body: CoverIn) -> Response:
    """Server-side render of the watermarked cover (what the paid file will look like)."""
    png = render_cover(_clean_svg(body.svg), "preview", watermark=True)
    return Response(png, media_type="image/png")


@app.post("/orders")
def create_order(body: OrderIn) -> dict:
    try:
        amount = pricing.price_for(body.product)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    order_id = db.create_order(body.product, amount, {"svg": _clean_svg(body.svg), "form": body.form})
    return _public(db.get_order(order_id))


@app.put("/orders/{order_id}")
def update_order(order_id: str, body: CoverIn) -> dict:
    order = _order_or_404(order_id)
    if "doc" in order["payload"]:
        raise HTTPException(400, "Utilise /documents pour modifier un document")
    if order["status"] == "PENDING":
        raise HTTPException(409, "Paiement en cours, réessaie dans un instant")
    if not _still_editable(order):
        raise HTTPException(403, "La période de modification gratuite (7 jours) est terminée")
    db.update_payload(order_id, {"svg": _clean_svg(body.svg), "form": body.form})
    return _public(db.get_order(order_id))


@app.post("/orders/{order_id}/pay")
def pay(order_id: str, body: PayIn) -> dict:
    order = _order_or_404(order_id)
    if order["status"] == "PAID":
        return _public(order)
    if order["status"] == "PENDING":
        raise HTTPException(409, "Un paiement est déjà en attente de confirmation")
    phone = ""
    if body.phone.strip():
        try:
            phone = fapshi.normalize_phone(body.phone)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    try:
        trans_id, link = fapshi.start(
            order["amount"], phone, fapshi.external_id(order_id),
            f"Paginya - {pricing.LABELS[order['product']]}", _return_url(body.return_url),
        )
    except fapshi.FapshiError as exc:
        raise HTTPException(502, f"Le paiement n'a pas pu démarrer : {exc}") from exc
    db.mark_pending(order_id, phone, trans_id)
    return {**_public(db.get_order(order_id)), "pay_link": link}


class AdminLoginIn(BaseModel):
    credential: str = ""  # Google's ID token


class AdminIn(BaseModel):
    token: str = ""  # the pass given by /admin/login


@app.get("/admin/config")
def admin_config() -> dict:
    """What the sign-in page needs: Google's public client id (empty when the team access is off)."""
    return {"client_id": config.GOOGLE_CLIENT_ID if admin.enabled() else ""}


@app.post("/admin/login")
def admin_login(body: AdminLoginIn) -> dict:
    try:
        email = admin.google_email(body.credential)
        return {"token": admin.issue(email), "email": email}
    except admin.AdminError as exc:
        raise HTTPException(403, str(exc)) from exc


@app.post("/orders/{order_id}/admin")
def admin_unlock(order_id: str, body: AdminIn) -> dict:
    """The team does not pay for its own documents: a valid pass unlocks the order as if it were paid."""
    if admin.email_of(body.token) is None:
        raise HTTPException(403, "Connexion équipe expirée : reconnecte-toi")
    _order_or_404(order_id)
    db.grant(order_id)
    return _public(db.get_order(order_id))


def _sync_with_fapshi(order: dict) -> dict:
    """Poll Fapshi for a pending order (the webhook is only sent once)."""
    if order["status"] != "PENDING" or not order["trans_id"]:
        return order
    try:
        tx = fapshi.payment_status(order["trans_id"])
    except fapshi.FapshiError:
        return order
    status = fapshi.STATUS_MAP.get(tx.get("status", ""))
    if status is None:
        return order
    if status == "PAID" and config.FAPSHI_MODE != "mock":
        # Never trust a success that doesn't match the order exactly.
        if not fapshi.matches(tx, order):
            log.error("Payment mismatch for order %s: %s", order["id"], tx)
            return order
    db.settle(order["id"], status)
    return db.get_order(order["id"])


@app.get("/orders/{order_id}")
def get_order(order_id: str) -> dict:
    return _public(_sync_with_fapshi(_order_or_404(order_id)))


@app.post("/orders/{order_id}/retry")
def retry(order_id: str) -> dict:
    """After FAILED/EXPIRED, allow a new payment attempt."""
    order = _order_or_404(order_id)
    if order["status"] in ("FAILED", "EXPIRED"):
        with db.connect() as c:
            c.execute("UPDATE orders SET status = 'DRAFT', trans_id = NULL WHERE id = ?", (order_id,))
    return _public(db.get_order(order_id))


@app.post("/webhooks/fapshi")
async def fapshi_webhook(request: Request) -> dict:
    secret = request.headers.get("x-wh-secret", "")
    if not config.FAPSHI_WEBHOOK_SECRET or not hmac.compare_digest(secret, config.FAPSHI_WEBHOOK_SECRET):
        raise HTTPException(401, "Signature invalide")
    body = await request.json()
    ext = str(body.get("externalId", ""))
    target = fapshi.forward_target(ext)
    if target:  # a payment of another app sharing the Fapshi service
        threading.Thread(target=fapshi.forward, args=(target, body, secret), daemon=True).start()
        return {"ok": True}
    order = db.get_order(fapshi.order_id_of(ext))
    if order is not None:
        # Re-check with Fapshi rather than trusting the body.
        _sync_with_fapshi(order)
    return {"ok": True}


@app.get("/orders/{order_id}/file.{fmt}")
def download(order_id: str, fmt: str) -> Response:
    if fmt not in MEDIA:
        raise HTTPException(404, "Format inconnu")
    order = _sync_with_fapshi(_order_or_404(order_id))
    if order["status"] != "PAID":
        raise HTTPException(402, "Paiement requis pour télécharger sans filigrane")
    if not _still_editable(order):
        raise HTTPException(410, "Lien expiré (7 jours après le paiement)")
    if "form_doc" in order["payload"]:
        path = forms_routes.final_file(order_id, fmt)
        name = "paginya-" + order["payload"]["form_doc"]["kind"]
        return Response(path.read_bytes(), media_type=MEDIA[fmt],
                        headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})
    if "doc" in order["payload"]:
        path = doc_routes.final_file(order_id, fmt)
        return Response(path.read_bytes(), media_type=MEDIA[fmt],
                        headers={"Content-Disposition": f'attachment; filename="paginya-document.{fmt}"'})
    data = render_cover(order["payload"]["svg"], fmt, watermark=False)
    filename = f"paginya-page-de-garde.{fmt}"
    return Response(data, media_type=MEDIA[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


# One address per app in production: the API also serves the static site (web/out) when WEB_DIR is set.
# Mounted last so every API route above keeps priority.
if os.getenv("WEB_DIR"):
    app.mount("/", StaticFiles(directory=os.environ["WEB_DIR"], html=True), name="site")
