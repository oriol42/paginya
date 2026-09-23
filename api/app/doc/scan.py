"""Photos of pages -> straightened image -> text.

1. straighten(): finds the sheet in the photo (largest 4-corner shape), corrects
   the perspective like CamScanner, evens out the lighting.
2. ocr_local(): Tesseract on our own server (free, nothing leaves the server).
   Default for every page; very good on printed text.
3. read_text(): Gemini (free tier), only for handwritten pages, only with the
   user's explicit consent since the image leaves our server (docs/JURIDIQUE.md).
"""
from __future__ import annotations

import base64
import csv
import io
import os
import re
import subprocess
import tempfile

import cv2
import httpx
import numpy as np
from PIL import Image, ImageOps

MAX_SIDE = 2000

PROMPT = (
    "Tu es un outil de transcription. Recopie EXACTEMENT le texte de cette page (imprimée ou manuscrite), "
    "en français ou en anglais, sans corriger, sans reformuler, sans ajouter de commentaire.\n"
    "- Un paragraphe par bloc, séparés par une ligne vide.\n"
    "- Garde les titres sur leur propre ligne, avec leur numérotation (I., A., 1.1, CHAPITRE…).\n"
    "- Garde les tirets et numéros des listes en début de ligne.\n"
    "- Pour un tableau : une ligne par rangée, cellules séparées par une tabulation.\n"
    "- Si un mot est illisible, écris [illisible].\n"
    "Réponds uniquement avec le texte transcrit."
)


class ScanError(RuntimeError):
    pass


class OcrUnavailable(ScanError):
    pass


def _order_corners(pts: np.ndarray) -> np.ndarray:
    pts = pts.reshape(4, 2).astype("float32")
    s, d = pts.sum(axis=1), np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")


def _find_sheet(img: np.ndarray) -> np.ndarray | None:
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        if cv2.contourArea(c) < 0.2 * w * h:
            break
        approx = cv2.approxPolyDP(c, 0.02 * cv2.arcLength(c, True), True)
        if len(approx) == 4 and cv2.isContourConvex(approx):
            return _order_corners(approx)
    return None


def straighten(data: bytes) -> tuple[bytes, bool]:
    """Returns (jpeg bytes of the cleaned page, whether a sheet outline was found)."""
    try:
        pil = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    except Exception as exc:  # not an image
        raise ScanError("Cette image est illisible") from exc
    pil.thumbnail((MAX_SIDE, MAX_SIDE))
    img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    corners = _find_sheet(img)
    if corners is not None:
        tl, tr, br, bl = corners
        width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
        target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype="float32")
        img = cv2.warpPerspective(img, cv2.getPerspectiveTransform(corners, target), (width, height))

    # Even out lighting (shadows from the phone) without destroying handwriting.
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    l_chan = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l_chan)
    img = cv2.cvtColor(cv2.merge((l_chan, a_chan, b_chan)), cv2.COLOR_LAB2BGR)
    ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if not ok:
        raise ScanError("Traitement de l'image impossible")
    return jpeg.tobytes(), corners is not None


def read_text(jpeg: bytes) -> str:
    provider = os.getenv("OCR_PROVIDER", "gemini")
    if provider == "mock":
        return "TEXTE LU (simulation)\nCeci est le texte transcrit de la page."
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise OcrUnavailable(
            "La lecture des photos n'est pas encore activée (clé Gemini manquante dans api/.env)."
        )
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [
                    {"text": PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                ]}],
                "generationConfig": {"temperature": 0},
            },
            timeout=90,
        )
    except httpx.HTTPError as exc:
        raise ScanError("Le service de lecture ne répond pas, réessaie") from exc
    if resp.status_code == 429:
        raise ScanError("Trop de pages lues aujourd'hui, réessaie dans un moment")
    if resp.status_code != 200:
        raise ScanError(f"Lecture impossible ({resp.status_code})")
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ScanError("La page n'a pas pu être lue (photo trop floue ?)") from exc
    return "\n".join(p.get("text", "") for p in parts).strip()


def ocr_local(jpeg: bytes) -> tuple[str, float]:
    """Tesseract (fra+eng). Returns (text, mean word confidence 0-100)."""
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ScanError("Cette image est illisible")
    if max(img.shape) < 1600:  # small photos: upscale, Tesseract likes ~300 dpi
        f = 1600 / max(img.shape)
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
        cv2.imwrite(tmp.name, img)
        try:
            out = subprocess.run(
                ["tesseract", tmp.name, "-", "-l", "fra+eng", "--psm", "3", "tsv"],
                capture_output=True, timeout=120, check=True,
            ).stdout.decode("utf-8", "replace")
        except FileNotFoundError as exc:
            raise OcrUnavailable("Tesseract n'est pas installé sur le serveur") from exc
        except subprocess.SubprocessError as exc:
            raise ScanError("Lecture impossible, réessaie avec une photo plus nette") from exc
    return _tsv_to_text(out)


def _tsv_to_text(tsv: str) -> tuple[str, float]:
    """Rebuild paragraphs from Tesseract's words.

    Tesseract gives visual lines. A line that reaches (almost) the right margin
    and doesn't end a sentence continues on the next line: we join them, so the
    detector sees real paragraphs (a wrapped line is not a new heading).
    """
    lines: dict[tuple, dict] = {}
    order: list[tuple] = []
    confs: list[float] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        word = (row.get("text") or "").strip()
        if row.get("level") != "5" or not word:
            continue
        key = (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))
        right = int(row["left"]) + int(row["width"])
        if key not in lines:
            lines[key] = {"words": [], "left": int(row["left"]), "right": right}
            order.append(key)
        entry = lines[key]
        entry["words"].append(word)
        entry["right"] = max(entry["right"], right)
        try:
            confs.append(float(row["conf"]))
        except (TypeError, ValueError):
            pass
    if not order:
        return "", 0.0
    margin_right = max(v["right"] for v in lines.values())
    margin_left = min(v["left"] for v in lines.values())
    width = max(1, margin_right - margin_left)

    paragraphs: list[str] = []
    current = ""
    prev_key = None
    for key in order:
        entry = lines[key]
        text = " ".join(entry["words"])
        continues = (
            current
            and prev_key is not None
            and key[:2] == prev_key[:2]
            and lines[prev_key]["right"] >= margin_left + 0.85 * width
            and not re.search(r"[.:;!?]$", current)
        )
        if continues:
            current = current[:-1] + text if current.endswith("-") else f"{current} {text}"
        else:
            if current:
                paragraphs.append(current)
            current = text
        prev_key = key
    if current:
        paragraphs.append(current)
    return "\n\n".join(paragraphs), (sum(confs) / len(confs) if confs else 0.0)
