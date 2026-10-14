"""Contact sheet of a PDF: python sheet.py in.pdf out.png [first] [count] [cols]"""
import subprocess, sys, tempfile, glob
from PIL import Image
pdf, out = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 1
count = int(sys.argv[4]) if len(sys.argv) > 4 else 8
cols = int(sys.argv[5]) if len(sys.argv) > 5 else 4
d = tempfile.mkdtemp()
subprocess.run(["pdftoppm", "-r", "58", "-f", str(first), "-l", str(first + count - 1), "-png", pdf, d + "/p"], check=True)
ims = [Image.open(f) for f in sorted(glob.glob(d + "/p*.png"))]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (w + 6), rows * (h + 6)), "#666")
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * (w + 6) + 3, (i // cols) * (h + 6) + 3))
sheet.save(out)
