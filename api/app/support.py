"""Support: a customer writes from the site, both team members see the same inbox and answer from it.

The customer keeps a secret link to the conversation (and finds it on their account when signed in), and
leaves a WhatsApp number or an e-mail so the team can also answer outside the site. Each new message rings
the team's phones through ntfy (free app, no account: subscribe to SUPPORT_NTFY_TOPIC); the notification
carries no content, only a link to the inbox.
"""
from __future__ import annotations

import logging
import threading

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import accounts, admin, config, db, pricing

log = logging.getLogger("propre")
router = APIRouter()
STATUSES = ("NEW", "ANSWERED", "CLOSED")


def notify(title: str, text: str) -> None:
    """Rings the team's phones (in the background: a slow ntfy never delays the customer)."""
    if not config.SUPPORT_NTFY_TOPIC:
        return

    def send() -> None:
        try:
            httpx.post(f"https://ntfy.sh/{config.SUPPORT_NTFY_TOPIC}", content=text.encode(), timeout=10,
                       params={"title": title, "tags": "speech_balloon", "click": f"{config.WEB_URL}/coulisses/"})
        except httpx.HTTPError:
            log.warning("ntfy unreachable")

    threading.Thread(target=send, daemon=True).start()


def _customer_view(t: dict) -> dict:
    return {
        "id": t["id"],
        "status": t["status"],
        "created_at": t["created_at"],
        "messages": [{"from": "toi" if m["author"] == "client" else "paginya", "body": m["body"], "ts": m["ts"]} for m in t["messages"]],
    }


def _ticket_or_404(ticket_id: str) -> dict:
    t = db.get_ticket(ticket_id) if len(ticket_id) == 32 else None
    if t is None:
        raise HTTPException(404, "Conversation introuvable")
    return t


class TicketIn(BaseModel):
    message: str = Field(min_length=3, max_length=3000)
    name: str = Field(default="", max_length=80)
    contact: str = Field(default="", max_length=120)
    order_id: str = Field(default="", max_length=40)
    token: str = Field(default="", max_length=600)


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=3000)


@router.post("/support")
def create(body: TicketIn) -> dict:
    account = accounts.account_of(body.token)
    contact = body.contact.strip() or (account["email"] if account else "")
    if not contact:
        raise HTTPException(400, "Laisse ton numéro WhatsApp ou ton e-mail pour qu'on puisse te répondre")
    order_id = body.order_id.strip() if db.get_order(body.order_id.strip()) else None
    ticket_id = db.create_ticket(account["sub"] if account else None, body.name.strip(), contact, order_id, body.message.strip())
    notify("Paginya : nouveau message", f"{body.name.strip() or 'Un client'} a écrit au support.")
    return _customer_view(db.get_ticket(ticket_id))


@router.get("/support/{ticket_id}")
def read(ticket_id: str) -> dict:
    return _customer_view(_ticket_or_404(ticket_id))


@router.post("/support/{ticket_id}/messages")
def answer(ticket_id: str, body: MessageIn) -> dict:
    t = _ticket_or_404(ticket_id)
    db.add_message(ticket_id, "client", body.message.strip())
    notify("Paginya : le client a répondu", f"{t['name'] or 'Un client'} a répondu au support.")
    return _customer_view(db.get_ticket(ticket_id))


@router.post("/account/tickets")
def my_tickets(body: accounts.TokenIn) -> list[dict]:
    account = accounts._account_or_401(body.token)
    return [{"id": t["id"], "status": t["status"], "updated_at": t["updated_at"], "last": t["last"][:140]}
            for t in db.list_tickets(account["sub"], limit=30)]


# ------------------------------------------------------------------ the team's side

class AdminIn(BaseModel):
    token: str = Field(default="", max_length=600)


class ReplyIn(AdminIn):
    message: str = Field(min_length=1, max_length=3000)


class StatusIn(AdminIn):
    status: str


class GiftIn(AdminIn):
    email: str = Field(max_length=200)
    plan: str = "essentiel"
    days: int = Field(default=30, ge=1, le=366)


def _team_or_403(token: str) -> str:
    email = admin.email_of(token)
    if email is None:
        raise HTTPException(403, "Connexion équipe expirée : reconnecte-toi")
    return email


@router.post("/admin/support")
def inbox(body: AdminIn) -> dict:
    _team_or_403(body.token)
    tickets = db.list_tickets()
    return {
        "waiting": sum(t["status"] == "NEW" for t in tickets),
        "tickets": [{"id": t["id"], "name": t["name"], "status": t["status"], "updated_at": t["updated_at"],
                     "last": (t["last"] or "")[:160], "last_author": t["last_author"]} for t in tickets],
    }


@router.post("/admin/support/{ticket_id}")
def thread(ticket_id: str, body: AdminIn) -> dict:
    """Everything needed to solve it: the conversation, the order and the customer's pass."""
    _team_or_403(body.token)
    t = _ticket_or_404(ticket_id)
    order = db.get_order(t["order_id"]) if t["order_id"] else None
    account = db.get_account(t["sub"]) if t["sub"] else None
    return {
        **{k: t[k] for k in ("id", "name", "contact", "status", "created_at", "order_id")},
        "messages": t["messages"],
        "order": order and {k: order[k] for k in ("id", "product", "amount", "status", "phone", "trans_id", "created_at", "paid_at")},
        "account": account and {"email": account["email"], **{k: v for k, v in accounts.view(account).items() if k != "email"}},
    }


@router.post("/admin/support/{ticket_id}/reply")
def reply(ticket_id: str, body: ReplyIn) -> dict:
    email = _team_or_403(body.token)
    _ticket_or_404(ticket_id)
    db.add_message(ticket_id, email, body.message.strip())
    return thread(ticket_id, AdminIn(token=body.token))


@router.post("/admin/support/{ticket_id}/status")
def status(ticket_id: str, body: StatusIn) -> dict:
    _team_or_403(body.token)
    _ticket_or_404(ticket_id)
    if body.status not in STATUSES:
        raise HTTPException(400, "Statut inconnu")
    db.set_ticket_status(ticket_id, body.status)
    return thread(ticket_id, AdminIn(token=body.token))


@router.post("/admin/gift")
def gift(body: GiftIn) -> dict:
    """Offers pass days to a customer (a payment that went wrong…). They must have signed in once."""
    _team_or_403(body.token)
    if body.plan not in pricing.PLANS:
        raise HTTPException(400, "Formule inconnue")
    account = db.account_by_email(body.email.strip())
    if account is None:
        raise HTTPException(404, "Aucun compte avec cette adresse : le client doit se connecter une fois avec Google")
    db.give_pass(account["sub"], body.plan, body.days)
    return {"email": account["email"], **{k: v for k, v in accounts.view(db.get_account(account["sub"])).items() if k != "email"}}
