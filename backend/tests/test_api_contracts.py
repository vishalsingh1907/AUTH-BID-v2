"""
SIH26100 — API Contract & Reset Endpoint Tests
Verifies that key verification, graph, decisions, report, and reset endpoints return expected envelopes.
"""
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_reset_demo_data_endpoint():
    """Verify POST /api/verification/reset clears and re-seeds sample tender."""
    res = client.post("/api/verification/reset")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["status"] == "reset_complete"
    assert data["data"]["tender_id"] == "GEM/2026/B/4521897"

def test_tenders_contract():
    """Verify GET /api/tenders returns list of tenders with metadata."""
    res = client.get("/api/tenders")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    tender = data["data"][0]
    assert "tender_id" in tender
    assert "bidder_count" in tender
    assert "verification_status" in tender

def test_bidders_contract():
    """Verify GET /api/bidders returns all 12 bidders."""
    res = client.get("/api/bidders")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["data"]) == 12

def test_collusion_graph_contract():
    """Verify GET /api/graph/collusion/{tender_id} returns nodes, edges, clusters."""
    res = client.get("/api/graph/collusion/GEM/2026/B/4521897")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "nodes" in data["data"]
    assert "edges" in data["data"]
    assert "clusters" in data["data"]
    assert len(data["data"]["clusters"]) >= 1

def test_capabilities_contract():
    """Verify GET /api/capabilities returns demo_mode and capability matrix."""
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "demo_mode" in data["data"]
    assert data["data"]["demo_mode"] is True
    assert "connectors" in data["data"]
    assert "gst_connector" in data["data"]["connectors"]
    assert data["data"]["connectors"]["gst_connector"]["status"] == "synthetic_demo"
    assert data["data"]["connectors"]["epfo_connector"]["status"] == "unavailable"

