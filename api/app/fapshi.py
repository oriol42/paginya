"""Fapshi direct-pay client (https://docs.fapshi.com).

- direct-pay sends a confirmation request to the customer's phone.
  It is disabled by default in live mode: Fapshi must activate it.
- The webhook is sent only once, so we also poll payment-status.
- mock mode lets the whole flow run locally without keys:
  numbers ending in 0 succeed, numbers ending in 1 fail (like Fapshi sandbox test numbers).
"""
import time
import uuid

import httpx

from . import config

# Fapshi statuses -> our order statuses
STATUS_MAP = {"SUCCESSFUL": "PAID", "FAILED": "FAILED", "EXPIRED": "EXPIRED"}

_mock_started: dict[str, tuple[float, str]] = {}
MOCK_DELAY_S = 6


class FapshiError(RuntimeError):
    pass


class DirectPayDisabled(FapshiError):
    """Fapshi answers 403 until it approves direct-pay for the service."""


def external_id(order_id: str) -> str:
    """What Fapshi stores for an order: the app prefix tells whose payment it is in a shared service."""
    return f"{config.FAPSHI_PREFIX}-{order_id}" if config.FAPSHI_PREFIX else order_id


def order_id_of(ext: str) -> str:
    """Order id from a Fapshi externalId (with or without the app prefix)."""
    head, sep, rest = ext.partition("-")
    return rest if sep and head == config.FAPSHI_PREFIX else ext


def matches(tx: dict, order: dict) -> bool:
    """A success counts only if it is exactly this order (amount and id, prefixed or not)."""
    return tx.get("amount") == order["amount"] and tx.get("externalId") in (external_id(order["id"]), order["id"])


def forward_target(ext: str) -> str | None:
    """Webhook address of the app a payment belongs to, when it is not us."""
    head, sep, _ = ext.partition("-")
    if sep and head != config.FAPSHI_PREFIX:
        return config.FAPSHI_FORWARD.get(head)
    return None


def forward(url: str, body: dict, secret: str) -> None:
    try:
        httpx.post(url, json=body, headers={"x-wh-secret": secret}, timeout=20)
    except httpx.HTTPError:
        pass  # the other app also polls Fapshi: nothing is lost


def _headers() -> dict:
    return {"apiuser": config.FAPSHI_API_USER, "apikey": config.FAPSHI_API_KEY}


def normalize_phone(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if digits.startswith("237") and len(digits) == 12:
        digits = digits[3:]
    if len(digits) != 9 or not digits.startswith("6"):
        raise ValueError("Numéro invalide : 9 chiffres commençant par 6 (ex. 670000000)")
    return digits


def direct_pay(amount: int, phone: str, external_id: str, message: str) -> str:
    """Start a payment; returns Fapshi's transId."""
    if config.FAPSHI_MODE == "mock":
        trans_id = "mock_" + uuid.uuid4().hex[:12]
        outcome = "FAILED" if phone.endswith("1") else "SUCCESSFUL"
        _mock_started[trans_id] = (time.time(), outcome)
        return trans_id
    resp = httpx.post(
        f"{config.FAPSHI_BASE_URL}/direct-pay",
        headers=_headers(),
        json={"amount": amount, "phone": phone, "externalId": external_id, "message": message},
        timeout=30,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code == 403:
        raise DirectPayDisabled(data.get("message", "direct-pay non activé"))
    if resp.status_code != 200 or "transId" not in data:
        raise FapshiError(data.get("message", f"Erreur Fapshi ({resp.status_code})"))
    return data["transId"]


def initiate_pay(amount: int, external_id: str, message: str, redirect_url: str) -> tuple[str, str]:
    """Payment page hosted by Fapshi (MoMo / Orange Money). Returns (transId, link)."""
    if config.FAPSHI_MODE == "mock":
        trans_id = "mock_" + uuid.uuid4().hex[:12]
        _mock_started[trans_id] = (time.time(), "SUCCESSFUL")
        return trans_id, redirect_url
    resp = httpx.post(
        f"{config.FAPSHI_BASE_URL}/initiate-pay",
        headers=_headers(),
        json={"amount": amount, "externalId": external_id, "message": message, "redirectUrl": redirect_url},
        timeout=30,
    )
    data = resp.json() if resp.content else {}
    if resp.status_code != 200 or "link" not in data:
        raise FapshiError(data.get("message", f"Erreur Fapshi ({resp.status_code})"))
    return data["transId"], data["link"]


def start(amount: int, phone: str, external_id: str, message: str, redirect_url: str) -> tuple[str, str | None]:
    """Starts a payment the best available way. Returns (transId, payment page link or None)."""
    if config.FAPSHI_PAY_METHOD != "link" and phone:
        try:
            return direct_pay(amount, phone, external_id, message), None
        except DirectPayDisabled:
            if config.FAPSHI_PAY_METHOD == "direct":
                raise
    return initiate_pay(amount, external_id, message, redirect_url)


def payment_status(trans_id: str) -> dict:
    """Returns Fapshi's transaction object (status, amount, externalId, ...)."""
    if config.FAPSHI_MODE == "mock":
        started, outcome = _mock_started.get(trans_id, (0.0, "EXPIRED"))
        status = outcome if time.time() - started >= MOCK_DELAY_S else "PENDING"
        return {"transId": trans_id, "status": status}
    resp = httpx.get(f"{config.FAPSHI_BASE_URL}/payment-status/{trans_id}", headers=_headers(), timeout=30)
    if resp.status_code != 200:
        raise FapshiError(f"Statut indisponible ({resp.status_code})")
    return resp.json()
