"""Train the structure model on synthetic messy documents and compare with the rules.

    .venv/bin/python -m ml.train 2500        # docs for training (validation: 300 other seeds)

Writes app/doc/structure_model.npz only if rules + model beat the rules alone on validation.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

from app.doc.detect import detect
from app.doc.extract import body_size
from app.doc.ml import MODEL_PATH, Model, features
from ml.evaluate import label_of, report
from ml.synth import sample  # noqa: F401  (reloaded for the generalisation check)


def dataset(seeds: range) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, int]]]:
    xs, ys, rs, spans = [], [], [], []
    k = 0
    for seed in seeds:
        s = globals()["sample"](seed)
        if s is None:
            continue
        raws, labels, _ = s
        tr = detect(raws, trace=True, refine=False)["trace"]
        xs.append(features(raws, tr, body_size(raws)))
        ys.append(np.array(labels))
        rs.append(np.array([label_of(tr.get(i)) for i in range(len(raws))]))
        spans.append((k, k + len(raws)))
        k += len(raws)
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(rs), spans


def train(x: np.ndarray, y: np.ndarray, epochs: int = 40, seed: int = 0) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    mu, sd = x.mean(0), x.std(0) + 1e-6
    xs = (x - mu) / sd
    d, h1, h2, c = xs.shape[1], 96, 48, 8
    p = {
        "W1": rng.normal(0, np.sqrt(2 / d), (d, h1)).astype(np.float32), "b1": np.zeros(h1, np.float32),
        "W2": rng.normal(0, np.sqrt(2 / h1), (h1, h2)).astype(np.float32), "b2": np.zeros(h2, np.float32),
        "W3": rng.normal(0, np.sqrt(2 / h2), (h2, c)).astype(np.float32), "b3": np.zeros(c, np.float32),
    }
    # class weights: rare classes (titles 4, captions) matter as much as paragraphs
    counts = np.bincount(y, minlength=c).astype(np.float32)
    cw = (counts.sum() / (c * np.maximum(counts, 1))) ** 0.5
    m = {k: np.zeros_like(v) for k, v in p.items()}
    v = {k: np.zeros_like(v) for k, v in p.items()}
    lr, b1, b2, eps, t = 2e-3, 0.9, 0.999, 1e-8, 0
    n = len(xs)
    for ep in range(epochs):
        idx = rng.permutation(n)
        loss = 0.0
        for s in range(0, n, 512):
            bi = idx[s:s + 512]
            xb, yb = xs[bi], y[bi]
            z1 = xb @ p["W1"] + p["b1"]; a1 = np.maximum(z1, 0)
            z2 = a1 @ p["W2"] + p["b2"]; a2 = np.maximum(z2, 0)
            z3 = a2 @ p["W3"] + p["b3"]
            z3 -= z3.max(1, keepdims=True)
            e = np.exp(z3); pr = e / e.sum(1, keepdims=True)
            w = cw[yb]
            loss += float(-(w * np.log(pr[np.arange(len(yb)), yb] + 1e-9)).sum())
            g3 = pr.copy(); g3[np.arange(len(yb)), yb] -= 1; g3 *= (w / w.sum())[:, None]
            g = {"W3": a2.T @ g3, "b3": g3.sum(0)}
            g2 = (g3 @ p["W3"].T) * (z2 > 0)
            g["W2"], g["b2"] = a1.T @ g2, g2.sum(0)
            g1 = (g2 @ p["W2"].T) * (z1 > 0)
            g["W1"], g["b1"] = xb.T @ g1, g1.sum(0)
            t += 1
            for k in p:
                g[k] += 1e-5 * p[k] if k.startswith("W") else 0
                m[k] = b1 * m[k] + (1 - b1) * g[k]
                v[k] = b2 * v[k] + (1 - b2) * g[k] ** 2
                p[k] -= lr * (m[k] / (1 - b1 ** t)) / (np.sqrt(v[k] / (1 - b2 ** t)) + eps)
        if ep in (epochs // 2, epochs * 3 // 4):
            lr /= 3
        if ep % 10 == 0 or ep == epochs - 1:
            print(f"  époque {ep + 1:2}/{epochs}  perte {loss / n:.4f}")
    return {**p, "mu": mu.astype(np.float32), "sd": sd.astype(np.float32)}


def hybrid(pr: np.ndarray, rules: np.ndarray, threshold: float, bullets: np.ndarray | None = None) -> np.ndarray:
    """Same decision logic as app.doc.ml.refine (on labels)."""
    k = pr.argmax(1)
    conf = pr.max(1) >= threshold
    out = rules.copy()
    take = conf & (((k >= 1) & (k <= 4)) | ((k == 0) & ((rules >= 1) & (rules <= 5))))
    if bullets is not None:
        take &= ~(bullets & (rules == 5))
    out[take] = k[take]
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2500
    t0 = time.time()
    xtr, ytr, _, _ = dataset(range(0, n))
    import os

    if os.environ.get("SYNTH_SPLIT") == "train":  # generalisation check: validate on the unseen half
        os.environ["SYNTH_SPLIT"] = "test"
        import importlib

        import ml.synth
        importlib.reload(ml.synth)
        globals()["sample"] = ml.synth.sample
    xva, yva, rva, _ = dataset(range(100_000, 100_300))
    print(f"données : {len(ytr)} paragraphes d'entraînement, {len(yva)} de validation ({time.time() - t0:.0f} s)")
    params = train(xtr, ytr)
    pr = Model(params).proba(xva)
    base = report(yva, rva, "Règles seules")
    report(yva, pr.argmax(1), "Modèle seul")
    best = (base["acc"], None)
    report_cache = {}
    for th in (0.6, 0.7, 0.8, 0.9, 0.95):
        r = report(yva, hybrid(pr, rva, th), f"Règles + modèle (seuil {th})")
        report_cache[th] = r["acc"]
        if r["acc"] > best[0]:
            best = (r["acc"], th)
    # prudence: real documents differ from synthetic ones → the most cautious threshold within 0.2 pt of the best
    ths = [th for th in (0.95, 0.9, 0.8, 0.7, 0.6) if best[1] is not None and report_cache[th] >= best[0] - 0.002]
    if ths:
        best = (best[0], ths[0])
    if os.environ.get("SYNTH_SPLIT"):
        print("(vérification de généralisation : modèle non enregistré)")
        sys.exit(0)
    if best[1] is None:
        print("Le modèle ne fait pas mieux que les règles : non enregistré.")
    else:
        params["threshold"] = np.array(best[1], np.float32)
        np.savez_compressed(MODEL_PATH, **params)
        print(f"Enregistré : {MODEL_PATH.name} (seuil {best[1]}, {MODEL_PATH.stat().st_size // 1024} Ko)")
