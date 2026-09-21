"""
SIH26100 — Verification Router
Triggers the agentic verification pipeline and returns results.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from models.database import (
    store_verification_result,
    get_all_results_for_tender,
    append_audit_entry,
    get_audit_trail,
    verify_audit_chain,
    tamper_audit_entry,
    restore_audit_trail,
    record_officer_decision,
    get_officer_decisions,
    record_anchor_receipt,
    get_latest_anchor_receipt,
    get_all_anchor_receipts,
    reset_demo_data,
    create_verification_run,
    update_verification_run,
    get_verification_run,
    list_verification_runs,
)
from mock_apis.synthetic_data import get_bidder_by_id, get_all_bidders, get_tender as get_sample_tender, check_blacklist
from models.auth import UserRole, require_roles
from config import settings
from routers.graph import _build_cross_bidder_graph
from documents.service import document_pipeline, DocumentValidationError, DocumentSecurityError
from datetime import datetime
import difflib
import hashlib
import json
import re
import os
import asyncio
import base64

router = APIRouter(prefix="/api/verification", tags=["Verification"])


def _sanitize_bidder_input(text: str) -> str:
    """
    Sanitizes untrusted bidder text and query inputs to isolate from LLM prompt instructions.
    Neutralizes injection attempts and markdown breakouts.
    """
    if not text:
        return ""
    # Filter common prompt injection instructions
    filtered = re.sub(
        r"(?i)(ignore\s+(all\s+)?previous\s+instructions|system\s+prompt|system:|developer:|\[INST\]|<\|im_start\|>)",
        "[SUSPICIOUS_DIRECTIVE_REMOVED]",
        text,
    )
    # Neutralize markdown code fences
    filtered = filtered.replace("```", "'''")
    return filtered.strip()[:1200]


def _run_compliance_checks(bidder: dict, tender: dict) -> list[dict]:
    """Run all compliance checks for a bidder against tender criteria."""
    criteria = tender.get("eligibility_criteria", {})
    checks = []

    # 1. GST Registration
    checks.append({
        "check_id": "CHK-001",
        "check_name": "GST Registration",
        "category": "GST",
        "result": "pass" if bidder["gst_status"] == "Active" else "fail",
        "details": f"GST Status: {bidder['gst_status']}. GSTIN: {bidder['gstin']}",
        "evidence": [{"source": "GST_PORTAL", "value": bidder["gst_status"]}],
    })

    # 2. PAN Verification (Fuzzy matching — difflib SequenceMatcher, 85% threshold)
    pan_name = bidder.get("pan_registered_name", bidder["entity_name"])
    similarity = difflib.SequenceMatcher(None, pan_name.lower(), bidder["entity_name"].lower()).ratio()
    name_match = similarity >= 0.85
    pan_result = "pass" if name_match else "warning"
    checks.append({
        "check_id": "CHK-002",
        "check_name": "PAN Verification",
        "category": "PAN",
        "result": pan_result,
        "details": f"PAN: {bidder['pan']}. Name on PAN: '{pan_name}'. Entity Name: '{bidder['entity_name']}'. Similarity: {similarity:.0%}. Match: {name_match}",
        "evidence": [{"source": "PAN_NSDL", "pan_name": pan_name, "entity_name": bidder["entity_name"], "similarity": round(similarity, 4)}],
    })

    # 3. Turnover Check
    turnovers = bidder.get("annual_turnover", [])
    avg_turnover = sum(t["amount"] for t in turnovers) / max(len(turnovers), 1) if turnovers else 0
    min_turnover = criteria.get("min_annual_turnover", 0)

    # MSE exemption: turnover requirement relaxed for MSE
    is_mse = bidder.get("msme_category") in ["Micro", "Small"]
    turnover_required = min_turnover if not is_mse else 0

    checks.append({
        "check_id": "CHK-003",
        "check_name": "Annual Turnover",
        "category": "Financial",
        "result": "pass" if avg_turnover >= turnover_required else "fail",
        "details": f"Avg turnover: ₹{avg_turnover:,.0f}. Required: ₹{turnover_required:,.0f}. MSE exemption: {is_mse}",
        "evidence": [{"source": "ITR_GST_CROSS", "turnovers": turnovers}],
    })

    # 4. Experience Years
    incorp_date = datetime.strptime(bidder["incorporation_date"], "%Y-%m-%d")
    years = (datetime.now() - incorp_date).days / 365.25
    min_years = criteria.get("min_experience_years", 0)
    checks.append({
        "check_id": "CHK-004",
        "check_name": "Experience",
        "category": "Experience",
        "result": "pass" if years >= min_years else "fail",
        "details": f"Operational since: {bidder['incorporation_date']} ({years:.1f} years). Required: {min_years} years",
        "evidence": [{"source": "MCA21", "incorporation_date": bidder["incorporation_date"]}],
    })

    # 5. Make in India
    mii_percent = bidder.get("make_in_india_percent", 0)
    mii_required = criteria.get("make_in_india_min_percent", 0)
    checks.append({
        "check_id": "CHK-005",
        "check_name": "Make in India",
        "category": "MII",
        "result": "pass" if mii_percent >= mii_required else "fail",
        "details": f"Domestic value addition: {mii_percent}%. Required: {mii_required}%",
        "evidence": [{"source": "SELF_DECLARATION", "percent": mii_percent}],
    })

    # 6. Certifications
    required_certs = set(criteria.get("required_certifications", []))
    held_certs = set(bidder.get("certifications", []))
    missing = required_certs - held_certs
    checks.append({
        "check_id": "CHK-006",
        "check_name": "Certifications",
        "category": "Certification",
        "result": "pass" if not missing else "fail",
        "details": f"Held: {', '.join(held_certs) or 'None'}. Missing: {', '.join(missing) or 'None'}",
        "evidence": [{"source": "DOCUMENT_UPLOAD", "held": list(held_certs), "missing": list(missing)}],
    })

    # 7. OEM Authorization
    checks.append({
        "check_id": "CHK-007",
        "check_name": "OEM Authorization",
        "category": "Authorization",
        "result": "pass" if bidder.get("oem_authorization") else "fail",
        "details": f"OEM: {bidder.get('oem_name', 'N/A')}. Authorized: {bidder.get('oem_authorization')}",
        "evidence": [{"source": "OEM_LETTER", "oem": bidder.get("oem_name")}],
    })

    # 8. EPFO Registration
    checks.append({
        "check_id": "CHK-008",
        "check_name": "EPFO Registration",
        "category": "Compliance",
        "result": "pass" if bidder.get("epfo_registered") else "fail",
        "details": f"EPFO Registered: {bidder.get('epfo_registered')}. Code: {bidder.get('epfo_establishment_code', 'N/A')}",
        "evidence": [{"source": "EPFO_PORTAL", "registered": bidder.get("epfo_registered")}],
    })

    # 9. MSME Status (if claimed)
    if bidder.get("msme_category"):
        valid_until = bidder.get("msme_valid_until", "")
        is_valid = valid_until and datetime.strptime(valid_until, "%Y-%m-%d") > datetime.now()
        checks.append({
            "check_id": "CHK-009",
            "check_name": "MSME Registration",
            "category": "MSME",
            "result": "pass" if is_valid else "warning",
            "details": f"Category: {bidder['msme_category']}. Valid until: {valid_until}. Currently valid: {is_valid}",
            "evidence": [{"source": "UDYAM_PORTAL", "category": bidder["msme_category"], "valid": is_valid}],
        })

    # 10. Blacklist Check
    bl_results = check_blacklist(bidder["pan"])
    is_actively_blacklisted = any(e["status"] == "Active" for e in bl_results)
    has_bl_history = len(bl_results) > 0
    checks.append({
        "check_id": "CHK-010",
        "check_name": "Blacklist / Debarment",
        "category": "Blacklist",
        "result": "fail" if is_actively_blacklisted else ("warning" if has_bl_history else "pass"),
        "details": f"Actively blacklisted: {is_actively_blacklisted}. History: {len(bl_results)} records",
        "evidence": [{"source": "BLACKLIST_DB", "records": bl_results}],
    })

    # 11. GST Filing Compliance
    filings = bidder.get("gst_filing_history", [])
    not_filed = [f for f in filings[-12:] if f["status"] == "Not Filed"]  # Last 12 months
    checks.append({
        "check_id": "CHK-011",
        "check_name": "GST Filing Compliance",
        "category": "GST",
        "result": "pass" if not not_filed else "warning",
        "details": f"Unfiled returns in last 12 months: {len(not_filed)}. Periods: {', '.join(f['period'] for f in not_filed) or 'None'}",
        "evidence": [{"source": "GST_PORTAL", "gaps": [f["period"] for f in not_filed]}],
    })

    # 12. Turnover vs GST Cross-Check (catches fabricated turnover certificates)
    filings_12m = bidder.get("gst_filing_history", [])[-12:]
    gst_implied_annual = sum(f.get("taxable_value", 0) for f in filings_12m)
    latest_declared = turnovers[-1]["amount"] if turnovers else 0
    if gst_implied_annual > 0 and latest_declared > 0:
        ratio = latest_declared / gst_implied_annual
        turnover_cross_ok = ratio <= 1.5  # declared should not exceed GST-implied by >50%
        checks.append({
            "check_id": "CHK-012",
            "check_name": "Turnover vs GST Cross-Check",
            "category": "Financial",
            "result": "pass" if turnover_cross_ok else "warning",
            "details": f"Declared: ₹{latest_declared:,.0f}. GST-implied (12m): ₹{gst_implied_annual:,.0f}. Ratio: {ratio:.2f}x. {'Consistent' if turnover_cross_ok else 'Discrepancy — possible fabrication'}",
            "evidence": [{"source": "GST_ITR_CROSS", "declared": latest_declared, "gst_implied": gst_implied_annual, "ratio": round(ratio, 2)}],
        })

    # 13. ESIC Registration & Statutory Compliance
    esic_reg = bidder.get("esic_registered", False)
    esic_code = bidder.get("esic_establishment_code")
    checks.append({
        "check_id": "CHK-013",
        "check_name": "ESIC Compliance",
        "category": "Labor",
        "result": "pass" if (esic_reg and esic_code) else ("warning" if esic_reg else "pass"),
        "details": f"ESIC Registered: {esic_reg}. Code: {esic_code or 'Exempt / Sub-threshold'}",
        "evidence": [{"source": "ESIC_PORTAL", "registered": esic_reg, "code": esic_code}],
    })

    # 14. Startup India & NSIC Status
    startup_reg = bidder.get("startup_india_registered", False)
    dipp_no = bidder.get("dipp_recognition_no")
    nsic_reg = bidder.get("nsic_registered", False)
    checks.append({
        "check_id": "CHK-014",
        "check_name": "Startup India / NSIC",
        "category": "Statutory",
        "result": "pass",
        "details": f"Startup India (DPIIT): {dipp_no or 'Standard Bidder'}. NSIC: {'Enrolled' if nsic_reg else 'Not Claimed'}",
        "evidence": [{"source": "DPIIT_NSIC_GATEWAY", "startup": startup_reg, "dipp": dipp_no, "nsic": nsic_reg}],
    })

    # 15. Income Tax Return (ITR) 3-Year Filing
    itr_filed = bidder.get("itr_filed_last_3_years", True)
    checks.append({
        "check_id": "CHK-015",
        "check_name": "Income Tax (ITR) Compliance",
        "category": "Income Tax",
        "result": "pass" if itr_filed else "fail",
        "details": f"ITR filed for last 3 Assessment Years (AY 2024-25, 2025-26, 2026-27): {'Verified' if itr_filed else 'Non-Compliant / Missing Returns'}",
        "evidence": [{"source": "CBDT_ITR_E-FILING", "status": "Filed" if itr_filed else "Unfiled", "pan": bidder.get("pan")}],
    })

    # 16. DigiLocker Document Provenance & Verification
    digilocker_ok = bidder.get("digilocker_verified", True)
    checks.append({
        "check_id": "CHK-016",
        "check_name": "DigiLocker & Document Integrity",
        "category": "Document",
        "result": "pass" if digilocker_ok else "fail",
        "details": f"Digital certificate provenance: {'Cryptographically Verified via DigiLocker / API Setu' if digilocker_ok else 'Unverified / Disclaimed Audit Opinion'}",
        "evidence": [{"source": "DIGILOCKER_GATEWAY", "verified": digilocker_ok}],
    })

    return checks


def _detect_anomalies(bidder: dict, all_bidders: list[dict]) -> list[dict]:
    """Detect anomalies by cross-referencing with all bidders."""
    anomalies = []

    # 1. Cross-bidder director overlap
    bidder_dirs = {d.get("din") or d.get("pan") for d in bidder.get("directors", [])}
    for other in all_bidders:
        if other["bidder_id"] == bidder["bidder_id"]:
            continue
        other_dirs = {d.get("din") or d.get("pan") for d in other.get("directors", [])}
        shared = bidder_dirs & other_dirs - {None}
        if shared:
            shared_names = []
            for d in bidder.get("directors", []):
                if (d.get("din") or d.get("pan")) in shared:
                    shared_names.append(d["name"])
            anomalies.append({
                "anomaly_id": f"ANM-DIR-{bidder['bidder_id']}-{other['bidder_id']}",
                "anomaly_type": "director_overlap",
                "severity": "critical",
                "title": f"Shared Directors with {other['entity_name']}",
                "description": f"Directors {', '.join(shared_names)} serve on both {bidder['entity_name']} and {other['entity_name']}. This is a strong collusion/bid-rigging indicator.",
                "evidence": [{"shared_identifiers": list(shared), "shared_names": shared_names}],
                "related_bidders": [other["bidder_id"]],
            })

    # 2. Address overlap
    bidder_addr = json.dumps(bidder["registered_address"], sort_keys=True)
    for other in all_bidders:
        if other["bidder_id"] == bidder["bidder_id"]:
            continue
        other_addr = json.dumps(other["registered_address"], sort_keys=True)
        if bidder_addr == other_addr:
            anomalies.append({
                "anomaly_id": f"ANM-ADDR-{bidder['bidder_id']}-{other['bidder_id']}",
                "anomaly_type": "address_overlap",
                "severity": "high",
                "title": f"Same Registered Address as {other['entity_name']}",
                "description": f"Both entities registered at: {bidder['registered_address']['line1']}, {bidder['registered_address']['city']}",
                "evidence": [{"address": bidder["registered_address"]}],
                "related_bidders": [other["bidder_id"]],
            })

    # 3. Bank account overlap (same IFSC + similar account)
    bidder_bank = bidder.get("bank_account", {})
    for other in all_bidders:
        if other["bidder_id"] == bidder["bidder_id"]:
            continue
        other_bank = other.get("bank_account", {})
        if bidder_bank.get("ifsc") == other_bank.get("ifsc") and bidder_bank.get("ifsc"):
            # Same branch
            if bidder_bank.get("account_no", "")[:10] == other_bank.get("account_no", "")[:10]:
                anomalies.append({
                    "anomaly_id": f"ANM-BANK-{bidder['bidder_id']}-{other['bidder_id']}",
                    "anomaly_type": "bank_overlap",
                    "severity": "high",
                    "title": f"Shared Bank Branch with {other['entity_name']}",
                    "description": f"Same bank branch (IFSC: {bidder_bank['ifsc']}) with similar account numbers",
                    "evidence": [{"ifsc": bidder_bank["ifsc"], "branch": bidder_bank.get("branch")}],
                    "related_bidders": [other["bidder_id"]],
                })

    # 4. Phone number overlap
    bidder_phones = {d.get("phone") for d in bidder.get("directors", []) if d.get("phone")}
    for other in all_bidders:
        if other["bidder_id"] == bidder["bidder_id"]:
            continue
        other_phones = {d.get("phone") for d in other.get("directors", []) if d.get("phone")}
        shared_phones = bidder_phones & other_phones
        if shared_phones:
            anomalies.append({
                "anomaly_id": f"ANM-PHONE-{bidder['bidder_id']}-{other['bidder_id']}",
                "anomaly_type": "phone_overlap",
                "severity": "high",
                "title": f"Shared Phone Number with {other['entity_name']}",
                "description": f"Phone number(s) {', '.join(shared_phones)} found in both entities",
                "evidence": [{"shared_phones": list(shared_phones)}],
                "related_bidders": [other["bidder_id"]],
            })

    # 5. Shell company detection
    incorp_date = datetime.strptime(bidder["incorporation_date"], "%Y-%m-%d")
    age_days = (datetime.now() - incorp_date).days
    if age_days < 365 and not bidder.get("gst_filing_history"):
        anomalies.append({
            "anomaly_id": f"ANM-SHELL-{bidder['bidder_id']}",
            "anomaly_type": "shell_company",
            "severity": "critical",
            "title": "Potential Corporate-Structure Anomaly",
            "description": f"Entity incorporated {age_days} days ago with no GST filing history and no certifications. Warrants officer scrutiny under GFR 151.",
            "evidence": [{"age_days": age_days, "gst_filings": 0, "certifications": len(bidder.get("certifications", []))}],
            "related_bidders": [],
        })

    # 6. GST filing gaps
    filings = bidder.get("gst_filing_history", [])
    gaps = [f["period"] for f in filings[-12:] if f["status"] == "Not Filed"]
    if gaps:
        anomalies.append({
            "anomaly_id": f"ANM-GSTGAP-{bidder['bidder_id']}",
            "anomaly_type": "gst_filing_gap",
            "severity": "medium",
            "title": "GST Filing Gaps",
            "description": f"GST returns not filed for periods: {', '.join(gaps)}",
            "evidence": [{"gap_periods": gaps}],
            "related_bidders": [],
        })

    # 7. Turnover decline
    turnovers = bidder.get("annual_turnover", [])
    if len(turnovers) >= 2:
        latest = turnovers[-1]["amount"]
        prev = turnovers[-2]["amount"]
        if latest < prev * 0.7:  # >30% decline
            anomalies.append({
                "anomaly_id": f"ANM-DECLINE-{bidder['bidder_id']}",
                "anomaly_type": "turnover_inconsistency",
                "severity": "medium",
                "title": "Significant Turnover Decline",
                "description": f"Turnover dropped from ₹{prev:,.0f} to ₹{latest:,.0f} ({((latest-prev)/prev*100):.1f}%)",
                "evidence": [{"turnovers": turnovers}],
                "related_bidders": [],
            })

    return anomalies


def _calculate_risk_score(checks: list[dict], anomalies: list[dict], bidder: dict, cluster_floor: float = 0.0) -> dict:
    """Calculate composite risk score 0-100."""
    # Component scores (higher = more risk)
    failed_checks = sum(1 for c in checks if c["result"] == "fail")
    warning_checks = sum(1 for c in checks if c["result"] == "warning")
    total_checks = max(len(checks), 1)

    # Cross-source consistency (30%)
    consistency_risk = ((failed_checks * 100 + warning_checks * 40) / total_checks) * 0.3

    # Collusion indicators (25%)
    collusion_anomalies = [a for a in anomalies if a["anomaly_type"] in ["director_overlap", "address_overlap", "bank_overlap", "phone_overlap"]]
    collusion_risk = min(len(collusion_anomalies) * 25, 100) * 0.25

    # Financial health (20%)
    turnovers = bidder.get("annual_turnover", [])
    financial_risk = 0
    if not turnovers:
        financial_risk = 80
    elif len(turnovers) >= 2 and turnovers[-1]["amount"] < turnovers[-2]["amount"] * 0.7:
        financial_risk = 50
    financial_risk *= 0.20

    # Document integrity (15%)
    shell_anomalies = [a for a in anomalies if a["anomaly_type"] == "shell_company"]
    gap_anomalies = [a for a in anomalies if a["anomaly_type"] == "gst_filing_gap"]
    doc_risk = (50 if shell_anomalies else 0) + (30 if gap_anomalies else 0)
    doc_risk = min(doc_risk, 100) * 0.15

    # Blacklist proximity (10%)
    bl_checks = [c for c in checks if c["category"] == "Blacklist"]
    bl_risk = 0
    for c in bl_checks:
        if c["result"] == "fail":
            bl_risk = 100
        elif c["result"] == "warning":
            bl_risk = 50
    bl_risk *= 0.10

    overall = consistency_risk + collusion_risk + financial_risk + doc_risk + bl_risk
    overall = min(round(overall, 1), 100)

    # Suspicious-cluster risk floor: bidders identified in a detected collusion cluster
    # receive a risk floor (e.g. 45.0 for High risk, 70.0 for Critical)
    effective_floor = cluster_floor or bidder.get("cluster_risk_floor", 0.0)
    if effective_floor > 0:
        overall = max(overall, effective_floor)

    if overall >= 70:
        level = "critical"
    elif overall >= 45:
        level = "high"
    elif overall >= 20:
        level = "medium"
    else:
        level = "low"

    # Separate eligibility state from risk score (Phase 6 requirement)
    has_statutory_failure = any(c.get("result") == "fail" for c in checks)
    has_indeterminate = any(c.get("result") in ["indeterminate", "unavailable"] for c in checks)

    if has_statutory_failure:
        eligibility_status = "Potential non-compliance"
    elif has_indeterminate:
        eligibility_status = "Indeterminate — source unavailable"
    elif level in ["high", "critical"] or warning_checks > 0:
        eligibility_status = "Requires officer review"
    else:
        eligibility_status = "Eligible based on available evidence"

    # Data completeness & uncertainty calculation
    indeterminate_checks = sum(1 for c in checks if c.get("result") in ["indeterminate", "unavailable"])
    data_completeness = max(0.0, round((1.0 - (indeterminate_checks / total_checks)) * 100, 1))
    uncertainty_level = "high" if data_completeness < 70 else ("medium" if data_completeness < 95 else "low")

    # Traceable contributing factors
    contributing_factors = []
    for c in checks:
        if c.get("result") in ["fail", "warning"]:
            contributing_factors.append(f"Check {c.get('check_name', c.get('check_id'))}: {c.get('result').upper()}")
    for a in anomalies:
        contributing_factors.append(f"Anomaly {a.get('title', a.get('anomaly_type'))} ({a.get('severity', 'info')})")

    return {
        "overall_score": overall,
        "compliance_score": round(max(0.0, 100.0 - overall), 1),
        "risk_level": level,
        "scoring_policy_version": "v2.1-sih26100",
        "eligibility_status": eligibility_status,
        "data_completeness": data_completeness,
        "uncertainty_level": uncertainty_level,
        "components": {
            "cross_source_consistency": round(consistency_risk / 0.3, 1),
            "collusion_indicators": round(collusion_risk / 0.25, 1),
            "financial_health": round(financial_risk / 0.20, 1),
            "document_integrity": round(doc_risk / 0.15, 1),
            "blacklist_proximity": round(bl_risk / 0.10, 1),
        },
        "raw_components": {
            "cross_source_consistency": round(consistency_risk / 0.3, 1),
            "collusion_indicators": round(collusion_risk / 0.25, 1),
            "financial_health": round(financial_risk / 0.20, 1),
            "document_integrity": round(doc_risk / 0.15, 1),
            "blacklist_proximity": round(bl_risk / 0.10, 1),
        },
        "weighted_contributions": {
            "cross_source_consistency": round(consistency_risk, 2),
            "collusion_indicators": round(collusion_risk, 2),
            "financial_health": round(financial_risk, 2),
            "document_integrity": round(doc_risk, 2),
            "blacklist_proximity": round(bl_risk, 2),
        },
        "weight_justifications": {
            "cross_source_consistency": "30% weight: Evaluates statutory pass/fail compliance across independent registries.",
            "collusion_indicators": "25% weight: Flags shared directors, addresses, bank branches, and contact identifiers.",
            "financial_health": "20% weight: Measures multi-year revenue stability and minimum turnover threshold.",
            "document_integrity": "15% weight: Detects filing gaps, shell company heuristics, and unverified filings.",
            "blacklist_proximity": "10% weight: Flags active or historical debarment records under CPPP/GeM.",
        },
        "contributing_factors": contributing_factors,
        "explanation": _generate_risk_explanation(overall, level, anomalies, checks),
    }


def _generate_risk_explanation(score: float, level: str, anomalies: list, checks: list) -> str:
    """Generate natural language risk explanation."""
    parts = []
    if level == "critical":
        parts.append(f"⚠️ CRITICAL RISK (Score: {score}/100).")
    elif level == "high":
        parts.append(f"🔴 HIGH RISK (Score: {score}/100).")
    elif level == "medium":
        parts.append(f"🟡 MEDIUM RISK (Score: {score}/100).")
    else:
        parts.append(f"🟢 LOW RISK (Score: {score}/100).")

    collusion = [a for a in anomalies if a["anomaly_type"] in ["director_overlap", "address_overlap", "bank_overlap"]]
    if collusion:
        related = set()
        for a in collusion:
            related.update(a.get("related_bidders", []))
        parts.append(f"Potential relationship indicators identified with {len(related)} other bidder(s) in this tender.")

    shell = [a for a in anomalies if a["anomaly_type"] == "shell_company"]
    if shell:
        parts.append("Entity exhibits corporate-structure anomalies (recent incorporation without verified filing history).")


    failed = [c for c in checks if c["result"] == "fail"]
    if failed:
        parts.append(f"{len(failed)} mandatory eligibility check(s) failed: {', '.join(c['check_name'] for c in failed)}.")

    return " ".join(parts)


@router.post("/run/{tender_id:path}")
async def run_verification(tender_id: str):
    """Run the full verification pipeline for all bidders in a tender."""
    tender = get_sample_tender()
    if tender["tender_id"] != tender_id:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    all_bidders = get_all_bidders()
    
    # Initialize durable verification run
    run = create_verification_run(
        tender_id=tender_id,
        initiating_user="officer",
        policy_version="v2.1-sih26100",
        total_bidders=len(all_bidders),
    )
    update_verification_run(run["run_id"], {"status": "running", "last_checkpoint": "STARTING_CROSS_BIDDER_GRAPH"})

    graph = _build_cross_bidder_graph(all_bidders)
    cluster_floors = {}
    for cluster in graph.get("clusters", []):
        members = cluster.get("members", [])
        floor = 70.0 if len(members) >= 3 else 45.0
        for m in members:
            cluster_floors[m] = max(cluster_floors.get(m, 0.0), floor)

    results = []
    per_bidder_status = {}

    for bidder in all_bidders:
        b_id = bidder["bidder_id"]
        per_bidder_status[b_id] = "running"
        update_verification_run(run["run_id"], {
            "last_checkpoint": f"VERIFYING_{b_id}",
            "per_bidder_status": per_bidder_status,
        })

        # Log to audit trail
        append_audit_entry(
            "orchestrator",
            "START_VERIFICATION",
            {"bidder_id": b_id, "tender_id": tender_id, "run_id": run["run_id"]},
            {"status": "started"},
        )

        # Run compliance checks
        checks = _run_compliance_checks(bidder, tender)
        append_audit_entry("compliance_checker", "COMPLIANCE_CHECKS", {"bidder_id": b_id, "run_id": run["run_id"]}, {"checks": len(checks)})

        # Detect anomalies
        anomalies = _detect_anomalies(bidder, all_bidders)
        append_audit_entry("anomaly_detector", "ANOMALY_DETECTION", {"bidder_id": b_id, "run_id": run["run_id"]}, {"anomalies": len(anomalies)})

        # Calculate risk score (with suspicious-cluster floor applied)
        risk_score = _calculate_risk_score(
            checks,
            anomalies,
            bidder,
            cluster_floor=cluster_floors.get(b_id, 0.0),
        )
        append_audit_entry("risk_scorer", "RISK_SCORING", {"bidder_id": b_id, "run_id": run["run_id"]}, {"score": risk_score["overall_score"]})

        # Build hard eligibility summary
        hard_eligibility = {}
        for c in checks:
            hard_eligibility[c["check_name"]] = c["result"]

        # Generate System Recommendation
        if risk_score["risk_level"] == "critical":
            recommendation = f"⚠️ REQUIRES OFFICER REVIEW. {bidder['entity_name']} exhibits critical risk indicators including potential relationship patterns. Recommend thorough verification before proceeding."
        elif risk_score["risk_level"] == "high":
            recommendation = f"🔴 ELEVATED RISK. {bidder['entity_name']} has compliance observations that warrant officer attention. Review evidence before recording determination."
        elif risk_score["risk_level"] == "medium":
            recommendation = f"🟡 MODERATE RISK. {bidder['entity_name']} has minor statutory observations. Review at officer's discretion."
        else:
            recommendation = f"🟢 LOW RISK. {bidder['entity_name']} satisfies evaluated criteria with no significant anomaly indicators. Subject to final officer determination."

        result = {
            "bidder_id": b_id,
            "entity_name": bidder["entity_name"],
            "tender_id": tender_id,
            "status": "completed",
            "risk_score": risk_score,
            "compliance_checks": checks,
            "anomalies": anomalies,
            "hard_eligibility": hard_eligibility,
            "system_recommendation": recommendation,
            "ai_recommendation": recommendation,  # Kept for backward compatibility
            "ai_confidence": 0.85,
            "completed_at": datetime.now().isoformat(),
        }

        store_verification_result(b_id, tender_id, result)
        results.append(result)
        per_bidder_status[b_id] = "completed"
        update_verification_run(run["run_id"], {
            "verified_bidders": len(results),
            "per_bidder_status": per_bidder_status,
        })

    # Complete durable run
    update_verification_run(run["run_id"], {
        "status": "completed",
        "completed_at": datetime.now().isoformat(),
        "last_checkpoint": "COMPLETED",
        "per_source_status": {
            "GST": "completed",
            "PAN": "completed",
            "MCA": "completed",
            "UDYAM": "completed",
            "BLACKLIST": "completed",
        },
    })

    return {
        "success": True,
        "data": {
            "run_id": run["run_id"],
            "tender_id": tender_id,
            "bidders_verified": len(results),
            "run_status": "completed",
            "results": results,
        },
    }


@router.get("/runs")
async def list_runs_endpoint(tender_id: str = None):
    """List all durable verification runs, optionally filtered by tender."""
    runs = list_verification_runs(tender_id)
    return {"success": True, "data": runs}


@router.get("/runs/{run_id}")
async def get_run_endpoint(run_id: str):
    """Get status and details of a specific durable verification run."""
    run = get_verification_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Verification run {run_id} not found")
    return {"success": True, "data": run}


@router.post("/runs/{run_id}/cancel")
async def cancel_run_endpoint(run_id: str):
    """Cancel a running verification job."""
    run = get_verification_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Verification run {run_id} not found")
    if run["status"] == "completed":
        raise HTTPException(status_code=400, detail="Cannot cancel an already completed run.")
    updated = update_verification_run(run_id, {
        "status": "cancelled",
        "last_checkpoint": "CANCELLED_BY_USER",
        "completed_at": datetime.now().isoformat(),
    })
    return {"success": True, "data": updated}


@router.post("/documents/{bidder_id}/upload")
async def upload_bidder_document(
    bidder_id: str,
    payload: dict,
):
    """
    Upload and securely ingest a bidder document into the evidence pipeline.
    Validates MIME type, file size, content signature, scans malware, and extracts fields.
    """
    file_name = payload.get("file_name")
    content_base64 = payload.get("content_base64")
    content_type = payload.get("content_type", "application/pdf")
    doc_type = payload.get("doc_type", "GENERIC_DOC")
    tender_id = payload.get("tender_id")

    if not file_name or not content_base64:
        raise HTTPException(status_code=400, detail="file_name and content_base64 are required.")

    try:
        content_bytes = base64.b64decode(content_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoded document content.")

    try:
        ingest_res = document_pipeline.ingest_document(
            file_name=file_name,
            content=content_bytes,
            content_type=content_type,
            bidder_id=bidder_id,
            doc_type=doc_type,
            tender_id=tender_id,
        )
    except DocumentSecurityError as e:
        raise HTTPException(status_code=422, detail=f"Security violation: {str(e)}")
    except DocumentValidationError as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")

    # Extract structured fields
    bidder = get_bidder_by_id(bidder_id) or {}
    extraction = document_pipeline.extract_document_fields(
        doc_id=ingest_res["doc_id"],
        doc_type=doc_type,
        content=content_bytes,
        known_bidder_data=bidder,
    )

    # Validate against registry
    validation = document_pipeline.validate_against_registry(
        extraction=extraction,
        registry_data=bidder,
    )

    append_audit_entry(
        "document_pipeline",
        "DOCUMENT_INGESTED",
        {"bidder_id": bidder_id, "doc_type": doc_type, "sha256": ingest_res["sha256_hash"]},
        {"status": validation.status, "doc_id": ingest_res["doc_id"]},
    )

    # Immediately index into Qdrant Vector DB for live GeM Copilot GraphRAG retrieval
    try:
        from ai.rag_service import rag_service
        file_path = ingest_res.get("file_path")
        if file_path and os.path.exists(file_path):
            rag_service.index_single_document(
                file_path=file_path,
                doc_id=ingest_res["doc_id"],
                bidder_id=bidder_id,
                doc_type=doc_type,
            )
    except Exception as e:
        logger.warning(f"Failed to index uploaded document into Qdrant: {e}")

    return {
        "success": True,
        "data": {
            "document": ingest_res,
            "extraction": extraction.model_dump(),
            "validation": validation.model_dump(),
        },
    }


@router.post("/documents/{doc_id}/verify-digilocker")
async def verify_doc_digilocker(doc_id: str, payload: dict = None):
    """
    Check document verification via DigiLocker issuer gateway.
    Truthful boundary: requires explicit consent token and reports truthful availability status.
    """
    consent_token = payload.get("consent_token") if payload else None
    res = document_pipeline.verify_digilocker_consent(doc_id=doc_id, consent_token=consent_token)
    return {"success": True, "data": res.model_dump()}


@router.get("/results/{tender_id:path}")
async def get_all_verification_results(tender_id: str):
    """Get all verification results for a tender."""
    results = get_all_results_for_tender(tender_id)
    return {
        "success": True,
        "data": {
            "tender_id": tender_id,
            "total_bidders": len(results),
            "results": results,
            "summary": {
                "low_risk": sum(1 for r in results if r.get("risk_score", {}).get("risk_level") == "low"),
                "medium_risk": sum(1 for r in results if r.get("risk_score", {}).get("risk_level") == "medium"),
                "high_risk": sum(1 for r in results if r.get("risk_score", {}).get("risk_level") == "high"),
                "critical_risk": sum(1 for r in results if r.get("risk_score", {}).get("risk_level") == "critical"),
            },
        },
    }


@router.get("/audit-trail")
async def get_audit_trail_endpoint():
    """Get the complete hash-chained audit trail."""
    trail = get_audit_trail()
    chain_valid = verify_audit_chain()
    return {
        "success": True,
        "data": {
            "entries": trail,
            "total_entries": len(trail),
            "chain_integrity": chain_valid,
        },
    }


@router.post("/tamper")
async def tamper_audit_endpoint(
    payload: dict = None,
    current_role: UserRole = Depends(require_roles([UserRole.ADMIN])),
):
    """Simulate tampering with an audit trail entry. Restricted to System Admin role."""
    step_id = payload.get("step_id") if payload else None
    result = tamper_audit_entry(step_id)
    chain_valid = verify_audit_chain()
    return {
        "success": True,
        "tamper_result": result,
        "chain_integrity": chain_valid,
        "executed_by_role": current_role.value,
    }


@router.post("/restore")
async def restore_audit_endpoint(
    current_role: UserRole = Depends(require_roles([UserRole.ADMIN])),
):
    """Restore cryptographic integrity and re-anchor SHA-256 chain. Restricted to System Admin role."""
    result = restore_audit_trail()
    chain_valid = verify_audit_chain()
    return {
        "success": True,
        "restore_result": result,
        "chain_integrity": chain_valid,
        "restored_by_role": current_role.value,
    }


@router.post("/anchor")
async def anchor_audit_trail_endpoint(
    current_role: UserRole = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    """
    Externally anchor the latest SHA-256 hash-chain state to a simulated
    public transparency log / RFC 3161 timestamp authority.
    Prevents retroactive admin alterations by publishing the cryptographic commitment.
    """
    trail = get_audit_trail()
    if not trail:
        raise HTTPException(status_code=400, detail="Audit trail is empty. Run verification first.")

    latest_hash = trail[-1]["current_hash"]
    merkle_content = "|".join(e["current_hash"] for e in trail)
    merkle_root = hashlib.sha256(merkle_content.encode()).hexdigest()

    receipt = {
        "receipt_id": f"ANCHOR-RFC3161-{int(datetime.now().timestamp())}",
        "anchored_at": datetime.now().isoformat(),
        "total_blocks": len(trail),
        "latest_block_id": trail[-1]["step_id"],
        "root_hash": latest_hash,
        "merkle_root": merkle_root,
        "external_service": settings.EXTERNAL_ANCHOR_SERVICE_URL,
        "proof_type": "Local Hash-Chain Commitment (RFC-3161 Format)",
        "digital_signature": hashlib.sha256(f"SIG_GEM_VIG_{merkle_root}".encode()).hexdigest()[:48],
        "status": "LOCAL_COMMITMENT",
        "anchored_by_role": current_role.value,
        "notes": "External timestamp authority anchoring planned for production environment.",
    }

    record_anchor_receipt(receipt)
    append_audit_entry(
        "anchor_service",
        "AUDIT_HASH_CHAIN_COMMITMENT_RECORDED",
        {"merkle_root": merkle_root, "blocks": len(trail)},
        {"receipt_id": receipt["receipt_id"], "status": "LOCAL_COMMITMENT"},
    )

    return {"success": True, "data": receipt}


@router.get("/anchor")
async def get_anchor_receipt_endpoint():
    """Get the latest external cryptographic anchor receipt."""
    latest = get_latest_anchor_receipt()
    all_receipts = get_all_anchor_receipts()
    return {
        "success": True,
        "data": {
            "latest_anchor": latest,
            "total_anchors": len(all_receipts),
            "history": all_receipts,
        },
    }


@router.post("/decision")
async def record_compliance_decision(
    payload: dict,
    current_role: UserRole = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    """
    Record an official evaluation decision (disqualified, eligible, review) with mandatory reason.
    Restricted to Officer and Admin roles under GFR Rule 151.
    """
    bidder_id = payload.get("bidder_id")
    tender_id = payload.get("tender_id", "GEM/2026/B/4521897")
    decision = payload.get("decision")
    reason = payload.get("reason", "").strip()
    justification = payload.get("justification", "").strip()
    officer_name = payload.get("officer_name", "P. V. Ramanathan")

    if not bidder_id or not decision:
        raise HTTPException(status_code=400, detail="bidder_id and decision are required")

    if decision == "disqualified" and (not reason or len(justification) < 5):
        raise HTTPException(
            status_code=400,
            detail="Disqualification requires a mandatory categorical reason and detailed justification notes.",
        )

    decision_record = {
        "decision_id": f"DEC-{bidder_id}-{int(datetime.now().timestamp())}",
        "bidder_id": bidder_id,
        "tender_id": tender_id,
        "decision": decision,
        "reason": reason,
        "justification": justification,
        "officer_name": officer_name,
        "role": current_role.value,
        "timestamp": datetime.now().isoformat(),
    }

    record_officer_decision(tender_id, decision_record)
    append_audit_entry(
        f"officer:{officer_name}",
        f"DECISION_{decision.upper()}",
        {"bidder_id": bidder_id, "reason": reason},
        {"status": "recorded", "decision_id": decision_record["decision_id"]},
    )

    return {"success": True, "data": decision_record}


@router.get("/decisions/{tender_id:path}")
async def get_tender_decisions(tender_id: str):
    """Get all recorded officer compliance decisions for a tender."""
    decisions = get_officer_decisions(tender_id)
    return {"success": True, "data": decisions}


@router.get("/report/{tender_id:path}")
async def get_scrutiny_report(tender_id: str):
    """Generate official GeM Evaluation Committee Scrutiny Memo."""
    tender = get_sample_tender()
    results = get_all_results_for_tender(tender_id)
    trail = get_audit_trail()
    chain_valid = verify_audit_chain()

    # Only truly clean bidders: low risk AND no failed/warning checks AND no anomalies
    clean_bidders = [
        r for r in results
        if r.get("risk_score", {}).get("risk_level") == "low"
        and not any(c["result"] in ("fail", "warning") for c in r.get("compliance_checks", []))
        and len(r.get("anomalies", [])) == 0
    ]
    flagged_bidders = [r for r in results if r.get("risk_score", {}).get("risk_level") in ["high", "critical"]]

    return {
        "success": True,
        "data": {
            "tender_id": tender_id,
            "title": tender.get("title"),
            "estimated_value": tender.get("estimated_value"),
            "generated_at": datetime.now().isoformat(),
            "committee_authority": "GeM Technical Scrutiny Sub-Committee (Officer-Supervised)",
            "summary": {
                "total_bidders": len(results),
                "recommended_for_financial_evaluation": len(clean_bidders),
                "disqualified_or_flagged": len(flagged_bidders),
                "cryptographic_verification": "VERIFIED_VALID" if chain_valid.get("valid") else "TAMPER_DETECTED",
                "audit_entries_count": len(trail),
                "root_hash": trail[-1]["current_hash"] if trail else "GENESIS",
            },
            "clean_bidders": clean_bidders,
            "disqualified_bidders": flagged_bidders,
        },
    }


def _build_copilot_system_instruction(tender_id: str, bidder_id: str | None = None) -> str:
    """Constructs a comprehensive, project-grounded system instruction for the AI Copilot."""
    return (
        "You are the GeM Vigilance & Legal AI Copilot for AuthBid, an advanced AI-powered procurement "
        "compliance, forensic verification, and anti-collusion intelligence platform for the Government e-Marketplace (GeM), India.\n\n"
        "=== TARGET TENDER ===\n"
        f"Tender ID: {tender_id}\n"
        "Title: Supply of 500 Desktop Computers with 3-Year Warranty\n"
        "Authority: Ministry of Electronics and Information Technology (MeitY) / National Informatics Centre (NIC)\n"
        "Estimated Value: ₹2.50 Cr (₹25,000,000 INR)\n"
        "EMD Amount: ₹5,00,000 (Exempt for verified MSEs under GFR 153)\n"
        "Mandatory Criteria: Min 3 years experience, Min ₹1.00 Cr annual turnover, Make in India (MII) >= 50%, OEM Authorization mandatory.\n\n"
        "=== COMPLETE BIDDER ROSTER & FORENSIC GROUND TRUTH ===\n"
        "1. TechVision Solutions Pvt. Ltd. (B001, Bid: ₹2.35 Cr, MII: 65%, OEM: HCL) - COLLUSION RING 1 LEADER. "
        "Shares 2 directors (Rajesh Kumar Sharma DIN: 09876543, Vikram Singh Chauhan DIN: 08765432) and registered address "
        "(Plot No. 45, Sector 18, Industrial Area Phase II, Gurugram) with B003 and B007. Coordinated cover bid syndicate.\n"
        "2. Reliable Computing Systems Ltd. (B002, Bid: ₹2.42 Cr, MII: 72%, OEM: Dell) - CLEAN BIDDER. Fully compliant, "
        "3-year turnover ₹12-15 Cr/year, active GST filings, OEM Dell certified. RECOMMENDED FULLY COMPLIANT L1 AWARDEE.\n"
        "3. DigiCore Infosystems Pvt. Ltd. (B003, Bid: ₹2.48 Cr, MII: 60%, OEM: Lenovo) - COLLUSION RING 1 ACCOMPLICE. "
        "Shares directors (DIN 09876543, 08765432) and Gurugram address with B001 & B007.\n"
        "4. GreenTech Peripherals Pvt. Ltd. (B004, Bid: ₹2.28 Cr, MII: 55%, OEM: HP) - ANOMALY: Expired MSME Udyam certificate "
        "(expired March 2026). Currently under 48-hr clarification notice. If valid, lowest price at ₹2.28 Cr (saving ₹22L vs estimate).\n"
        "5. NexGen IT Solutions Pvt. Ltd. (B005, Bid: ₹2.39 Cr, MII: 58%, OEM: Acer) - COLLUSION RING 2 (Related Party Nexus). "
        "Shares Punjab National Bank branch (IFSC: PUNB0123400, Nehru Place, New Delhi) and authorized signatory phone (9098765432) with B009.\n"
        "6. Bharat Electronics & Computing Ltd. (B006, Bid: ₹2.45 Cr, MII: 80%, OEM: Bharat) - ANOMALY: PAN/GST entity name mismatch "
        "('Bharat Electronics and Computers Ltd.' vs GST 'Bharat Electronics & Computing Ltd.'). 2% Levenshtein discrepancy.\n"
        "7. Quantum Digital Services Pvt. Ltd. (B007, Bid: ₹2.20 Cr, MII: 52%, OEM: Intex) - SHELL COMPANY / CARTEL COVER. "
        "Incorporated <90 days ago, zero GST returns filed, un-audited provisional figures, shared directors with B001/B003. "
        "Flagged for summary rejection under PMLA Section 66 & GeM Debarment.\n"
        "8. MegaByte Computers Pvt. Ltd. (B008, Bid: ₹2.40 Cr, MII: 62%, OEM: Dell) - ANOMALY: Historical debarment (debarred 2023 for delayed supply, "
        "cleared 2024). Eligible to bid under GFR 151 but flagged for enhanced scrutiny.\n"
        "9. CloudFirst Technologies Pvt. Ltd. (B009, Bid: ₹2.32 Cr, MII: 68%, OEM: HP) - COLLUSION RING 2. "
        "Shared banking (PUNB0123400) and primary contact phone with B005. Cover bidding structure.\n"
        "10. Pinnacle Systems India Pvt. Ltd. (B010, Bid: ₹2.48 Cr, MII: 75%, OEM: Lenovo) - CLEAN BIDDER. Fully compliant.\n"
        "11. ByteWave Electronics Pvt. Ltd. (B011, Bid: ₹2.30 Cr, MII: 55%, OEM: Asus) - ANOMALY: 2 non-consecutive GST filing gaps in 2025. "
        "Strong financials (₹28 Cr turnover). Lowest technically viable if B004 fails clarification.\n"
        "12. Atlas Infosys Solutions Pvt. Ltd. (B012, Bid: ₹2.46 Cr, MII: 70%, OEM: HCL) - CLEAN BIDDER. Fully compliant.\n\n"
        "=== AUTHBID PLATFORM ARCHITECTURE & CAPABILITIES ===\n"
        "- 6-Stage Automated Verification Pipeline: Connects to GSTN (returns, turnover), PAN/CBDT (identity, name matching), "
        "MCA21 (CIN, DIN registry, director cross-referencing), Udyam (MSME classification & GFR 153 exemption), "
        "Debarment/Blacklist (CPPP/GeM GFR 151 records), and Financials (3-yr turnover, OEM authorization).\n"
        "- Anti-Collusion Graph & Cartel Ring Detection: Resolves multi-entity networks across DINs, physical addresses, "
        "bank IFSC/account numbers, phone numbers, and emails using NetworkX/Neo4j graph analysis to uncover bid-rigging cartels.\n"
        "- Composite Risk Scoring: 0-100 score weighing collusion indicators, statutory compliance, document validity, and financial stability.\n"
        "- RFC 3161 Merkle Audit Trail: Every verification step, score change, and officer decision is cryptographically anchored "
        "in an immutable SHA-256 hash-chained audit ledger with tamper detection.\n"
        "- Statutory Show-Cause Generator: Formulates formal legal notices with exact DINs, IFSCs, and statutory clauses.\n"
        "- Commercial Evaluation & L1 Price Discovery: Eliminates disqualified cartel/shell bids to identify genuine compliant L1 awardee.\n\n"
        "=== LEGAL & STATUTORY FRAMEWORK ===\n"
        "- Competition Act, 2002 Section 3(3)(a)-(d): Prohibits anti-competitive agreements, bid rigging, and collusive bidding.\n"
        "- General Financial Rules (GFR) 2017:\n"
        "  * Rule 151: Debarment from bidding for offenses or commercial malpractices (up to 2-3 years).\n"
        "  * Rule 153: Mandatory purchase preference and EMD exemptions for Micro & Small Enterprises (MSEs).\n"
        "  * Rule 173: Transparency, competition, fairness, and evaluation criteria for contract awards.\n"
        "  * Rule 175: Code of Integrity in Public Procurement (prohibiting conflict of interest, collusion, misrepresentation).\n"
        "=== CONVERSATIONAL VS FORENSIC QUERIES ===\n"
        "- If the user provides a simple greeting, conversational message, or asks who you are / what you can do (e.g. 'hello', 'hi', 'hey', 'namaste', 'who are you', 'how are you', 'what can you do', 'help'):\n"
        "  Respond warmly and conversationally as the GeM Vigilance AI Copilot for AuthBid. Set 'title': 'GeM Copilot Assistant', 'summary': '<Warm greeting explaining your role and giving examples of questions you can answer for Tender GEM/2026/B/4521897 and its 12 bidders>', 'evidence': [], 'legal_statute': '', 'recommendation': '', and 'is_chat': true.\n"
        "- If the user asks a specific question about tenders, bidders, collusion rings, shell companies, price evaluation, or platform features:\n"
        "  Provide the rigorous forensic analysis with populated evidence, legal_statute, and recommendation, and 'is_chat': false.\n\n"
        "=== RESPONSE CONTRACT ===\n"
        "You MUST respond ONLY with a single valid JSON object with EXACTLY these keys:\n"
        "{\n"
        '  "title": "<Concise descriptive title>",\n'
        '  "summary": "<High-level executive summary of findings tailored to the user query>",\n'
        '  "evidence": ["<Specific evidence point 1>", "<Specific evidence point 2>", ...],\n'
        '  "legal_statute": "<Relevant Indian legal statutes, GFR rules, or GeM clauses cited>",\n'
        '  "recommendation": "<Actionable legal / vigilance recommendation for procurement officer>",\n'
        '  "is_chat": false\n'
        "}\n"
        "Do NOT wrap in markdown code blocks. Return strictly valid JSON."
    )


def _detect_mentioned_bidder(query_text: str) -> str | None:
    """Detects if a query specifically targets any of the 12 bidders by ID or name."""
    q = query_text.lower()
    bidder_map = {
        "b001": "B001", "techvision": "B001",
        "b002": "B002", "reliable": "B002", "relicomp": "B002",
        "b003": "B003", "digicore": "B003",
        "b004": "B004", "greentech": "B004",
        "b005": "B005", "nexgen": "B005",
        "b006": "B006", "bharat": "B006",
        "b007": "B007", "quantum": "B007",
        "b008": "B008", "megabyte": "B008",
        "b009": "B009", "cloudfirst": "B009",
        "b010": "B010", "pinnacle": "B010",
        "b011": "B011", "bytewave": "B011",
        "b012": "B012", "atlas": "B012",
    }
    for key, b_id in bidder_map.items():
        if re.search(r'\b' + re.escape(key) + r'\b', q):
            return b_id
    return None


def _query_gemini_copilot(raw_query: str, query: str, tender_id: str, bidder_id: str | None, untrusted_context: str) -> dict | None:
    """
    Attempts to answer copilot query via Google Gemini LLM using langchain-google-genai.
    Uses candidate model fallback and rich AuthBid project knowledge grounding.
    Returns structured dictionary matching Copilot response contract, or None on failure.
    """
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")
    if not api_key or not api_key.strip() or api_key.strip() in ["your_gemini_api_key_here", ""]:
        return None

    # Preferred candidate models (prioritize fast, supported models)
    preferred_model = settings.LLM_MODEL or "gemini-2.5-flash"
    models_to_try = [preferred_model, "gemini-2.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
    candidate_models = []
    for m in models_to_try:
        if m and m not in candidate_models:
            candidate_models.append(m)

    # Dynamic bidder enrichment if mentioned in query
    additional_bidder_context = ""
    target_bidder_id = bidder_id or _detect_mentioned_bidder(raw_query)
    if target_bidder_id:
        b_info = get_bidder_by_id(target_bidder_id)
        if b_info:
            b_summary = {
                "bidder_id": b_info.get("bidder_id"),
                "entity_name": b_info.get("entity_name"),
                "bid_amount": b_info.get("bid_amount"),
                "pan": b_info.get("pan"),
                "gstin": b_info.get("gstin"),
                "cin": b_info.get("cin"),
                "anomalies": b_info.get("anomalies"),
                "directors": [d.get("name") for d in b_info.get("directors", [])],
                "oem_name": b_info.get("oem_name"),
                "make_in_india_percent": b_info.get("make_in_india_percent"),
            }
            additional_bidder_context = f"\nTarget Bidder Dossier ({target_bidder_id}):\n{json.dumps(b_summary, default=str)}"

    # GraphRAG Retrieval: Retrieve Knowledge Graph facts + Document Vector chunks
    rag_context = ""
    retrieved_chunks = []
    graph_facts = []
    try:
        from ai.rag_service import rag_service
        retrieved_chunks = rag_service.retrieve(raw_query, bidder_id=target_bidder_id, top_k=4)
        graph_facts = rag_service.retrieve_graph_context(target_bidder_id) if target_bidder_id else []

        if retrieved_chunks or graph_facts:
            rag_context = "\n\nRetrieved Ground-Truth Intelligence (GraphRAG):\n"
            if graph_facts:
                rag_context += "--- Knowledge Graph Evidence (Neo4j Multi-Entity Resolution) ---\n"
                for gf in graph_facts:
                    rag_context += f"• {gf}\n"
            if retrieved_chunks:
                rag_context += "\n--- Document Evidence (Vector RAG) ---\n"
                for c in retrieved_chunks:
                    rag_context += f"• [{c['file_name']} | Page {c['page']}]: {c['text']}\n"
    except Exception as e:
        rag_context = ""

    system_instruction = _build_copilot_system_instruction(tender_id, target_bidder_id)
    user_content = f"User Query: {raw_query}\nTarget Tender: {tender_id}"
    if untrusted_context:
        user_content += f"\nBidder Context (Sanitized):\n{untrusted_context}"
    if additional_bidder_context:
        user_content += additional_bidder_context
    if rag_context:
        user_content += rag_context

    for model_name in candidate_models:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import SystemMessage, HumanMessage

            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key.strip(),
                request_timeout=20,
                max_retries=1,
            )

            response = llm.invoke([
                SystemMessage(content=system_instruction),
                HumanMessage(content=user_content),
            ])
            raw_content = response.content
            if isinstance(raw_content, list):
                content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw_content).strip()
            else:
                content = str(raw_content).strip()

            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            content = content.strip()

            parsed = json.loads(content)
            if isinstance(parsed, dict) and "title" in parsed and "summary" in parsed:
                evidence_list = [str(e) for e in parsed.get("evidence", [])] if isinstance(parsed.get("evidence"), list) else []
                is_chat = parsed.get("is_chat", False) or (len(evidence_list) == 0 and not parsed.get("legal_statute") and not parsed.get("recommendation"))
                
                citations = [
                    {
                        "doc_id": c.get("doc_id"),
                        "file_name": c.get("file_name"),
                        "page": c.get("page", 1),
                        "bidder_id": c.get("bidder_id"),
                        "score": round(float(c.get("score", 0.0)), 3),
                        "snippet": (c.get("text", "")[:180] + "...") if len(c.get("text", "")) > 180 else c.get("text", ""),
                        "view_url": f"/api/verification/documents/{c.get('doc_id')}/view" if c.get("doc_id") else None,
                    }
                    for c in retrieved_chunks
                ] if retrieved_chunks else []

                return {
                    "title": str(parsed["title"]),
                    "summary": str(parsed["summary"]),
                    "evidence": evidence_list,
                    "legal_statute": str(parsed.get("legal_statute", "")),
                    "recommendation": str(parsed.get("recommendation", "")),
                    "disclaimer": f"AI-generated analysis ({model_name}) — verify independently against statutory records before making legal determinations.",
                    "context_applied": untrusted_context or additional_bidder_context,
                    "is_chat": is_chat,
                    "citations": citations,
                    "graph_citations": graph_facts[:4] if graph_facts else [],
                }
        except Exception:
            continue

    return None


@router.post("/copilot")
async def copilot_query(payload: dict):
    """
    AI Vigilance & Legal Procurement Copilot for AuthBid.
    Answers technical, legal, anti-collusion, and forensic questions regarding Tender GEM/2026/B/4521897,
    specific bidders (B001 to B012), platform features (Audit trail, Graph, Risk scoring, Show Cause),
    and statutory provisions (Competition Act 2002, GFR 2017).
    Powered by live Google Gemini LLM with exhaustive deterministic fallback.
    """
    raw_query = payload.get("query", "")
    query = _sanitize_bidder_input(raw_query).lower()
    tender_id = payload.get("tender_id", "GEM/2026/B/4521897")
    bidder_id = payload.get("bidder_id") or _detect_mentioned_bidder(raw_query)

    # 1. Handle common greetings and conversational messages immediately
    greetings = {"hello", "hi", "hey", "hola", "namaste", "good morning", "good afternoon", "good evening", "yo", "sup", "who are you", "what can you do", "help", "greet", "greeting", "hey there", "hello copilot"}
    clean_q = re.sub(r"[^\w\s]", "", query).strip()
    if clean_q in greetings or clean_q == "":
        return {
            "success": True,
            "data": {
                "title": "GeM Vigilance Copilot",
                "summary": (
                    "Namaste! I am your GeM Vigilance & Legal AI Copilot for AuthBid, monitoring Tender GEM/2026/B/4521897 "
                    "('Supply of 500 Desktop Computers with 3-Year Warranty', ₹2.50 Cr).\n\n"
                    "I am ready to help you evaluate bids and detect irregularities. You can ask me:\n"
                    "• Bidder Analysis: Ask about any of the 12 bidders (e.g., 'What is wrong with B006?', 'Why is B007 a shell company?')\n"
                    "• Collusion Forensics: Ask about 'Collusion Ring 1' (B001, B003, B007) or 'Ring 2' (B005, B009)\n"
                    "• Commercial Evaluation: Ask 'Who is the recommended L1 bidder?'\n"
                    "• Platform Features: Ask how the Anti-Collusion Graph or RFC 3161 Audit Trail works\n"
                    "• Statutory Citations: Ask about grounds under GFR 151, GFR 175, or Competition Act 2002"
                ),
                "evidence": [],
                "legal_statute": "",
                "recommendation": "",
                "disclaimer": "AI Copilot — Ready to assist with procurement intelligence.",
                "is_chat": True,
            }
        }

    # Construct isolated untrusted bidder document segment
    untrusted_context = ""
    if bidder_id:
        bidder = get_bidder_by_id(bidder_id)
        if bidder:
            sanitized_name = _sanitize_bidder_input(bidder.get("entity_name", ""))
            untrusted_context = (
                f'<untrusted_bidder_context source="uploaded_dossier" bidder_id="{bidder_id}" sanitized="true">'
                f'Entity: {sanitized_name}, PAN: {bidder.get("pan")}, GSTIN: {bidder.get("gstin")}'
                f'</untrusted_bidder_context>'
            )

    # 2. Attempt live LLM response via Google Gemini asynchronously with timeout
    try:
        live_response = await asyncio.to_thread(
            _query_gemini_copilot, raw_query, query, tender_id, bidder_id, untrusted_context
        )
    except Exception:
        live_response = None

    if live_response:
        return {
            "success": True,
            "data": live_response,
        }

    # 2. Comprehensive deterministic rule-based fallback based on canonical AuthBid intelligence
    # ── Ring 1 (Bid Rigging Cartel) ──
    if "ring 1" in query or "ring1" in query or ("collusion" in query and any(x in query for x in ["techvision", "b001", "b003", "b007", "cartel"])):
        return {
            "success": True,
            "data": {
                "title": "Analysis of Collusion Ring 1 (Bid Rigging Cartel)",
                "summary": "Forensic graph analysis resolved an active bid-rigging syndicate operating across three entities: TechVision Solutions (B001), DigiCore Infosystems (B003), and Quantum Digital Services (B007).",
                "evidence": [
                    "Shared Directors: Rajesh Kumar Sharma (DIN: 09876543) and Vikram Singh Chauhan (DIN: 08765432) hold board seats simultaneously across B001, B003, and B007.",
                    "Common Physical Address: All three entities list Plot No. 45, Sector 18, Industrial Area Phase II, Gurugram, Haryana as their registered office.",
                    "Shell Entity Planting: Quantum Digital Services (B007) was incorporated merely 90 days ago with zero prior GST filing history, created to submit an artificial cover bid to satisfy the three-bidder minimum threshold.",
                    "Price Coordination: Bids are clustered tightly (₹2.20 Cr, ₹2.35 Cr, ₹2.48 Cr) around the ₹2.50 Cr estimate to manipulate L1 determination."
                ],
                "legal_statute": "Section 3(3)(d) of the Competition Act, 2002 (Bid Rigging or Collusive Bidding) & Rule 175 of General Financial Rules (GFR) 2017.",
                "recommendation": "Disqualify all three bidders immediately. Forfeit EMD, initiate 2-year debarment proceedings under Rule 151 of GFR 2017, and refer dossier to the Competition Commission of India (CCI).",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── Ring 2 (Related Party Nexus) ──
    elif "ring 2" in query or "ring2" in query or any(x in query for x in ["b005", "b009", "nexus", "cloudfirst", "nexgen"]):
        return {
            "success": True,
            "data": {
                "title": "Analysis of Collusion Ring 2 (Related Party Bidding)",
                "summary": "NexGen IT Solutions (B005) and CloudFirst Technologies (B009) have submitted competitive bids while sharing operational and financial infrastructure.",
                "evidence": [
                    "Shared Banking: Both entities route tender transactions through Punjab National Bank branch (IFSC: PUNB0123400) with identical account prefix series.",
                    "Common Contact: The authorized signatory mobile number for NexGen IT Solutions matches the direct phone contact of CloudFirst Technologies' primary director (9098765432).",
                    "Cover Bidding Pattern: Bid amounts (₹2.39 Cr vs ₹2.32 Cr) are structured to protect CloudFirst Technologies while maintaining an illusion of market competition."
                ],
                "legal_statute": "GeM General Terms & Conditions Clause 4.14 (Prohibition of Related Party Bidding) & Section 3(3)(c) Competition Act 2002.",
                "recommendation": "Issue Show-Cause notice seeking justification within 48 hours. If common control is confirmed, reject both bids and debar from future MeitY tenders.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── Shell Company / B007 ──
    elif "b007" in query or "shell" in query or "quantum" in query:
        return {
            "success": True,
            "data": {
                "title": "Forensic Entity Report: Quantum Digital Services Pvt. Ltd. (B007)",
                "summary": "Quantum Digital Services exhibits 4 classic indicators of a synthetic front/shell company.",
                "evidence": [
                    "Age of Incorporation: Incorporated June 2026 (less than 90 days operational), failing the 3-year tender experience requirement.",
                    "GST Compliance: Zero GSTR-3B filings recorded in the central tax portal.",
                    "Turnover Inadequacy: Submitted un-audited provisional figures with invalid ICAI UDIN.",
                    "Director Nexus: Directorial overlap with B001 (TechVision Solutions) and B003 (DigiCore Infosystems)."
                ],
                "legal_statute": "Prevention of Money Laundering Act (PMLA) Section 66 & GeM Seller Debarment Policy Section 3.",
                "recommendation": "Immediate summary rejection and freeze on GeM seller account.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── L1 Evaluation & Price Discovery ──
    elif any(x in query for x in ["l1", "lowest", "winner", "award", "price discovery", "commercial"]):
        return {
            "success": True,
            "data": {
                "title": "L1 Commercial Evaluation & Award Recommendation",
                "summary": "After filtering out disqualified collusion rings and non-compliant entities, genuine price discovery indicates compliant L1 standing.",
                "evidence": [
                    "Lowest Bidder Overall: Quantum Digital Services (₹2.20 Cr) — DISQUALIFIED (Shell entity in Collusion Ring 1).",
                    "Second Lowest: GreenTech Peripherals (₹2.28 Cr) — UNDER SCRUTINY (Expired MSME certificate requiring 48-hr clarification).",
                    "Lowest Fully Compliant Bidder: ByteWave Electronics (B011, ₹2.30 Cr) has minor GST gaps. If disqualified, Reliable Computing Systems (B002, ₹2.42 Cr) represents the cleanest compliant L1."
                ],
                "legal_statute": "GFR 2017 Rule 173(xxi) — Evaluation of Bids and Award of Contract.",
                "recommendation": "Reject cover bids B007, B001, B003. Request MSE certificate renewal from B004. If clarified, award to B004 at ₹2.28 Cr (saving ₹22 Lakhs vs estimate). Otherwise, award to Reliable Computing Systems (B002) at ₹2.42 Cr.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── B004 / GreenTech (Expired MSME) ──
    elif "b004" in query or "greentech" in query or "expired msme" in query:
        return {
            "success": True,
            "data": {
                "title": "Bidder Dossier: GreenTech Peripherals Pvt. Ltd. (B004)",
                "summary": "GreenTech Peripherals submitted the second-lowest bid (₹2.28 Cr) but has an expired MSME Udyam certificate requiring statutory clarification.",
                "evidence": [
                    "Bid Amount: ₹2.28 Cr (₹22 Lakhs below estimated tender value of ₹2.50 Cr).",
                    "MSME Status: Udyam Registration (UDYAM-DL-01-0023456) expired on 31-March-2026.",
                    "Exemption Claim: Claimed EMD and turnover exemption under GFR Rule 153 using expired credentials.",
                    "Make in India: Declared 55% local content with valid OEM authorization from HP India."
                ],
                "legal_statute": "GFR 2017 Rule 153 (Public Procurement Policy for MSEs) & GeM Bid Eligibility Guidelines.",
                "recommendation": "Issue 48-hour clarification notice to submit renewed Udyam certificate. If submitted, consider for L1 award; if not, evaluate without MSE preference.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── B006 / Bharat Electronics (PAN/GST Mismatch) ──
    elif "b006" in query or "bharat" in query or "pan mismatch" in query or "name mismatch" in query:
        return {
            "success": True,
            "data": {
                "title": "Bidder Dossier: Bharat Electronics & Computing Ltd. (B006)",
                "summary": "B006 exhibits a nomenclature discrepancy between its CBDT PAN record and its GSTN registration.",
                "evidence": [
                    "PAN Legal Name: 'Bharat Electronics and Computers Ltd.' (PAN: AABCB3456D).",
                    "GSTN Trade Name: 'Bharat Electronics & Computing Ltd.' (GSTIN: 07AABCB3456D1Z9).",
                    "Levenshtein Discrepancy: 2% character mismatch ('Computers' vs 'Computing').",
                    "Turnover & Experience: Exceeds all mandatory financial and technical criteria with 80% Make in India content."
                ],
                "legal_statute": "GFR 2017 Rule 173 (Verification of Credentials) & PAN-GST Validation Protocols.",
                "recommendation": "Seek clerical clarification and CA certificate confirming single corporate identity within 48 hours. Not considered intentional fraud.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── B008 / MegaByte (Debarment History) ──
    elif "b008" in query or "megabyte" in query or "debarment" in query or "blacklist" in query:
        return {
            "success": True,
            "data": {
                "title": "Bidder Dossier: MegaByte Computers Pvt. Ltd. (B008)",
                "summary": "MegaByte Computers has a past debarment record that has been legally served and cleared.",
                "evidence": [
                    "Historical Debarment: Debarred by Department of Posts for 12 months in 2023 for delayed delivery.",
                    "Current Status: Debarment expired in October 2024; currently Active and in good standing on CPPP/GeM.",
                    "Bid Details: ₹2.40 Cr bid amount, 62% Make in India, Dell OEM authorization.",
                    "Statutory Eligibility: Eligible to participate under GFR 151 as debarment period has lapsed."
                ],
                "legal_statute": "GFR 2017 Rule 151 (Debarment from Bidding) & GeM Debarment Policy Section 4.",
                "recommendation": "Verify no active appeals or ongoing vigilance cases. If clear, treat as technically eligible.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── B011 / ByteWave (GST Filing Gaps) ──
    elif "b011" in query or "bytewave" in query or "gst gap" in query:
        return {
            "success": True,
            "data": {
                "title": "Bidder Dossier: ByteWave Electronics Pvt. Ltd. (B011)",
                "summary": "ByteWave Electronics submitted a competitive bid of ₹2.30 Cr but has 2 non-consecutive GST filing gaps in 2025.",
                "evidence": [
                    "Bid Amount: ₹2.30 Cr (Second lowest compliant bid, saving ₹20 Lakhs).",
                    "Financial Strength: Annual turnover ₹28.00 Cr (well above ₹1.00 Cr requirement).",
                    "Tax Filing Gap: GSTR-3B missing for May 2025 and October 2025; subsequent filings up to date.",
                    "OEM Authorization: Valid Asus OEM certificate, 55% Make in India content."
                ],
                "legal_statute": "GeM Seller Due Diligence Guidelines & Central Goods and Services Tax (CGST) Act Section 39.",
                "recommendation": "Request proof of tax payment/challans for the two missing return periods before contract execution.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── Clean Bidders: B002, B010, B012 ──
    elif any(x in query for x in ["b002", "b010", "b012", "clean", "reliable", "pinnacle", "atlas"]):
        return {
            "success": True,
            "data": {
                "title": "Evaluation of Clean & Compliant Bidders",
                "summary": "Three bidders have passed all 11 forensic verification vectors with zero anomalies: B002, B010, and B012.",
                "evidence": [
                    "Reliable Computing Systems Ltd. (B002): Bid ₹2.42 Cr, Dell OEM, 72% MII, ₹12-15 Cr turnover, pristine GST/PAN record. Top clean L1 recommendation.",
                    "Pinnacle Systems India Pvt. Ltd. (B010): Bid ₹2.48 Cr, Lenovo OEM, 75% MII, ₹18 Cr turnover, flawless compliance.",
                    "Atlas Infosys Solutions Pvt. Ltd. (B012): Bid ₹2.46 Cr, HCL OEM, 70% MII, ₹14 Cr turnover, clean compliance history."
                ],
                "legal_statute": "GFR 2017 Rule 173 (Award of Contract to Responsive and Compliant Bidder).",
                "recommendation": "Award contract to Reliable Computing Systems Ltd. (B002) as the cleanest compliant L1 bidder if B004 fails MSME clarification.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── AuthBid Platform Features & Capabilities ──
    elif any(x in query for x in ["authbid", "features", "capabilities", "what is", "how does", "pipeline", "platform"]):
        return {
            "success": True,
            "data": {
                "title": "AuthBid Platform Capabilities & Architecture",
                "summary": "AuthBid is an AI-powered vigilance, forensic compliance, and anti-collusion intelligence platform built for GeM procurement officers.",
                "evidence": [
                    "6-Stage Automated Verification: Real-time verification across GSTN (returns), CBDT/PAN (name matching), MCA21 (DINs/CIN), Udyam (MSME), Central Debarment (GFR 151), and Financials.",
                    "Anti-Collusion Graph Engine: Multi-entity NetworkX/Neo4j graph resolving shared directors, common addresses, shared bank accounts (IFSC), phone numbers, and emails.",
                    "Composite Risk Scoring: 0-100 score weighing collusion indicators, statutory compliance, document validity, and financial stability.",
                    "RFC 3161 Merkle Audit Trail: Every verification step, score change, and officer decision is cryptographically anchored in an immutable SHA-256 hash-chained audit ledger.",
                    "Statutory Show-Cause Generator: Formulates formal legal notices with exact DINs, IFSCs, and statutory citations under GFR 151/175 and Competition Act 2002.",
                    "Commercial Evaluation & L1 Discovery: Automatically filters out cartel/shell bids to discover genuine compliant L1 awardees."
                ],
                "legal_statute": "Competition Act 2002 Section 3(3), GFR 2017 Rules 151, 153, 173, 175, and GeM GTC 4.14.",
                "recommendation": "Utilize the Triage Queue and Copilot Drawer to review anomalous bidders before opening commercial bids.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── Anti-Collusion Graph & Cartel Detection ──
    elif any(x in query for x in ["graph", "neo4j", "network", "directors"]):
        return {
            "success": True,
            "data": {
                "title": "Anti-Collusion Knowledge Graph Intelligence",
                "summary": "AuthBid's forensic graph engine evaluates entity relationships across 5 node types: Bidders, Directors, Addresses, Banks, and Contacts.",
                "evidence": [
                    "Ring 1 Resolution: B001, B003, and B007 linked by shared directors Rajesh Kumar Sharma (DIN: 09876543) and Vikram Singh Chauhan (DIN: 08765432), plus shared Gurugram address.",
                    "Ring 2 Resolution: B005 and B009 linked by Punjab National Bank branch (IFSC: PUNB0123400) and authorized phone number (9098765432).",
                    "Degree & Centrality Metrics: Identifies hub nodes and coordinated cover bidding patterns.",
                    "Visual Graph View: Interactive multi-cluster visualization accessible in the Graph tab."
                ],
                "legal_statute": "Competition Act 2002 Section 3(3) (Anti-Competitive Agreements & Cartels).",
                "recommendation": "Export graph evidence report and attach as Annexure A to formal disqualification orders.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── Audit Trail & RFC 3161 Ledger ──
    elif any(x in query for x in ["audit", "merkle", "rfc 3161", "hash", "tamper", "blockchain", "ledger"]):
        return {
            "success": True,
            "data": {
                "title": "Cryptographic Audit Ledger & RFC 3161 Merkle Trail",
                "summary": "AuthBid maintains a tamper-proof SHA-256 hash-chained audit ledger ensuring legal accountability for every decision.",
                "evidence": [
                    "Immutable Hash Chain: Each audit entry contains previous_hash, timestamp, agent_id, action, and current_hash.",
                    "Merkle Root Sealing: Hourly batches are anchored via RFC 3161 compliant timestamping authority.",
                    "Tamper Detection: Automated cryptographic chain verification flags any unauthorized alteration or sequence breach.",
                    "Officer Decision Tracking: All disqualifications, show-cause issuances, and overrides are cryptographically logged with role attribution."
                ],
                "legal_statute": "Information Technology Act 2000 Section 65B (Admissibility of Electronic Records) & GFR 2017 Rule 175.",
                "recommendation": "Verify audit chain integrity prior to final contract award signing to ensure an incontrovertible legal record.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }

    # ── General Fallback for Tender GEM/2026/B/4521897 ──
    else:
        return {
            "success": True,
            "data": {
                "title": "AuthBid GeM Procurement Compliance Intelligence",
                "summary": f"Intelligence report for Tender {tender_id} ('Supply of 500 Desktop Computers with 3-Year Warranty', ₹2.50 Cr). Monitoring 12 active bidders across 11 compliance vectors.",
                "evidence": [
                    "Total Bidders Monitored: 12 (B001 to B012).",
                    "Collusion Syndicates Detected: 2 Rings (5 Bidders: B001, B003, B007 in Ring 1; B005, B009 in Ring 2).",
                    "Shell Entity Flagged: B007 (Quantum Digital Services) incorporated <90 days ago with zero GST filings.",
                    "Compliance Anomalies: B004 (Expired MSME), B006 (PAN name typo), B008 (Past debarment cleared), B011 (GST filing gaps).",
                    "Clean Compliant Candidates: 3 Bidders (B002 Reliable Computing, B010 Pinnacle Systems, B012 Atlas Infosys).",
                    "Audit Trail Status: Cryptographically sealed with SHA-256 hash chains."
                ],
                "legal_statute": "General Financial Rules (GFR) 2017 Rules 151, 153, 173, 175 & Competition Act 2002 Section 3(3).",
                "recommendation": "Review the Bidder Intelligence Dossiers and Scrutiny Memo before proceeding to financial bid opening.",
                "disclaimer": "AI-generated analysis — verify independently against statutory records before making legal determinations.",
                "context_applied": untrusted_context,
            }
        }


@router.get("/show-cause/{bidder_id}")
async def generate_show_cause_notice(
    bidder_id: str,
    current_role: UserRole = Depends(require_roles([UserRole.OFFICER, UserRole.ADMIN])),
):
    """
    Generate formal Government of India Show-Cause Notice under GFR 2017 & Competition Act.
    Restricted to Officer and Admin roles.
    """
    bidder = get_bidder_by_id(bidder_id)
    if not bidder:
        raise HTTPException(status_code=404, detail=f"Bidder {bidder_id} not found")

    is_ring1 = bidder_id in ["B001", "B003", "B007"]
    is_ring2 = bidder_id in ["B005", "B009"]

    charges = []
    if is_ring1:
        charges.append("Violations under Section 3(3)(a) and 3(3)(d) of Competition Act 2002 (Bid Rigging and Cartelization).")
        charges.append("Concealment of common directorships (DIN: 09876543, 08765432) across participating competing entities.")
        charges.append("Submission of non-genuine cover bids to circumvent the GeM three-bidder competition requirement.")
    elif is_ring2:
        charges.append("Violation of GeM GTC Clause 4.14 — Anti-Competitive Practice through Related Party Bidding.")
        charges.append("Operation of competing tender entities utilizing shared financial banking channels (IFSC: PUNB0123400).")
    elif bidder_id == "B004":
        charges.append("Claiming MSE exemption using an expired MSME Udyam registration (expired 2025-12-31).")
    else:
        charges.append("Discrepancies identified during multi-source automated compliance verification.")

    return {
        "success": True,
        "data": {
            "notice_number": f"GEM/VIG/2026/SCN-{bidder_id}-904",
            "date": datetime.now().strftime("%d-%m-%Y"),
            "issuing_authority": "Directorate of Vigilance & Technical Scrutiny, GeM",
            "tender_id": "GEM/2026/B/4521897",
            "bidder": {
                "bidder_id": bidder["bidder_id"],
                "entity_name": bidder["entity_name"],
                "pan": bidder["pan"],
                "gstin": bidder["gstin"],
                "registered_address": bidder["registered_address"],
            },
            "charges": charges,
            "legal_clauses": [
                "Rule 151 & 175 of General Financial Rules (GFR), 2017",
                "Section 3(3) of Competition Act, 2002",
                "GeM Incident Management & Debarment Policy Version 3.2"
            ],
            "response_deadline_days": 7,
            "officer_name": "P. V. Ramanathan",
            "officer_designation": "Chief Vigilance Officer, GeM",
        },
    }


@router.get("/documents/{bidder_id}")
async def get_bidder_documents(bidder_id: str):
    """Get verified digital document vault for a bidder."""
    bidder = get_bidder_by_id(bidder_id)
    if not bidder:
        raise HTTPException(status_code=404, detail=f"Bidder {bidder_id} not found")

    raw_doc_defs = [
        {
            "doc_id": f"DOC-GST-{bidder_id}",
            "doc_type": "GST_REG06",
            "doc_name": "GST Registration Certificate (REG-06)",
            "verification_source": "GSTN API (Realtime)",
            "status": "verified" if bidder.get("gst_status") == "Active" else "flagged",
        },
        {
            "doc_id": f"DOC-PAN-{bidder_id}",
            "doc_type": "PAN_CARD",
            "doc_name": "Permanent Account Number (PAN Card)",
            "verification_source": "CBDT / NSDL Database",
            "status": "verified" if bidder.get("pan_status") == "Valid" else "flagged",
        },
        {
            "doc_id": f"DOC-MSME-{bidder_id}",
            "doc_type": "UDYAM_CERT",
            "doc_name": "Udyam MSME Registration Certificate",
            "verification_source": "Ministry of MSME Udyam Portal",
            "status": "verified" if bidder.get("msme_category") else "not_applicable",
        },
        {
            "doc_id": f"DOC-OEM-{bidder_id}",
            "doc_type": "OEM_AUTH",
            "doc_name": "OEM Authorization Letter (MAF)",
            "verification_source": "Direct OEM Registry",
            "status": "verified",
        },
        {
            "doc_id": f"DOC-AUDIT-{bidder_id}",
            "doc_type": "BALANCE_SHEET",
            "doc_name": "Audited Balance Sheets (3 Financial Years)",
            "verification_source": "MCA21 & ICAI UDIN Registry",
            "status": "flagged" if bidder_id == "B007" else "verified",
        },
        {
            "doc_id": f"DOC-MII-{bidder_id}",
            "doc_type": "MII_DECLARATION",
            "doc_name": "Make in India (MII) Self-Declaration",
            "verification_source": "DPIIT MII Portal",
            "status": "verified",
        },
    ]

    doc_search_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/documents")),
    ]

    docs = []
    for d_def in raw_doc_defs:
        doc_id = d_def["doc_id"]
        doc_type = d_def["doc_type"]
        file_name = f"{doc_id}.pdf"
        file_path = None
        for s_dir in doc_search_dirs:
            p = os.path.join(s_dir, file_name)
            if os.path.exists(p):
                file_path = p
                break

        if file_path:
            with open(file_path, "rb") as f:
                content = f.read()
            file_hash = hashlib.sha256(content).hexdigest()
            file_size = len(content)
            extraction = document_pipeline.extract_document_fields(doc_id, doc_type, content, bidder)
            extracted_dict = {k: v.value for k, v in extraction.fields.items()}
            ocr_score = extraction.ocr_match_score
            has_pdf = True
        else:
            file_hash = hashlib.sha256(f"{bidder_id}_{doc_type}".encode()).hexdigest()
            file_size = 0
            extracted_dict = {}
            ocr_score = 95.0
            has_pdf = False

        docs.append({
            "doc_id": doc_id,
            "doc_name": d_def["doc_name"],
            "verification_source": d_def["verification_source"],
            "status": d_def["status"],
            "ocr_match_score": ocr_score,
            "sha256_hash": file_hash,
            "file_size_bytes": file_size,
            "has_pdf": has_pdf,
            "download_url": f"/api/verification/documents/{doc_id}/download",
            "view_url": f"/api/verification/documents/{doc_id}/view",
            "extracted_data": extracted_dict,
        })

    return {
        "success": True,
        "data": {
            "bidder_id": bidder_id,
            "entity_name": bidder["entity_name"],
            "documents": docs,
        },
    }


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str):
    """Download authentic document PDF evidence."""
    clean_id = os.path.basename(doc_id)
    doc_search_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/documents")),
    ]
    for s_dir in doc_search_dirs:
        p = os.path.join(s_dir, f"{clean_id}.pdf")
        if os.path.exists(p):
            return FileResponse(p, media_type="application/pdf", filename=f"{clean_id}.pdf")

    raise HTTPException(status_code=404, detail=f"Document file {clean_id}.pdf not found.")


@router.get("/documents/{doc_id}/view")
async def view_document(doc_id: str):
    """Stream authentic document PDF evidence with inline disposition for in-browser viewing."""
    clean_id = os.path.basename(doc_id)
    doc_search_dirs = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/documents")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/documents")),
    ]
    for s_dir in doc_search_dirs:
        p = os.path.join(s_dir, f"{clean_id}.pdf")
        if os.path.exists(p):
            return FileResponse(
                p,
                media_type="application/pdf",
                headers={"Content-Disposition": f"inline; filename={clean_id}.pdf"},
            )

    raise HTTPException(status_code=404, detail=f"Document file {clean_id}.pdf not found.")


@router.post("/reset")
async def reset_demo_endpoint():
    """Reset demo state back to clean initial state with sample tender seeded."""
    res = reset_demo_data()
    return {"success": True, "data": res}


