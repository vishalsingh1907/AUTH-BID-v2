"""
Unit tests confirming all documentation and implementation inconsistency fixes:
1. Canonical bidder names and estimated tender value
2. Graph explainability: bank, phone, and email overlap detection and node/edge rendering
3. Copilot query structure and canonical canned fallback
4. Show-cause notice canonical citation
"""
import pytest
from mock_apis.synthetic_data import get_tender, get_all_bidders, get_bidder_by_id
from routers.graph import _build_cross_bidder_graph, _build_bidder_graph
from routers.verification import copilot_query, generate_show_cause_notice
from models.auth import UserRole


def test_canonical_tender_and_bidders():
    """Verify tender estimated value is ₹2.50 Cr and canonical entity names are intact."""
    tender = get_tender("GEM/2026/B/4521897")
    assert tender is not None
    assert tender["estimated_value"] == 25000000

    bidders = get_all_bidders()
    assert len(bidders) == 12

    expected_names = {
        "B001": "TechVision Solutions Pvt. Ltd.",
        "B002": "Reliable Computing Systems Ltd.",
        "B003": "DigiCore Infosystems Pvt. Ltd.",
        "B004": "GreenTech Peripherals",
        "B005": "NexGen IT Solutions Pvt. Ltd.",
        "B006": "Bharat Electronics & Computing",
        "B007": "Quantum Digital Services Pvt. Ltd.",
        "B008": "MegaByte Computers Pvt. Ltd.",
        "B009": "CloudFirst Technologies Pvt. Ltd.",
        "B010": "Pinnacle Systems India Pvt. Ltd.",
        "B011": "ByteWave Electronics Pvt. Ltd.",
        "B012": "Atlas Infosys Solutions Pvt. Ltd.",
    }

    for bid_id, name in expected_names.items():
        bidder = get_bidder_by_id(bid_id)
        assert bidder is not None
        assert bidder["entity_name"] == name


def test_graph_phone_and_email_nodes():
    """Verify graph builder generates phone and email nodes and edges."""
    bidders = get_all_bidders()
    graph = _build_cross_bidder_graph(bidders)

    node_types = {n["type"] for n in graph["nodes"]}
    assert "bidder" in node_types
    assert "director" in node_types
    assert "address" in node_types
    assert "bank" in node_types
    assert "phone" in node_types
    assert "email" in node_types

    edge_rels = {e["relationship"] for e in graph["edges"]}
    assert "HAS_DIRECTOR" in edge_rels
    assert "REGISTERED_AT" in edge_rels
    assert "BANKS_WITH" in edge_rels
    assert "USES_PHONE" in edge_rels
    assert "USES_EMAIL" in edge_rels


def test_graph_cluster_indicators_ring2_and_ring1():
    """Verify Ring 2 (bank/phone based) and Ring 1 have detailed shared indicators."""
    bidders = get_all_bidders()
    graph = _build_cross_bidder_graph(bidders)

    assert len(graph["clusters"]) == 2

    # Ring 2 check: members B005 and B009
    ring2 = next((c for c in graph["clusters"] if "B005" in c["members"] and "B009" in c["members"]), None)
    assert ring2 is not None
    assert len(ring2["shared_indicators"]) >= 2
    indicators_text = " ".join(ring2["shared_indicators"])
    assert "PUNB0123400" in indicators_text
    assert "9098765432" in indicators_text

    # Ring 1 check: members B001, B003, B007
    ring1 = next((c for c in graph["clusters"] if "B001" in c["members"] and "B007" in c["members"]), None)
    assert ring1 is not None
    assert len(ring1["shared_indicators"]) >= 4
    ring1_text = " ".join(ring1["shared_indicators"])
    assert "09876543" in ring1_text
    assert "08765432" in ring1_text
    assert "Shared registered address" in ring1_text


def test_single_bidder_graph_has_phone_and_email():
    """Verify single bidder graph includes phone and email nodes."""
    b1 = get_bidder_by_id("B001")
    g = _build_bidder_graph(b1)
    types = {n["type"] for n in g["nodes"]}
    assert "phone" in types
    assert "email" in types


@pytest.mark.asyncio
async def test_copilot_query_structure_and_canonical_data():
    """Verify copilot query returns compliant schema with canonical entities."""
    # Test Ring 1 query
    res = await copilot_query({"query": "Explain Collusion Ring 1 and evidence against B001, B003, B007"})
    assert res["success"] is True
    data = res["data"]
    assert "title" in data
    assert "summary" in data
    assert "evidence" in data
    assert isinstance(data["evidence"], list)
    assert "legal_statute" in data
    assert "recommendation" in data
    assert "disclaimer" in data

    # Test Ring 2 query
    res2 = await copilot_query({"query": "Explain Ring 2 and nexus between B005 and B009"})
    assert res2["success"] is True
    data2 = res2["data"]
    assert "title" in data2
    assert "summary" in data2

    # Test L1 query
    res_l1 = await copilot_query({"query": "Who is the lowest compliant bidder L1?"})
    assert res_l1["success"] is True
    assert "L1" in res_l1["data"]["title"] or "Commercial" in res_l1["data"]["title"]


@pytest.mark.asyncio
async def test_show_cause_canonical_citations():
    """Verify show cause notices cite canonical DINs and bank IFSC."""
    res_b001 = await generate_show_cause_notice("B001", current_role=UserRole.OFFICER)
    assert res_b001["success"] is True
    charges_b001 = " ".join(res_b001["data"]["charges"])
    assert "09876543" in charges_b001
    assert "08765432" in charges_b001

    res_b005 = await generate_show_cause_notice("B005", current_role=UserRole.OFFICER)
    assert res_b005["success"] is True
    charges_b005 = " ".join(res_b005["data"]["charges"])
    assert "PUNB0123400" in charges_b005
