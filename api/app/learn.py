"""Paginya learns from the documents it lays out, by itself, every night.

1. On arrival (`snapshot`): the paragraphs' features (numbers only: sizes, bold, numbering, position… never the
   text) and what the engine decided are kept next to the document; odd results are flagged (`health`).
2. Once paid (`harvest`, each night): the plan the customer kept is the right answer. The customer's corrections
   (a line made a title, a title removed, a level changed) become examples for the model.
3. Each night (`retrain`): the model is trained again on the synthetic documents plus every real example, and only
   replaces the current one if it does at least as well on the synthetic check, on real documents it has not seen
   and on the corpus of documents with a known plan. Otherwise nothing changes.
4. The flagged documents wait in Coulisses (/admin/learn): new kinds of errors need a new rule, written by a person.
   The file itself is kept only when the customer agreed (« J'aide Paginya à s'améliorer »), 12 months at most.

Run by hand: python -m app.learn nightly | harvest | retrain
"""
from __future__ import annotations

import difflib
import hashlib
import json
import logging
import re
import shutil
import sys
import threading
import time
import unicodedata
from pathlib import Path

import numpy as np

from . import config, db

log = logging.getLogger("paginya.learn")

def root() -> Path:
    return config.DATA_DIR / "learn"


def samples_dir() -> Path:
    return root() / "samples"


def files_dir() -> Path:
    return root() / "files"  # the files customers let us keep


def corpus_dir() -> Path:
    return root() / "corpus"  # documents with a known plan (*.truth.json), copied from api/data/corpus


def model_path() -> Path:
    return root() / "structure_model.npz"  # the learned model, preferred to the one shipped with the code (doc/ml.py)


def history_path() -> Path:
    return root() / "history.json"

MIN_DOCS = 20  # below this, real examples are too few to change anything
KEEP_FILES_DAYS = 365

PARA, H1, LIST, CAPTION, TOC = 0, 1, 5, 6, 7


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", str(t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()[:200]


def label(b: dict | None) -> int:
    """A block as one of the model's classes (-1: not something the model decides: table, figure, code…)."""
    if not b:
        return -1
    t = b.get("type")
    if t == "heading":
        return H1 + min(max(int(b.get("level", 1) or 1), 1), 4) - 1
    if t == "list":
        return LIST
    if t == "caption":
        return CAPTION
    if t == "paragraph":
        return PARA
    if t == "toc":
        return TOC
    return -1


# --- 1. on arrival ---------------------------------------------------------------------------------------------

_FORMULA = re.compile(r"\S\s*[=≤≥≠⇒]\s*\S")


def health(result: dict, raws: list) -> list[str]:
    """What looks wrong in a result, the checks of the corpus bench (ml/study/bench) in short."""
    blocks, meta = result["blocks"], result["meta"]
    heads = [b for b in blocks if b["type"] == "heading" and not b.get("hidden")]
    paras = [b for b in blocks if b["type"] == "paragraph" and not b.get("hidden")]
    words = meta.get("words", 0)
    out = []
    if words > 600 and len(heads) < 2:
        out.append("aucun titre")
    if len(heads) > 8 and len(heads) > 0.45 * max(1, len(paras)):
        out.append(f"trop de titres ({len(heads)} pour {len(paras)} paragraphes)")
    if any(len(h["text"]) > 140 for h in heads):
        out.append("titre trop long")
    if sum(h["text"].rstrip().endswith((".", ";", ",")) and len(h["text"]) > 60 for h in heads) >= 2:
        out.append("phrases prises pour des titres")
    if any(_FORMULA.search(h["text"]) for h in heads):
        out.append("formule prise pour un titre")
    if len(heads) >= 6 and len({h.get("level") for h in heads}) == 1:
        out.append("tous les titres au même niveau")
    from .doc.extract import junk_rate

    text = "\n".join(b.get("text", "") for b in blocks if b.get("text"))
    if text and junk_rate(text) >= 0.08:
        out.append("texte peu lisible (police, scan)")
    if raws and sum(1 for r in raws if r.text and len(r.text) < 3) > 0.3 * len(raws):
        out.append("texte en miettes")
    return out


