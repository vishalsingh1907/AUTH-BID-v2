"""
SIH26100 — AI Governance & Model-Assisted Analysis Schemas
Enforces strict boundaries:
- Models NEVER make statutory pass/fail determinations
- Models assist by summarizing evidence, explaining relationships, and suggesting follow-up
- All responses adhere to structured JSON contracts with source evidence citations
"""
from typing import List, Dict, Any, Protocol
from pydantic import BaseModel, Field
import re


class ObservedFact(BaseModel):
    statement: str
    evidence_ids: List[str] = Field(default_factory=list)
    source: str


class ModelReviewResponse(BaseModel):
    summary: str
    observed_facts: List[ObservedFact] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    suggested_follow_up: List[str] = Field(default_factory=list)
    officer_decision_required: bool = True
    disclaimer: str = "Model-assisted analysis; officer review required."
    provider: str = "deterministic_fallback"
    model_name: str = "rule_based"
    prompt_template_version: str = "v1.0"
    input_hash: str = ""
    output_hash: str = ""
    latency_ms: int = 0
    validation_status: str = "valid"


class PromptSanitizer:
    """Sanitizes untrusted bidder text and redacts sensitive PII before prompt injection."""

    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?previous\s+instructions",
        r"(?i)system\s+prompt",
        r"(?i)system:",
        r"(?i)developer:",
        r"(?i)\[INST\]",
        r"(?i)<\|im_start\|>",
        r"(?i)disregard\s+above",
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        if not text:
            return ""
        cleaned = text
        for pat in cls.INJECTION_PATTERNS:
            cleaned = re.sub(pat, "[SUSPICIOUS_DIRECTIVE_REMOVED]", cleaned)
        # Neutralize markdown code fences
        cleaned = cleaned.replace("```", "'''")
        return cleaned.strip()[:1500]

    @classmethod
    def redact_pii(cls, text: str) -> str:
        if not text:
            return ""
        # Redact 10-digit mobile numbers
        redacted = re.sub(r"\b[6-9]\d{9}\b", "[REDACTED_PHONE]", text)
        # Redact bank account numbers (9 to 18 digits)
        redacted = re.sub(r"\b\d{11,18}\b", "[REDACTED_ACCOUNT]", redacted)
        return redacted


class AnalysisProvider(Protocol):
    name: str
    version: str

    async def review_evidence(
        self,
        tender_id: str,
        bidder_id: str,
        query: str,
        sanitized_context: str,
        evidence_items: List[Dict[str, Any]],
    ) -> ModelReviewResponse:
        ...
