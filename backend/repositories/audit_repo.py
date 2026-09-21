"""
SIH26100 — Audit Repository
Persists hash-chained audit events to PostgreSQL/SQLite.
Implements tamper-evident append-only semantics.
On startup, last hash is reloaded from DB to maintain chain continuity.
"""
import hashlib
import json
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.orm import AuditEvent


# ═══════════════════════════════════════════════════════════════
# CHAIN HEAD CACHE (in-memory pointer to last persisted hash)
# ═══════════════════════════════════════════════════════════════
_chain_head: Optional[str] = None   # loaded from DB on first access


def _get_chain_head(db: Session) -> str:
    """Return the current hash-chain head from DB (last committed event's current_hash)."""
    global _chain_head
    if _chain_head is not None:
        return _chain_head
    # Load from DB on startup
    last = db.query(AuditEvent).order_by(desc(AuditEvent.timestamp)).first()
    _chain_head = last.current_hash if last else "GENESIS"
    return _chain_head


def _set_chain_head(new_hash: str) -> None:
    global _chain_head
    _chain_head = new_hash


# ═══════════════════════════════════════════════════════════════
# AUDIT APPEND
# ═══════════════════════════════════════════════════════════════
def append_audit_event(
    db: Session,
    event_type: str,
    actor_id: str,
    input_data: dict,
    output_data: dict,
    tender_id: Optional[str] = None,
    bidder_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    policy_version: str = "v1.0",
) -> dict:
    """
    Append a tamper-evident audit event to the persistent hash chain.
    Each event includes the hash of the previous event, ensuring chain integrity.
    Returns the created event as a dict.
    """
    prev_hash = _get_chain_head(db)
    event_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"

    input_hash = hashlib.sha256(
        json.dumps(input_data, sort_keys=True, default=str).encode()
    ).hexdigest()
    output_hash = hashlib.sha256(
        json.dumps(output_data, sort_keys=True, default=str).encode()
    ).hexdigest()

    entry_content = f"{prev_hash}|{actor_id}|{event_type}|{input_hash}|{output_hash}"
    current_hash = hashlib.sha256(entry_content.encode()).hexdigest()

    event = AuditEvent(
        event_id=event_id,
        event_type=event_type,
        actor_id=actor_id,
        tender_id=tender_id,
        bidder_id=bidder_id,
        input_hash=input_hash,
        output_hash=output_hash,
        prev_hash=prev_hash,
        current_hash=current_hash,
        details={
            "input_summary": str(input_data)[:400],
            "output_summary": str(output_data)[:400],
        },
        policy_version=policy_version,
        correlation_id=correlation_id,
        timestamp=datetime.now(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    _set_chain_head(current_hash)

    return _event_to_dict(event)


# ═══════════════════════════════════════════════════════════════
# AUDIT READ
# ═══════════════════════════════════════════════════════════════
def get_audit_trail(db: Session, limit: int = 500) -> list[dict]:
    """Return the most recent audit events ordered chronologically."""
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp).limit(limit).all()
    return [_event_to_dict(e) for e in events]


def verify_audit_chain(db: Session) -> dict:
    """
    Cryptographically verify the integrity of the entire persisted audit chain.
    Returns {"valid": True/False, "entries_checked": N, ...}
    """
    events = db.query(AuditEvent).order_by(AuditEvent.timestamp).all()
    if not events:
        return {"valid": True, "entries_checked": 0, "mode": "TAMPER_EVIDENT_LOCAL_HASH_CHAIN"}

    prev_hash = "GENESIS"
    for i, event in enumerate(events):
        if event.prev_hash != prev_hash:
            return {
                "valid": False,
                "broken_at": event.event_id,
                "expected_prev": prev_hash,
                "actual_prev": event.prev_hash,
                "entries_checked": i + 1,
                "mode": "TAMPER_EVIDENT_LOCAL_HASH_CHAIN",
            }
        content = f"{event.prev_hash}|{event.actor_id}|{event.event_type}|{event.input_hash}|{event.output_hash}"
        recomputed = hashlib.sha256(content.encode()).hexdigest()
        if recomputed != event.current_hash:
            return {
                "valid": False,
                "broken_at": event.event_id,
                "reason": "Hash mismatch — cryptographic integrity broken (tampering detected)",
                "entries_checked": i + 1,
                "mode": "TAMPER_EVIDENT_LOCAL_HASH_CHAIN",
            }
        prev_hash = event.current_hash

    return {
        "valid": True,
        "entries_checked": len(events),
        "root_hash": events[-1].current_hash if events else "GENESIS",
        "mode": "TAMPER_EVIDENT_LOCAL_HASH_CHAIN",
        "note": "External RFC-3161 anchoring: NOT_CONFIGURED (planned for production)",
    }


# ═══════════════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════════════
def _event_to_dict(event: AuditEvent) -> dict:
    return {
        "step_id": event.event_id,
        "agent_id": event.actor_id,
        "action": event.event_type,
        "input_hash": event.input_hash,
        "output_hash": event.output_hash,
        "prev_hash": event.prev_hash,
        "current_hash": event.current_hash,
        "timestamp": event.timestamp.isoformat() if event.timestamp else None,
        "tender_id": event.tender_id,
        "bidder_id": event.bidder_id,
        "correlation_id": event.correlation_id,
        "details": event.details or {},
    }
