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


class ModelNotFound(ScanError):
    """The provider answered 404: the model name is wrong or retired."""


def _check_response(resp: httpx.Response, model: str = "") -> None:
    if resp.status_code == 429:
        raise ScanError("Trop de pages lues aujourd'hui, réessaie dans un moment")
    if resp.status_code == 404:
        raise ModelNotFound(f"modèle introuvable ({model or '404'})")
    if resp.status_code in (400, 401, 403):
        try:
            detail = str(resp.json()["error"]["message"])[:120]
        except (KeyError, ValueError, TypeError):
            detail = ""
        raise ScanError(f"clé refusée ou requête invalide ({resp.status_code}) {detail}".strip())
    if resp.status_code != 200:
        raise ScanError(f"Lecture impossible ({resp.status_code})")


def _read_gemini(jpeg: bytes, key: str, prompt: str = PROMPT) -> str:
    """Tries the configured model, then the usual names if Google says the model does not exist."""
    models = [m for m in dict.fromkeys([os.getenv("GEMINI_MODEL", "").strip(), "gemini-flash-latest", "gemini-2.5-flash"]) if m]
    for i, model in enumerate(models):
        try:
            return _gemini_call(jpeg, key, prompt, model)
        except ModelNotFound:
            if i == len(models) - 1:
                raise
    raise ScanError("Lecture impossible")


def _gemini_call(jpeg: bytes, key: str, prompt: str, model: str) -> str:
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={
                "contents": [{"parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg).decode()}},
                ]}],
                "generationConfig": {"temperature": 0},
            },
            timeout=90,
        )
    except httpx.HTTPError as exc:
        raise ScanError("Le service de lecture ne répond pas, réessaie") from exc
    _check_response(resp, model)
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, ValueError) as exc:
        raise ScanError("La page n'a pas pu être lue (photo trop floue ?)") from exc
    return "\n".join(p.get("text", "") for p in parts).strip()


def _read_openai_compatible(jpeg: bytes, key: str, base_url: str, model: str, prompt: str = PROMPT) -> str:
    """Groq and OpenRouter both speak the OpenAI chat-completions format."""
    data_url = "data:image/jpeg;base64," + base64.b64encode(jpeg).decode()
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]}],
            },
            timeout=90,
        )
    except httpx.HTTPError as exc:
        raise ScanError("Le service de lecture ne répond pas, réessaie") from exc
    _check_response(resp, model)
    try:
        return (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise ScanError("La page n'a pas pu être lue (photo trop floue ?)") from exc


def _read_groq(jpeg: bytes, key: str, prompt: str = PROMPT) -> str:
    model = os.getenv("GROQ_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
    return _read_openai_compatible(jpeg, key, "https://api.groq.com/openai/v1", model, prompt)


def _read_openrouter(jpeg: bytes, key: str, prompt: str = PROMPT) -> str:
    model = os.getenv("OPENROUTER_MODEL", "google/gemma-3-27b-it:free")
    return _read_openai_compatible(jpeg, key, "https://openrouter.ai/api/v1", model, prompt)


# name -> (environment variable holding the key, reader)
PROVIDERS = {
    "gemini": ("GEMINI_API_KEY", _read_gemini),
    "groq": ("GROQ_API_KEY", _read_groq),
    "openrouter": ("OPENROUTER_API_KEY", _read_openrouter),
}


def read_text_with_engine(jpeg: bytes, prompt: str | None = None) -> tuple[str, str]:
    """Reads a page with the first provider that works. Returns (text, provider name).

    `prompt` replaces the default transcription instructions (used for exam papers).

    Order comes from OCR_PROVIDERS (default "gemini,groq,openrouter"). A provider
    without a key is skipped; a provider that fails (quota, outage) hands over
    to the next one. Only if all of them fail does the last error reach the user.
    """
    if os.getenv("OCR_PROVIDER") == "mock":
        return "TEXTE LU (simulation)\nCeci est le texte transcrit de la page.", "mock"
    order = [n.strip() for n in os.getenv("OCR_PROVIDERS", "gemini,groq,openrouter").split(",") if n.strip()]
    errors: list[str] = []
    tried = False
    for name in order:
        if name not in PROVIDERS:
            continue
        env_var, reader = PROVIDERS[name]
        key = os.getenv(env_var, "")
        if not key:
            continue
        tried = True
        try:
            return reader(jpeg, key, prompt or PROMPT), name
        except ScanError as exc:
            errors.append(f"{name} : {exc}")
    if not tried:
        raise OcrUnavailable(
            "La lecture des photos n'est pas encore activée (ajoute une clé dans api/.env : "
            "GEMINI_API_KEY, GROQ_API_KEY ou OPENROUTER_API_KEY)."
        )
    raise ScanError(" | ".join(errors) or "Lecture impossible")


def read_text(jpeg: bytes) -> str:
    return read_text_with_engine(jpeg)[0]

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
