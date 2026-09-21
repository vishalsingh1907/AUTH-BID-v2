"""
SIH26100 — Authentication Router
Provides login, token refresh, and user profile endpoints.
Roles are stored in the database and returned in the JWT.
Clients CANNOT self-assign roles — the server reads role from DB.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import logging

from db.session import get_sync_db
from repositories.user_repo import get_user_by_email, get_user_by_id
from services.auth_service import (
    verify_password,
    create_access_token,
    decode_access_token,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ═══════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════
class LoginRequest(BaseModel):
    email: str
    # max_length=72 enforces bcrypt's hard limit at the validation layer.
    # Passwords longer than 72 bytes are silently truncated by bcrypt <4 and
    # raise ValueError in bcrypt >=4; we reject them explicitly with a 422.
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    user_id: str
    email: str
    name: str
    role: str


class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool


# ═══════════════════════════════════════════════════════════════
# AUTH DEPENDENCY (used by all protected routes)
# ═══════════════════════════════════════════════════════════════
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_sync_db),
) -> dict:
    """
    Decode and validate JWT. Fetch user from DB to confirm role is current.
    Returns dict with {user_id, email, role, name}.
    Raises 401 if token is invalid or user is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Re-fetch from DB to ensure role hasn't changed and user is still active
    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return {
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,   # Role is from DB, not token payload
    }


def require_role(*allowed_roles: str):
    """FastAPI dependency factory for role-based authorization."""
    def checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Action requires role in {list(allowed_roles)}. "
                    f"Your role is '{current_user['role']}'."
                ),
            )
        return current_user
    return checker


# Convenience role-check dependencies
require_admin = require_role("admin")
require_officer_or_admin = require_role("officer", "admin")
require_auditor_or_above = require_role("officer", "admin", "auditor")
require_any_authenticated = require_role("officer", "admin", "auditor", "viewer")


# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════
@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: Session = Depends(get_sync_db)):
    """
    Authenticate with email + password.
    Returns a signed JWT containing user identity.
    Role is set from database — client cannot influence it.
    """
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact system administrator.",
        )

    token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,  # Role from DB, never from client
    )
    logger.info(f"[AUTH] Login successful: {user.email} (role={user.role})")
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
    )


@router.get("/me", response_model=UserProfile)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile (from DB, not token)."""
    return UserProfile(
        user_id=current_user["user_id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        is_active=True,
    )


@router.get("/demo-credentials")
async def get_demo_credentials():
    """
    Return demo credentials for SIH evaluation.
    This endpoint exists ONLY in DEMO_MODE and provides the default user accounts.
    """
    from config import settings
    if not settings.DEMO_MODE:
        raise HTTPException(status_code=404, detail="Not found.")
    return {
        "success": True,
        "data": {
            "note": "DEMO MODE — These are pre-seeded accounts for SIH evaluation only.",
            "accounts": [
                {"email": "admin@authbid.gov.in", "password": "Admin@SIH2026", "role": "admin"},
                {"email": "officer@authbid.gov.in", "password": "Officer@SIH2026", "role": "officer"},
                {"email": "auditor@authbid.gov.in", "password": "Auditor@SIH2026", "role": "auditor"},
                {"email": "viewer@authbid.gov.in", "password": "Viewer@SIH2026", "role": "viewer"},
            ],
        },
    }
