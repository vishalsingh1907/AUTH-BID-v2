"""
SIH26100 — MCA21 Corporate Registry Connector
Validates CIN, incorporation date, and active Director Identification Numbers (DINs).
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


class MCAConnector:
    name: str = "MCA21 Corporate Registry Connector"
    source_type: str = "MCA21"
    status: ConnectorStatus = ConnectorStatus.SYNTHETIC_DEMO
    version: str = "v1.3"

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

        identifier = request.identifier_value.strip()
        all_b = get_all_bidders()
        # Find bidder by CIN or PAN or bidder_id
        bidder = next(
            (b for b in all_b if b.get("cin") == identifier or b.get("pan") == identifier or b.get("bidder_id") == identifier),
            None,
        )

        if not bidder:
            self.breaker.record_success()
            return ConnectorResult(
                source_name=self.name,
                source_environment=self.status,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.NOT_FOUND,
                normalized_data={"cin": identifier, "status": "NOT_FOUND"},
                failure_classification="CORPORATE_RECORD_NOT_FOUND",
                confidence=1.0,
            )

        self.breaker.record_success()
        normalized = {
            "cin": bidder.get("cin"),
            "company_name": bidder.get("entity_name"),
            "incorporation_date": bidder.get("incorporation_date"),
            "company_status": "Active",
            "directors": bidder.get("directors", []),
            "registered_address": bidder.get("registered_address", {}),
        }

        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.SUCCESS,
            normalized_data=normalized,
            raw_response={"directors_count": len(bidder.get("directors", []))},
            evidence_references=[f"EVID-MCA-{bidder.get('cin') or identifier}"],
            source_freshness="REALTIME",
            confidence=1.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "healthy" if self.breaker.state == "CLOSED" else "degraded",
            "environment": self.status.value,
        }
