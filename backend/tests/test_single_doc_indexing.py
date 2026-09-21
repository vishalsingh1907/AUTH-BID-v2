"""
Test for single document indexing in Qdrant Vector DB.
Verifies that dynamically ingested documents are immediately indexed and retrievable.
"""

import os
import pytest
from ai.rag_service import rag_service

def test_index_single_document_and_retrieve():
    """Verify that a newly provided PDF can be indexed into Qdrant and queried."""
    sample_pdf = os.path.abspath("data/documents/DOC-GST-B001.pdf")
    if not os.path.exists(sample_pdf):
        pytest.skip("Sample PDF data/documents/DOC-GST-B001.pdf not found.")

    # Index sample document as dynamic upload
    chunks = rag_service.index_single_document(
        file_path=sample_pdf,
        doc_id="DOC-DYNAMIC-TEST-001",
        bidder_id="B001",
        doc_type="GST_REG06",
    )
    assert len(chunks) > 0
    assert chunks[0].doc_id == "DOC-DYNAMIC-TEST-001"
    assert chunks[0].bidder_id == "B001"

    # Verify retrieval
    results = rag_service.retrieve("GSTIN TechVision Solutions", bidder_id="B001", top_k=2)
    assert len(results) > 0
    doc_ids = [r["doc_id"] for r in results]
    assert any("B001" in str(r.get("bidder_id", "")) for r in results)
