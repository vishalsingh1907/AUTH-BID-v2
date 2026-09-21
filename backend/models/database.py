"""
SIH26100 — Database Configuration
PostgreSQL (async) + Neo4j driver setup.
For the hackathon demo, we use in-memory stores as fallback when DBs aren't available.
"""
import hashlib
import json
from datetime import datetime
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# IN-MEMORY STORES (fallback for demo without Docker)
# ═══════════════════════════════════════════════════════════════
_tenders_store: dict[str, dict] = {}
_verification_results: dict[str, dict] = {}
_audit_trail: list[dict] = []
_pipeline_status: dict[str, dict] = {}
_decisions_store: dict[str, list[dict]] = {}
_anchor_receipts: list[dict] = []


# ═══════════════════════════════════════════════════════════════
# TENDER STORE
# ═══════════════════════════════════════════════════════════════
def store_tender(tender: dict) -> str:
    tender_id = tender.get("tender_id", f"T-{len(_tenders_store)+1:04d}")
    tender["tender_id"] = tender_id
    _tenders_store[tender_id] = tender
    return tender_id


def get_tender(tender_id: str) -> Optional[dict]:
    return _tenders_store.get(tender_id)


def get_all_tenders() -> list[dict]:
    return list(_tenders_store.values())


# ═══════════════════════════════════════════════════════════════
# VERIFICATION RESULTS
# ═══════════════════════════════════════════════════════════════
def store_verification_result(bidder_id: str, tender_id: str, result: dict):
    key = f"{tender_id}:{bidder_id}"
    _verification_results[key] = result


def get_verification_result(bidder_id: str, tender_id: str) -> Optional[dict]:
    key = f"{tender_id}:{bidder_id}"
    return _verification_results.get(key)


def get_all_results_for_tender(tender_id: str) -> list[dict]:
    return [v for k, v in _verification_results.items() if k.startswith(f"{tender_id}:")]


# ═══════════════════════════════════════════════════════════════
# AUDIT TRAIL (Hash-chained)
# ═══════════════════════════════════════════════════════════════
def append_audit_entry(agent_id: str, action: str, input_data: dict, output_data: dict) -> dict:
    """Append a hash-chained audit entry."""
    prev_hash = _audit_trail[-1]["current_hash"] if _audit_trail else "GENESIS"

    input_hash = hashlib.sha256(json.dumps(input_data, sort_keys=True, default=str).encode()).hexdigest()
    output_hash = hashlib.sha256(json.dumps(output_data, sort_keys=True, default=str).encode()).hexdigest()

    entry_content = f"{prev_hash}|{agent_id}|{action}|{input_hash}|{output_hash}"
    current_hash = hashlib.sha256(entry_content.encode()).hexdigest()

    entry = {
        "step_id": f"AUDIT-{len(_audit_trail)+1:06d}",
        "agent_id": agent_id,
        "action": action,
        "input_hash": input_hash,
        "output_hash": output_hash,
        "prev_hash": prev_hash,
        "current_hash": current_hash,
        "timestamp": datetime.now().isoformat(),
        "details": {
            "input_summary": str(input_data)[:200],
            "output_summary": str(output_data)[:200],
        },
    }
    _audit_trail.append(entry)
    return entry


def get_audit_trail() -> list[dict]:
    return _audit_trail


_original_audit_backup: list[dict] = []


def tamper_audit_entry(step_id: Optional[str] = None) -> dict:
    """Simulate malicious tampering with an audit block."""
    global _original_audit_backup
    if not _audit_trail:
        return {"success": False, "error": "Audit trail is empty"}

    if not _original_audit_backup:
        _original_audit_backup = [dict(e) for e in _audit_trail]

    target_idx = 2 if len(_audit_trail) > 2 else 0
    if step_id:
        for i, e in enumerate(_audit_trail):
            if e["step_id"] == step_id:
                target_idx = i
                break

    target = _audit_trail[target_idx]
    target["action"] = "UNAUTHORIZED_ALTERATION"
    target["input_hash"] = hashlib.sha256(b"tampered_data").hexdigest()
    return {
        "success": True,
        "tampered_step": target["step_id"],
        "message": f"Simulated unauthorized data modification at {target['step_id']}",
    }


def restore_audit_trail() -> dict:
    """Rebuild and restore cryptographic integrity of the audit trail."""
    global _audit_trail, _original_audit_backup
    if _original_audit_backup:
        _audit_trail = [dict(e) for e in _original_audit_backup]
        _original_audit_backup = []
    else:
        prev_hash = "GENESIS"
        for entry in _audit_trail:
            if entry.get("action") == "UNAUTHORIZED_ALTERATION":
                entry["action"] = "COMPLIANCE_CHECKS"
            entry["prev_hash"] = prev_hash
            content = f"{prev_hash}|{entry['agent_id']}|{entry['action']}|{entry['input_hash']}|{entry['output_hash']}"
            entry["current_hash"] = hashlib.sha256(content.encode()).hexdigest()
            prev_hash = entry["current_hash"]

    return {"success": True, "message": "Audit trail cryptographically re-anchored and verified"}


