"""SQLAlchemy engine, session factory and the declarative Base.

Synchronous SQLAlchemy (pymysql driver). Route handlers are plain ``def`` so
FastAPI runs them in its threadpool — that keeps the sync DB calls off the async
event loop, which is the correct pairing for a sync driver.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # transparently revive stale MySQL connections
    pool_recycle=3600,     # recycle hourly (MySQL drops idle conns)
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist. Imports models for registration."""
    from . import models  # noqa: F401  (registers ORM classes on Base.metadata)

    Base.metadata.create_all(bind=engine)
