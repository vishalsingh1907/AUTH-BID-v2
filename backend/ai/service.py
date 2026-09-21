"""
SIH26100 — Evidence Review Service
Coordinates prompt sanitization, provider execution, fallback resolution, and model run logging.
"""
from typing import List, Dict, Any, Optional
from ai.governance import ModelReviewResponse, PromptSanitizer
from ai.gemini_provider import GeminiAnalysisProvider
from ai.rule_fallback_provider import RuleFallbackProvider
from models.database import append_audit_entry


class EvidenceReviewService:
    def __init__(self):
        self.gemini_provider = GeminiAnalysisProvider()
        self.fallback_provider = RuleFallbackProvider()

    async def review(
        self,
        tender_id: str,
        bidder_id: Optional[str],
        query: str,
        untrusted_bidder_text: str = "",
        evidence_items: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelReviewResponse:
        evidence_items = evidence_items or []
        # 1. Sanitize query and untrusted input
        clean_query = PromptSanitizer.sanitize_text(query)
        clean_context = PromptSanitizer.sanitize_text(untrusted_bidder_text)
        clean_context = PromptSanitizer.redact_pii(clean_context)

        # 2. Attempt model execution via Gemini
        response: Optional[ModelReviewResponse] = None
        try:
            response = await self.gemini_provider.review_evidence(
                tender_id=tender_id,
                bidder_id=bidder_id or "",
                query=clean_query,
                sanitized_context=clean_context,
                evidence_items=evidence_items,
            )
        except Exception:
            response = None

        # 3. Fallback to deterministic rule provider if Gemini unavailable
        if not response:
            response = await self.fallback_provider.review_evidence(
                tender_id=tender_id,
                bidder_id=bidder_id or "",
                query=clean_query,
                sanitized_context=clean_context,
                evidence_items=evidence_items,
            )

        # 4. Record audit entry for review request
        append_audit_entry(
            agent_id=f"ai_reviewer:{response.provider}",
            action="EVIDENCE_REVIEW_QUERY",
            input_data={"query": clean_query, "bidder_id": bidder_id, "input_hash": response.input_hash},
            output_data={"summary": response.summary[:150], "output_hash": response.output_hash, "latency_ms": response.latency_ms},
        )

        return response


# Singleton instance
evidence_review_service = EvidenceReviewService()
