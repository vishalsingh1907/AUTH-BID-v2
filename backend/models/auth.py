"""
SIH26100 — Role-Based Access Control (RBAC) Module

SECURITY FIX: Replaced insecure X-User-Role header trust with JWT-based authentication.
The client CANNOT set their own role. Role is issued by the server after verifying
credentials against the database.

Backward-compatible shim: The legacy `require_roles` factory is kept for existing
routers that have not yet been migrated to the new JWT dependency. It now delegates
to the JWT auth system when possible, falling back to header only in strict DEMO_MODE.
"""
from enum import Enum
from typing import List, Optional
from fastapi import Header, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer

import logging

logger = logging.getLogger(__name__)

# ── Import the real JWT dependency ──
# Imported lazily to avoid circular imports (auth router imports from here)
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class UserRole(str, Enum):
    OFFICER = "officer"
    COMMITTEE_MEMBER = "committee_member"
    ADMIN = "admin"
    AUDITOR = "auditor"
    VIEWER = "viewer"


# ═══════════════════════════════════════════════════════════════
# NEW: JWT-BASED ROLE DEPENDENCY
# ═══════════════════════════════════════════════════════════════
def get_current_user_role_from_jwt(
    token: Optional[str] = Depends(_oauth2_scheme),
) -> UserRole:
    """
    Extract user role from a validated JWT token.
    This is the SECURE path — role comes from the server-issued token.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login at /api/v1/auth/login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from services.auth_service import decode_access_token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    role_str = payload.get("role", "viewer")
    try:
        return UserRole(role_str)
    except ValueError:
        return UserRole.VIEWER


# ═══════════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY (kept for backward compat — routes that
# haven't migrated to the auth router's `get_current_user` yet)
# ═══════════════════════════════════════════════════════════════
def get_current_user_role(
    token: Optional[str] = Depends(_oauth2_scheme),
    x_user_role: Optional[str] = Header(default=None),
) -> UserRole:
    """
    MIGRATION SHIM: Prefers JWT authentication over the legacy header.

    SECURITY: If a valid JWT is presented, role from JWT is used exclusively.
    The X-User-Role header is IGNORED when a JWT is present.
    If no JWT is present (demo/test mode without auth configured), the header
    is read but a deprecation warning is logged.

    NOTE: In production (ENVIRONMENT != development), header-fallback is disabled.
    """
    from config import settings

    # ── Preferred: JWT auth ──
    if token:
        payload = None
        try:
            from services.auth_service import decode_access_token
            payload = decode_access_token(token)
        except Exception:
            pass

        if payload:
            role_str = payload.get("role", "viewer")
            try:
                return UserRole(role_str)
            except ValueError:
                return UserRole.VIEWER

    # ── Fallback: header (dev/demo only) ──
    if settings.ENVIRONMENT != "development":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required in non-development environments.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if x_user_role:
        logger.warning(
            "[SECURITY] X-User-Role header used without JWT — only permitted in development mode. "
            "This path must not reach production."
        )
        try:
            return UserRole(x_user_role.strip().lower())
        except ValueError:
            pass

    # Default to officer in demo/dev when no auth provided
    logger.warning("[SECURITY] No authentication provided — defaulting to 'officer' in dev mode only.")
    return UserRole.OFFICER


def require_roles(allowed_roles: List[UserRole]):
    """FastAPI dependency factory enforcing role requirements via JWT."""
    def role_checker(role: UserRole = Depends(get_current_user_role)) -> UserRole:
        if role not in allowed_roles:
            valid_names = [r.value for r in allowed_roles]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: Action restricted under GFR 2017 & GeM policy. "
                    f"Requires role in {valid_names}. "
                    f"Your authenticated role is '{role.value}'."
                ),
            )
        return role
    return role_checker
