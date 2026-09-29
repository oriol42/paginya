"""Abuse protection for a free server: per-IP limits on actions that cost work, and security headers.

Limits are counted in memory (one small server): enough to stop a script flooding the API,
never reached by a real person. Behind Render's proxy the client IP is the first X-Forwarded-For entry.
"""
from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse

# (method, path regex, max requests, window in seconds): first match wins; other writes share DEFAULT_WRITE
LIMITS: list[tuple[str, str, int, int]] = []
DEFAULT_WRITE = (120, 600)

HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}

_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_lock = threading.Lock()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else "") or (request.client.host if request.client else "?")


def _rule(method: str, path: str) -> tuple[str, int, int] | None:
    for m, pattern, n, window in LIMITS:
        if method == m and re.fullmatch(pattern, path):
            return f"{m}:{pattern}", n, window
    if method in ("POST", "PUT", "DELETE", "PATCH"):
        return "write", *DEFAULT_WRITE
    return None


def allowed(ip: str, bucket: str, n: int, window: int, now: float | None = None) -> bool:
    now = now or time.time()
    with _lock:
        q = _hits[(ip, bucket)]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= n:
            return False
        q.append(now)
        if len(_hits) > 50_000:  # never grow without bound
            _hits.clear()
        return True


async def middleware(request: Request, call_next):
    ip = client_ip(request)
    # payment notifications are signed and must never be refused; the test client is not a visitor
    rule = None if request.url.path.startswith("/webhooks") or ip == "testclient" else _rule(request.method, request.url.path)
    if rule and not allowed(ip, *rule):
        return JSONResponse({"detail": "Trop de demandes d'un coup. Attends quelques minutes puis réessaie."}, status_code=429)
    response = await call_next(request)
    for k, v in HEADERS.items():
        response.headers.setdefault(k, v)
    return response
