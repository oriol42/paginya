"""What Paginya understood about an imported document, shown to the user before anything is changed.

`analyze` turns the detection result (kind, counts) and what the Word file already has (cover, sommaire,
page numbers) into a short report with the reasons ("j'ai reconnu un rapport de stage parce que…") and a
proposed plan, element by element: cover / toc / numbers each "keep", "add", "redo" or "none".
"""
from __future__ import annotations

from .exam_scan import exam_signals
from .render import options_for

KIND_LABELS = {
    "memoire": "un mémoire",
    "rapport_stage": "un rapport de stage",
    "rapport": "un rapport",
    "expose": "un exposé ou un devoir",
    "cours": "un cours",
    "administratif": "une lettre ou un document administratif",
    "document": "un document",
    "epreuve": "une épreuve d'examen",
}
LONG_KINDS = ("memoire", "rapport_stage", "rapport")
PLAN_VALUES = {"cover": {"keep", "redo", "add", "none"}, "toc": {"keep", "redo", "add", "none"}, "numbers": {"keep", "redo", "add", "none"}}


def blocks_text(blocks: list[dict]) -> str:
    return "\n".join(str(b.get("text") or "") for b in blocks if b.get("type") != "figure")


def why(kind: str, meta: dict) -> list[str]:
    """Plain reasons for the recognised kind, from what the detection counted."""
    reasons: list[str] = []
    cover = meta.get("cover") or {}
    label = (cover.get("doc_label") or "").strip()
    if label:
        reasons.append(f"la page de garde indique « {label} »")
    if meta.get("headings", 0) >= 5:
        reasons.append(f"{meta['headings']} titres bien structurés")
    words = meta.get("words", 0)
    if words:
        reasons.append(f"{words:,} mots".replace(",", " "))
    if cover.get("structure") or cover.get("period"):
        reasons.append("un stage effectué dans une structure d'accueil")
    if kind in LONG_KINDS and cover.get("supervisors"):
        reasons.append("un encadreur est cité")
    return reasons[:4]


def default_plan(kind: str, existing: dict | None, options: dict) -> dict:
    """What to do for each element: keep what is there, add what the kind needs and is missing."""
    ex = existing or {}
    plan = {"cover": "none", "toc": "none", "numbers": "none"}
    if ex.get("cover"):
        plan["cover"] = "keep"
    elif options.get("cover"):
        plan["cover"] = "add"
    if ex.get("toc"):
        plan["toc"] = "keep"
    elif (options.get("toc") or ex.get("toc_title")) and (ex.get("titles", 0) >= 3 or not ex):
        plan["toc"] = "add"  # asked by the kind of document, or by a "Sommaire" page left empty
    if ex.get("page_numbers"):
        plan["numbers"] = "keep"
    elif options.get("page_numbers"):
        plan["numbers"] = "add"
    return plan


def numbers_hint(kind: str, existing: dict | None) -> str:
    """A suggestion, never an order: the numbering the file has does not follow the usual convention."""
    ex = existing or {}
    if not ex.get("page_numbers"):
        return ""
    scheme = ex.get("numbering")
    if ex.get("numbers_on_cover"):
        return "Ta page de garde porte un numéro : en général elle est comptée mais sans numéro affiché."
    if scheme == "arabic" and ex.get("cover") and ex.get("intro") and kind in LONG_KINDS:
        return "Tes pages sont en chiffres arabes partout. Dans les mémoires et rapports camerounais, les pages avant l'introduction sont en chiffres romains (i, ii, iii…)."
    return ""


def analyze(kind: str, meta: dict, blocks: list[dict], options: dict, existing: dict | None, is_docx: bool) -> dict:
    exam = exam_signals(blocks_text(blocks))
    shown = "epreuve" if exam["likely"] else kind
    return {
        "kind": shown,
        "kind_label": KIND_LABELS.get(shown, "un document"),
        "detected_kind": kind,
        "why": exam["reasons"][:4] if exam["likely"] else why(kind, meta),
        "exam": exam["likely"],
        "docx": is_docx,
        "existing": existing,
        "plan": default_plan(kind, existing, options),
        "hint": numbers_hint(kind, existing),
    }


def clean_plan(plan: dict | None, current: dict) -> dict:
    out = dict(current)
    for key, allowed in PLAN_VALUES.items():
        if plan and plan.get(key) in allowed:
            out[key] = plan[key]
    return out


__all__ = ["analyze", "clean_plan", "default_plan", "options_for", "KIND_LABELS"]
