"""
SIH26100 — Database Session & Engine Configuration
Supports PostgreSQL via SQLAlchemy 2.0 with automatic SQLite fallback for local demo/testing without external Docker.
"""
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from models.orm import Base
import os

# ── Sync Engine (for migrations, sync tasks, and SQLite fallback) ──
SYNC_DB_URL = settings.DATABASE_URL_SYNC

# Fallback to local SQLite if PostgreSQL is not running or in demo mode without container
if settings.ENVIRONMENT == "development" and not os.environ.get("USE_POSTGRES"):
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "authbid_dev.db")
    SYNC_DB_URL = f"sqlite:///{os.path.abspath(SQLITE_PATH)}"

sync_engine = create_engine(
    SYNC_DB_URL,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in SYNC_DB_URL else {},
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    expire_on_commit=False,
)


def init_db():
    """Create all tables in the configured database."""
    Base.metadata.create_all(bind=sync_engine)


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency for synchronous DB sessions."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()
