"""Configuration read from environment variables (see .env.example)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

FONTS_DIR = BASE_DIR / "fonts"
DATA_DIR = Path(os.getenv("PROPRE_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "propre.sqlite3"

# "mock" simulates payments locally (no Fapshi keys needed),
# "sandbox" and "live" call Fapshi for real.
FAPSHI_MODE = os.getenv("FAPSHI_MODE", "mock")
FAPSHI_BASE_URL = {
    "sandbox": "https://sandbox.fapshi.com",
    "live": "https://live.fapshi.com",
}.get(FAPSHI_MODE, "")
FAPSHI_API_USER = os.getenv("FAPSHI_API_USER", "")
FAPSHI_API_KEY = os.getenv("FAPSHI_API_KEY", "")
FAPSHI_WEBHOOK_SECRET = os.getenv("FAPSHI_WEBHOOK_SECRET", "")
# "direct": the customer confirms on their phone (needs Fapshi's approval); "link": Fapshi's payment page;
# "auto": direct, and the payment page while Fapshi has not activated direct-pay.
FAPSHI_PAY_METHOD = os.getenv("FAPSHI_PAY_METHOD", "auto")
# One Fapshi service can be shared by several apps: each payment's externalId starts with the app's prefix,
# and the app that receives the webhook forwards the others (FAPSHI_FORWARD = "AF=https://.../webhooks/fapshi").
FAPSHI_PREFIX = os.getenv("FAPSHI_PREFIX", "PG")
FAPSHI_FORWARD = dict(x.split("=", 1) for x in os.getenv("FAPSHI_FORWARD", "").split(",") if "=" in x)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# The team's own documents are free: this code (typed once on /admin) unlocks an order without paying. Empty = off.
ADMIN_CODE = os.getenv("ADMIN_CODE", "")

# Paid orders stay downloadable/editable this long (decision: 7 days).
ORDER_VALIDITY_DAYS = 7
