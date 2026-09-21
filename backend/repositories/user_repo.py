"""
SIH26100 — User Repository
Provides database-backed user lookup for authentication.
Roles are sourced from the database; never from client-supplied headers or tokens beyond initial claim.
"""
from typing import Optional
from sqlalchemy.orm import Session
from models.orm import User, Organization


# ═══════════════════════════════════════════════════════════════
# USER REPOSITORY
# ═══════════════════════════════════════════════════════════════

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Look up a user by email address. Returns None if not found."""
    return db.query(User).filter(User.email == email, User.is_active).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    """Look up a user by primary key ID."""
    return db.query(User).filter(User.id == user_id, User.is_active).first()


def create_user(
    db: Session,
    user_id: str,
    org_id: str,
    email: str,
    name: str,
    role: str,
    hashed_password: str,
) -> User:
    """Create and persist a new user. Role must be set by admin, not client."""
    user = User(
        id=user_id,
        org_id=org_id,
        email=email,
        name=name,
        role=role,
        hashed_password=hashed_password,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def user_exists(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None


# ═══════════════════════════════════════════════════════════════
# ORGANIZATION REPOSITORY
# ═══════════════════════════════════════════════════════════════

def get_or_create_default_org(db: Session) -> Organization:
    """Get or create the default demo organization."""
    org = db.query(Organization).filter(Organization.code == "GEM-DEMO").first()
    if not org:
        org = Organization(
            id="ORG-GEM-DEMO-001",
            name="Government e-Marketplace (Demo)",
            code="GEM-DEMO",
            domain="gem.gov.in",
        )
        db.add(org)
        db.commit()
        db.refresh(org)
    return org
