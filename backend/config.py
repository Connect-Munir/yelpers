"""Configuration: reads settings from environment / a local .env file.

Kept dependency-free (no pydantic-settings / python-dotenv needed) so it runs in
the same interpreter as the scraper without extra installs. Defaults target a
stock XAMPP MySQL (host 127.0.0.1:3306, user "root", empty password).
"""

from __future__ import annotations

import os
from pathlib import Path

# Project root = the folder containing scraper.py (one level up from backend/).
BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, ignores blanks and # comments.

    Uses setdefault so real environment variables always win over the file.
    """
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env(BASE_DIR / ".env")

# --- Database (XAMPP MySQL defaults) --------------------------------------- #
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "scraper_db")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    "?charset=utf8mb4"
)

# --- Scraper integration --------------------------------------------------- #
# The backend launches this exact script as a subprocess (same as gui.py),
# so the anti-bot scraper runs unchanged in its own process.
SCRAPER_PATH = BASE_DIR / "scraper.py"
# Per-job CSV files the scraper writes and the backend ingests.
JOBS_DIR = BASE_DIR / "backend" / "_jobs"

# --- CORS ------------------------------------------------------------------ #
# Comma-separated origins; "*" allows any (fine for local dev).
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# --- Auth ------------------------------------------------------------------ #
# Secret used to sign login tokens (JWT). Set SECRET_KEY in .env; the fallback
# only exists so local dev doesn't crash if it's missing.
SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-change-me")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))
