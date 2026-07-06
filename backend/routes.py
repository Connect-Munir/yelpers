"""API endpoints. All mounted under /api."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from . import crud
from .database import get_db
from .jobs import manager
from .schemas import (
    BusinessListOut,
    BusinessOut,
    JobOut,
    ScrapeRequest,
    StatsOut,
)

router = APIRouter(prefix="/api", tags=["scraper"])


# --- health & stats -------------------------------------------------------- #
@router.get("/health")
def health() -> dict:
    """Liveness probe + DB connectivity check."""
    db_ok = True
    detail = "ok"
    try:
        db = next(get_db())
        crud.get_stats(db)
        db.close()
    except Exception as exc:  # noqa: BLE001
        db_ok = False
        detail = str(exc)
    return {"status": "ok", "database": db_ok, "detail": detail}


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)) -> StatsOut:
    return StatsOut(**crud.get_stats(db))


# --- businesses ------------------------------------------------------------ #
@router.get("/businesses", response_model=BusinessListOut)
def list_businesses(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    niche: str | None = Query(None),
    search: str | None = Query(None, description="Match company name or location."),
) -> BusinessListOut:
    items, total = crud.list_businesses(
        db, limit=limit, offset=offset, niche=niche, search=search
    )
    return BusinessListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[BusinessOut.model_validate(b) for b in items],
    )


@router.get("/businesses.csv")
def export_csv(
    db: Session = Depends(get_db),
    niche: str | None = Query(None),
    search: str | None = Query(None),
) -> StreamingResponse:
    """Download the current results as an Excel-friendly CSV."""
    items, _ = crud.list_businesses(db, limit=100000, offset=0, niche=niche, search=search)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["Business Niche", "Company Name", "Location: USA", "Phone Number", "Yelp URL", "Website URL"]
    )
    for b in items:
        writer.writerow([b.niche, b.company_name, b.location, b.phone, b.yelp_url, b.website_url])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


@router.delete("/businesses/{business_id}")
def delete_business(business_id: int, db: Session = Depends(get_db)) -> dict:
    if not crud.delete_business(db, business_id):
        raise HTTPException(status_code=404, detail=f"Business {business_id} not found")
    return {"success": True, "deleted": business_id}


# --- scrape jobs ----------------------------------------------------------- #
@router.post("/scrape", response_model=JobOut, status_code=202)
def start_scrape(req: ScrapeRequest) -> JobOut:
    job = manager.start(
        term=req.term,
        location=req.location,
        max_results=req.max_results,
        max_all=req.max_all,
        headless=req.headless,
    )
    return JobOut(**job.to_dict())


@router.get("/scrape", response_model=list[JobOut])
def list_jobs() -> list[JobOut]:
    return [JobOut(**j.to_dict()) for j in manager.list()]


@router.get("/scrape/{job_id}", response_model=JobOut)
def get_job(job_id: str) -> JobOut:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobOut(**job.to_dict())


@router.post("/scrape/{job_id}/stop", response_model=JobOut)
def stop_job(job_id: str) -> JobOut:
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    manager.stop(job_id)
    return JobOut(**job.to_dict())
