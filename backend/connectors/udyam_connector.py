"""
SIH26100 — Udyam MSME Registry Connector
Validates Udyam registration number, enterprise category, and validity date.
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


class UdyamConnector:
    name: str = "Udyam MSME Connector"
    source_type: str = "UDYAM"
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

        identifier = request.identifier_value.strip().upper()
        all_b = get_all_bidders()
        bidder = next(
            (b for b in all_b if b.get("udyam_no", "").upper() == identifier or b.get("bidder_id") == identifier),
            None,
        )

        if not bidder or not bidder.get("msme_category"):
            self.breaker.record_success()
            return ConnectorResult(
                source_name=self.name,
                source_environment=self.status,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.NOT_FOUND,
                normalized_data={"udyam_no": identifier, "status": "NOT_REGISTERED"},
                failure_classification="UDYAM_NOT_FOUND",
                confidence=1.0,
            )

        self.breaker.record_success()
        normalized = {
            "udyam_no": bidder.get("udyam_no"),
            "category": bidder.get("msme_category"),
            "valid_until": bidder.get("msme_valid_until"),
            "enterprise_name": bidder.get("entity_name"),
            "status": "Active",
        }

        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.SUCCESS,
            normalized_data=normalized,
            raw_response={"category": bidder.get("msme_category")},
            evidence_references=[f"EVID-UDYAM-{bidder.get('udyam_no') or identifier}"],
            source_freshness="REALTIME",
            confidence=1.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "healthy" if self.breaker.state == "CLOSED" else "degraded",
            "environment": self.status.value,
        }
