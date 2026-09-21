"""
SIH26100 — GSTN Registry Connector
Connects to simulated or sandbox GST Portal (GSTN).
Extracts active registration status, jurisdiction, and 12-month return filing history.
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


class GSTConnector:
    name: str = "GSTN Registry Connector"
    source_type: str = "GSTN"
    status: ConnectorStatus = ConnectorStatus.SYNTHETIC_DEMO
    version: str = "v1.2"

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

        gstin = request.identifier_value.strip().upper()
        # Find bidder by GSTIN
        all_b = get_all_bidders()
        bidder = next((b for b in all_b if b.get("gstin", "").upper() == gstin), None)

        if not bidder:
            self.breaker.record_success()
            return ConnectorResult(
                source_name=self.name,
                source_environment=self.status,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.NOT_FOUND,
                normalized_data={"gstin": gstin, "status": "NOT_FOUND"},
                evidence_references=[],
                failure_classification="IDENTIFIER_NOT_FOUND",
                confidence=1.0,
            )

        self.breaker.record_success()
        normalized = {
            "gstin": gstin,
            "legal_name": bidder.get("entity_name"),
            "trade_name": bidder.get("trade_name"),
            "status": bidder.get("gst_status", "Active"),
            "filing_history": bidder.get("gst_filing_history", []),
            "annual_taxable_value": sum(f.get("taxable_value", 0) for f in bidder.get("gst_filing_history", [])[-12:]),
        }

        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.SUCCESS,
            normalized_data=normalized,
            raw_response={"raw_status": bidder.get("gst_status"), "count": len(bidder.get("gst_filing_history", []))},
            evidence_references=[f"EVID-GSTN-{gstin}"],
            source_freshness="REALTIME",
            confidence=1.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "healthy" if self.breaker.state == "CLOSED" else "degraded",
            "environment": self.status.value,
            "circuit_state": self.breaker.state,
        }
