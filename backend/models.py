"""SQLAlchemy ORM models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .database import Base

# Allowed roles — single source of truth.
ROLE_USER = "user"
ROLE_ADMIN = "admin"
VALID_ROLES = {ROLE_USER, ROLE_ADMIN}


class User(Base):
    """An account that can log in. Separate from Business (scraped data).

    Authorization always reads ``role`` from this row at request time (never
    from the token), so promoting/demoting a user takes effect immediately.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=ROLE_USER, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @property
    def is_admin(self) -> bool:
        return self.role == ROLE_ADMIN


class Business(Base):
    """One scraped Yelp business. Mirrors the scraper's CSV columns.

    ``yelp_url`` is unique — it's the de-dup key, so re-scraping a business
    refreshes its row instead of inserting a duplicate (matching the scraper's
    own CSV append behaviour).
    """

    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    niche = Column(String(255), index=True, nullable=False, default="")
    company_name = Column(String(512), index=True, nullable=False, default="")
    location = Column(String(512), nullable=False, default="")
    phone = Column(String(64), nullable=False, default="")
    yelp_url = Column(String(512), unique=True, index=True, nullable=False)
    website_url = Column(String(1024), nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
