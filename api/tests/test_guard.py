"""Abuse protection: per-IP limits and security headers."""
from fastapi.testclient import TestClient

from app import guard
from app.main import app


def test_limit_per_ip_and_window():
    assert all(guard.allowed("1.2.3.4", "t", 3, 60, now=100 + i) for i in range(3))
    assert not guard.allowed("1.2.3.4", "t", 3, 60, now=104)  # 4th in the window: refused
    assert guard.allowed("5.6.7.8", "t", 3, 60, now=104)  # another visitor is not affected
    assert guard.allowed("1.2.3.4", "t", 3, 60, now=200)  # window passed


def test_routes_have_their_own_limits():
    assert guard._rule("POST", "/documents")[1] == 30
    assert guard._rule("POST", "/documents/abc/render")[1] == 150
    assert guard._rule("PUT", "/documents/abc")[0] == "write"
    assert guard._rule("GET", "/documents/abc") is None


def test_security_headers():
    r = TestClient(app).get("/health")
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"
