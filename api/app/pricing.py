"""Prices are always computed server-side (never trusted from the browser)."""

PRICES_XAF = {
    "page_de_garde": 350,
    "lettre": 350,
    "epreuve": 550,
    "cv": 550,
    "document_court": 1000,
    "rapport": 2000,
    "memoire": 3000,
    "pass_30j": 5000,
}

LABELS = {
    "page_de_garde": "Page de garde",
    "lettre": "Lettre / demande",
    "epreuve": "Épreuve",
    "cv": "CV",
    "document_court": "Document (≤ 15 pages)",
    "rapport": "Rapport / exposé",
    "memoire": "Mémoire",
    "pass_30j": "Pass 30 jours",
}


def price_for(product: str) -> int:
    if product not in PRICES_XAF:
        raise ValueError(f"Produit inconnu : {product}")
    return PRICES_XAF[product]
