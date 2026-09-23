"""Accuracy of structure detection on synthetic messy documents (rules alone, or rules + model)."""
from __future__ import annotations

import sys
from collections import Counter

import numpy as np

from app.doc.detect import detect
from ml.synth import CAPTION, H1, LIST, NAMES, PARA, TOC, sample


def label_of(it: dict | None) -> int:
    if it is None:
        return PARA  # merged into a table etc.
    t = it.get("type")
    if t == "toc":
        return TOC
    if t == "heading":
        return H1 + min(max(int(it.get("level", 1)), 1), 4) - 1
    if t == "list":
        return LIST
    if t == "caption":
        return CAPTION
    return PARA


def predict_rules(raws, refine: bool = False) -> list[int]:
    tr = detect(raws, trace=True, refine=refine)["trace"]
    return [label_of(tr.get(i)) for i in range(len(raws))]


def report(y: np.ndarray, p: np.ndarray, title: str, by_mode: dict | None = None) -> dict:
    head_t = (y >= 1) & (y <= 4)
    head_p = (p >= 1) & (p <= 4)
    tp = (head_t & head_p).sum()
    prec, rec = tp / max(head_p.sum(), 1), tp / max(head_t.sum(), 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    lvl = (p[head_t] == y[head_t]).mean()
    acc = (p == y).mean()
    print(f"{title:28} exactitude {acc:6.1%} | titres F1 {f1:6.1%} (précision {prec:5.1%}, rappel {rec:5.1%}) | bon niveau {lvl:6.1%}")
    if by_mode:
        for mode, (yy, pp) in sorted(by_mode.items()):
            print(f"   {mode:8} exactitude {(yy == pp).mean():6.1%}  ({len(yy)} paragraphes)")
    return {"acc": acc, "f1": f1, "level": lvl}


def confusion(y, p):
    c = Counter(zip(y.tolist(), p.tolist()))
    print("vrai → prédit (erreurs les plus fréquentes)")
    for (a, b), n in c.most_common(40):
        if a != b:
            print(f"   {NAMES[a]:10} → {NAMES[b]:10} {n}")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    ys, ps, modes = [], [], {}
    for seed in range(100_000, 100_000 + n):
        s = sample(seed)
        if s is None:
            continue
        raws, labels, h = s
        pr = predict_rules(raws)
        ys += labels
        ps += pr
        a, b = modes.setdefault(h.mode, ([], []))
        a += labels
        b += pr
    y, p = np.array(ys), np.array(ps)
    report(y, p, "Règles actuelles", {k: (np.array(a), np.array(b)) for k, (a, b) in modes.items()})
    confusion(y, p)
