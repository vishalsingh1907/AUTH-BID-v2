"""
SIH26100 — Deterministic Rule-Based Analysis Provider
Provides structured, evidence-grounded review responses when language models are unavailable or unconfigured.
Explicitly labeled as 'Rule-based fallback'.
"""
from typing import List, Dict, Any
from datetime import datetime
import hashlib
import json
from ai.governance import ModelReviewResponse, ObservedFact


class RuleFallbackProvider:
    name: str = "Deterministic Rule Engine"
    version: str = "v1.0"

    async def review_evidence(
        self,
        tender_id: str,
        bidder_id: str,
        query: str,
        sanitized_context: str,
        evidence_items: List[Dict[str, Any]],
    ) -> ModelReviewResponse:
        start_time = datetime.now()
        input_content = f"{tender_id}|{bidder_id}|{query}|{sanitized_context}"
        input_hash = hashlib.sha256(input_content.encode()).hexdigest()

        observed_facts: List[ObservedFact] = []
        uncertainties: List[str] = []
        follow_ups: List[str] = []

        # Ground findings in evidence_items passed from policy/connectors
        for item in evidence_items:
            req_id = item.get("requirement_id", "REQ-UNKNOWN")
            outcome = item.get("outcome", "unknown")
            details = item.get("details", "")
            citation = item.get("citation", "Statutory Rules")
            evid_ids = item.get("evidence_ids", [])

            observed_facts.append(
                ObservedFact(
                    statement=f"[{outcome.upper()}] {item.get('name', req_id)}: {details}",
                    evidence_ids=evid_ids or [f"EVID-{req_id}"],
                    source=f"{citation}",
                )
            )

            if outcome in ["fail", "warning"]:
                follow_ups.append(f"Review {item.get('name', req_id)} ({citation}) before final decision.")
            elif outcome == "indeterminate":
                uncertainties.append(f"Data for {item.get('name', req_id)} was incomplete or source was unavailable.")

        if not observed_facts:
            observed_facts.append(
                ObservedFact(
                    statement="General compliance query evaluated against statutory rules.",
                    evidence_ids=[f"EVID-TENDER-{tender_id}"],
                    source="Tender Policy Definition v1.0",
                )
            )

        summary = (
            f"Rule-based assessment for bidder {bidder_id or 'all bidders'} in tender {tender_id}. "
            f"Evaluated {len(observed_facts)} statutory and technical evidence items. "
            f"{len(follow_ups)} item(s) require officer attention."
        )

        response_dict = {
            "summary": summary,
            "observed_facts": [f.model_dump() for f in observed_facts],
            "uncertainties": uncertainties or ["None identified based on available records."],
            "suggested_follow_up": follow_ups or ["Proceed to officer evaluation."],
        }
        output_hash = hashlib.sha256(json.dumps(response_dict, sort_keys=True).encode()).hexdigest()
        latency_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return ModelReviewResponse(
            summary=summary,
            observed_facts=observed_facts,
            uncertainties=uncertainties or ["None identified based on available records."],
            suggested_follow_up=follow_ups or ["Proceed to officer evaluation."],
            officer_decision_required=True,
            disclaimer="Rule-based fallback; officer review required.",
            provider="deterministic_fallback",
            model_name="rule_based_policy_v1",
            prompt_template_version="v1.0",
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=latency_ms,
            validation_status="valid",
        )
