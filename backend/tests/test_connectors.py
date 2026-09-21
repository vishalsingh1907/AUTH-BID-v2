"""
SIH26100 — Connector Framework Contract Tests
Verifies that all registry connectors adhere to the ConnectorResult protocol and handle outages/unavailable states truthfully.
"""
import pytest
from connectors.base import (
    VerificationRequest,
    ConnectorStatus,
    ResponseStatus,
    CircuitBreaker,
)
from connectors.manager import connector_manager


@pytest.mark.asyncio
async def test_gst_connector_success():
    req = VerificationRequest(
        request_id="REQ-TEST-GST-01",
        source_type="GSTN",
        identifier_type="GSTIN",
        identifier_value="06AABCT1234A1Z5",  # B001 GSTIN
        correlation_id="CORR-001",
    )
    res = await connector_manager.verify(req)
    assert res.response_status == ResponseStatus.SUCCESS
    assert res.source_environment == ConnectorStatus.SYNTHETIC_DEMO
    assert res.normalized_data["status"] == "Active"
    assert res.response_hash != ""


@pytest.mark.asyncio
async def test_pan_connector_success():
    req = VerificationRequest(
        request_id="REQ-TEST-PAN-01",
        source_type="PAN",
        identifier_type="PAN",
        identifier_value="AABCT1234A",  # B001 PAN
        correlation_id="CORR-002",
    )
    res = await connector_manager.verify(req)
    assert res.response_status == ResponseStatus.SUCCESS
    assert res.normalized_data["status"] == "Valid"


@pytest.mark.asyncio
async def test_unavailable_connector_truthful_state():
    req = VerificationRequest(
        request_id="REQ-TEST-EPFO-01",
        source_type="EPFO",
        identifier_type="EPFO_CODE",
        identifier_value="EPFO12345",
        correlation_id="CORR-003",
    )
    res = await connector_manager.verify(req)
    assert res.response_status == ResponseStatus.UNAVAILABLE
    assert res.source_environment == ConnectorStatus.UNAVAILABLE
    assert res.failure_classification == "CONNECTOR_NOT_PROVISIONED"
    assert res.confidence == 0.0


def test_circuit_breaker_behavior():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=10)
    assert cb.can_attempt() is True
    cb.record_failure()
    assert cb.can_attempt() is True
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.can_attempt() is False
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.can_attempt() is True
