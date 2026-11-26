"""The profile of a corpus of decks (from measure.py), and how far Paginya's decks are from the designers'.

Usage: python -I profile_decks.py pro.jsonl [ours.jsonl ...]
       python -I profile_decks.py --compare pro.jsonl before.jsonl after.jsonl
       python -I profile_decks.py --save pro.jsonl designers.json   (the numbers the tests hold Paginya to)
Prints, for each corpus, the quartiles of each measure on the cover, the content slides and the closing slide,
then how the decks move: transitions, animations, their durations and pace.
Font sizes are brought to a 13.33-inch wide slide (PowerPoint's 16:9) so a 4:3 deck compares.
"""
import json
import statistics
import sys
from collections import Counter

WIDE = 13.333
MEASURES = ("words", "title_size", "max_size", "body_size", "n_sizes", "left", "top", "text_area", "ink_area", "pic_area", "big_pic",
            "n_text", "n_ink", "edges", "fills")
NAMES = {1: "Apparaître", 2: "Entrée brusque", 10: "Fondu", 16: "Fractionner", 21: "Roue", 22: "Balayer", 23: "Zoom (ancien)", 26: "Rebondir",
         31: "Agrandir et tourner", 37: "S'élever", 42: "Monter (Float In)", 47: "Descendre", 53: "Zoom", 55: "Développer", 6: "Cercle"}


def load(path: str) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def roles(deck: dict):
    """cover, content..., end: the first and last slides are their own kind."""
    slides = deck["slides"]
    for i, s in enumerate(slides):
        role = "cover" if i == 0 else ("end" if i == len(slides) - 1 else "content")
        scale = WIDE / deck.get("width_in", WIDE)
        row = dict(s)
        for key in ("title_size", "max_size", "body_size"):
            if row.get(key):
                row[key] = round(row[key] * scale, 1)
        yield role, row


def quartiles(values: list[float]) -> tuple:
    values = sorted(v for v in values if v is not None)
    if not values:
        return (None, None, None, 0)
    if len(values) < 4:
        m = statistics.median(values)
        return (values[0], m, values[-1], len(values))
    q = statistics.quantiles(values, n=4)
    return (round(q[0], 3), round(q[1], 3), round(q[2], 3), len(values))


def profile(decks: list[dict]) -> dict:
    by_role: dict[str, list[dict]] = {"cover": [], "content": [], "end": []}
    for deck in decks:
        for role, row in roles(deck):
            by_role[role].append(row)
    out = {"decks": len(decks), "slides": sum(len(d["slides"]) for d in decks), "roles": {}}
    for role, rows in by_role.items():
        out["roles"][role] = {m: quartiles([r.get(m) for r in rows]) for m in MEASURES}
        if rows:
            out["roles"][role]["photo_share"] = round(sum(r["pic_area"] > 0.08 for r in rows) / len(rows), 3)
            out["roles"][role]["bleed_share"] = round(sum(r["bleed"] > 0 or r["bg"] == "picture" for r in rows) / len(rows), 3)
            dark = [r["bg_lum"] < 0.18 for r in rows if r.get("bg_lum") is not None]
            out["roles"][role]["dark_share"] = round(sum(dark) / len(dark), 3) if dark else None
            out["roles"][role]["shadow_share"] = round(sum(r["shadows"] > 0 for r in rows) / len(rows), 3)
            out["roles"][role]["gradient_share"] = round(sum(r["gradients"] > 0 for r in rows) / len(rows), 3)
    rows = [r for d in decks for r in d["slides"]]
    trans = Counter((r["transition"] or {}).get("kind", "aucune") for r in rows)
    tdur = [r["transition"]["dur"] for r in rows if r["transition"] and r["transition"]["kind"] != "none"]
    anims = [a for r in rows for a in r["anims"]]
    animated = [r for r in rows if r["anims"]]
    entr = Counter(NAMES.get(a["id"], str(a["id"])) for a in anims if a["cls"] == "entr")
    out["motion"] = {
        "transitions": dict(trans.most_common(8)),
        "transition_ms": quartiles(tdur),
        "animated_share": round(len(animated) / max(1, len(rows)), 3),
        "effects_per_animated_slide": quartiles([len(r["anims"]) for r in animated]),
        "classes": dict(Counter(a["cls"] for a in anims).most_common()),
        "entrances": dict(entr.most_common(10)),
        "effect_ms": quartiles([a["dur"] for a in anims if a["cls"] == "entr" and a["dur"] > 1]),
        "triggers": dict(Counter(a["node"] for a in anims).most_common()),
        "delays_ms": quartiles([a["delay"] for a in anims if a["delay"] > 0]),
        "decks_with_motion": sum(any(r["anims"] or r["transition"] for r in d["slides"]) for d in decks),
    }
    return out


