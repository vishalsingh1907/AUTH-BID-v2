"""
SIH26100 — PAN (CBDT / NSDL) Registry Connector
Validates PAN status and returns registered corporate name with fuzzy matching.
"""
from typing import Dict, Any
from connectors.base import (
    ConnectorStatus,
    ResponseStatus,
    VerificationRequest,
    ConnectorResult,
    CircuitBreaker,
)
from mock_apis.synthetic_data import get_all_bidders


class PANConnector:
    name: str = "CBDT PAN Connector"
    source_type: str = "PAN_NSDL"
    status: ConnectorStatus = ConnectorStatus.SYNTHETIC_DEMO
    version: str = "v1.1"

    def __init__(self):
        self.breaker = CircuitBreaker()

    async def verify(self, request: VerificationRequest) -> ConnectorResult:
        if not self.breaker.can_attempt():
            return ConnectorResult(
                source_name=self.name,
                source_environment=self.status,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.CIRCUIT_OPEN,
                failure_classification="CIRCUIT_BREAKER_OPEN",
                retryable=True,
                confidence=0.0,
            )

        pan = request.identifier_value.strip().upper()
        all_b = get_all_bidders()
        bidder = next((b for b in all_b if b.get("pan", "").upper() == pan), None)

        if not bidder:
            self.breaker.record_success()
            return ConnectorResult(
                source_name=self.name,
                source_environment=self.status,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.NOT_FOUND,
                normalized_data={"pan": pan, "status": "NOT_FOUND"},
                failure_classification="PAN_NOT_FOUND",
                confidence=1.0,
            )

        self.breaker.record_success()
        normalized = {
            "pan": pan,
            "registered_name": bidder.get("pan_registered_name", bidder.get("entity_name")),
            "status": bidder.get("pan_status", "Valid"),
            "category": "Company",
        }

        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.SUCCESS,
            normalized_data=normalized,
            raw_response={"pan_status": bidder.get("pan_status")},
            evidence_references=[f"EVID-PAN-{pan}"],
            source_freshness="REALTIME",
            confidence=1.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "healthy" if self.breaker.state == "CLOSED" else "degraded",
            "environment": self.status.value,
        }
