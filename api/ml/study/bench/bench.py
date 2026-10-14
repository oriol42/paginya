"""Paginya corpus bench: every file through the real API (create -> confirm -> render), with automatic checks.

Usage: PROPRE_DATA_DIR=<tmp> python bench.py <corpus dir> <out dir> [name filter]
"""
import base64, json, os, re, shutil, sys, time, traceback, collections
from pathlib import Path

sys.path.insert(0, "/home/oriol/Documents/propre/api")
os.environ.setdefault("FAPSHI_MODE", "mock")
from fastapi.testclient import TestClient
from app import config, guard
from app.main import app

guard.LIMITS.clear()
guard.DEFAULT_WRITE = (10**9, 600)
CORPUS, OUT = Path(sys.argv[1]), Path(sys.argv[2])
FILTER = sys.argv[3] if len(sys.argv) > 3 else ""
OUT.mkdir(parents=True, exist_ok=True)

TOC_LINE = re.compile(r"\.{4,}\s*\d+\s*$|\s\d{1,3}\s*$")
BULLET = re.compile(r"^\s*[-–—•●■◆❖➤▪·*o]\s+\S")
NUM_ONLY = re.compile(r"^\s*(page\s*)?\d{1,3}(\s*(/|sur)\s*\d{1,3})?\s*$", re.I)


def checks(view: dict) -> list[str]:
    blocks, meta = view["blocks"], view["meta"]
    out = []
    heads = [b for b in blocks if b["type"] == "heading"]
    paras = [b for b in blocks if b["type"] == "paragraph"]
    words = meta.get("words", 0)
    if words > 600 and len(heads) < 2:
        out.append(f"AUCUN_TITRE ({len(heads)} titres pour {words} mots)")
    if len(heads) > 8 and len(heads) > 0.45 * max(1, len(paras)):
        out.append(f"TROP_DE_TITRES ({len(heads)} titres / {len(paras)} paragraphes)")
    long_h = [h["text"] for h in heads if len(h["text"]) > 140]
    if long_h:
        out.append(f"TITRE_TROP_LONG x{len(long_h)}: {long_h[0][:90]!r}")
    sent_h = [h["text"] for h in heads if h["text"].rstrip().endswith((".", ";", ",")) and len(h["text"]) > 60]
    if sent_h:
        out.append(f"TITRE_PHRASE x{len(sent_h)}: {sent_h[0][:90]!r}")
    low_h = [h["text"] for h in heads if h["text"][:1].islower()]
    if low_h:
        out.append(f"TITRE_MINUSCULE x{len(low_h)}: {low_h[0][:70]!r}")
    dots = [b["text"] for b in blocks if b.get("text") and re.search(r"\.{5,}|…{3,}|_{6,}", b["text"])]
    if dots:
        out.append(f"POINTILLES x{len(dots)}: {dots[0][:80]!r}")
    nums = [b["text"] for b in paras if NUM_ONLY.match(b["text"])]
    if nums:
        out.append(f"NUMERO_SEUL x{len(nums)}: {nums[:4]}")
    bul = [b["text"] for b in paras if BULLET.match(b["text"])]
    if bul:
        out.append(f"PUCE_EN_PARAGRAPHE x{len(bul)}: {bul[0][:70]!r}")
    rep = collections.Counter(b["text"].strip() for b in blocks if b.get("text") and 3 < len(b["text"].strip()) < 90)
    reps = [(t, n) for t, n in rep.items() if n >= 4]
    if reps:
        out.append(f"LIGNE_REPETEE x{len(reps)}: {reps[0][0][:60]!r}×{reps[0][1]}")
    short = sum(1 for a, b in zip(paras, paras[1:]) if 25 < len(a["text"]) < 95 and not a["text"].rstrip().endswith((".", ":", "!", "?", ";")) and b["text"][:1].islower())
    if short >= 3:
        out.append(f"PHRASES_COUPEES x{short}")
    empty = [b for b in blocks if b["type"] in ("paragraph", "heading") and not (b.get("text") or "").strip()]
    if empty:
        out.append(f"BLOC_VIDE x{len(empty)}")
    caps = [b["text"] for b in paras if len(b["text"]) > 30 and b["text"].upper() == b["text"] and re.search(r"[A-Z]{4}", b["text"])]
    if len(caps) >= 3:
        out.append(f"PARAGRAPHE_MAJUSCULES x{len(caps)}: {caps[0][:70]!r}")
    lv = [h["level"] for h in heads]
    jumps = sum(1 for a, b in zip(lv, lv[1:]) if b - a > 1)
    if jumps >= 2:
        out.append(f"SAUT_DE_NIVEAU x{jumps}")
    if heads and len(set(lv)) == 1 and len(heads) > 12:
        out.append(f"TITRES_TOUS_NIVEAU_{lv[0]} x{len(heads)}")
    return out