def show(name: str, p: dict) -> None:
    print(f"\n=== {name}: {p['decks']} présentations, {p['slides']} diapos")
    for role, measures in p["roles"].items():
        print(f"  [{role}]")
        for m, v in measures.items():
            print(f"    {m:15} {v}")
    print("  [mouvement]")
    for k, v in p["motion"].items():
        print(f"    {k:28} {v}")




# --- how close a corpus is to the designers' ------------------------------------------------------

SCORED = {  # measure: what is compared (on content slides unless said), and why
    "n_sizes": "tailles de texte par diapo",
    "body_size": "taille du texte courant",
    "title_size": "taille du titre",
    "left": "marge de gauche",
    "n_text": "blocs de texte par diapo",
    "edges": "alignements à gauche différents",
    "fills": "couleurs pleines différentes",
    "words": "mots par diapo",
    "text_area": "surface occupée par le texte",
}
SHARES = {"shadow_share": "diapos avec ombre", "gradient_share": "diapos avec dégradé", "photo_share": "diapos avec photo"}


def band(values: list[float], low: float = 0.1, high: float = 0.9) -> tuple[float, float]:
    values = sorted(v for v in values if v is not None)
    if not values:
        return (0.0, 0.0)
    return values[int(low * (len(values) - 1))], values[int(high * (len(values) - 1))]


def rows_of(decks: list[dict], role: str = "content") -> list[dict]:
    return [row for deck in decks for r, row in roles(deck) if r == role]


def norms(pro: list[dict]) -> dict:
    """What the designers usually do, kept as numbers only (designers.json): for each measure its 10th percentile,
    median and 90th percentile; for each habit the share of their slides that have it; how their decks move."""
    out = {"decks": len(pro), "slides": sum(len(d["slides"]) for d in pro), "bands": {}, "shares": {}}
    for role in ("content", "cover"):
        theirs = rows_of(pro, role)
        for m in SCORED:
            lo, hi = band([r.get(m) for r in theirs])
            if hi:
                out["bands"][f"{role}:{m}"] = [lo, quartiles([r.get(m) for r in theirs])[1], hi]
    content = profile(pro)["roles"]["content"]
    out["shares"] = {m: content[m] for m in SHARES}
    out["motion"] = profile(pro)["motion"]
    return out


def score(norm: dict, ours: list[dict]) -> dict:
    """For each measure, the share of our slides inside the designers' usual range (10th to 90th percentile);
    for the habits counted in slides (shadows, gradients, photos), how near our share is to theirs."""
    out = {}
    for key, (lo, mid, hi) in norm["bands"].items():
        role, m = key.split(":")
        vals = [r.get(m) for r in rows_of(ours, role) if r.get(m) is not None]
        if vals:
            out[key] = {"label": SCORED[m], "pro": (lo, mid, hi), "ours": quartiles(vals)[1], "inside": round(sum(lo <= v <= hi for v in vals) / len(vals), 2)}
    mine = profile(ours)["roles"]["content"]
    for m, label in SHARES.items():
        theirs = norm["shares"][m]
        gap = abs(theirs - mine[m]) if m == "photo_share" else max(0.0, mine[m] - theirs)  # fewer shadows than the designers is no fault
        out[f"content:{m}"] = {"label": label, "pro": theirs, "ours": mine[m], "inside": round(1 - min(1.0, gap / max(theirs, 0.15)), 2)}
    out["score"] = round(sum(v["inside"] for v in out.values()) / len(out), 3)
    return out


def closeness(pro: list[dict], ours: list[dict]) -> dict:
    return score(norms(pro), ours)


def compare(pro_path: str, *paths: str) -> None:
    pro = load(pro_path)
    results = {path.rsplit("/", 1)[-1]: closeness(pro, load(path)) for path in paths}
    names = list(results)
    print(f"{'critère':42} {'designers (p10 / médiane / p90)':34} " + " ".join(f"{n[:22]:>24}" for n in names))
    for key in results[names[0]]:
        if key == "score":
            continue
        row = results[names[0]][key]
        pro_txt = str(row["pro"]) if not isinstance(row["pro"], tuple) else " / ".join(f"{v:g}" for v in row["pro"])
        cells = []
        for n in names:
            r = results[n].get(key)
            cells.append(f"{str(r['ours'])[:9]:>9} ({r['inside'] * 100:3.0f} %)" if r else " " * 24)
        print(f"{key.split(':')[0][:7]:7} {row['label'][:34]:34} {pro_txt[:34]:34} " + " ".join(f"{c:>24}" for c in cells))
    print(f"{'score de proximité':77} " + " ".join(f"{results[n]['score'] * 100:23.1f}%" for n in names))


if __name__ == "__main__":
    if sys.argv[1] == "--compare":
        compare(*sys.argv[2:])
    elif sys.argv[1] == "--save":  # python profile_decks.py --save pro.jsonl designers.json
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            json.dump(norms(load(sys.argv[2])), f, ensure_ascii=False, indent=1)
    else:
        for path in sys.argv[1:]:
            show(path.rsplit("/", 1)[-1], profile(load(path)))
