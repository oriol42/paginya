"""Does changing the document type break anything? Every type on several real documents, in both orders."""
import base64, os, sys, time
from pathlib import Path
sys.path.insert(0, "/home/oriol/Documents/propre/api")
from fastapi.testclient import TestClient
from app import guard
from app.main import app
from app.doc.render import KINDS
guard.LIMITS.clear(); guard.DEFAULT_WRITE = (10**9, 600)
C = Path(sys.argv[1])
names = ["loc03", "hm_stage_gras_centre_sommaire.docx", "hm_expose_souligne.docx", "hm_lettre_tout_normal_sansgarde.docx", "gh_Halima", "hm_cours_souligne_sansgarde.paste", "loc02", "dicames_4"]
with TestClient(app) as c:
    for n in names:
        p = next(f for f in sorted(C.iterdir()) if f.name.startswith(n) and not f.name.endswith(".json"))
        body = {"text": p.read_text()} if p.suffix == ".paste" else {"filename": p.name, "data": base64.b64encode(p.read_bytes()).decode()}
        v = c.post("/documents", json=body).json()
        oid, nb = v["id"], len(v["blocks"])
        c.put(f"/documents/{oid}", json={"confirm": True})
        row = [f"{p.name[:34]:34} auto={v['meta']['kind']:13} mode={v['mode']:7}"]
        for k in KINDS:
            r = c.put(f"/documents/{oid}", json={"kind": k})
            if r.status_code != 200: row.append(f"{k}:PUT{r.status_code}"); continue
            d = r.json()
            r2 = c.post(f"/documents/{oid}/render")
            ok = r2.status_code == 200 and r2.json()["render"]["pages"] > 0 and len(r2.json()["blocks"]) == nb
            row.append(f"{k}:{r2.json()['render']['pages'] if r2.status_code == 200 else r2.status_code}p{'' if ok else '!!'}[{''.join(x[0] for x, on in d['options'].items() if on)}|{d['plan']['cover'][0]}{d['plan']['toc'][0]}{d['plan']['numbers'][0]}]")
        print(" ".join(row), flush=True)
