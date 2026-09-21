"""
SIH26100 — Base Registry Connector Protocol & Models
Provides standardized connector contracts, timeouts, retry backoff, circuit breaking, and hash auditing.
"""
from typing import Optional, Dict, Any, List, Protocol
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import hashlib
import json
import asyncio


class ConnectorStatus(str, Enum):
    LIVE = "live"
    SANDBOX = "sandbox"
    SYNTHETIC_DEMO = "synthetic_demo"
    UNAVAILABLE = "unavailable"


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"
    ERROR = "error"


class VerificationRequest(BaseModel):
    request_id: str
    source_type: str  # GSTN, PAN, MCA, UDYAM, BLACKLIST, EPFO, ESIC, DIGILOCKER
    identifier_type: str  # GSTIN, PAN, CIN, DIN, UDYAM_NO, EPFO_CODE
    identifier_value: str
    correlation_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConnectorResult(BaseModel):
    source_name: str
    source_environment: ConnectorStatus
    request_id: str
    correlation_id: str
    retrieval_timestamp: datetime = Field(default_factory=datetime.now)
    response_status: ResponseStatus
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Dict[str, Any] = Field(default_factory=dict)
    evidence_references: List[str] = Field(default_factory=list)
    source_freshness: str = "REALTIME"  # REALTIME, CACHED, STALE, UNKNOWN
    failure_classification: Optional[str] = None
    retryable: bool = False
    confidence: float = 1.0
    response_hash: str = ""

    def model_post_init(self, __context: Any) -> None:
        if not self.response_hash:
            content = json.dumps(self.normalized_data, sort_keys=True, default=str)
            self.response_hash = hashlib.sha256(content.encode()).hexdigest()


class RegistryConnector(Protocol):
    name: str
    source_type: str
    status: ConnectorStatus
    version: str

    async def verify(self, request: VerificationRequest) -> ConnectorResult:
        ...

    async def health_check(self) -> Dict[str, Any]:
        ...


class CircuitBreaker:
    """Simple in-memory circuit breaker to prevent hammering unavailable external sources."""

    def __init__(self, failure_threshold: int = 3, recovery_timeout_seconds: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now().timestamp()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def can_attempt(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if self.last_failure_time and (datetime.now().timestamp() - self.last_failure_time) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN allows a trial attempt
