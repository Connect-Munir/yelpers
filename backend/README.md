# LeadHarvest backend (FastAPI + MySQL)

A FastAPI service that drives the Yelp scraper, stores results in MySQL (XAMPP),
and serves the `web/` frontend.

## Architecture

```
web/ (frontend)  ──fetch /api──▶  FastAPI (backend/)  ──subprocess──▶  scraper.py ──▶ per-job CSV
                                        │                                                 │
                                        └──────────── ingest (upsert on Yelp URL) ───────┘
                                                          ▼
                                                    MySQL: scraper_db.businesses
```

The scraper is launched as a **subprocess** (same pattern as `gui.py`), so the
anti-bot Selenium code runs unchanged. Each job writes its own CSV, which the
backend ingests into MySQL, de-duplicating on `Yelp URL`.

## Prerequisites

1. **XAMPP MySQL running**, with a database named `scraper_db`.
2. Python deps (installed into the same interpreter that runs the scraper):
   ```powershell
   python -m pip install -r requirements.txt
   ```

## Configure

Defaults target a stock XAMPP MySQL (user `root`, no password). Override in
`.env` at the project root if needed:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=scraper_db
```

## Run

From the project root:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
```

Then open **http://127.0.0.1:8000/** — the frontend, API and Swagger docs
(`/docs`) are all served from there. Tables are created automatically on startup.

> When you hit **Run scrape now**, a real Chrome window opens on this machine.
> If Yelp shows a CAPTCHA, solve it once in that window — the scraper continues
> automatically and saves leads to MySQL.

## API

| Method | Path                       | Purpose                                  |
|--------|----------------------------|------------------------------------------|
| GET    | `/api/health`              | Liveness + DB connectivity               |
| GET    | `/api/stats`               | Lead/niche/website/phone counts          |
| GET    | `/api/businesses`          | List leads (`limit`,`offset`,`niche`,`search`) |
| GET    | `/api/businesses.csv`      | Export leads as CSV                       |
| DELETE | `/api/businesses/{id}`     | Delete a lead                            |
| POST   | `/api/scrape`              | Start a scrape job                       |
| GET    | `/api/scrape`              | List jobs                                |
| GET    | `/api/scrape/{id}`         | Job status + live log + previews         |
| POST   | `/api/scrape/{id}/stop`    | Stop a running job (saves what it has)   |

## Layout

```
backend/
├── main.py       FastAPI app, CORS, startup, static mount
├── config.py     env/.env settings (DB URL, paths)
├── database.py   SQLAlchemy engine/session, init_db
├── models.py     Business ORM model
├── schemas.py    Pydantic request/response schemas
├── crud.py       queries + upsert (dedup on Yelp URL)
├── jobs.py       JobManager: runs scraper subprocess, ingests CSV
└── routes.py     API endpoints
```
