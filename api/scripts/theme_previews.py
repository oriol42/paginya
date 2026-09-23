"""Generates web/public/themes/<theme>.png: a real page rendered by Propre in each style."""
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.doc import office  # noqa: E402
from app.doc.detect import detect  # noqa: E402
from app.doc.extract import from_text  # noqa: E402
from app.doc.render import THEMES, build_docx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT.parent / "web" / "public" / "themes"
blocks = detect(from_text((ROOT / "tests/fixtures/rapport_brut.txt").read_text()))["blocks"]
OUT.mkdir(parents=True, exist_ok=True)
for theme in THEMES:
    tmp = Path(tempfile.mkdtemp())
    doc = {"blocks": blocks, "style": {"theme": theme, "color": "#0E9F6E"}, "options": {"toc": False, "toc_end": False, "lists": False}}
    (tmp / "raw.docx").write_bytes(build_docx(doc, tmp / "images"))
    office.finalize(tmp / "raw.docx", tmp / "final.docx", tmp / "final.pdf")
    # the page showing chapter I (title, list, table)
    pages = office.page_count(tmp / "final.pdf")
    target = 1
    for n in range(1, pages + 1):
        text = subprocess.run(["pdftotext", "-f", str(n), "-l", str(n), str(tmp / "final.pdf"), "-"], capture_output=True, text=True).stdout
        if "Tableau" in text and "Historique" in text:
            target = n
            break
    subprocess.run(["pdftoppm", "-r", "60", "-png", "-singlefile", "-f", str(target), "-l", str(target), str(tmp / "final.pdf"), str(OUT / theme)], check=True)
    print(theme, target)
