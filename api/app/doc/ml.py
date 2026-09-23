"""Learned correction of the structure rules (small neural network, numpy only, no GPU, <1 ms/doc).

The rules decide first. The model sees each paragraph's formatting, its neighbours, the whole
document's habits AND the rules' decision, and only overrides when it is confident. It was trained
on synthetic "badly formatted" documents built from well-structured ones (see ml/synth.py, ml/train.py).
"""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np

from .extract import Raw

MODEL_PATH = Path(__file__).with_name("structure_model.npz")

# classes (same order as ml/synth.py)
PARA, H1, H2, H3, H4, LIST, CAPTION, TOC = range(8)

KINDS = ["partie", "chapitre", "style1", "roman", "upper", "style2", "letter", "dec1", "big", "bold",
         "style3", "dec2", "short", "style4", "dec3", "dec4", "special"]
TYPES = ["heading", "list", "caption", "paragraph", "toc"]

_R = {
    "decimal": re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s+\S"),
    "num": re.compile(r"^\d{1,2}\s*[.)°]\s+\S"),
    "nodot": re.compile(r"^\d{1,2}\s+[A-ZÀ-Ý]"),
    "roman": re.compile(r"^[IVX]{1,5}\s*[.\-–—)/]\s*\S"),
    "letter": re.compile(r"^[A-H]\s*[.\-–—)/]\s+\S"),
    "lower": re.compile(r"^[a-z]\s*[.)]\s+\S"),
    "bullet": re.compile(r"^\s*([-–—•*➢►▪▫◦✓✔→>§]|o(?=\s))\s*\S"),
    "caption": re.compile(r"^(tableau|table|tab\.|figure|fig\.?|graphique|graph\.|photo|sch[ée]ma|carte|diagramme)\s*(n\s*[°o]\s*)?\d", re.I),
    "partie": re.compile(r"^((premi|deuxi|troisi|quatri)[eè]\w*\s+partie|partie\s+\w+)", re.I),
    "chapitre": re.compile(r"^(chapitre|chapter)\s+\w+", re.I),
    "colon_end": re.compile(r":\s*$"),
    "sentence_end": re.compile(r"[.;!?]\s*$"),
}


