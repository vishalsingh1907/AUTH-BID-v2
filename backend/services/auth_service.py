"""
SIH26100 — Authentication Service
Handles user creation, login, JWT token issuance, and password hashing.
Roles are stored in the database; clients cannot self-assign roles.
"""
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ═══════════════════════════════════════════════════════════════
# PASSWORD UTILITIES
# ═══════════════════════════════════════════════════════════════
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ═══════════════════════════════════════════════════════════════
# JWT TOKEN UTILITIES
# ═══════════════════════════════════════════════════════════════
def create_access_token(user_id: str, email: str, role: str) -> str:
    """Issue a signed JWT containing user identity and database-backed role."""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,          # Role comes from DB, NOT from client
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "authbid-sih26100",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT. Returns payload dict or None on failure.
    Raises no exceptions — callers receive None and should issue 401.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("sub") is None:
            return None
        return payload
    except JWTError:
        return None


# ═══════════════════════════════════════════════════════════════
# DEMO USER SEED DATA
# ═══════════════════════════════════════════════════════════════
DEMO_USERS = [
    {
        "id": "USR-ADMIN-001",
        "email": "admin@authbid.gov.in",
        "name": "System Administrator",
        "role": "admin",
        "password": "Admin@SIH2026",
    },
    {
        "id": "USR-OFFICER-001",
        "email": "officer@authbid.gov.in",
        "name": "P. V. Ramanathan",
        "role": "officer",
        "password": "Officer@SIH2026",
    },
    {
        "id": "USR-AUDITOR-001",
        "email": "auditor@authbid.gov.in",
        "name": "S. K. Verma",
        "role": "auditor",
        "password": "Auditor@SIH2026",
    },
    {
        "id": "USR-VIEWER-001",
        "email": "viewer@authbid.gov.in",
        "name": "Demo Viewer",
        "role": "viewer",
        "password": "Viewer@SIH2026",
    },
]
