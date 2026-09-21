"""
SIH26100 — Policy Engine Data Models
Defines PolicyRequirement, EvaluationResult, and PolicyDefinition.
Supports deterministic statutory and tender-specific requirement evaluation.
"""
from typing import Optional, List, Dict, Any, Callable
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


class RequirementSeverity(str, Enum):
    MANDATORY = "mandatory"      # Binary failure results in disqualification recommendation
    TECHNICAL = "technical"      # Technical requirement; clarification may be permitted
    ADVISORY = "advisory"        # Informational or risk factor


class EvaluationOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"  # Source unavailable, missing data, or connector outage


class PolicyRequirement(BaseModel):
    requirement_id: str
    name: str
    category: str  # GST, PAN, MCA, MSME, Financial, Experience, Blacklist, Labor, Technical
    citation: str  # E.g. "GFR 2017 Rule 151", "Competition Act 2002 Sec 3(3)"
    severity: RequirementSeverity = RequirementSeverity.MANDATORY
    policy_version: str = "v1.0"
    source_priority: str = "REGISTRY_FIRST"  # REGISTRY_FIRST, DOCUMENT_ONLY, CROSS_SOURCE
    clarification_permitted: bool = True
    applicability_condition: Optional[str] = None  # None means always applicable
    required_evidence_type: str = "STATUTORY_REGISTRY"
    description: str = ""


class EvaluationResult(BaseModel):
    requirement_id: str
    name: str
    category: str
    citation: str
    outcome: EvaluationOutcome
    severity: RequirementSeverity
    details: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    source_status: str = "verified"  # verified, unavailable, stale, unverified
    rule_version: str = "v1.0"
    evaluated_at: datetime = Field(default_factory=datetime.now)
    confidence: float = 1.0
    suggested_officer_follow_up: Optional[str] = None
