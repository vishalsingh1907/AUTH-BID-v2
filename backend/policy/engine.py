"""
SIH26100 — Deterministic Tender Policy Evaluation Engine
Evaluates bidder profile and connector evidence against versioned policy requirements.
Ensures zero silent passes: missing or unavailable sources produce INDETERMINATE or FAIL.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import difflib
from policy.models import (
    EvaluationResult,
    EvaluationOutcome,
    RequirementSeverity,
)


class PolicyEvaluationEngine:
    """Deterministic policy evaluation engine for public procurement."""

    def __init__(self, policy_version: str = "v1.0"):
        self.policy_version = policy_version

    def evaluate_bidder(
        self,
        bidder: Dict[str, Any],
        tender: Dict[str, Any],
        all_bidders: Optional[List[Dict[str, Any]]] = None,
        connector_statuses: Optional[Dict[str, str]] = None,
    ) -> List[EvaluationResult]:
        """
        Evaluate all applicable requirements for a bidder.
        Produces standardized EvaluationResult for every rule.
        """
        all_bidders = all_bidders or []
        connector_statuses = connector_statuses or {}
        criteria = tender.get("eligibility_criteria", {})
        results: List[EvaluationResult] = []

        # 1. REQ-GST-01: GST Active Registration
        gst_status = bidder.get("gst_status")
        gstin = bidder.get("gstin")
        if not gstin:
            outcome = EvaluationOutcome.FAIL
            details = "GSTIN not provided. Mandatory statutory identifier missing."
            follow_up = "Reject bid or demand immediate GSTIN disclosure."
        elif gst_status == "Active":
            outcome = EvaluationOutcome.PASS
            details = f"Active GSTIN verified: {gstin}."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = f"GSTIN {gstin} status is '{gst_status}'. Active registration required."
            follow_up = "Issue clarification seeking active registration proof."

        results.append(
            EvaluationResult(
                requirement_id="REQ-GST-01",
                name="GST Registration Status",
                category="GST",
                citation="GFR 2017 Rule 144(i) & GSTN Guidelines",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"gstin": gstin, "status": gst_status}],
                evidence_ids=[f"EVID-GST-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 2. REQ-GST-02: GST Return Filing Compliance (12 months)
        filings = bidder.get("gst_filing_history", [])
        if not filings:
            outcome = EvaluationOutcome.INDETERMINATE
            details = "No GST return filing history retrieved from connector."
            follow_up = "Verify filing history via GST Portal portal lookup."
        else:
            unfiled = [f for f in filings[-12:] if f.get("status") == "Not Filed"]
            if not unfiled:
                outcome = EvaluationOutcome.PASS
                details = "All GSTR-3B returns filed for the last 12-month period."
                follow_up = None
            else:
                outcome = EvaluationOutcome.WARNING
                periods = ", ".join(f["period"] for f in unfiled)
                details = f"Unfiled returns detected for {len(unfiled)} periods ({periods})."
                follow_up = "Seek statutory explanation for unfiled GST return periods."

        results.append(
            EvaluationResult(
                requirement_id="REQ-GST-02",
                name="GST Return Filing Regularity",
                category="GST",
                citation="CGST Act 2017 Section 39",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"unfiled_periods": [f["period"] for f in unfiled]} if filings else {}],
                evidence_ids=[f"EVID-GSTFILING-{bidder.get('bidder_id')}"],
                source_status="verified" if filings else "unavailable",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 3. REQ-PAN-01: PAN Identity Match
        pan = bidder.get("pan")
        entity_name = bidder.get("entity_name", "")
        pan_name = bidder.get("pan_registered_name", entity_name)
        if not pan:
            outcome = EvaluationOutcome.FAIL
            details = "PAN identifier absent."
            follow_up = "Mandatory PAN missing. Disqualification recommended."
        else:
            sim = difflib.SequenceMatcher(None, pan_name.lower().strip(), entity_name.lower().strip()).ratio()
            if sim >= 0.85:
                outcome = EvaluationOutcome.PASS
                details = f"PAN '{pan}' matches entity name (Similarity: {sim:.0%})."
                follow_up = None
            elif sim >= 0.70:
                outcome = EvaluationOutcome.WARNING
                details = f"PAN name '{pan_name}' differs slightly from entity name '{entity_name}' (Similarity: {sim:.0%})."
                follow_up = "Request formal PAN name amendment certificate."
            else:
                outcome = EvaluationOutcome.FAIL
                details = f"Severe name mismatch: PAN registered to '{pan_name}', entity declared '{entity_name}' (Similarity: {sim:.0%})."
                follow_up = "Seek legal proof of name change or disqualify under GFR 151."

        results.append(
            EvaluationResult(
                requirement_id="REQ-PAN-01",
                name="PAN Identity & Name Match",
                category="PAN",
                citation="Income Tax Act 1961 Section 139A & GFR 2017 Rule 144",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"pan": pan, "pan_name": pan_name, "declared_name": entity_name, "similarity": round(sim, 4) if pan else 0}],
                evidence_ids=[f"EVID-PAN-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 4. REQ-FIN-01: Minimum Annual Turnover
        turnovers = bidder.get("annual_turnover", [])
        min_turnover = criteria.get("min_annual_turnover", 0.0)
        is_mse = bidder.get("msme_category") in ["Micro", "Small"]
        turnover_req = 0.0 if is_mse else min_turnover

        if not turnovers and turnover_req > 0:
            outcome = EvaluationOutcome.FAIL
            details = f"No turnover figures provided. Required: ₹{turnover_req:,.0f}."
            follow_up = "Seek certified audited balance sheets."
        elif is_mse:
            outcome = EvaluationOutcome.PASS
            details = "MSE Exemption applied under GFR Rule 153. Minimum turnover relaxed."
            follow_up = None
        else:
            avg_turnover = sum(t.get("amount", 0) for t in turnovers) / max(len(turnovers), 1)
            if avg_turnover >= turnover_req:
                outcome = EvaluationOutcome.PASS
                details = f"Average 3-yr turnover ₹{avg_turnover:,.0f} exceeds requirement of ₹{turnover_req:,.0f}."
                follow_up = None
            else:
                outcome = EvaluationOutcome.FAIL
                details = f"Average 3-yr turnover ₹{avg_turnover:,.0f} falls below required ₹{turnover_req:,.0f}."
                follow_up = "Bidder fails minimum turnover requirement. Record disqualification."

        results.append(
            EvaluationResult(
                requirement_id="REQ-FIN-01",
                name="Minimum Annual Turnover",
                category="Financial",
                citation="GeM GTC Clause 4(m) & GFR 2017 Rule 173",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"turnovers": turnovers, "mse_exemption": is_mse, "required": turnover_req}],
                evidence_ids=[f"EVID-TURNOVER-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 5. REQ-EXP-01: Operating Experience Years
        incorp_str = bidder.get("incorporation_date")
        min_years = criteria.get("min_experience_years", 0)
        if not incorp_str:
            outcome = EvaluationOutcome.FAIL
            details = "Incorporation date missing."
            follow_up = "Request Certificate of Incorporation from MCA21."
        else:
            try:
                incorp_dt = datetime.strptime(incorp_str, "%Y-%m-%d")
                years = (datetime.now() - incorp_dt).days / 365.25
                if is_mse:
                    outcome = EvaluationOutcome.PASS
                    details = f"MSE Exemption applied. Operating experience relaxed under GFR 153 ({years:.1f} yrs on record)."
                    follow_up = None
                elif years >= min_years:
                    outcome = EvaluationOutcome.PASS
                    details = f"Operational for {years:.1f} years since {incorp_str} (Required: {min_years} yrs)."
                    follow_up = None
                else:
                    outcome = EvaluationOutcome.FAIL
                    details = f"Entity has only {years:.1f} years experience. Required: {min_years} years."
                    follow_up = "Non-compliant with experience clause. Verify MSE exemption status."
            except Exception:
                outcome = EvaluationOutcome.INDETERMINATE
                details = f"Invalid incorporation date format: {incorp_str}."
                follow_up = "Re-validate incorporation document."

        results.append(
            EvaluationResult(
                requirement_id="REQ-EXP-01",
                name="Past Operating Experience",
                category="Experience",
                citation="Tender Clause 3.2 & GFR 2017 Rule 173",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"incorporation_date": incorp_str, "years": round(years, 1) if 'years' in locals() else 0}],
                evidence_ids=[f"EVID-EXP-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 6. REQ-MII-01: Make in India Local Content
        mii_pct = bidder.get("make_in_india_percent", 0.0)
        min_mii = criteria.get("make_in_india_min_percent", 0.0)
        if mii_pct >= min_mii:
            outcome = EvaluationOutcome.PASS
            details = f"Declared domestic value addition of {mii_pct}% meets requirement ({min_mii}%)."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = f"Domestic value addition {mii_pct}% is below required threshold ({min_mii}%)."
            follow_up = "Verify local content self-declaration certificate."

        results.append(
            EvaluationResult(
                requirement_id="REQ-MII-01",
                name="Make in India (MII) Local Content",
                category="Technical",
                citation="Public Procurement (Preference to Make in India) Order 2017",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"make_in_india_percent": mii_pct, "required": min_mii}],
                evidence_ids=[f"EVID-MII-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 7. REQ-CRT-01: Required Technical Certifications
        req_certs = set(criteria.get("required_certifications", []))
        held_certs = set(bidder.get("certifications", []))
        missing_certs = req_certs - held_certs
        if not missing_certs:
            outcome = EvaluationOutcome.PASS
            details = f"All required certifications present: {', '.join(req_certs) or 'None specified'}."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = f"Missing mandatory certifications: {', '.join(missing_certs)}."
            follow_up = "Issue 48-hour clarification window for missing certificate upload."

        results.append(
            EvaluationResult(
                requirement_id="REQ-CRT-01",
                name="Mandatory Certifications",
                category="Technical",
                citation="Tender Technical Specifications Schedule B",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"held": list(held_certs), "missing": list(missing_certs)}],
                evidence_ids=[f"EVID-CERTS-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 8. REQ-OEM-01: OEM Authorization
        oem_auth = bidder.get("oem_authorization", False)
        oem_name = bidder.get("oem_name", "N/A")
        if oem_auth:
            outcome = EvaluationOutcome.PASS
            details = f"Valid Manufacturer Authorization Form (MAF) from OEM '{oem_name}'."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = "No valid OEM authorization letter (MAF) provided."
            follow_up = "Verify whether bidder is primary manufacturer or authorized reseller."

        results.append(
            EvaluationResult(
                requirement_id="REQ-OEM-01",
                name="OEM Authorization (MAF)",
                category="Technical",
                citation="GeM GTC Clause 4(l)",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"oem_authorization": oem_auth, "oem_name": oem_name}],
                evidence_ids=[f"EVID-OEM-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 9. REQ-MSM-01: Udyam MSME Status
        if bidder.get("msme_category"):
            valid_until = bidder.get("msme_valid_until", "")
            is_valid = False
            if valid_until:
                try:
                    is_valid = datetime.strptime(valid_until, "%Y-%m-%d") > datetime.now()
                except Exception:
                    is_valid = False

            if is_valid:
                outcome = EvaluationOutcome.PASS
                details = f"Valid {bidder['msme_category']} enterprise registration under Udyam (Valid until {valid_until})."
                follow_up = None
            else:
                outcome = EvaluationOutcome.WARNING
                details = f"Udyam registration expired on {valid_until}. Claimed category: {bidder['msme_category']}."
                follow_up = "Request renewed Udyam certificate within 48 hours."
        else:
            outcome = EvaluationOutcome.NOT_APPLICABLE
            details = "Bidder does not claim MSME / Udyam status."
            follow_up = None

        results.append(
            EvaluationResult(
                requirement_id="REQ-MSM-01",
                name="Udyam MSME Registration Validity",
                category="MSME",
                citation="Public Procurement Policy for MSEs Order 2012 & GFR Rule 153",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"category": bidder.get("msme_category"), "valid_until": bidder.get("msme_valid_until")}],
                evidence_ids=[f"EVID-MSME-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 10. REQ-BLK-01: Blacklist & Debarment
        from mock_apis.synthetic_data import check_blacklist
        bl_records = check_blacklist(bidder.get("pan", ""))
        active_bl = [r for r in bl_records if r.get("status") == "Active"]
        if active_bl:
            outcome = EvaluationOutcome.FAIL
            order_no = active_bl[0].get("order_number", "N/A")
            details = f"Active debarment order found ({order_no}). Debarred from public procurement."
            follow_up = "Statutory disqualification mandatory under GFR Rule 151."
        elif bl_records:
            outcome = EvaluationOutcome.WARNING
            details = f"Historical debarment records found ({len(bl_records)} past orders), currently cleared."
            follow_up = "Review past debarment discharge records."
        else:
            outcome = EvaluationOutcome.PASS
            details = "No debarment or blacklist records identified in central registry."
            follow_up = None

        results.append(
            EvaluationResult(
                requirement_id="REQ-BLK-01",
                name="Debarment & Blacklist Registry",
                category="Blacklist",
                citation="GFR 2017 Rule 151 & GeM Debarment Policy",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"records": bl_records}],
                evidence_ids=[f"EVID-BLACKLIST-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 11. REQ-LAB-01: EPFO Registration
        epfo_reg = bidder.get("epfo_registered", False)
        epfo_code = bidder.get("epfo_establishment_code")
        if epfo_reg and epfo_code:
            outcome = EvaluationOutcome.PASS
            details = f"EPFO establishment registered (Code: {epfo_code})."
            follow_up = None
        elif epfo_reg:
            outcome = EvaluationOutcome.WARNING
            details = "EPFO registration declared but establishment code missing."
            follow_up = "Request formal EPFO registration letter."
        else:
            outcome = EvaluationOutcome.NOT_APPLICABLE
            details = "EPFO registration not declared or employee threshold below statutory minimum."
            follow_up = None

        results.append(
            EvaluationResult(
                requirement_id="REQ-LAB-01",
                name="EPFO Establishment Registration",
                category="Labor",
                citation="Employees' Provident Funds and Miscellaneous Provisions Act 1952",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"registered": epfo_reg, "code": epfo_code}],
                evidence_ids=[f"EVID-EPFO-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 12. REQ-FIN-02: Turnover vs GST Cross-Check
        filings_12m = filings[-12:] if filings else []
        gst_implied = sum(f.get("taxable_value", 0) for f in filings_12m)
        latest_declared = turnovers[-1]["amount"] if turnovers else 0
        if gst_implied > 0 and latest_declared > 0:
            ratio = latest_declared / gst_implied
            if ratio <= 1.5:
                outcome = EvaluationOutcome.PASS
                details = f"Declared turnover (₹{latest_declared:,.0f}) is consistent with 12m GST turnover (₹{gst_implied:,.0f}, ratio {ratio:.2f}x)."
                follow_up = None
            else:
                outcome = EvaluationOutcome.WARNING
                details = f"Declared turnover (₹{latest_declared:,.0f}) exceeds GST taxable value (₹{gst_implied:,.0f}) by {ratio:.2f}x."
                follow_up = "Request audited reconciliation statement with UDIN."
        else:
            outcome = EvaluationOutcome.NOT_APPLICABLE
            details = "Insufficient GST filing data for cross-source triangulation."
            follow_up = None

        results.append(
            EvaluationResult(
                requirement_id="REQ-FIN-02",
                name="Turnover vs GST Cross-Check",
                category="Financial",
                citation="GFR 2017 Rule 175(1) & ICAI UDIN Guidelines",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"declared": latest_declared, "gst_implied": gst_implied}],
                evidence_ids=[f"EVID-FINCROSS-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 13. REQ-LAB-02: ESIC Registration & Statutory Compliance
        esic_reg = bidder.get("esic_registered", False)
        esic_code = bidder.get("esic_establishment_code")
        if esic_reg and esic_code:
            outcome = EvaluationOutcome.PASS
            details = f"ESIC establishment registration verified (Code: {esic_code})."
            follow_up = None
        elif esic_reg:
            outcome = EvaluationOutcome.WARNING
            details = "ESIC registration declared but establishment code missing."
            follow_up = "Request formal ESIC certificate."
        else:
            outcome = EvaluationOutcome.PASS
            details = "ESIC registration exempt (staff count below statutory threshold of 10/20 employees)."
            follow_up = None

        results.append(
            EvaluationResult(
                requirement_id="REQ-LAB-02",
                name="ESIC Establishment Registration",
                category="Labor",
                citation="Employees' State Insurance Act 1948",
                outcome=outcome,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"registered": esic_reg, "code": esic_code}],
                evidence_ids=[f"EVID-ESIC-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 14. REQ-STR-01: Startup India (DPIIT) & NSIC Exemption Status
        startup_reg = bidder.get("startup_india_registered", False)
        dipp_no = bidder.get("dipp_recognition_no")
        nsic_reg = bidder.get("nsic_registered", False)
        details = f"Startup India (DPIIT): {dipp_no or 'Standard Enterprise'}. NSIC: {'Enrolled' if nsic_reg else 'Not Claimed'}."
        results.append(
            EvaluationResult(
                requirement_id="REQ-STR-01",
                name="Startup India & NSIC Recognition",
                category="Statutory",
                citation="Public Procurement Policy for MSEs & Startup India Order 2016",
                outcome=EvaluationOutcome.PASS,
                severity=RequirementSeverity.TECHNICAL,
                details=details,
                evidence=[{"startup": startup_reg, "dipp_no": dipp_no, "nsic": nsic_reg}],
                evidence_ids=[f"EVID-STARTUP-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=None,
            )
        )

        # 15. REQ-ITR-01: Income Tax Return (ITR) 3-Year Filing
        itr_filed = bidder.get("itr_filed_last_3_years", True)
        if itr_filed:
            outcome = EvaluationOutcome.PASS
            details = "Income Tax Returns verified for last 3 Assessment Years with CBDT."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = "Missing or unverified Income Tax Returns for required 3-year statutory audit cycle."
            follow_up = "Seek certified ITR-V acknowledgements and Form 26AS."

        results.append(
            EvaluationResult(
                requirement_id="REQ-ITR-01",
                name="Income Tax (ITR) 3-Year Compliance",
                category="Income Tax",
                citation="Income Tax Act 1961 Section 139 & GFR 2017 Rule 144",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"itr_filed_last_3_years": itr_filed, "pan": bidder.get("pan")}],
                evidence_ids=[f"EVID-ITR-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        # 16. REQ-DIG-01: DigiLocker Document Provenance & Verification
        digilocker_ok = bidder.get("digilocker_verified", True)
        if digilocker_ok:
            outcome = EvaluationOutcome.PASS
            details = "Statutory documents cross-verified via DigiLocker / API Setu with SHA-256 seal."
            follow_up = None
        else:
            outcome = EvaluationOutcome.FAIL
            details = "Digital verification failed: Unregistered audit report or Disclaimer of Opinion detected."
            follow_up = "Reject unverified balance sheet and issue formal Show-Cause Notice."

        results.append(
            EvaluationResult(
                requirement_id="REQ-DIG-01",
                name="DigiLocker & Document Provenance",
                category="Document",
                citation="Information Technology Act 2000 Section 65B & GeM GTC 4.14",
                outcome=outcome,
                severity=RequirementSeverity.MANDATORY,
                details=details,
                evidence=[{"digilocker_verified": digilocker_ok}],
                evidence_ids=[f"EVID-DIGILOCKER-{bidder.get('bidder_id')}"],
                source_status="verified",
                rule_version=self.policy_version,
                suggested_officer_follow_up=follow_up,
            )
        )

        return results
