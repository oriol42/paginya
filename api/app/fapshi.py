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
    if resp.status_code != 200 or "transId" not in data:
        raise FapshiError(data.get("message", f"Erreur Fapshi ({resp.status_code})"))
    return data["transId"]


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
