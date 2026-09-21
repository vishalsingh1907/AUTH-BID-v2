"""
Unit tests for Secure Document Evidence Pipeline (Phase 4).
"""
import pytest
from documents.service import (
    DocumentPipelineService,
    DocumentValidationError,
    DocumentSecurityError,
    EICAR_SIGNATURE,
)


@pytest.fixture
def doc_service(tmp_path):
    return DocumentPipelineService(storage_dir=str(tmp_path / "documents"))


def test_valid_pdf_ingestion(doc_service):
    # Valid PDF content starting with %PDF-
    valid_pdf = b"%PDF-1.5 \x00\x01\x02 test pdf content"
    res = doc_service.ingest_document(
        file_name="gst_certificate.pdf",
        content=valid_pdf,
        content_type="application/pdf",
        bidder_id="B001",
        doc_type="GST_REG06",
    )
    assert res["status"] == "uploaded"
    assert res["file_name"] == "gst_certificate.pdf"
    assert len(res["sha256_hash"]) == 64
    assert res["file_size_bytes"] == len(valid_pdf)


def test_invalid_extension_rejected(doc_service):
    with pytest.raises(DocumentValidationError, match="not permitted"):
        doc_service.ingest_document(
            file_name="script.exe",
            content=b"%PDF-1.5 test",
            content_type="application/pdf",
            bidder_id="B001",
            doc_type="GST_REG06",
        )


def test_magic_bytes_mismatch_rejected(doc_service):
    # Claimed PDF but starts with arbitrary text
    invalid_content = b"NOT_A_PDF_HEADER"
    with pytest.raises(DocumentValidationError, match="signature does not match"):
        doc_service.ingest_document(
            file_name="document.pdf",
            content=invalid_content,
            content_type="application/pdf",
            bidder_id="B001",
            doc_type="GST_REG06",
        )


def test_malware_detection_eicar(doc_service):
    malicious_pdf = b"%PDF-1.4 " + EICAR_SIGNATURE
    with pytest.raises(DocumentSecurityError, match="Malware detected"):
        doc_service.ingest_document(
            file_name="infected.pdf",
            content=malicious_pdf,
            content_type="application/pdf",
            bidder_id="B001",
            doc_type="GST_REG06",
        )


def test_malicious_script_payload_rejected(doc_service):
    exploit_pdf = b"%PDF-1.4 /JavaScript << /JS (app.alert('pwned')) >>"
    with pytest.raises(DocumentSecurityError, match="Malicious payload detected"):
        doc_service.ingest_document(
            file_name="exploit.pdf",
            content=exploit_pdf,
            content_type="application/pdf",
            bidder_id="B001",
            doc_type="GST_REG06",
        )


def test_structured_extraction_and_registry_cross_check(doc_service):
    content = b"%PDF-1.5 test gst content"
    extraction = doc_service.extract_document_fields(
        doc_id="DOC-GST-B001",
        doc_type="GST_REG06",
        content=content,
        known_bidder_data={"gstin": "06AABCT1234A1Z5", "entity_name": "Acme Tech Solutions"},
    )
    assert extraction.fields["gstin"].value == "06AABCT1234A1Z5"
    assert extraction.fields["gstin"].confidence >= 0.95

    # Matching registry data
    val_match = doc_service.validate_against_registry(
        extraction=extraction,
        registry_data={"gstin": "06AABCT1234A1Z5", "entity_name": "Acme Tech Solutions"},
    )
    assert val_match.status == "verified"
    assert len(val_match.discrepancies) == 0

    # Mismatched registry data
    val_mismatch = doc_service.validate_against_registry(
        extraction=extraction,
        registry_data={"gstin": "07FAKEGSTIN99Z1", "entity_name": "Other Entity"},
    )
    assert val_mismatch.status == "mismatched"
    assert any("GSTIN mismatch" in d for d in val_mismatch.discrepancies)


def test_digilocker_boundary_honest_unavailable(doc_service):
    # Without consent token
    res1 = doc_service.verify_digilocker_consent(doc_id="DOC-PAN-B001")
    assert res1.status == "unavailable"
    assert "explicit bidder consent" in res1.message

    # With consent token, still truthful about unavailable direct gateway
    res2 = doc_service.verify_digilocker_consent(doc_id="DOC-PAN-B001", consent_token="CONSENT-12345")
    assert res2.status == "unavailable"
    assert "unavailable in this environment" in res2.message
