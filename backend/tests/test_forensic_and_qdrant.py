"""
SIH26100 — Unit Tests for Deep Forensic Validators & Qdrant Vector DB
Tests:
1. GSTIN format, state code, embedded PAN validation.
2. PAN entity type and structure validation.
3. UDIN 18-digit ICAI specification and unverified detection.
4. DIN 8-digit MCA verification.
5. Qdrant vector search retrieval with HNSW cosine similarity.
"""
import pytest
from documents.forensic_validators import (
    validate_gstin,
    validate_pan,
    validate_udin,
    validate_din,
)
from ai.rag_service import rag_service


def test_gstin_valid():
    res = validate_gstin("06AABCT1234A1Z5", expected_pan="AABCT1234A")
    assert res["valid"] is True
    assert res["state_code"] == "06"
    assert res["state_name"] == "Haryana"
    assert res["embedded_pan"] == "AABCT1234A"


def test_gstin_invalid_state_and_pan_mismatch():
    # Invalid state code 99
    res_bad_state = validate_gstin("99AABCT1234A1Z5")
    assert res_bad_state["valid"] is False
    assert "Invalid GST State Code" in res_bad_state["reason"]

    # PAN mismatch
    res_pan_mismatch = validate_gstin("06AABCT1234A1Z5", expected_pan="OTHERPAN00")
    assert res_pan_mismatch["valid"] is False
    assert "does not match" in res_pan_mismatch["reason"]


def test_pan_valid_and_entity_type():
    # Company PAN (4th char 'C')
    res_corp = validate_pan("AABCT1234A")
    assert res_corp["valid"] is True
    assert res_corp["entity_type"] == "Company / Corporation"

    # Individual PAN (4th char 'P')
    res_indiv = validate_pan("ABCPS1234K")
    assert res_indiv["valid"] is True
    assert res_indiv["entity_type"] == "Individual / Person"


def test_udin_valid_and_shell_flagged():
    # Valid 18-digit UDIN
    res_valid = validate_udin("24089123AB45678901")
    assert res_valid["valid"] is True
    assert res_valid["ca_membership_no"] == "089123"
    assert res_valid["audit_year_prefix"] == "2024"

    # Flagged UDIN for shell entity B007
    res_shell = validate_udin("NOT_GENERATED")
    assert res_shell["valid"] is False
    assert "Missing or un-generated UDIN" in res_shell["reason"]


def test_din_validation():
    assert validate_din("09876543")["valid"] is True
    assert validate_din("123")["valid"] is False
    assert validate_din("ABCDEFGH")["valid"] is False


def test_qdrant_vector_retrieval():
    # Ensure Qdrant vector database returns top chunks
    chunks = rag_service.retrieve("What is the annual turnover in B001 balance sheet?", top_k=3)
    assert len(chunks) > 0
    assert any("DOC-AUDIT-B001" in c["doc_id"] for c in chunks)
    assert all(c["vector_source"] == "qdrant_hnsw" for c in chunks)
