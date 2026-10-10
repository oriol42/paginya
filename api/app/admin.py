"""The team's own documents are free: an admin signs in with Google, the server checks who it is.

Nothing secret is typed or kept in the site. Google proves the e-mail address (ID token, checked with
Google itself), the server only lets the addresses listed in ADMIN_EMAILS through, then hands the
browser a signed pass valid for 30 days. Unset GOOGLE_CLIENT_ID / ADMIN_EMAILS / ADMIN_SECRET = off.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time

import httpx

from . import config

PASS_DAYS = 30
TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


class AdminError(Exception):
    pass


def enabled() -> bool:
    return bool(config.GOOGLE_CLIENT_ID and config.ADMIN_EMAILS and config.ADMIN_SECRET)


def google_email(credential: str) -> str:
    """The verified e-mail behind a Google ID token. Google checks the signature and the expiry."""
    try:
        res = httpx.get(TOKENINFO, params={"id_token": credential}, timeout=10)
    except httpx.HTTPError as exc:
        raise AdminError("Google ne répond pas, réessaie") from exc
    info = res.json() if res.status_code == 200 else {}
    if info.get("aud") != config.GOOGLE_CLIENT_ID or info.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise AdminError("Connexion Google refusée")
    if str(info.get("email_verified")).lower() != "true" or not info.get("email"):
        raise AdminError("Adresse Google non vérifiée")
    return str(info["email"]).lower()


def _sign(text: str) -> str:
    return hmac.new(config.ADMIN_SECRET.encode(), text.encode(), hashlib.sha256).hexdigest()


def issue(email: str, now: float | None = None) -> str:
    """A pass for this address: "<email>|<expiry>|<signature>", base64."""
    if not enabled() or email.lower() not in config.ADMIN_EMAILS:
        raise AdminError("Ce compte n'est pas un compte de l'équipe")
    body = f"{email.lower()}|{int((now or time.time()) + PASS_DAYS * 86400)}"
    return base64.urlsafe_b64encode(f"{body}|{_sign(body)}".encode()).decode()


def email_of(token: str, now: float | None = None) -> str | None:
    """The admin behind a pass, or None (forged, expired, or no longer on the list)."""
    if not enabled() or not token:
        return None
    try:
        email, expiry, signature = base64.urlsafe_b64decode(token.encode()).decode().rsplit("|", 2)
        fresh = int(expiry) > (now or time.time())
    except (ValueError, UnicodeDecodeError):
        return None
    if not fresh or not hmac.compare_digest(signature, _sign(f"{email}|{expiry}")) or email not in config.ADMIN_EMAILS:
        return None
    return email
