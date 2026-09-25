"""Study: real reports (Memoire Online HTML) → Raw paragraphs → Paginya detect; compare with the author's own structure."""
import glob, html, re, sys, collections
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from app.doc.extract import Raw, from_text
from app.doc.detect import detect

D = sys.argv[2] if len(sys.argv) > 2 else "corpus"  # pages Memoire Online téléchargées (non versionnées)

def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()

def body(s):
    a = s.find("( Télécharger le fichier original )".encode("latin-1").decode("latin-1"))
    s = s[a if a > 0 else 0:]
    for end in ("Rechercher sur le site", "Bitcoin is a swarm", "sommaire</a>\n<a", "WOW !!"):
        e = s.rfind(end)
    e = s.find('class="rechercher') 
    return s

def raws_of(s):
    out = []
    for m in re.finditer(r"<(h[1-4]|p|tr)\b([^>]*)>(.*?)</\1>", s, re.S | re.I):
        tag, attrs, inner = m.group(1).lower(), m.group(2), m.group(3)
        if tag == "tr":
            cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", inner, re.S | re.I)]
            if any(cells): out.append(("row", cells))
            continue
        text = clean(inner)
        if not text or len(text) < 2: continue
        strong = clean(" ".join(re.findall(r"<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>", inner, re.S | re.I)))
        bold = bool(strong) and len(strong) >= 0.9 * len(text)
        centered = "center" in attrs.lower()
        truth = "H" if tag.startswith("h") or (bold and len(text) < 150 and not text.endswith(".")) else "P"
        out.append((truth, Raw(text=text, bold=bold or tag.startswith("h"), centered=centered, source="docx")))
    return out

def doc_pages(first):
    pages = [first] + sorted(glob.glob(first.replace(".html", "_*.html")))
    items = []
    for p in pages:
        s = open(p, "rb").read().decode("latin-1")
        a = s.find("fichier original")
        z = s.find("Rechercher sur le site", a + 100)
        s = s[a: z if z > 0 else None]
        items += raws_of(s)
    return items

tot = collections.Counter()
for f in sorted(glob.glob(f"{D}/d??.html")):
    items = doc_pages(f)
    raws, truth = [], []
    rows = []
    for t, r in items:
        if t == "row":
            continue
        raws.append(r); truth.append(t)
    if len(raws) < 8: continue
    for mode in ("docx", "text"):
        rr = raws if mode == "docx" else from_text("\n\n".join(r.text for r in raws))
        res = detect(rr, trace=True)
        if mode == "docx":
            tr = res["trace"]
            tp = sum(1 for i, t in enumerate(truth) if t == "H" and tr.get(i, {}).get("type") == "heading")
            fp = sum(1 for i, t in enumerate(truth) if t == "P" and tr.get(i, {}).get("type") == "heading")
            fn = sum(1 for i, t in enumerate(truth) if t == "H" and tr.get(i, {}).get("type") not in ("heading", "toc"))
            toc = sum(1 for i in tr if tr[i].get("type") == "toc")
            tot.update(tp=tp, fp=fp, fn=fn)
            m = res["meta"]
            print(f"{f.split('/')[-1]} paras={len(raws)} H_vrais={truth.count('H')} trouvés={tp} faux+={fp} ratés={fn} sommaire_retiré={toc} kind={m['kind']}")
            for i, t in enumerate(truth):
                got = tr.get(i, {}).get("type")
                if (t == "H") != (got == "heading") and got != "toc" and len(sys.argv) > 1:
                    print("   ", t, "→", got, "|", raws[i].text[:90])
p = tot["tp"] / max(1, tot["tp"] + tot["fp"]); r = tot["tp"] / max(1, tot["tp"] + tot["fn"])
print(f"TOTAL précision={p:.2f} rappel={r:.2f}", dict(tot))
