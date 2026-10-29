"""Phone photos of real pages, simulated, through the real /scans route: how much of the text comes back, how fast.

Usage: PROPRE_DATA_DIR=<tmp> python photos.py <pdf files...>
Each page is printed at 150 dpi, then "photographed": put on a table, seen at an angle, lit unevenly, a little
blurred, rotated, JPEG-compressed at a phone's size. Score = share of the page's words found back (in order).
"""
import base64, difflib, os, random, re, subprocess, sys, tempfile, time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, "/home/oriol/Documents/propre/api")
os.environ.setdefault("FAPSHI_MODE", "mock")
from fastapi.testclient import TestClient  # noqa: E402
from app import guard  # noqa: E402
from app.main import app  # noqa: E402

guard.LIMITS.clear()
guard.DEFAULT_WRITE = (10**9, 600)


def words(t: str) -> list[str]:
    return re.findall(r"[a-zà-ÿ0-9]{2,}", t.lower())


def photo(page: np.ndarray, rng: random.Random, level: str) -> bytes:
    h, w = page.shape[:2]
    H, W = int(h * 1.35), int(w * 1.35)
    table = np.full((H, W, 3), (rng.randint(60, 140), rng.randint(50, 110), rng.randint(30, 80)), np.uint8)  # wood-ish
    table = cv2.add(table, np.random.default_rng(rng.randint(0, 9999)).integers(0, 30, (H, W, 3), dtype=np.uint8))
    hard = {"easy": 0.03, "phone": 0.07, "bad": 0.12}[level]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    ox, oy = (W - w) / 2, (H - h) / 2
    dst = np.float32([[ox + rng.uniform(-1, 1) * hard * w, oy + rng.uniform(-1, 1) * hard * h] for _ in range(1)] +
                     [[ox + w + rng.uniform(-1, 1) * hard * w, oy + rng.uniform(-1, 1) * hard * h],
                      [ox + w + rng.uniform(-1, 1) * hard * w, oy + h + rng.uniform(-1, 1) * hard * h],
                      [ox + rng.uniform(-1, 1) * hard * w, oy + h + rng.uniform(-1, 1) * hard * h]])
    m = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(cv2.cvtColor(page, cv2.COLOR_GRAY2BGR), m, (W, H), borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), m, (W, H))
    img = np.where(mask[..., None] > 0, warped, table)
    # uneven light: a shadow from one side, a warm tint
    gx = np.linspace(rng.uniform(0.55, 0.85) if level != "easy" else 0.9, 1.0, W)[None, :, None]
    gy = np.linspace(1.0, rng.uniform(0.7, 1.0), H)[:, None, None]
    img = np.clip(img * gx * gy * np.array([0.92, 0.97, 1.0]), 0, 255).astype(np.uint8)
    if level != "easy":
        img = cv2.GaussianBlur(img, (0, 0), {"phone": 0.8, "bad": 1.6}[level])
    img = cv2.resize(img, (3000, int(3000 * H / W)))  # a 12-megapixel phone, roughly
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(60, 85)])
    return jpg.tobytes()


def main(pdfs: list[str]) -> None:
    rng = random.Random(7)
    c = TestClient(app).__enter__()
    tot, n = {}, {}
    for pdf in pdfs:
        pages = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
        for pg in rng.sample(range(2, max(3, pages)), min(2, max(1, pages - 2))):
            truth = subprocess.run(["pdftotext", "-f", str(pg), "-l", str(pg), pdf, "-"], capture_output=True, text=True).stdout
            if len(words(truth)) < 60:
                continue
            with tempfile.TemporaryDirectory() as d:
                subprocess.run(["pdftoppm", "-r", "150", "-gray", "-f", str(pg), "-l", str(pg), "-png", pdf, f"{d}/p"], check=True)
                page = cv2.imread(next(Path(d).glob("p*.png")).as_posix(), cv2.IMREAD_GRAYSCALE)
            for level in ("easy", "phone", "bad"):
                jpg = photo(page, rng, level)
                t = time.time()
                r = c.post("/scans", json={"data": base64.b64encode(jpg).decode(), "kind": "document"})
                dt = time.time() - t
                got = r.json().get("text", "") if r.status_code == 200 else ""
                sm = difflib.SequenceMatcher(a=words(truth), b=words(got), autojunk=False)
                score = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(words(truth)))
                tot[level] = tot.get(level, 0) + score
                n[level] = n.get(level, 0) + 1
                print(f"{Path(pdf).name[:38]:38} p{pg:<3} {level:5} {r.status_code} {dt:5.1f}s mots retrouvés {score:5.1%}"
                      f" redressée={r.json().get('straightened') if r.status_code == 200 else r.text[:60]}", flush=True)
    for level in tot:
        print(f"MOYENNE {level:5}: {tot[level] / n[level]:.1%} sur {n[level]} photos")


if __name__ == "__main__":
    main(sys.argv[1:])
