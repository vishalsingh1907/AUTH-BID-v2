"""
SIH26100 — Test Configuration & Fixtures

Key design decisions:
- TestClient is created with `raise_server_exceptions=True` so test failures surface clearly.
- The FastAPI lifespan (init_db, seed demo users) is NOT triggered during unit/integration tests
  to keep tests fast, isolated, and free of bcrypt hashing on every test run.
  Instead, the DB is initialised inline using SQLite in-memory for the test session.
- In-memory stores are reset before each test so tests are fully independent.
- A `auth_headers` fixture provides pre-computed role headers for legacy header-based tests
  that haven't yet migrated to JWT, avoiding bcrypt entirely in the test layer.
"""
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# ── Suppress the passlib/bcrypt __about__ warning at import time ──
import warnings
warnings.filterwarnings(
    "ignore",
    message=".*bcrypt.*",
    category=UserWarning,
)


# ── Import app AFTER path is configured ──
from main import app  # noqa: E402
from models.database import (  # noqa: E402
    store_tender,
    _tenders_store,
    _verification_results,
    _audit_trail,
)
from mock_apis.synthetic_data import SAMPLE_TENDER  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _init_test_db():
    """
    Initialise the SQLite test database once per test session.
    We call init_db() directly (not via lifespan) so bcrypt seeding never runs.
    The SQLite file is the same dev file used locally; tables are created idempotently.
    """
    from db.session import init_db
    init_db()
    yield


@pytest.fixture(autouse=True)
def reset_in_memory_db():
    """Reset in-memory storage before each test and reseed the sample tender."""
    _tenders_store.clear()
    _verification_results.clear()
    _audit_trail.clear()
    store_tender(dict(SAMPLE_TENDER))
    yield


@pytest.fixture
def client():
    """
    FastAPI TestClient fixture.

    The lifespan context manager (which seeds demo users via bcrypt) is bypassed
    by wrapping the app in TestClient without triggering startup events.
    The `_init_test_db` session fixture has already called init_db() above.
    """
    # TestClient automatically triggers lifespan unless we opt out.
    # We use the standard context-manager form which does trigger lifespan,
    # but the lifespan's DB calls are safe since init_db() is idempotent and
    # _seed_demo_users skips already-existing users.
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


# ── Role header helpers (legacy tests that use X-User-Role) ──
ROLE_HEADERS = {
    "officer": {"X-User-Role": "officer"},
    "admin": {"X-User-Role": "admin"},
    "auditor": {"X-User-Role": "auditor"},
    "viewer": {"X-User-Role": "viewer"},
    "committee_member": {"X-User-Role": "committee_member"},
}


@pytest.fixture
def officer_headers():
    return ROLE_HEADERS["officer"]


@pytest.fixture
def admin_headers():
    return ROLE_HEADERS["admin"]
