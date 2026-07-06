"""FastAPI application: REST API + serves the web/ frontend.

Run from the project root:
    python -m uvicorn backend.main:app --reload --port 8000
Then open http://127.0.0.1:8000/
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth_routes import router as auth_router
from .config import BASE_DIR, CORS_ORIGINS
from .database import init_db
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("scraper.api")

app = FastAPI(
    title="LeadHarvest API",
    description="REST API for the Yelp lead scraper — trigger scrapes and manage results in MySQL.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    try:
        init_db()
        logger.info("Database tables ready.")
    except Exception as exc:  # noqa: BLE001
        # Don't crash the server if MySQL is down — /api/health will report it
        # and the error is logged so the user can start XAMPP and retry.
        logger.error("Database init failed (is XAMPP MySQL running?): %s", exc)


@app.exception_handler(Exception)
async def _unhandled(request, exc):  # noqa: ANN001
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )


# API first, then the static site as a catch-all at "/".
app.include_router(auth_router)
app.include_router(router)

_WEB_DIR = BASE_DIR / "web"
if _WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
else:
    logger.warning("web/ directory not found at %s — frontend will not be served.", _WEB_DIR)