def snapshot(order_id: str, raws: list, result: dict, trace: dict, folder: Path) -> None:
    """Keeps, next to the document, what the model will need to learn from it once paid. Never fails the request."""
    try:
        from .doc.detect import detect
        from .doc.extract import body_size
        from .doc.ml import features

        rules = detect(raws, trace=True, refine=False)["trace"]  # the model's input, as in ml/train.py
        x = features(raws, rules, body_size(raws))
        raw_block = np.array([int(trace.get(i, {}).get("id", 0) or 0) for i in range(len(raws))], dtype=np.int32)
        blocks = [[b["id"], label(b), _norm(b.get("text", ""))] for b in result["blocks"] if not b.get("hidden")]
        np.savez_compressed(folder / "learn.npz", x=x, raw_block=raw_block)
        (folder / "learn.json").write_text(json.dumps({"blocks": blocks, "engine": engine_version()}), encoding="utf-8")
        reasons = health(result, raws)
        if reasons:
            db.flag_doc(order_id, kind=result["meta"].get("kind", ""), words=result["meta"].get("words", 0), reasons=reasons)
    except Exception:  # noqa: BLE001 — learning is a bonus, the document comes first
        log.exception("snapshot failed for %s", order_id)


def snapshot_later(order_id: str, raws: list, result: dict, trace: dict, folder: Path) -> None:
    threading.Thread(target=snapshot, args=(order_id, raws, result, trace, folder), daemon=True).start()


def engine_version() -> str:
    """Changes whenever the rules change: features made by other rules are not mixed with the new ones."""
    h = hashlib.sha1()
    for p in sorted((Path(__file__).parent / "doc").glob("*.py")):
        if p.name != "ml.py":
            h.update(p.read_bytes())
    return h.hexdigest()[:12]


# --- 2. once paid ----------------------------------------------------------------------------------------------

def align(before: list[list], after: list[dict]) -> dict[int, int | None]:
    """{block id at arrival: label the customer kept}. A block whose text the customer rewrote or deleted: None."""
    a = [t for _, _, t in before]
    b = [_norm(x.get("text", "")) for x in after]
    kept: dict[int, int | None] = {bid: None for bid, _, _ in before}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                kept[before[i1 + k][0]] = label(after[j1 + k])
        elif tag == "replace" and i2 - i1 == j2 - j1:
            for k in range(i2 - i1):  # a title retyped a little ("1.1 Les lois" → "1.1 Les lois du travail")
                if difflib.SequenceMatcher(a=a[i1 + k], b=b[j1 + k]).ratio() >= 0.8:
                    kept[before[i1 + k][0]] = label(after[j1 + k])
    return kept


def harvest_one(order_id: str, folder: Path, order: dict) -> dict | None:
    meta = json.loads((folder / "learn.json").read_text(encoding="utf-8"))
    with np.load(folder / "learn.npz") as z:
        x, raw_block = z["x"], z["raw_block"]
    before = meta["blocks"]
    after = [b for b in order["payload"].get("doc", {}).get("blocks", []) if not b.get("hidden")]
    kept = align(before, after)
    first = {bid: lab for bid, lab, _ in before}
    y = np.full(len(raw_block), -1, dtype=np.int8)
    rules = np.full(len(raw_block), -1, dtype=np.int8)
    for i, bid in enumerate(raw_block.tolist()):
        if bid and kept.get(bid) is not None and kept[bid] >= 0:
            y[i], rules[i] = kept[bid], first.get(bid, -1)
    changed = int(sum(1 for bid, lab, _ in before if kept.get(bid) is not None and kept[bid] != lab))
    deleted_heads = int(sum(1 for bid, lab, _ in before if kept.get(bid) is None and H1 <= lab <= 4))
    samples_dir().mkdir(parents=True, exist_ok=True)
    np.savez_compressed(samples_dir() / f"{order_id}.npz", x=x[y >= 0], y=y[y >= 0], rules=rules[y >= 0])
    (samples_dir() / f"{order_id}.json").write_text(json.dumps({"engine": meta.get("engine"), "at": time.time(), "changed": changed}), encoding="utf-8")
    corrections = changed + deleted_heads
    doc = order["payload"].get("doc", {})
    fields = {"corrections": corrections}
    if corrections >= max(3, 0.05 * len(before)):
        fields["reasons"] = [f"{corrections} corrections du client"]
    if doc.get("help"):
        src = next(folder.glob("source.*"), None)
        if src is not None:
            dest = files_dir() / order_id
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / src.name)
            fields["has_file"] = 1
    db.flag_doc(order_id, kind=doc.get("meta", {}).get("kind", ""), words=doc.get("meta", {}).get("words", 0), **fields)
    (folder / "learn.done").write_text(str(time.time()))
    return {"order": order_id, "corrections": corrections, "examples": int((y >= 0).sum())}


