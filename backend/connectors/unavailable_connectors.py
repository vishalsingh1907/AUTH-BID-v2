"""
SIH26100 — Explicitly Unavailable Registry Connectors
Provides honest UNAVAILABLE status for planned future integrations (EPFO, ESIC, Startup India, NSIC, DigiLocker).
Ensures zero silent passes and zero false claims of live government integration.
"""
from typing import Dict, Any
from connectors.base import (
    ConnectorStatus,
    ResponseStatus,
    VerificationRequest,
    ConnectorResult,
)


class UnavailableConnector:
    """Standardized stub for connectors that are not yet provisioned in the current environment."""

    def __init__(self, name: str, source_type: str, authority: str):
        self.name = name
        self.source_type = source_type
        self.authority = authority
        self.status = ConnectorStatus.UNAVAILABLE
        self.version = "v0.0-stub"

    async def verify(self, request: VerificationRequest) -> ConnectorResult:
        return ConnectorResult(
            source_name=self.name,
            source_environment=self.status,
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            response_status=ResponseStatus.UNAVAILABLE,
            normalized_data={},
            raw_response={"authority": self.authority, "status": "CONNECTOR_UNAVAILABLE"},
            failure_classification="CONNECTOR_NOT_PROVISIONED",
            retryable=False,
            confidence=0.0,
        )

    async def health_check(self) -> Dict[str, Any]:
        return {
            "connector": self.name,
            "status": "unavailable",
            "environment": self.status.value,
            "authority": self.authority,
        }


# Planned connectors
EPFOConnector = lambda: UnavailableConnector("EPFO Connector", "EPFO", "Employees' Provident Fund Organisation")
ESICConnector = lambda: UnavailableConnector("ESIC Connector", "ESIC", "Employees' State Insurance Corporation")
StartupIndiaConnector = lambda: UnavailableConnector("Startup India Connector", "STARTUP_INDIA", "DPIIT")
NSICConnector = lambda: UnavailableConnector("NSIC Connector", "NSIC", "National Small Industries Corporation")
DigiLockerConnector = lambda: UnavailableConnector("DigiLocker Verification Connector", "DIGILOCKER", "NeGD / MeitY")
