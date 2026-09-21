"""
SIH26100 — Policy Evaluation Engine Tests
Verifies deterministic policy evaluation against statutory clauses, GFR 151, and zero silent passes.
"""
import pytest
from policy.engine import PolicyEvaluationEngine
from policy.models import EvaluationOutcome, RequirementSeverity
from mock_apis.synthetic_data import get_all_bidders, get_tender


def test_policy_engine_evaluation():
    engine = PolicyEvaluationEngine()
    bidders = get_all_bidders()
    tender = get_tender()

    assert len(bidders) == 12
    # Test first bidder (B001)
    results = engine.evaluate_bidder(bidders[0], tender)
    assert len(results) >= 11

    # Check that required fields exist on all evaluation results
    for r in results:
        assert r.requirement_id.startswith("REQ-")
        assert r.name
        assert r.citation
        assert r.outcome in [
            EvaluationOutcome.PASS,
            EvaluationOutcome.FAIL,
            EvaluationOutcome.WARNING,
            EvaluationOutcome.NOT_APPLICABLE,
            EvaluationOutcome.INDETERMINATE,
        ]
        assert r.details
        assert r.source_status
        assert r.rule_version == "v1.0"
        assert len(r.evidence_ids) >= 1


def test_policy_engine_clean_bidder():
    engine = PolicyEvaluationEngine()
    bidders = get_all_bidders()
    tender = get_tender()

    # B002 is Reliable Computing Systems (Clean compliant bidder)
    b002 = next(b for b in bidders if b["bidder_id"] == "B002")
    results = engine.evaluate_bidder(b002, tender)

    # Mandatory checks should pass
    mandatory_results = [r for r in results if r.severity == RequirementSeverity.MANDATORY]
    assert all(r.outcome == EvaluationOutcome.PASS for r in mandatory_results)


def test_policy_engine_expired_msme():
    engine = PolicyEvaluationEngine()
    bidders = get_all_bidders()
    tender = get_tender()

    # B004 has expired MSME
    b004 = next(b for b in bidders if b["bidder_id"] == "B004")
    results = engine.evaluate_bidder(b004, tender)

    msme_result = next(r for r in results if r.requirement_id == "REQ-MSM-01")
    assert msme_result.outcome == EvaluationOutcome.WARNING
    assert "expired" in msme_result.details.lower()
    assert msme_result.suggested_officer_follow_up is not None
