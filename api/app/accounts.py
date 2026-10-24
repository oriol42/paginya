"""Customer accounts: a Google sign-in, needed only for the 30-day passes (never lost with the phone).

The browser keeps a signed token (no password, nothing secret typed). A pass (Essentiel or Pro) unlocks a
number of documents per day and never renews by itself. An account whose e-mail is in ADMIN_EMAILS is the
team's: every document is unlocked without paying, without limit.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from . import admin, config, db, pricing

router = APIRouter()
TOKEN_DAYS = 180


def enabled() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.ACCOUNT_SECRET)


def _sign(text: str) -> str:
    return hmac.new(config.ACCOUNT_SECRET.encode(), f"account|{text}".encode(), hashlib.sha256).hexdigest()


def issue(sub: str, now: float | None = None) -> str:
    body = f"{sub}|{int((now or time.time()) + TOKEN_DAYS * 86400)}"
    return base64.urlsafe_b64encode(f"{body}|{_sign(body)}".encode()).decode()


def account_of(token: str, now: float | None = None) -> dict | None:
    """The account behind a token, or None (forged, expired, or accounts off)."""
    if not enabled() or not token:
        return None
    try:
        sub, expiry, signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
        fresh = int(expiry) > (now or time.time())
    except (ValueError, UnicodeDecodeError):
        return None
    if not fresh or not hmac.compare_digest(signature, _sign(f"{sub}|{expiry}")):
        return None
    return db.get_account(sub)


def is_team(account: dict) -> bool:
    return account["email"].lower() in config.ADMIN_EMAILS


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}" if domain else ""


def has_pass(account: dict) -> bool:
    return account["pass_until"] > time.time()


def view(account: dict) -> dict:
    now = time.time()
    active = has_pass(account)
    plan = pricing.plan_of(account) if active else ""
    return {
        "email": _mask(account["email"]),
        "team": is_team(account),
        "pass_until": account["pass_until"] if active else 0,
        "pass_days": max(0, -(-int(account["pass_until"] - now) // 86400)),
        "plan": plan,
        "per_day": pricing.PLANS[plan]["per_day"] if plan else 0,
        "used_today": db.unlocked_today(account["sub"]) if active else 0,
    }


def _account_or_401(token: str) -> dict:
    account = account_of(token)
    if account is None:
        raise HTTPException(401, "Reconnecte-toi avec Google")
    return account


class GoogleIn(BaseModel):
    credential: str = Field(max_length=4000)


class TokenIn(BaseModel):
    token: str = Field(max_length=600)


class PassIn(TokenIn):
    plan: str = "essentiel"


@router.get("/account/config")
def account_config() -> dict:
    return {"client_id": config.GOOGLE_CLIENT_ID if enabled() else ""}


@router.post("/account/google")
def google_login(body: GoogleIn) -> dict:
    if not enabled():
        raise HTTPException(503, "Connexion Google pas encore activée")
    try:
        sub, email = admin.google_identity(body.credential)
    except admin.AdminError as exc:
        raise HTTPException(401, str(exc)) from exc
    return {**view(db.save_account(sub, email)), "token": issue(sub)}


@router.post("/account/me")
def me(body: TokenIn) -> dict:
    return view(_account_or_401(body.token))


@router.post("/account/pass")
def buy_pass(body: PassIn) -> dict:
    """An order for a pass, paid like any other (/orders/{id}/pay); once PAID the account gets 30 days."""
    account = _account_or_401(body.token)
    if body.plan not in pricing.PLANS:
        raise HTTPException(400, "Formule inconnue")
    product = f"pass_{body.plan}"
    order_id = db.create_order(product, pricing.price_for(product), {"pass_for": account["sub"], "plan": body.plan})
    order = db.get_order(order_id)
    return {"id": order_id, "status": order["status"], "amount": order["amount"]}


@router.post("/orders/{order_id}/unlock")
def unlock(order_id: str, body: TokenIn) -> dict:
    """A document is free for a team account, or for an active pass within its daily limit."""
    account = _account_or_401(body.token)
    order = db.get_order(order_id)
    if order is None or "pass_for" in order["payload"]:
        raise HTTPException(404, "Document introuvable")
    if order["status"] == "PAID":
        pass  # already unlocked: downloading it again never counts
    elif is_team(account):
        db.grant(order_id, f"team:{account['email']}")
    elif has_pass(account):
        plan = pricing.PLANS[pricing.plan_of(account)]
        if plan["per_day"] and db.unlocked_today(account["sub"]) >= plan["per_day"]:
            raise HTTPException(429, f"Tu as utilisé tes {plan['per_day']} documents du jour. Ça repart à minuit, ou paie celui-ci à part.")
        db.grant(order_id, f"pass:{account['sub']}")
    else:
        raise HTTPException(402, "Pas de pass en cours")
    return {"id": order_id, "status": db.get_order(order_id)["status"]}
