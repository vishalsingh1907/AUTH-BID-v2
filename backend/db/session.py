"""
SIH26100 — Database Session & Engine Configuration
Supports PostgreSQL via SQLAlchemy 2.0 with automatic SQLite fallback for local demo/testing.

Priority:
  1. PostgreSQL — when USE_POSTGRES=1 env var is set or ENVIRONMENT=production
  2. SQLite   — automatic fallback for demo/dev without Docker
"""
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from config import settings
from models.orm import Base
import os
import logging

logger = logging.getLogger(__name__)

# ── Determine DB URL ──
SYNC_DB_URL = settings.DATABASE_URL_SYNC

use_postgres = (
    os.environ.get("USE_POSTGRES", "").lower() in ("1", "true", "yes")
    or settings.ENVIRONMENT.lower() in ("production", "prod")
)

if not use_postgres:
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), "..", "authbid_dev.db")
    SYNC_DB_URL = f"sqlite:///{os.path.abspath(SQLITE_PATH)}"
    logger.info(f"[DB] Using SQLite fallback: {SYNC_DB_URL}")
else:
    logger.info(f"[DB] Using PostgreSQL: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}")

_connect_args = {}
if "sqlite" in SYNC_DB_URL:
    _connect_args = {"check_same_thread": False}

sync_engine = create_engine(
    SYNC_DB_URL,
    echo=False,
    connect_args=_connect_args,
    # Pool settings for multi-worker safety
    pool_pre_ping=True,
)

SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine,
    expire_on_commit=False,
)


def init_db() -> None:
    """
    Create all tables in the configured database.
    Idempotent — safe to call on every startup.
    Uses SQLAlchemy metadata to create missing tables without destroying existing data.
    """
    Base.metadata.create_all(bind=sync_engine)
    logger.info("[DB] Database initialized — all tables ensured.")


def get_sync_db() -> Generator[Session, None, None]:
    """FastAPI dependency for synchronous DB sessions."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> dict:
    """Check database connectivity. Returns status dict."""
    try:
        with sync_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "engine": SYNC_DB_URL.split("://")[0]}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
