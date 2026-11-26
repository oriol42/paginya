"""See decks as pictures: each one printed to PDF by LibreOffice (as the site's previews), then a contact sheet.

Usage: PROPRE_DATA_DIR=<tmp> python -I look.py <out_dir> deck.pptx [...] [--cols 5] [--dpi 40]
"""
import glob
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # api/
from PIL import Image  # noqa: E402

from app.doc import office  # noqa: E402


def sheet(pdf: Path, out: Path, cols: int, dpi: int, last: int = 30) -> int:
    d = tempfile.mkdtemp()
    subprocess.run(["pdftoppm", "-r", str(dpi), "-l", str(last), "-png", str(pdf), d + "/p"], check=True)
    ims = [Image.open(f).convert("RGB") for f in sorted(glob.glob(d + "/p*.png"))]
    if not ims:
        return 0
    w, h = ims[0].size
    rows = (len(ims) + cols - 1) // cols
    page = Image.new("RGB", (cols * (w + 6), rows * (h + 6)), "#8a8a8a")
    for i, im in enumerate(ims):
        page.paste(im.resize((w, h)), ((i % cols) * (w + 6) + 3, (i // cols) * (h + 6) + 3))
    page.save(out)
    shutil.rmtree(d, ignore_errors=True)
    return len(ims)


if __name__ == "__main__":
    args = sys.argv[1:]
    cols = int(args[args.index("--cols") + 1]) if "--cols" in args else 5
    dpi = int(args[args.index("--dpi") + 1]) if "--dpi" in args else 40
    args = [a for i, a in enumerate(args) if a not in ("--cols", "--dpi") and (i == 0 or args[i - 1] not in ("--cols", "--dpi"))]
    out = Path(args[0])
    out.mkdir(parents=True, exist_ok=True)
    for src in map(Path, args[1:]):
        pdf = out / f"{src.stem}.pdf"
        if not pdf.exists():
            work = Path(tempfile.mkdtemp()) / "deck.pptx"  # a copy: LibreOffice never touches the original
            shutil.copy(src, work)
            try:
                office.slides_to_pdf(work, pdf)
            except Exception as e:  # noqa: BLE001 - a deck LibreOffice cannot open is skipped
                print("échec", src.name, str(e)[:120])
                continue
        print("ok", src.stem, sheet(pdf, out / f"{src.stem}.png", cols, dpi))
