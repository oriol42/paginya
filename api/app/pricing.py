"""Prices are always computed server-side (never trusted from the browser).

One price for any single document, whatever its kind or length (no account needed), or a 30-day unlimited
pass on a Google account (companies, print shops). Passes never renew by themselves: the customer pays again each time.
Since 22/11/2026: 100 F a document, 2 000 F the Pro pass. Fapshi's smallest payment is 100 F.
"""

DOCUMENT_PRICE = 100

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

# plan -> price, documents per day (0 = unlimited), label, still sold. "pass_30j" is the pass sold before the plans: it is Pro.
# Essentiel (3 000 F, 10 a day) is no longer sold since a document costs 100 F: the passes already bought keep working
# until they end, and their days are converted at their value if the customer moves to Pro (db._extend_pass).
PLANS = {
    "essentiel": {"amount": 3000, "per_day": 10, "label": "Pass Essentiel 30 jours", "sold": False},
    "pro": {"amount": 2000, "per_day": 0, "label": "Pass Pro 30 jours", "sold": True},
}
SOLD_PLANS = [k for k, p in PLANS.items() if p["sold"]]
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
