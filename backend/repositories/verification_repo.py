"""
SIH26100 — Verification Repository
Persists verification runs and their results to the database.
"""
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from models.orm import VerificationRun, BidderAssessment, ComplianceCheckResult


# ═══════════════════════════════════════════════════════════════
# VERIFICATION RUNS
# ═══════════════════════════════════════════════════════════════

def create_verification_run(
    db: Session,
    tender_db_id: str,
    tender_id: str,
    initiating_user_id: str,
    policy_version: str = "v2.1-sih26100",
    total_bidders: int = 0,
) -> dict:
    run_id = f"RUN-{tender_id.replace('/', '-')}-{int(datetime.now().timestamp())}"
    run = VerificationRun(
        id=str(uuid.uuid4()),
        tender_id=tender_db_id,
        run_id=run_id,
        status="running",
        initiating_user_id=initiating_user_id,
        policy_version=policy_version,
        started_at=datetime.now(),
        total_bidders=total_bidders,
        verified_bidders=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"run_id": run_id, "db_id": run.id, "status": "running"}


def update_verification_run(
    db: Session,
    run_id: str,
    updates: dict,
) -> Optional[VerificationRun]:
    run = db.query(VerificationRun).filter(VerificationRun.run_id == run_id).first()
    if not run:
        return None
    for k, v in updates.items():
        if hasattr(run, k):
            setattr(run, k, v)
    db.commit()
    return run


def get_verification_run(db: Session, run_id: str) -> Optional[VerificationRun]:
    return db.query(VerificationRun).filter(VerificationRun.run_id == run_id).first()


def list_verification_runs(db: Session, tender_id: Optional[str] = None) -> list:
    q = db.query(VerificationRun)
    if tender_id:
        # Join with tender to filter by tender_id string
        from models.orm import Tender
        q = q.join(Tender, VerificationRun.tender_id == Tender.id).filter(
            Tender.tender_id == tender_id
        )
    return q.order_by(desc(VerificationRun.created_at)).limit(50).all()


# ═══════════════════════════════════════════════════════════════
# BIDDER ASSESSMENT (compliance result per bidder per run)
# ═══════════════════════════════════════════════════════════════

def store_bidder_assessment(
    db: Session,
    run_db_id: str,
    tender_db_id: str,
    bidder_db_id: str,
    compliance_checks: list[dict],
    risk_score: dict,
    anomalies: list[dict],
    hard_eligibility: dict,
    system_recommendation: str,
    eligibility_status: str,
) -> str:
    """Persist a complete bidder assessment. Returns the assessment DB id."""
    assessment_id = str(uuid.uuid4())
    assessment = BidderAssessment(
        id=assessment_id,
        run_id=run_db_id,
        tender_id=tender_db_id,
        bidder_id=bidder_db_id,
        status="completed",
        hard_eligibility=hard_eligibility,
        system_recommendation=system_recommendation,
        completed_at=datetime.now(),
    )
    db.add(assessment)
    db.flush()  # get the id

    # Store each compliance check result
    for chk in compliance_checks:
        check_result = ComplianceCheckResult(
            id=str(uuid.uuid4()),
            assessment_id=assessment_id,
            check_id=chk.get("check_id", ""),
            check_name=chk.get("check_name", ""),
            category=chk.get("category", ""),
            result=chk.get("result", "indeterminate"),
            details=chk.get("details", ""),
            evidence=chk.get("evidence", []),
            rule_version=chk.get("rule_version", "v2.1-sih26100"),
            confidence=chk.get("confidence", 1.0),
        )
        db.add(check_result)

    db.commit()
    return assessment_id
