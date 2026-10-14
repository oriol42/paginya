import json, sys, glob
for f in sorted(glob.glob(sys.argv[1] + "/res/*.json")):
    r = json.load(open(f))
    if len(sys.argv) > 2 and sys.argv[2] not in r["file"]: continue
    rn = " ".join(f"{m}:{i.get('pages', i.get('status'))}p/{i['s']}s" for m, i in r.get("renders", {}).items())
    print(f"\n## {r['file'][:70]}  [{r.get('kind')}/{r.get('shown')}] {r.get('words')} mots, titres {r.get('levels')}, {r.get('types')}")
    print(f"   mode={r.get('mode')} plan={r.get('plan')} existing={r.get('existing')} | {rn} | create {r.get('create_s')}s")
    print(f"   titre: {r.get('title')!r} cover: {r.get('cover')}")
    for k in ("create_error", "crash"):
        if r.get(k): print("   !!", k, r[k][-300:])
    for m, i in r.get("renders", {}).items():
        if i.get("error"): print("   !! render", m, i["error"][-300:])
    if r.get("truth"):
        t = r["truth"]; print(f"   VERITE rappel={t['recall']} precision={t['precision']} niveaux={t['levels']}\n     manquants={t['missing']}\n     en trop={t['extra']}")
    for c in r.get("checks", []): print("   -", c[:200])
