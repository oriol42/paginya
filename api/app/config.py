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

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# Paid orders stay downloadable/editable this long (decision: 7 days).
ORDER_VALIDITY_DAYS = 7