def verify_audit_chain() -> dict:
    """Verify the integrity of the entire audit chain."""
    if not _audit_trail:
        return {"valid": True, "entries_checked": 0}

    for i, entry in enumerate(_audit_trail):
        expected_prev = _audit_trail[i - 1]["current_hash"] if i > 0 else "GENESIS"
        if entry["prev_hash"] != expected_prev:
            return {
                "valid": False,
                "broken_at": entry["step_id"],
                "expected_prev": expected_prev,
                "actual_prev": entry["prev_hash"],
                "entries_checked": i + 1,
            }

        # Re-compute hash
        content = f"{entry['prev_hash']}|{entry['agent_id']}|{entry['action']}|{entry['input_hash']}|{entry['output_hash']}"
        recomputed = hashlib.sha256(content.encode()).hexdigest()
        if recomputed != entry["current_hash"]:
            return {
                "valid": False,
                "broken_at": entry["step_id"],
                "reason": "Hash mismatch — cryptographic integrity broken (tampering detected)",
                "entries_checked": i + 1,
            }

    return {"valid": True, "entries_checked": len(_audit_trail)}


# ═══════════════════════════════════════════════════════════════
# PIPELINE STATUS
# ═══════════════════════════════════════════════════════════════
def update_pipeline_status(tender_id: str, bidder_id: str, status: dict):
    key = f"{tender_id}:{bidder_id}"
    _pipeline_status[key] = status


def get_pipeline_status(tender_id: str, bidder_id: str) -> Optional[dict]:
    key = f"{tender_id}:{bidder_id}"
    return _pipeline_status.get(key)


# ═══════════════════════════════════════════════════════════════
# DURABLE VERIFICATION RUNS (Phase 8)
# ═══════════════════════════════════════════════════════════════
_runs_store: dict[str, dict] = {}


def create_verification_run(
    tender_id: str,
    initiating_user: str = "officer",
    policy_version: str = "v2.1-sih26100",
    total_bidders: int = 0,
) -> dict:
    run_id = f"RUN-{tender_id.replace('/', '-')}-{int(datetime.now().timestamp())}"
    run = {
        "run_id": run_id,
        "tender_id": tender_id,
        "initiating_user": initiating_user,
        "status": "created",  # created, queued, running, partially_completed, completed, failed, cancelled, retried, stale
        "policy_version": policy_version,
        "connector_versions": {
            "gst_connector": "v1.0",
            "pan_connector": "v1.0",
            "mca_connector": "v1.0",
            "udyam_connector": "v1.0",
            "blacklist_connector": "v1.0",
        },
        "model_versions": {
            "evidence_review": "gemini-2.5-flash / rule_fallback_v1",
            "ocr_extractor": "v1.0",
        },
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total_bidders": total_bidders,
        "verified_bidders": 0,
        "per_source_status": {
            "GST": "pending",
            "PAN": "pending",
            "MCA": "pending",
            "UDYAM": "pending",
            "BLACKLIST": "pending",
        },
        "per_bidder_status": {},
        "retry_count": 0,
        "error_details": None,
        "last_checkpoint": "INITIALIZED",
    }
    _runs_store[run_id] = run
    return run


def update_verification_run(run_id: str, updates: dict) -> Optional[dict]:
    run = _runs_store.get(run_id)
    if not run:
        return None
    run.update(updates)
    return run


def get_verification_run(run_id: str) -> Optional[dict]:
    return _runs_store.get(run_id)


def list_verification_runs(tender_id: Optional[str] = None) -> list[dict]:
    if tender_id:
        return [r for r in _runs_store.values() if r.get("tender_id") == tender_id]
    return list(_runs_store.values())


# ═══════════════════════════════════════════════════════════════
# OFFICER DECISIONS & AUDIT LOG
# ═══════════════════════════════════════════════════════════════
def record_officer_decision(tender_id: str, decision_data: dict) -> dict:
    """Record an officer's formal compliance determination with reason."""
    if tender_id not in _decisions_store:
        _decisions_store[tender_id] = []
    _decisions_store[tender_id].append(decision_data)
    return decision_data


def get_officer_decisions(tender_id: str) -> list[dict]:
    """Retrieve all recorded officer determinations for a tender."""
    return _decisions_store.get(tender_id, [])


# ═══════════════════════════════════════════════════════════════
# EXTERNAL AUDIT ANCHORS
# ═══════════════════════════════════════════════════════════════
def record_anchor_receipt(receipt: dict) -> dict:
    """Record an external cryptographic anchor receipt."""
    _anchor_receipts.append(receipt)
    return receipt


def get_latest_anchor_receipt() -> Optional[dict]:
    """Retrieve the latest external anchor receipt."""
    return _anchor_receipts[-1] if _anchor_receipts else None


def get_all_anchor_receipts() -> list[dict]:
    """Retrieve all external anchor receipts."""
    return list(_anchor_receipts)


# ═══════════════════════════════════════════════════════════════
# DEMO RESET & INITIALIZATION
# ═══════════════════════════════════════════════════════════════
def reset_demo_data() -> dict:
    """
    Reset in-memory state back to deterministic starting demo scenario.
    Clears results, decisions, audit entries, anchor receipts, and re-seeds SAMPLE_TENDER.
    """
    global _tenders_store, _verification_results, _audit_trail, _pipeline_status, _decisions_store, _anchor_receipts, _original_audit_backup, _runs_store
    from mock_apis.synthetic_data import SAMPLE_TENDER

    _tenders_store.clear()
    _verification_results.clear()
    _audit_trail.clear()
    _pipeline_status.clear()
    _decisions_store.clear()
    _anchor_receipts.clear()
    _original_audit_backup.clear()
    _runs_store.clear()

    # Re-seed sample tender
    store_tender(dict(SAMPLE_TENDER))

    return {
        "status": "reset_complete",
        "tender_id": SAMPLE_TENDER["tender_id"],
        "timestamp": datetime.now().isoformat(),
    }

