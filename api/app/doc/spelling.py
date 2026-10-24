"""Spelling and grammar fixes, proposed by an AI and applied only if the user accepts them, one by one.

Paginya never writes for the student: the AI may only fix spelling, agreement, conjugation, accents and
punctuation, in the text's own language (French or English), never rephrase nor translate. Every proposal is
checked here before it reaches the user: one that changes too much, drops a number or an equation is thrown away.
The text leaves our server (Gemini first, Groq if Gemini is busy), so the user is asked first.
"""
from __future__ import annotations

import difflib
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from .scan import ModelNotFound, ScanError, ServiceBusy, _check_response, _try_models

CHUNK_CHARS = 6000
MAX_CHARS = 150_000  # ~ a 25 000-word thesis
FIXABLE = ("paragraph", "heading", "list", "caption", "quote")

PROMPT = (
    "Tu es un correcteur orthographique. Voici des paragraphes numérotés d'un document d'étudiant camerounais, "
    "en français ou en anglais. Corrige UNIQUEMENT : l'orthographe, les accents, les accords, la conjugaison, "
    "la ponctuation et les majuscules fautives. Ne reformule jamais, ne change pas le style, ne traduis pas, "
    "ne remplace pas un mot correct par un synonyme, ne touche pas aux noms propres, sigles, chiffres, références, "
    "formules ni aux repères ⟦…⟧. Garde la langue de chaque paragraphe.\n"
    "Réponds avec un objet JSON {\"fixes\": [{\"i\": numéro, \"t\": \"paragraphe corrigé en entier\"}]} "
    "qui contient seulement les paragraphes où tu as corrigé quelque chose. Aucun autre texte.\n\n"
)


class SpellError(Exception):
    pass


def _ask_gemini(payload: str, key: str) -> str:
    # flash-lite answers in ~3 s; gemini-flash-latest "thinks" for a minute per chunk (25/10/2026): last resort only
    models = [os.getenv("GEMINI_TEXT_MODEL", ""), "gemini-3.5-flash-lite", "gemini-flash-latest"]

    def call(model: str) -> str:
        try:
            r = httpx.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                           headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                           json={"contents": [{"parts": [{"text": PROMPT + payload}]}],
                                 "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}, timeout=120)
        except httpx.HTTPError as exc:
            raise ServiceBusy("Gemini ne répond pas") from exc
        _check_response(r, model)
        try:
            return "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
        except (KeyError, IndexError, ValueError) as exc:
            raise ScanError("réponse vide") from exc

    return _try_models(models, call)


def _ask_groq(payload: str, key: str) -> str:
    models = [os.getenv("GROQ_TEXT_MODEL", ""), "openai/gpt-oss-120b", "openai/gpt-oss-20b"]

    def call(model: str) -> str:
        try:
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions",
                           headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                           json={"model": model, "temperature": 0, "response_format": {"type": "json_object"},
                                 "messages": [{"role": "user", "content": PROMPT + payload}]}, timeout=120)
        except httpx.HTTPError as exc:
            raise ServiceBusy("Groq ne répond pas") from exc
        _check_response(r, model)
        try:
            return r.json()["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, ValueError) as exc:
            raise ScanError("réponse vide") from exc

    return _try_models(models, call)


def ask(payload: str) -> tuple[str, str]:
    """(JSON text, provider) from the first AI that answers."""
    errors = []
    for name, env, fn in (("gemini", "GEMINI_API_KEY", _ask_gemini), ("groq", "GROQ_API_KEY", _ask_groq)):
        key = os.getenv(env, "")
        if not key:
            continue
        try:
            return fn(payload, key), name
        except (ScanError, ModelNotFound, ServiceBusy) as exc:
            errors.append(f"{name} : {exc}")
    raise SpellError("La correction n'est pas disponible pour le moment. Réessaie dans quelques minutes." if errors
                     else "La correction n'est pas encore activée sur le serveur.")


_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_MARK = re.compile(r"⟦eq\d+⟧", re.I)


def acceptable(before: str, after: str) -> bool:
    """A real fix, and only a fix: close to the original, same numbers, same equations."""
    after = after.strip()
    if not after or after == before.strip():
        return False
    if sorted(_NUM.findall(before)) != sorted(_NUM.findall(after)) or sorted(_MARK.findall(before)) != sorted(_MARK.findall(after)):
        return False
    if not 0.85 <= len(after) / max(1, len(before)) <= 1.15:
        return False
    if abs(len(after.split()) - len(before.split())) > max(2, len(before.split()) // 10):
        return False
    return difflib.SequenceMatcher(None, before, after, autojunk=False).ratio() >= 0.85


def _chunks(items: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    out, cur, size = [], [], 0
    for i, t in items:
        if cur and size + len(t) > CHUNK_CHARS:
            out.append(cur)
            cur, size = [], 0
        cur.append((i, t))
        size += len(t)
    return out + ([cur] if cur else [])


def propose(blocks: list[dict], on_call=None) -> list[dict]:
    """[{"block": index, "before": text, "after": text}] for every accepted fix, in document order."""
    items = [(i, b["text"]) for i, b in enumerate(blocks)
             if b.get("type") in FIXABLE and not b.get("hidden") and len((b.get("text") or "").strip()) >= 3]
    if sum(len(t) for _, t in items) > MAX_CHARS:
        raise SpellError("Document trop long pour la correction automatique (25 000 mots au plus).")
    texts = dict(items)

    def run(chunk: list[tuple[int, str]]) -> list[dict] | None:
        payload = "\n".join(json.dumps({"i": i, "t": t}, ensure_ascii=False) for i, t in chunk)
        try:
            raw, provider = ask(payload)
        except SpellError:
            return None  # this part stays as it is; the others are still proposed
        if on_call:
            on_call(provider)
        try:
            fixes = json.loads(raw).get("fixes", [])
        except (ValueError, AttributeError):
            return []
        out = []
        for f in fixes if isinstance(fixes, list) else []:
            i, t = f.get("i") if isinstance(f, dict) else None, f.get("t") if isinstance(f, dict) else None
            if isinstance(i, int) and i in texts and isinstance(t, str) and acceptable(texts[i], t):
                out.append({"block": i, "before": texts[i], "after": t.strip()})
        return out

    chunks = _chunks(items)
    if not chunks:
        return []
    with ThreadPoolExecutor(max_workers=3) as pool:  # a few calls at once: the free quotas allow it, the user waits less
        results = list(pool.map(run, chunks))
    if all(r is None for r in results):
        ask("")  # every call failed: raises the reason (quota, no key)
    return sorted((f for r in results if r for f in r), key=lambda f: f["block"])
