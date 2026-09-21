"""
SIH26100 — Officer Decision Repository
Persists officer procurement decisions to the database.
Every decision is also appended to the audit trail.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from models.orm import OfficerDecision


def record_decision(
    db: Session,
    tender_id: str,
    bidder_id: str,
    officer_user_id: str,
    officer_name: str,
    role: str,
    decision: str,
    reason: Optional[str],
    justification: Optional[str],
) -> dict:
    """
    Persist an officer's formal procurement decision.
    Decision states: eligible | review | disqualified | requires_clarification | pending_review
    """
    decision_id = f"DEC-{uuid.uuid4().hex[:12].upper()}"
    record = OfficerDecision(
        decision_id=decision_id,
        tender_id=tender_id,
        bidder_id=bidder_id,
        officer_user_id=officer_user_id,
        officer_name=officer_name,
        role=role,
        decision=decision,
        reason=reason,
        justification=justification,
        created_at=datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _decision_to_dict(record)


def get_decisions_for_tender(db: Session, tender_id: str) -> list[dict]:
    """Return all officer decisions for a tender."""
    records = db.query(OfficerDecision).filter(
        OfficerDecision.tender_id == tender_id
    ).order_by(OfficerDecision.created_at).all()
    return [_decision_to_dict(r) for r in records]


def get_latest_decision_for_bidder(
    db: Session, tender_id: str, bidder_id: str
) -> Optional[dict]:
    """Return the most recent officer decision for a specific bidder in a tender."""
    record = db.query(OfficerDecision).filter(
        OfficerDecision.tender_id == tender_id,
        OfficerDecision.bidder_id == bidder_id,
    ).order_by(OfficerDecision.created_at.desc()).first()
    return _decision_to_dict(record) if record else None


def _decision_to_dict(record: OfficerDecision) -> dict:
    return {
        "decision_id": record.decision_id,
        "tender_id": record.tender_id,
        "bidder_id": record.bidder_id,
        "officer_user_id": record.officer_user_id,
        "officer_name": record.officer_name,
        "role": record.role,
        "decision": record.decision,
        "reason": record.reason,
        "justification": record.justification,
        "timestamp": record.created_at.isoformat() if record.created_at else None,
    }
