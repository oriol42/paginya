"""Durable file storage: a local folder in dev, Supabase Storage in production.

On Hugging Face Spaces the disk is wiped at every restart, so anything that can't be rebuilt
(the user's original file, extracted images, shop photos) is kept here; the local disk is a cache.

SUPABASE_URL + SUPABASE_SERVICE_KEY (+ STORAGE_BUCKET) switch to Supabase.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

URL = os.getenv("SUPABASE_URL", "").rstrip("/")
KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET = os.getenv("STORAGE_BUCKET", "files")
REMOTE = bool(URL and KEY)


def _local_root() -> Path:
    from .config import DATA_DIR

    return Path(os.getenv("STORAGE_DIR", DATA_DIR / "objects"))


def _h(extra: dict | None = None) -> dict:
    return {"Authorization": f"Bearer {KEY}", "apikey": KEY, **(extra or {})}


def _safe(key: str) -> str:
    if ".." in key or key.startswith("/"):
        raise ValueError("bad storage key")
    return key


def ensure_bucket(public: bool = False) -> None:
    if not REMOTE:
        return
    r = httpx.get(f"{URL}/storage/v1/bucket/{BUCKET}", headers=_h(), timeout=20)
    if r.status_code == 200:
        return
    httpx.post(f"{URL}/storage/v1/bucket", headers=_h(), json={"id": BUCKET, "name": BUCKET, "public": public}, timeout=20)


def put(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    key = _safe(key)
    if REMOTE:
        r = httpx.post(f"{URL}/storage/v1/object/{BUCKET}/{key}", content=data,
                       headers=_h({"Content-Type": content_type, "x-upsert": "true"}), timeout=60)
        r.raise_for_status()
        return
    path = _local_root() / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def get(key: str) -> bytes | None:
    key = _safe(key)
    if REMOTE:
        r = httpx.get(f"{URL}/storage/v1/object/{BUCKET}/{key}", headers=_h(), timeout=60)
        return r.content if r.status_code == 200 else None
    path = _local_root() / key
    return path.read_bytes() if path.is_file() else None


def list_keys(prefix: str) -> list[str]:
    """Keys directly or indirectly under `prefix` (one level of sub-folders is enough for us)."""
    prefix = _safe(prefix.rstrip("/"))
    if REMOTE:
        out: list[str] = []
        stack = [prefix]
        while stack:
            p = stack.pop()
            r = httpx.post(f"{URL}/storage/v1/object/list/{BUCKET}", headers=_h(), json={"prefix": p, "limit": 1000}, timeout=30)
            if r.status_code != 200:
                continue
            for item in r.json():
                full = f"{p}/{item['name']}"
                if item.get("id") is None:  # a "folder"
                    stack.append(full)
                else:
                    out.append(full)
        return out
    root = _local_root()
    base = root / prefix
    return [str(p.relative_to(root)) for p in base.rglob("*") if p.is_file()] if base.exists() else []


def delete_prefix(prefix: str) -> None:
    keys = list_keys(prefix)
    if not keys:
        return
    if REMOTE:
        httpx.request("DELETE", f"{URL}/storage/v1/object/{BUCKET}", headers=_h(), json={"prefixes": keys}, timeout=30)
        return
    import shutil

    shutil.rmtree(_local_root() / prefix.rstrip("/"), ignore_errors=True)


def public_url(key: str, local_base: str) -> str:
    """URL for public files (bucket must be public in Supabase). `local_base` serves them in dev."""
    key = _safe(key)
    return f"{URL}/storage/v1/object/public/{BUCKET}/{key}" if REMOTE else f"{local_base.rstrip('/')}/{key}"
