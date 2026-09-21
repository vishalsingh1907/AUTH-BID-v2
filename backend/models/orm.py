"""
SIH26100 — Production SQLAlchemy 2.0 Domain Entities
Defines the complete PostgreSQL schema for AuthBid:
- Organization, User, Role, Permission
- Tender, TenderRequirement, RequirementVersion
- Bidder, BidSubmission, Document, DocumentVersion, DocumentExtraction
- RegistryConnector, RegistryRequest, RegistryResponseSnapshot
- VerificationRun, BidderAssessment, ComplianceCheckResult, EvidenceItem, AnomalyFinding, RelationshipEdge, RiskAssessment
- ModelRun, Recommendation, OfficerDecision, AuditEvent, AnchorCommitment
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    pass


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════
# 1. CORE TENANCY & ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    tenders: Mapped[List["Tender"]] = relationship("Tender", back_populates="organization")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="officer", nullable=False)  # officer, committee_member, admin
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")


# ═══════════════════════════════════════════════════════════════
# 2. TENDER & REQUIREMENTS ENGINE
# ═══════════════════════════════════════════════════════════════
class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    org_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=True, index=True)
    tender_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(16), default="INR")
    published_date: Mapped[str] = mapped_column(String(64), nullable=False)
    closing_date: Mapped[str] = mapped_column(String(64), nullable=False)
    ministry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_criteria: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(64), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="tenders")
    requirements: Mapped[List["TenderRequirement"]] = relationship("TenderRequirement", back_populates="tender")
    submissions: Mapped[List["BidSubmission"]] = relationship("BidSubmission", back_populates="tender")


class TenderRequirement(Base):
    __tablename__ = "tender_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # GST, PAN, MCA, MSME, Financial, Experience
    applicability_condition: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    required_evidence_type: Mapped[str] = mapped_column(String(128), nullable=False)
    source_priority: Mapped[str] = mapped_column(String(128), default="REGISTRY_FIRST")
    validation_rule: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    severity: Mapped[str] = mapped_column(String(32), default="mandatory")  # mandatory, technical, advisory
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    citation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    tender: Mapped["Tender"] = relationship("Tender", back_populates="requirements")


class RequirementVersion(Base):
    __tablename__ = "requirement_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    requirement_id: Mapped[str] = mapped_column(String(36), ForeignKey("tender_requirements.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    changes_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════
# 3. BIDDER & SUBMISSIONS
# ═══════════════════════════════════════════════════════════════
class Bidder(Base):
    __tablename__ = "bidders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    bidder_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    entity_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trade_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    pan: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    gstin: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cin: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    udyam_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    registered_address: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    bank_account: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    directors: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    annual_turnover: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    certifications: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    submissions: Mapped[List["BidSubmission"]] = relationship("BidSubmission", back_populates="bidder")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="bidder")


class BidSubmission(Base):
    __tablename__ = "bid_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=False, index=True)
    bidder_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidders.id"), nullable=False, index=True)
    bid_amount: Mapped[float] = mapped_column(Float, nullable=False)
    submission_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String(64), default="submitted", index=True)
    make_in_india_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    oem_authorization: Mapped[bool] = mapped_column(Boolean, default=False)
    oem_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    epfo_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    epfo_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    tender: Mapped["Tender"] = relationship("Tender", back_populates="submissions")
    bidder: Mapped["Bidder"] = relationship("Bidder", back_populates="submissions")


# ═══════════════════════════════════════════════════════════════
# 4. DOCUMENT EVIDENCE REGISTER
# ═══════════════════════════════════════════════════════════════
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    bidder_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidders.id"), nullable=False, index=True)
    tender_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=True, index=True)
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False)  # GST_REG06, PAN_CARD, BALANCE_SHEET, UDYAM
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="application/pdf")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded")  # uploaded, verified, flagged, rejected
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    bidder: Mapped["Bidder"] = relationship("Bidder", back_populates="documents")
    versions: Mapped[List["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document")
    extractions: Mapped[List["DocumentExtraction"]] = relationship("DocumentExtraction", back_populates="document")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    document: Mapped["Document"] = relationship("Document", back_populates="versions")


class DocumentExtraction(Base):
    __tablename__ = "document_extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id"), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(128), default="deterministic_ocr")
    model_version: Mapped[str] = mapped_column(String(64), default="v1.0")
    extracted_fields: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence_scores: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    ocr_match_score: Mapped[float] = mapped_column(Float, default=100.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    document: Mapped["Document"] = relationship("Document", back_populates="extractions")


# ═══════════════════════════════════════════════════════════════
# 5. REGISTRY CONNECTORS & SNAPSHOTS
# ═══════════════════════════════════════════════════════════════
class RegistryConnector(Base):
    __tablename__ = "registry_connectors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)  # GSTN, PAN_NSDL, MCA21, UDYAM, CPPP
    status: Mapped[str] = mapped_column(String(32), default="synthetic_demo")  # live, sandbox, synthetic_demo, unavailable
    version: Mapped[str] = mapped_column(String(32), default="v1.0")
    base_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RegistryRequest(Base):
    __tablename__ = "registry_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("registry_connectors.id"), nullable=False, index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RegistryResponseSnapshot(Base):
    __tablename__ = "registry_response_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    request_id: Mapped[str] = mapped_column(String(36), ForeignKey("registry_requests.id"), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(36), ForeignKey("registry_connectors.id"), nullable=False, index=True)
    response_status: Mapped[str] = mapped_column(String(32), default="success")
    response_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    response_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# ═══════════════════════════════════════════════════════════════
# 6. VERIFICATION RUNS & ASSESSMENTS
# ═══════════════════════════════════════════════════════════════
class VerificationRun(Base):
    __tablename__ = "verification_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)  # created, queued, running, completed, failed
    initiating_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_bidders: Mapped[int] = mapped_column(Integer, default=0)
    verified_bidders: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assessments: Mapped[List["BidderAssessment"]] = relationship("BidderAssessment", back_populates="run")


class BidderAssessment(Base):
    __tablename__ = "bidder_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("verification_runs.id"), nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=False, index=True)
    bidder_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidders.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    hard_eligibility: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    system_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    run: Mapped["VerificationRun"] = relationship("VerificationRun", back_populates="assessments")
    checks: Mapped[List["ComplianceCheckResult"]] = relationship("ComplianceCheckResult", back_populates="assessment")
    anomalies: Mapped[List["AnomalyFinding"]] = relationship("AnomalyFinding", back_populates="assessment")
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship("RiskAssessment", back_populates="assessment", uselist=False)


class ComplianceCheckResult(Base):
    __tablename__ = "compliance_check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidder_assessments.id"), nullable=False, index=True)
    requirement_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tender_requirements.id"), nullable=True)
    check_id: Mapped[str] = mapped_column(String(64), nullable=False)
    check_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(32), nullable=False)  # pass, fail, warning, not_applicable, indeterminate
    details: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    rule_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assessment: Mapped["BidderAssessment"] = relationship("BidderAssessment", back_populates="checks")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidder_assessments.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    identifier_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    provenance: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AnomalyFinding(Base):
    __tablename__ = "anomaly_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidder_assessments.id"), nullable=False, index=True)
    anomaly_id: Mapped[str] = mapped_column(String(64), nullable=False)
    anomaly_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    related_bidders: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assessment: Mapped["BidderAssessment"] = relationship("BidderAssessment", back_populates="anomalies")


class RelationshipEdge(Base):
    __tablename__ = "relationship_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=False, index=True)
    source_bidder_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_bidder_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False)  # SHARED_DIRECTOR, SHARED_ADDRESS, SHARED_BANK, SHARED_PHONE
    evidence_item_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidder_assessments.id"), unique=True, nullable=False, index=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)  # low, medium, high, critical
    components: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_score: Mapped[float] = mapped_column(Float, default=0.0)
    scoring_policy_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    assessment: Mapped["BidderAssessment"] = relationship("BidderAssessment", back_populates="risk_assessment")


# ═══════════════════════════════════════════════════════════════
# 7. AI GOVERNANCE & MODEL RUNS
# ═══════════════════════════════════════════════════════════════
class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    tender_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tenders.id"), nullable=True, index=True)
    bidder_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("bidders.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default="google_gemini")
    model_name: Mapped[str] = mapped_column(String(64), default="gemini-2.5-flash")
    model_version: Mapped[str] = mapped_column(String(32), default="2026-03")
    prompt_template_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    validation_result: Mapped[str] = mapped_column(String(32), default="valid")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("bidder_assessments.id"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    observed_facts: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    uncertainties: Mapped[List[str]] = mapped_column(JSON, default=list)
    suggested_follow_up: Mapped[List[str]] = mapped_column(JSON, default=list)
    officer_decision_required: Mapped[bool] = mapped_column(Boolean, default=True)
    disclaimer: Mapped[str] = mapped_column(String(255), default="Model-assisted analysis; officer review required.")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


# ═══════════════════════════════════════════════════════════════
# 8. OFFICER DECISIONS & AUDIT LEDGER
# ═══════════════════════════════════════════════════════════════
class OfficerDecision(Base):
    __tablename__ = "officer_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    decision_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    bidder_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    officer_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    officer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(64), default="officer")
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # eligible, review, disqualified
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    tender_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    bidder_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    current_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    policy_version: Mapped[str] = mapped_column(String(32), default="v1.0")
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)


class AnchorCommitment(Base):
    __tablename__ = "anchor_commitments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    receipt_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    tender_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    merkle_root: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    root_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    total_blocks: Mapped[int] = mapped_column(Integer, default=0)
    external_service: Mapped[str] = mapped_column(String(255), nullable=False)
    proof_type: Mapped[str] = mapped_column(String(128), nullable=False)
    digital_signature: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PUBLISHED_EXTERNAL")
    anchored_by_role: Mapped[str] = mapped_column(String(64), default="officer")
    anchored_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
