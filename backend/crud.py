"""Database operations for Business rows."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Business

# CSV header -> model attribute. Keeps the scraper's column names as the
# single source of truth (see scraper.CSV_FIELDS).
CSV_TO_FIELD = {
    "Business Niche": "niche",
    "Company Name": "company_name",
    "Location: USA": "location",
    "Phone Number": "phone",
    "Yelp URL": "yelp_url",
    "Website URL": "website_url",
}


def upsert_business(db: Session, row: dict) -> tuple[Business, bool]:
    """Insert or refresh a business keyed on its Yelp URL.

    ``row`` uses the scraper's CSV column names. Returns (obj, created).
    Caller is responsible for committing.
    """
    data = {field: (row.get(col) or "").strip() for col, field in CSV_TO_FIELD.items()}
    yelp_url = data.get("yelp_url", "")
    if not yelp_url:
        raise ValueError("row has no Yelp URL")

    existing = db.scalar(select(Business).where(Business.yelp_url == yelp_url))
    if existing is None:
        obj = Business(**data)
        db.add(obj)
        # Flush so a later upsert of the same URL in this batch finds it
        # (the session has autoflush off, and SELECTs won't see pending rows).
        db.flush()
        return obj, True

    # Refresh — newest scrape wins (but never blank out a value with an empty one).
    for field, value in data.items():
        if field == "yelp_url":
            continue
        if value:
            setattr(existing, field, value)
    return existing, False


def list_businesses(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    niche: str | None = None,
    search: str | None = None,
) -> tuple[list[Business], int]:
    """Return (page, total) with optional niche filter and free-text search."""
    stmt = select(Business)
    count_stmt = select(func.count(Business.id))

    if niche:
        stmt = stmt.where(Business.niche == niche)
        count_stmt = count_stmt.where(Business.niche == niche)
    if search:
        like = f"%{search}%"
        cond = Business.company_name.like(like) | Business.location.like(like)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    stmt = stmt.order_by(Business.updated_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all()), total


def get_business(db: Session, business_id: int) -> Business | None:
    return db.get(Business, business_id)


def delete_business(db: Session, business_id: int) -> bool:
    obj = db.get(Business, business_id)
    if obj is None:
        return False
    db.delete(obj)
    db.commit()
    return True


def get_stats(db: Session) -> dict:
    total = db.scalar(select(func.count(Business.id))) or 0
    niches = db.scalar(select(func.count(func.distinct(Business.niche)))) or 0
    with_website = db.scalar(
        select(func.count(Business.id)).where(Business.website_url != "")
    ) or 0
    with_phone = db.scalar(
        select(func.count(Business.id)).where(Business.phone != "")
    ) or 0
    return {
        "total_leads": total,
        "total_niches": niches,
        "with_website": with_website,
        "with_phone": with_phone,
    }