def _n(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def score(view: dict, truth: list) -> dict:
    heads = [(b["level"], _n(b["text"])) for b in view["blocks"] if b["type"] == "heading"]
    used, matched, missing = set(), [], []
    for lv, text in truth:
        key = _n(text)
        hit = next((i for i, (_, h) in enumerate(heads) if i not in used and (h.endswith(key) or key in h) and len(h) < len(key) + 40), None)
        if hit is None:
            missing.append(text)
        else:
            used.add(hit); matched.append((lv, heads[hit][0]))
    extra = [view_h for i, view_h in enumerate(b["text"] for b in view["blocks"] if b["type"] == "heading") if i not in used]
    sign = lambda x: (x > 0) - (x < 0)
    pairs = list(zip(matched, matched[1:]))
    order = sum(1 for (a, x), (b, y) in pairs if sign(b - a) == sign(y - x)) / len(pairs) if pairs else 1.0
    return {"recall": round(len(matched) / max(1, len(truth)), 2), "precision": round(len(matched) / max(1, len(heads)), 2), "levels": round(order, 2),
            "missing": missing[:12], "extra": [e[:80] for e in extra[:12]]}


def summary(view: dict) -> dict:
    blocks = view["blocks"]
    c = collections.Counter(b["type"] for b in blocks)
    lv = collections.Counter(b["level"] for b in blocks if b["type"] == "heading")
    cover = view["meta"].get("cover") or {}
    ex = view["meta"].get("existing") or {}
    return {
        "kind": view["meta"].get("kind"), "shown": (view.get("analysis") or {}).get("kind"), "words": view["meta"].get("words"),
        "title": (view["meta"].get("title") or "")[:90], "types": dict(c), "levels": {str(k): v for k, v in sorted(lv.items())},
        "mode": view.get("mode"), "plan": view.get("plan"),
        "cover": {k: (v if isinstance(v, (str, int, bool)) else len(v)) for k, v in cover.items() if v} if cover else None,
        "existing": {k: v for k, v in ex.items() if k in ("cover", "toc", "page_numbers", "own_layout", "titles", "numbering", "toc_title")} if ex else None,
    }


def run(c: TestClient, path: Path) -> dict:
    res: dict = {"file": path.name, "size": path.stat().st_size}
    t = time.time()
    body = {"filename": path.name, "data": base64.b64encode(path.read_bytes()).decode()} if path.suffix.lower() != ".paste" else {"text": path.read_text()}
    r = c.post("/documents", json=body)
    res["create_s"] = round(time.time() - t, 1)
    if r.status_code != 200:
        res["create_error"] = f"{r.status_code} {r.text[:200]}"
        return res
    v = r.json()
    oid = v["id"]
    res.update(summary(v))
    res["checks"] = checks(v)
    tf = path.with_name(path.name + ".truth.json")
    if tf.is_file():
        res["truth"] = score(v, json.loads(tf.read_text()))
    res["headings"] = [f"{b['level']} {b['text'][:100]}" for b in v["blocks"] if b["type"] == "heading"][:400]
    (OUT / "blocks").mkdir(exist_ok=True)
    (OUT / "blocks" / f"{path.name}.txt").write_text("\n".join(
        f"[{b['type'][:4]}{b.get('level', '')}] " + (b.get("text") or (f"<rows {len(b.get('rows', []))}>" if b["type"] == "table" else b.get("image", "")))[:400]
        + ("" if b["type"] != "list" else " | " + " | ".join(str(i)[:80] for i in b.get("items", [])[:12])) for b in v["blocks"]))
    modes = [v.get("mode", "rebuild")] + (["rebuild"] if v.get("mode") == "keep" else [])
    res["renders"] = {}
    for m in modes:
        t = time.time()
        try:
            c.put(f"/documents/{oid}", json={"mode": m, "confirm": True})
            r = c.post(f"/documents/{oid}/render")
            info = {"s": round(time.time() - t, 1), "status": r.status_code}
            if r.status_code == 200:
                info["pages"] = r.json()["render"]["pages"]
                pdf = config.DATA_DIR / "docs" / oid / "build" / "final.pdf"
                (OUT / "pdf").mkdir(exist_ok=True)
                shutil.copy(pdf, OUT / "pdf" / f"{path.stem}.{m}.pdf")
            else:
                info["error"] = r.text[:300]
        except Exception:
            info = {"s": round(time.time() - t, 1), "status": "EXC", "error": traceback.format_exc()[-900:]}
        res["renders"][m] = info
    time.sleep(0.5)
    return res


with TestClient(app) as client:
    files = sorted(p for p in CORPUS.iterdir() if p.is_file() and FILTER in p.name and not p.name.endswith(".json"))
    for p in files:
        dest = OUT / "res" / f"{p.name}.json"
        dest.parent.mkdir(exist_ok=True)
        try:
            res = run(client, p)
        except Exception:
            res = {"file": p.name, "crash": traceback.format_exc()[-1500:]}
        dest.write_text(json.dumps(res, ensure_ascii=False, indent=1))
        r = res.get("renders", {})
        print(p.name[:60].ljust(60), res.get("kind", "-"), res.get("create_error") or res.get("crash", "")[-200:] or
              " ".join(f"{m}:{i.get('pages', i.get('status'))}p/{i['s']}s" for m, i in r.items()), "|", len(res.get("checks", [])), "alertes",
              "| R{recall} P{precision} N{levels}".format(**res["truth"]) if res.get("truth") else "", flush=True)