def harvest() -> list[dict]:
    done = []
    for folder in sorted((config.DATA_DIR / "docs").glob("*/learn.npz")):
        folder = folder.parent
        if (folder / "learn.done").exists() or not (folder / "learn.json").exists():
            continue
        order = db.get_order(folder.name)
        if order is None or order["status"] != "PAID" or "doc" not in order["payload"]:
            continue
        try:
            if r := harvest_one(folder.name, folder, order):
                done.append(r)
        except Exception:  # noqa: BLE001
            log.exception("harvest failed for %s", folder.name)
    return done


# --- 3. each night ---------------------------------------------------------------------------------------------

def _real(engine: str) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    out = []
    for p in sorted(samples_dir().glob("*.npz")):
        info = json.loads(p.with_suffix(".json").read_text()) if p.with_suffix(".json").exists() else {}
        if info.get("engine") != engine:
            continue  # made by other rules: its features would mislead the model
        with np.load(p) as z:
            if len(z["y"]):
                out.append((z["x"], z["y"].astype(np.int64), z["rules"].astype(np.int64)))
    return out


def _synthetic(engine: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Synthetic training and checking sets of ml/train.py, made once per version of the rules (a few minutes)."""
    cache = root() / f"synth-{engine}.npz"
    if cache.exists():
        with np.load(cache) as z:
            return z["xtr"], z["ytr"], z["xva"], z["yva"], z["rva"]
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ml.train import dataset

    xtr, ytr, _, _ = dataset(range(0, 1500))
    xva, yva, rva, _ = dataset(range(100_000, 100_300))
    for old in root().glob("synth-*.npz"):
        old.unlink()
    np.savez_compressed(cache, xtr=xtr, ytr=ytr, xva=xva, yva=yva, rva=rva)
    return xtr, ytr, xva, yva, rva


def _corpus_score(params: dict | None) -> float | None:
    """Mean of recall, precision and levels on the documents of known plan, with this model (None: no corpus)."""
    truths = sorted(corpus_dir().glob("*.truth.json"))
    if not truths:
        return None
    from .doc import ml
    from .doc.detect import detect
    from .doc.extract import from_docx, from_pdf, from_text

    saved = ml._model
    ml._model = ml.Model(params) if params else None
    try:
        total = 0.0
        for t in truths:
            src = t.with_name(t.name.removesuffix(".truth.json"))
            img = root() / "tmp-img"
            raws = from_docx(src, img) if src.suffix == ".docx" else from_pdf(src, img) if src.suffix == ".pdf" else from_text(src.read_text())
            heads = [(b["level"], _norm(b["text"])) for b in detect(raws)["blocks"] if b["type"] == "heading" and not b.get("hidden")]
            truth = json.loads(t.read_text())
            used, matched = set(), []
            for lv, text in truth:
                key = _norm(text)
                hit = next((i for i, (_, h) in enumerate(heads) if i not in used and (h.endswith(key) or key in h) and len(h) < len(key) + 40), None)
                if hit is not None:
                    used.add(hit)
                    matched.append((lv, heads[hit][0]))
            sign = lambda v: (v > 0) - (v < 0)  # noqa: E731
            pairs = list(zip(matched, matched[1:]))
            order = sum(1 for (a, x), (b, y) in pairs if sign(b - a) == sign(y - x)) / len(pairs) if pairs else 1.0
            total += (len(matched) / max(1, len(truth)) + len(matched) / max(1, len(heads)) + order) / 3
        shutil.rmtree(root() / "tmp-img", ignore_errors=True)
        return total / len(truths)
    finally:
        ml._model = saved


def retrain() -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ml.train import hybrid, train

    from .doc import ml

    engine = engine_version()
    real = _real(engine)
    res: dict = {"at": time.time(), "engine": engine, "real_docs": len(real), "accepted": False}
    if len(real) < MIN_DOCS:
        res["why"] = f"{len(real)} documents payés avec cette version du moteur (il en faut {MIN_DOCS})"
        return res
    split = max(1, len(real) // 5)  # the newest fifth is kept aside to check on documents never seen
    train_real, check_real = real[:-split], real[-split:]
    xtr, ytr, xva, yva, rva = _synthetic(engine)
    xr = np.concatenate([x for x, _, _ in train_real])
    yr = np.concatenate([y for _, y, _ in train_real])
    # each real paragraph counts three times: they are few, and they are what customers really send
    params = train(np.concatenate([xtr, xr, xr, xr]), np.concatenate([ytr, yr, yr, yr]))
    current = ml.Model.load(model_path() if model_path().exists() else ml.MODEL_PATH)
    xc = np.concatenate([x for x, _, _ in check_real])
    yc = np.concatenate([y for _, y, _ in check_real])
    rc = np.concatenate([r for _, _, r in check_real])

    def score(model, threshold: float) -> tuple[float, float]:
        if model is None:
            return float((rva == yva).mean()), float((rc == yc).mean())
        return (float((hybrid(model.proba(xva), rva, threshold) == yva).mean()),
                float((hybrid(model.proba(xc), rc, threshold) == yc).mean()))

    cur_th = float(current.p.get("threshold", 0.9)) if current else 0.9
    cur = score(current, cur_th)
    best = None
    for th in (0.95, 0.9, 0.8, 0.7):  # the most cautious threshold that does as well
        s = score(ml.Model(params), th)
        if s[0] >= cur[0] - 0.001 and s[1] >= cur[1] and (best is None or sum(s) > sum(best[1]) + 0.002):
            best = (th, s)
    res.update(synthetic=[round(cur[0], 4), None], real=[round(cur[1], 4), None])
    if best is None:
        res["why"] = "le nouveau modèle ne fait pas mieux que l'actuel"
        return res
    params["threshold"] = np.array(best[0], np.float32)
    res.update(synthetic=[round(cur[0], 4), round(best[1][0], 4)], real=[round(cur[1], 4), round(best[1][1], 4)], threshold=best[0])
    before, after = _corpus_score(current.p if current else None), _corpus_score(params)
    res["corpus"] = [None if before is None else round(before, 4), None if after is None else round(after, 4)]
    if before is not None and after < before - 0.002:
        res["why"] = "moins bon sur les documents de référence"
        return res
    root().mkdir(parents=True, exist_ok=True)
    tmp = root() / "structure_model.new.npz"
    np.savez_compressed(tmp, **params)
    tmp.replace(model_path())  # atomic: the server picks it up at its next document
    res["accepted"] = True
    return res


def _record(res: dict) -> None:
    hist = json.loads(history_path().read_text()) if history_path().exists() else []
    hist = (hist + [res])[-60:]
    root().mkdir(parents=True, exist_ok=True)
    history_path().write_text(json.dumps(hist, ensure_ascii=False))


def forget_old_files() -> None:
    limit = time.time() - KEEP_FILES_DAYS * 86400
    for d in files_dir().glob("*"):
        if d.is_dir() and d.stat().st_mtime < limit:
            shutil.rmtree(d, ignore_errors=True)


def nightly() -> dict:
    root().mkdir(parents=True, exist_ok=True)
    harvested = harvest()
    forget_old_files()
    res = retrain()
    res["harvested"] = len(harvested)
    _record(res)
    log.info("nightly: %s", res)
    return res


def status() -> dict:
    hist = json.loads(history_path().read_text()) if history_path().exists() else []
    return {"history": hist[-14:], "samples": len(list(samples_dir().glob("*.npz"))), "learned_model": model_path().exists(),
            "model_date": model_path().stat().st_mtime if model_path().exists() else None}


# --- the nightly run, inside the server --------------------------------------------------------------------------

def _seconds_to(hour: int, minute: int) -> float:
    now = time.time() + 3600  # Cameroon: UTC+1 all year
    day = now - now % 86400
    target = day + hour * 3600 + minute * 60
    return (target if target > now else target + 86400) - now


def start_nightly(hour: int = 2, minute: int = 30) -> None:
    """At 2:30 (Cameroon), when nobody is laying out a document, in a separate low-priority process."""
    import subprocess

    def loop() -> None:
        while True:
            time.sleep(_seconds_to(hour, minute))
            try:
                root().mkdir(parents=True, exist_ok=True)
                with open(root() / "nightly.log", "a") as out:
                    subprocess.run(["nice", "-n", "15", sys.executable, "-m", "app.learn", "nightly"], stdout=out, stderr=out,
                                   timeout=3 * 3600, cwd=str(Path(__file__).resolve().parent.parent))
            except Exception:  # noqa: BLE001
                log.exception("nightly run failed")

    threading.Thread(target=loop, daemon=True, name="learn-nightly").start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    what = sys.argv[1] if len(sys.argv) > 1 else "nightly"
    print(json.dumps({"nightly": nightly, "harvest": harvest, "retrain": retrain}[what](), ensure_ascii=False, default=str), flush=True)