def _upper(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return sum(c.isupper() for c in letters) / len(letters) if len(letters) >= 3 else 0.0


def _own(r: Raw, base: float) -> list[float]:
    t = r.text.strip()
    style_lvl = 0
    m = re.match(r"^(heading|titre|title)\s*(\d)?$", r.style)
    if m:
        style_lvl = int(m.group(2) or 1)
    words = len(t.split())
    return [
        math.log1p(len(t)) / 7, min(words, 60) / 60, float(r.bold), max(-4.0, min(10.0, (r.size - base) if r.size and base else 0.0)) / 6,
        float(r.centered), min(r.indent, 3) / 3, float(r.list_kind == "bullet"), float(r.list_kind == "number"),
        *[float(style_lvl == k) for k in range(5)], float(r.source == "docx"),
        _upper(t), float(t[:1].isupper()), float(bool(_R["sentence_end"].search(t))), float(bool(_R["colon_end"].search(t))),
        *[float(bool(_R[k].search(t))) for k in ("decimal", "num", "nodot", "roman", "letter", "lower", "bullet", "caption", "partie", "chapitre")],
        (t.split()[0].count(".") if _R["decimal"].search(t) else 0) / 3,
        float(len(t) <= 90 and not _R["sentence_end"].search(t)),
    ]


def _rules(it: dict | None) -> list[float]:
    it = it or {"type": "paragraph"}
    t = it.get("type", "paragraph")
    lvl = int(it.get("level", 0) or 0) if t == "heading" else 0
    return [*[float(t == k) for k in TYPES], *[float(lvl == k) for k in range(1, 5)], *[float(it.get("kind") == k) for k in KINDS]]


def features(raws: list[Raw], trace: dict[int, dict], base: float) -> np.ndarray:
    n = len(raws)
    own = [_own(r, base) for r in raws]
    rules = [_rules(trace.get(i)) for i in range(n)]
    sizes = sorted({round(r.size) for r in raws if r.size and base and r.size > base + 0.5}, reverse=True)
    doc = [
        sum(r.bold for r in raws) / max(n, 1),
        sum(bool(re.match(r"^(heading|titre)", r.style)) for r in raws) / max(n, 1),
        float(any(_R["partie"].search(r.text) for r in raws)),
        len(sizes) / 4,
    ]
    empty_own = [0.0] * len(own[0]) if own else []
    empty_rules = [0.0] * len(rules[0]) if rules else []
    rows = []
    last_heading_level = 0
    for i, r in enumerate(raws):
        prev_o = own[i - 1] if i > 0 else empty_own
        next_o = own[i + 1] if i + 1 < n else empty_own
        prev_r = rules[i - 1] if i > 0 else empty_rules
        next_r = rules[i + 1] if i + 1 < n else empty_rules
        size_rank = (sizes.index(round(r.size)) + 1) / 4 if r.size and round(r.size) in sizes else 0.0
        rows.append([*own[i], *rules[i], *prev_o, *prev_r, *next_o, *next_r,
                     math.log1p(len(raws[i + 2].text)) / 7 if i + 2 < n else 0.0,
                     size_rank, last_heading_level / 4, i / max(n, 1), *doc])
        it = trace.get(i)
        if it and it.get("type") == "heading":
            last_heading_level = int(it.get("level", 1) or 1)
    return np.asarray(rows, dtype=np.float32)


class Model:
    """Tiny MLP: standardise → ReLU(96) → ReLU(48) → softmax(8)."""

    def __init__(self, params: dict[str, np.ndarray]):
        self.p = params

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "Model | None":
        if not path.exists():
            return None
        with np.load(path) as z:
            return cls({k: z[k] for k in z.files})

    def proba(self, x: np.ndarray) -> np.ndarray:
        p = self.p
        h = (x - p["mu"]) / p["sd"]
        h = np.maximum(h @ p["W1"] + p["b1"], 0)
        h = np.maximum(h @ p["W2"] + p["b2"], 0)
        z = h @ p["W3"] + p["b3"]
        z -= z.max(axis=1, keepdims=True)
        e = np.exp(z)
        return e / e.sum(axis=1, keepdims=True)


_model: Model | None | bool = False


def model() -> Model | None:
    global _model
    if _model is False:
        _model = Model.load()
    return _model  # type: ignore[return-value]


def refine(raws: list[Raw], trace: dict[int, dict], base: float, threshold: float = 0.9) -> int:
    """Corrects the rules' items in place where the model is confident. Returns the number of changes."""
    m = model()
    if m is None or not raws:
        return 0
    pr = m.proba(features(raws, trace, base))
    changed = 0
    for i, it in trace.items():
        if it.get("type") in ("toc", "table", "figure") or it.get("kind") in ("special", "partie", "chapitre"):
            continue  # certain by construction
        if it.get("type") == "list" and (raws[i].list_kind or _R["bullet"].search(raws[i].text)):
            continue  # a bullet is a bullet: never promoted to a heading
        k = int(pr[i].argmax())
        if pr[i, k] < threshold:
            continue
        t = it.get("type")
        if H1 <= k <= H4:
            lvl = k - H1 + 1
            if t != "heading" or it.get("level") != lvl:
                if t != "heading":
                    it.pop("ordered", None)
                    if it.get("_full"):
                        it["text"] = it.pop("_full")  # "2. Le cadre conceptuel" keeps its number
                    it["type"] = "heading"
                    it["kind"] = "ml"
                it["level"] = lvl
                changed += 1
        elif k == PARA and t in ("heading", "list") and it.get("kind") not in ("style1", "style2", "style3", "style4"):
            it["type"] = "paragraph"
            it.pop("level", None)
            it.pop("kind", None)
            it.pop("ordered", None)
            changed += 1
    return changed
