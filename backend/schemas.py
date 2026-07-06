"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScrapeRequest(BaseModel):
    """Body for POST /api/scrape — mirrors the scraper's CLI flags."""

    term: str = Field(..., min_length=1, max_length=255, description="Search niche, e.g. 'plumbers'.")
    location: str = Field(..., min_length=1, max_length=255, description="City/region, e.g. 'Austin, TX'.")
    max_results: int = Field(20, ge=1, le=1000, description="Cap on businesses to scrape.")
    max_all: bool = Field(False, description="Scrape every result Yelp returns (ignores max_results).")
    headless: bool = Field(False, description="Run Chrome without a window (can't solve CAPTCHAs).")


class BusinessOut(BaseModel):
    """A business row returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    niche: str
    company_name: str
    location: str
    phone: str
    yelp_url: str
    website_url: str
    created_at: datetime
    updated_at: datetime


class BusinessListOut(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[BusinessOut]


class StatsOut(BaseModel):
    total_leads: int
    total_niches: int
    with_website: int
    with_phone: int


class JobOut(BaseModel):
    """Live status of a scrape job."""

    id: str
    status: str  # queued | running | done | error | stopped
    term: str
    location: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    scraped: int = 0          # rows the scraper reported finding
    imported: int = 0         # rows written to MySQL
    return_code: int | None = None
    message: str = ""
    log: list[str] = []       # tail of the scraper's console output
    previews: list[dict] = [] # lightweight {name, phone, website} for live display
