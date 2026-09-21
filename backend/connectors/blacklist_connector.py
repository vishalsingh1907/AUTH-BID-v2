"""
SIH26100 — CPPP / GeM Debarment Registry Connector
Validates vendor PAN against Central Public Procurement Portal and GeM debarment lists.
"""
from typing import Dict, Any
from connectors.base import (
    ConnectorStatus,
    ResponseStatus,
    VerificationRequest,
    ConnectorResult,
    CircuitBreaker,
)
from mock_apis.synthetic_data import check_blacklist


class BlacklistConnector:
    name: str = "CPPP / GeM Debarment Connector"
    source_type: str = "BLACKLIST"
    status: ConnectorStatus = ConnectorStatus.SYNTHETIC_DEMO
    version: str = "v1.0"

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
        records = check_blacklist(pan)
        self.breaker.record_success()

        active_orders = [r for r in records if r.get("status") == "Active"]
        normalized = {
            "pan": pan,
            "has_records": len(records) > 0,
            "is_actively_debarred": len(active_orders) > 0,
            "total_records": len(records),
            "records": records,
        }

        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.SUCCESS,
            normalized_data=normalized,
            raw_response={"match_count": len(records)},
            evidence_references=[f"EVID-DEBARMENT-{pan}"],
            source_freshness="REALTIME",
            confidence=1.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "healthy" if self.breaker.state == "CLOSED" else "degraded",
            "environment": self.status.value,
        }
