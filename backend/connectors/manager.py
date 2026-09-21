"""
SIH26100 — Registry Connector Manager
Orchestrates registry verification requests across GSTN, PAN, MCA21, Udyam, Blacklist, and unavailable sources.
"""
from typing import Dict, Any, List
from connectors.base import (
    RegistryConnector,
    VerificationRequest,
    ConnectorResult,
    ConnectorStatus,
    ResponseStatus,
)
from connectors.gst_connector import GSTConnector
from connectors.pan_connector import PANConnector
from connectors.mca_connector import MCAConnector
from connectors.udyam_connector import UdyamConnector
from connectors.blacklist_connector import BlacklistConnector
from connectors.unavailable_connectors import (
    EPFOConnector,
    ESICConnector,
    StartupIndiaConnector,
    NSICConnector,
    DigiLockerConnector,
)


class ConnectorManager:
    """Central registry connector manager."""

    def __init__(self):
        self._connectors: Dict[str, Any] = {
            "GSTN": GSTConnector(),
            "PAN": PANConnector(),
            "MCA": MCAConnector(),
            "UDYAM": UdyamConnector(),
            "BLACKLIST": BlacklistConnector(),
            "EPFO": EPFOConnector(),
            "ESIC": ESICConnector(),
            "STARTUP_INDIA": StartupIndiaConnector(),
            "NSIC": NSICConnector(),
            "DIGILOCKER": DigiLockerConnector(),
        }

    def get_connector(self, source_type: str) -> Any:
        return self._connectors.get(source_type.upper())

    async def verify(self, request: VerificationRequest) -> ConnectorResult:
        connector = self.get_connector(request.source_type)
        if not connector:
            return ConnectorResult(
                source_name=f"Unknown ({request.source_type})",
                source_environment=ConnectorStatus.UNAVAILABLE,
                request_id=request.request_id,
                correlation_id=request.correlation_id,
                response_status=ResponseStatus.UNAVAILABLE,
                failure_classification="CONNECTOR_NOT_FOUND",
                confidence=0.0,
            )

        return await connector.verify(request)

    async def health_check_all(self) -> Dict[str, Any]:
        results = {}
        for source, conn in self._connectors.items():
            results[source] = await conn.health_check()
        return results

    def get_capability_matrix(self) -> Dict[str, Dict[str, str]]:
        matrix = {}
        for source, conn in self._connectors.items():
            matrix[source.lower()] = {
                "name": conn.name,
                "source_type": conn.source_type,
                "status": conn.status.value,
                "version": conn.version,
            }
        return matrix


# Singleton instance
connector_manager = ConnectorManager()
