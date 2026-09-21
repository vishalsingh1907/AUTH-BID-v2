"""
SIH26100 — AuthBid API
AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement

Main FastAPI application entry point.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings, validate_startup_config
from db.session import init_db, get_sync_db, check_db_health
from mock_apis.synthetic_data import SAMPLE_TENDER

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ── Routers ──
from routers.auth import router as auth_router
from routers.tenders import router as tenders_router
from routers.bidders import router as bidders_router
from routers.verification import router as verification_router
from routers.graph import router as graph_router
from mock_apis.gst_api import router as gst_router
from mock_apis.pan_api import router as pan_router
from mock_apis.udyam_api import router as udyam_router
from mock_apis.mca_api import router as mca_router
from mock_apis.blacklist_api import router as blacklist_router


def _seed_demo_users(db) -> None:
    """Seed the 4 demo users into the database if they don't already exist."""
    from repositories.user_repo import get_or_create_default_org, user_exists, create_user
    from services.auth_service import hash_password, DEMO_USERS

    org = get_or_create_default_org(db)
    for u in DEMO_USERS:
        if not user_exists(db, u["email"]):
            create_user(
                db=db,
                user_id=u["id"],
                org_id=org.id,
                email=u["email"],
                name=u["name"],
                role=u["role"],
                hashed_password=hash_password(u["password"]),
            )
            logger.info(f"[SEED] Created demo user: {u['email']} (role={u['role']})")


def _seed_demo_tender(db) -> None:
    """Seed the sample tender into the database if it doesn't exist."""
    from models.orm import Tender
    from models.database import store_tender

    # Also keep in-memory store for backward compat with existing routers
    store_tender(SAMPLE_TENDER)

    existing = db.query(Tender).filter(
        Tender.tender_id == SAMPLE_TENDER["tender_id"]
    ).first()
    if not existing:
        tender_orm = Tender(
            tender_id=SAMPLE_TENDER["tender_id"],
            title=SAMPLE_TENDER["title"],
            category=SAMPLE_TENDER["category"],
            estimated_value=SAMPLE_TENDER["estimated_value"],
            currency=SAMPLE_TENDER.get("currency", "INR"),
            published_date=SAMPLE_TENDER.get("published_date", "2026-01-15"),
            closing_date=SAMPLE_TENDER.get("closing_date", "2026-02-28"),
            ministry=SAMPLE_TENDER.get("ministry"),
            department=SAMPLE_TENDER.get("department"),
            description=SAMPLE_TENDER.get("description", ""),
            eligibility_criteria=SAMPLE_TENDER.get("eligibility_criteria", {}),
            status="active",
        )
        db.add(tender_orm)
        db.commit()
        logger.info(f"[SEED] Created demo tender: {SAMPLE_TENDER['tender_id']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: validate config, initialize DB, seed demo data."""
    validate_startup_config(settings)

    # Initialize database tables (idempotent)
    init_db()

    # Check DB health
    health = check_db_health()
    if health["status"] != "healthy":
        logger.error(f"[STARTUP] DB health check failed: {health}")
    else:
        logger.info(f"[STARTUP] DB healthy — engine: {health['engine']}")

    # Seed demo data
    db_gen = get_sync_db()
    db = next(db_gen)
    try:
        _seed_demo_users(db)
        _seed_demo_tender(db)
        logger.info("[STARTUP] Demo data seeded.")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass

    logger.info(
        f"[READY] {settings.APP_NAME} v{settings.APP_VERSION} — "
        f"env={settings.ENVIRONMENT}, demo_mode={settings.DEMO_MODE}"
    )
    yield
    logger.info("[SHUTDOWN] Shutting down AuthBid API.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Officer-Supervised Tender Compliance and Bidder Risk Assessment Platform for GeM Procurement. "
        "Combines deterministic statutory validation, structured evidence provenance, cross-bidder "
        "relationship analysis, explainable risk scoring, and model-assisted evidence review. "
        "All external registry connectors use SYNTHETIC_DEMO data unless a live API key is configured."
    ),
    lifespan=lifespan,
)

# ── CORS ──
_cors_origins = settings.BACKEND_CORS_ORIGINS if settings.ENVIRONMENT != "development" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# ── Register Routers ──
app.include_router(auth_router)
app.include_router(tenders_router)
app.include_router(bidders_router)
app.include_router(verification_router)
app.include_router(graph_router)
# Mock/synthetic registry adapters (labeled SYNTHETIC_DEMO)
app.include_router(gst_router)
app.include_router(pan_router)
app.include_router(udyam_router)
app.include_router(mca_router)
app.include_router(blacklist_router)


@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "demo_mode": settings.DEMO_MODE,
        "data_mode": "SYNTHETIC_DEMO — All registry connectors use simulated data",
        "authentication": "JWT Bearer — Login at /api/v1/auth/login",
        "endpoints": {
            "docs": "/docs",
            "auth": "/api/v1/auth/login",
            "demo_credentials": "/api/v1/auth/demo-credentials",
            "capabilities": "/api/capabilities",
            "tenders": "/api/tenders",
            "bidders": "/api/bidders",
            "verification": "/api/verification",
            "graph": "/api/graph",
            "synthetic_adapters": {
                "gst": "/api/v1/gst [SYNTHETIC_DEMO]",
                "pan": "/api/v1/pan [SYNTHETIC_DEMO]",
                "udyam": "/api/v1/udyam [SYNTHETIC_DEMO]",
                "mca": "/api/v1/mca [SYNTHETIC_DEMO]",
                "blacklist": "/api/v1/blacklist [SYNTHETIC_DEMO]",
            },
        },
    }


@app.get("/health")
async def health_check():
    db_health = check_db_health()
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "demo_mode": settings.DEMO_MODE,
        "database": db_health,
    }


@app.get("/api/capabilities")
async def get_capabilities():
    """Return the platform capability matrix and connector readiness."""
    return {
        "success": True,
        "data": {
            "environment": settings.ENVIRONMENT,
            "demo_mode": settings.DEMO_MODE,
            "audit_mode": "TAMPER_EVIDENT_LOCAL_HASH_CHAIN",
            "external_timestamp": "NOT_CONFIGURED",
            "authentication": "JWT_BEARER",
            "connectors": settings.CAPABILITY_MATRIX,
        },
    }
