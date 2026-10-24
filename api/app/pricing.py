"""Prices are always computed server-side (never trusted from the browser).

One price for any single document, whatever its kind or length (no account needed), or a 30-day pass on a
Google account with a daily limit. Passes never renew by themselves: the customer pays again each time.
"""

DOCUMENT_PRICE = 550

# product -> label; every document costs DOCUMENT_PRICE (the kind is kept for the receipt and the stats)
DOCUMENTS = {
    "page_de_garde": "Page de garde",
    "lettre": "Lettre / demande",
    "epreuve": "Épreuve",
    "cv": "CV",
    "document_court": "Document",
    "rapport": "Rapport / exposé",
    "memoire": "Mémoire",
}

# plan -> price, documents per day, label. "pass_30j" is the 5 000 F pass sold before the plans: it is Pro.
PLANS = {
    "essentiel": {"amount": 3000, "per_day": 5, "label": "Pass Essentiel 30 jours"},
    "pro": {"amount": 5000, "per_day": 40, "label": "Pass Pro 30 jours"},
}
PASS_DAYS = 30

PRICES_XAF = {**{k: DOCUMENT_PRICE for k in DOCUMENTS}, **{f"pass_{k}": p["amount"] for k, p in PLANS.items()}, "pass_30j": PLANS["pro"]["amount"]}
LABELS = {**DOCUMENTS, **{f"pass_{k}": p["label"] for k, p in PLANS.items()}, "pass_30j": PLANS["pro"]["label"]}


def price_for(product: str) -> int:
    if product not in PRICES_XAF:
        raise ValueError(f"Produit inconnu : {product}")
    return PRICES_XAF[product]


def plan_of(account: dict) -> str:
    """The plan of an account's current pass ('' for a pass bought before the plans: it was the Pro price)."""
    return account.get("plan") or "pro"
