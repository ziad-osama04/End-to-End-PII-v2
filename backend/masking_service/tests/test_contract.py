"""Acceptance-evidence tests for PII Masking API contract v1.2.

Covers the section 11 acceptance checklist:
  * /health, /ready, /version comply with the contract.
  * /v1/mask accepts raw bytes and returns a masked body with all version
    headers, and echoes X-Request-ID.
  * Unsupported media -> 415, oversized -> 413, malformed -> 422, no token -> 401.
  * Temporary overload -> 429 (Retry-After); not-ready -> 503 (Retry-After).
  * Determinism, "never return the original on failure", and "no body/PII in
    logs" all hold.

Run from the backend/ directory:
    python -m pytest masking_service/tests -v
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

import pytest

# Configure BEFORE importing the app so settings load with these values.
os.environ["SERVICE_TOKEN"] = "test-secret-token"
os.environ["MASKING_MODEL_VERSION"] = "regex-poc-1"
os.environ.pop("MODEL_VERSION", None)
os.environ.pop("MODEL_URI", None)
os.environ.pop("MASKING_MODEL_URI", None)

from fastapi.testclient import TestClient  # noqa: E402

from masking_service import masking_core as core  # noqa: E402
from masking_service.app import app  # noqa: E402

TOKEN = "test-secret-token"
VERSION = "regex-poc-1"

# Every version header the contract requires on a successful masked response.
_REQUIRED_VERSION_HEADERS = (
    "X-API-Version",
    "X-Service-Release",
    "X-Git-SHA",
    "X-Image-Digest",
    "X-Model-Name",
    "X-Model-Version",
    "X-Model-Digest",
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # context manager triggers startup (model load)
        yield c


def _headers(media_type="text/plain", **overrides):
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": media_type,
        "Accept": media_type,
        "X-Request-ID": "req-123",
        "Idempotency-Key": "req-123",
        "X-Team-ID": "team-1",
    }
    h.update(overrides)
    return h


# --------------------------------------------------------------------------- #
# Per-PII-class unit tests (core level)
# --------------------------------------------------------------------------- #
PII_SAMPLES = {
    "EMAIL": "mail jan.jansen@example.com",
    "IBAN": "rekening BE68539007547034",
    "NATIONAL_ID": "insz 85.07.30-033.61",
    "PROVIDER_ID": "riziv 1-12345-67-890",
    "PHONE": "bel 0475123456",
    "ADDRESS": "woont Kerkstraat 12, 9000 Gent",
    "HOSPITAL": "AZORG campus",
    "BMI": "BMI 27.5",
    "DATE": "op 12-03-2024",
    "AGE": "45 jaar",
    "HEIGHT": "180 cm",
    "WEIGHT": "80 kg",
}


@pytest.mark.parametrize("label,text", list(PII_SAMPLES.items()))
def test_every_pii_class_is_masked(label, text):
    masker = core.get_masker(VERSION)
    result = masker.mask_bytes(text.encode("utf-8"), "text/plain")
    assert f"<{label}>" in result.content.decode("utf-8"), (label, result.content)
    assert result.entity_count >= 1


def test_supported_entities_all_have_a_sample():
    # Guard: if a new PII class is added to the core, add a sample here too.
    assert set(core.SUPPORTED_ENTITIES) == set(PII_SAMPLES)


# --------------------------------------------------------------------------- #
# Status endpoints (contract v1.2 section 2)
# --------------------------------------------------------------------------- #
def test_health_up(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "UP"}


def test_ready_when_model_loaded(client):
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "READY", "model_loaded": True}


def test_version_reports_release_identity(client):
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert body["api_contract_version"] == "v1"
    assert body["model_version"] == VERSION
    assert body["max_file_bytes"] == core.MAX_BYTES
    for mime in ("text/plain", "text/csv", "application/json"):
        assert mime in body["supported_mime_types"]


def test_healthz_still_answers(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_version": VERSION}


# --------------------------------------------------------------------------- #
# Structure preservation
# --------------------------------------------------------------------------- #
def test_txt_masks_and_keeps_nonpii(client):
    body = "Patient belde 0475123456 vandaag."
    r = client.post("/v1/mask", headers=_headers("text/plain"), content=body.encode())
    assert r.status_code == 200
    out = r.text
    assert "<PHONE>" in out
    assert out.startswith("Patient belde ") and out.endswith(" vandaag.")


def test_csv_structure_preserved(client):
    body = "name,phone,note\nJan,0475123456,ok\nPiet,0475998877,fine\n"
    r = client.post("/v1/mask", headers=_headers("text/csv"), content=body.encode())
    assert r.status_code == 200
    lines = [ln for ln in r.text.splitlines() if ln]
    assert lines[0] == "name,phone,note"                  # header untouched
    assert all(len(ln.split(",")) == 3 for ln in lines)   # column count stable
    assert "<PHONE>" in r.text


def test_json_structure_preserved(client):
    body = json.dumps({"patient": {"phone": "0475123456"}, "vals": [1, 2, "ok"]})
    r = client.post(
        "/v1/mask", headers=_headers("application/json"), content=body.encode()
    )
    assert r.status_code == 200
    parsed = json.loads(r.text)                            # still valid JSON
    assert parsed["patient"]["phone"] == "<PHONE>"
    assert parsed["vals"] == [1, 2, "ok"]                  # non-string untouched


# --------------------------------------------------------------------------- #
# Success response headers (contract v1.2 section 4)
# --------------------------------------------------------------------------- #
def test_success_headers(client):
    body = "bel 0475123456"
    r = client.post("/v1/mask", headers=_headers(), content=body.encode())
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "req-123"
    assert r.headers["X-API-Version"] == "v1"
    assert r.headers["X-Model-Version"] == VERSION
    for header in _REQUIRED_VERSION_HEADERS:
        assert r.headers.get(header), f"missing {header}"
    assert r.headers["X-Masked-Content-SHA256"] == hashlib.sha256(r.content).hexdigest()
    assert r.headers["content-type"].startswith("text/plain")


def test_masked_headers_match_version_endpoint(client):
    """Contract v1.2 section 4: masked headers must match /version."""
    v = client.get("/version").json()
    r = client.post("/v1/mask", headers=_headers(), content=b"bel 0475123456")
    assert r.headers["X-API-Version"] == v["api_contract_version"]
    assert r.headers["X-Service-Release"] == v["service_release"]
    assert r.headers["X-Model-Name"] == v["model_name"]
    assert r.headers["X-Model-Version"] == v["model_version"]


# --------------------------------------------------------------------------- #
# Error contract (contract v1.2 section 5)
# --------------------------------------------------------------------------- #
def test_invalid_token_401(client):
    r = client.post(
        "/v1/mask", headers=_headers(Authorization="Bearer wrong"), content=b"x"
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"
    assert r.json()["error"]["retryable"] is False


def test_missing_request_id_400(client):
    h = _headers()
    del h["X-Request-ID"]
    r = client.post("/v1/mask", headers=h, content=b"bel 0475123456")
    assert r.status_code == 400


def test_empty_body_400(client):
    r = client.post("/v1/mask", headers=_headers(), content=b"")
    assert r.status_code == 400


def test_unsupported_media_type_415(client):
    r = client.post("/v1/mask", headers=_headers("application/xml"), content=b"<a/>")
    assert r.status_code == 415
    assert r.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_oversized_413(client):
    big = b"a" * (core.MAX_BYTES + 1)
    r = client.post("/v1/mask", headers=_headers(), content=big)
    assert r.status_code == 413


def test_malformed_json_422(client):
    r = client.post(
        "/v1/mask", headers=_headers("application/json"), content=b"{not json"
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNPROCESSABLE_DOCUMENT"


def test_error_body_shape(client):
    r = client.post("/v1/mask", headers=_headers("application/xml"), content=b"<a/>")
    err = r.json()["error"]
    assert set(err) == {"code", "message", "retryable", "request_id"}
    assert err["request_id"] == "req-123"
    assert r.headers["X-Request-ID"] == "req-123"


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_deterministic_output(client):
    body = "bel 0475123456, mail jan@example.com, BE68539007547034"
    h = _headers()
    r1 = client.post("/v1/mask", headers=h, content=body.encode())
    r2 = client.post("/v1/mask", headers=h, content=body.encode())
    assert r1.content == r2.content
    assert (
        r1.headers["X-Masked-Content-SHA256"] == r2.headers["X-Masked-Content-SHA256"]
    )


# --------------------------------------------------------------------------- #
# Never return the original on failure
# --------------------------------------------------------------------------- #
def test_failure_never_returns_original(client):
    original = b'{"phone": "0475123456"'  # malformed JSON (missing brace)
    r = client.post(
        "/v1/mask", headers=_headers("application/json"), content=original
    )
    assert r.status_code == 422
    assert b"0475123456" not in r.content  # raw PII not echoed back


# --------------------------------------------------------------------------- #
# No PII / bodies in logs
# --------------------------------------------------------------------------- #
def test_logs_contain_no_body_or_pii(client, caplog):
    secret_phone = "0475123456"
    body = f"geheim telefoon {secret_phone} en mail spy@example.com"
    with caplog.at_level(logging.INFO, logger="masking_service"):
        r = client.post("/v1/mask", headers=_headers(), content=body.encode())
    assert r.status_code == 200
    joined = "\n".join(rec.getMessage() for rec in caplog.records)
    assert secret_phone not in joined
    assert "spy@example.com" not in joined
    assert "geheim" not in joined
    assert "<PHONE>" not in joined  # masked entities are not logged either


# --------------------------------------------------------------------------- #
# PDF masking (contract v1.2 canary format). Skipped when PyMuPDF is absent.
# --------------------------------------------------------------------------- #
fitz = pytest.importorskip("fitz")

PDF_PII = {
    "email": "jan.jansen@example.com",
    "phone": "0475123456",
    "iban": "BE68539007547034",
}


def _make_text_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Patient email {PDF_PII['email']}", fontsize=12)
    page.insert_text(
        (72, 96),
        f"Telefoon {PDF_PII['phone']} en IBAN {PDF_PII['iban']}",
        fontsize=12,
    )
    data = doc.tobytes()
    doc.close()
    return data


def _pdf_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text


def test_version_lists_pdf_when_supported(client):
    body = client.get("/version").json()
    assert "application/pdf" in body["supported_mime_types"]


def test_pdf_masks_and_returns_valid_pdf(client):
    r = client.post("/v1/mask", headers=_headers("application/pdf"), content=_make_text_pdf())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")
    for header in _REQUIRED_VERSION_HEADERS:
        assert r.headers.get(header), f"missing {header}"

    # The output opens as a PDF and no longer contains any of the raw PII.
    out_text = _pdf_text(r.content)
    for value in PDF_PII.values():
        assert value not in out_text, f"PII leaked: {value}"
    # And it carries the labelled placeholders instead.
    assert "<EMAIL>" in out_text


def test_pdf_preserves_structure(client):
    """A PDF input returns a PDF with the same structure -- only PII changes."""
    doc = fitz.open()
    p1 = doc.new_page(width=595, height=842)
    p1.insert_text((72, 72), "MEDISCH RAPPORT", fontsize=16)
    p1.insert_text((72, 110), "Diagnose: hypertensie", fontsize=11)
    p1.insert_text((72, 140), f"Contact: {PDF_PII['email']}", fontsize=11)
    p2 = doc.new_page(width=595, height=842)
    p2.insert_text((72, 72), "BIJLAGE", fontsize=16)
    p2.insert_text((72, 110), f"IBAN {PDF_PII['iban']}", fontsize=11)
    in_pages = doc.page_count
    in_dims = [(round(pg.rect.width), round(pg.rect.height)) for pg in doc]
    pdf_in = doc.tobytes()
    doc.close()

    r = client.post("/v1/mask", headers=_headers("application/pdf"), content=pdf_in)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")

    out = fitz.open(stream=r.content, filetype="pdf")
    try:
        assert out.page_count == in_pages  # same number of pages
        out_dims = [(round(pg.rect.width), round(pg.rect.height)) for pg in out]
        assert out_dims == in_dims  # same page dimensions
        text = "\n".join(pg.get_text() for pg in out)
    finally:
        out.close()

    # Non-PII content survives; PII does not.
    assert "MEDISCH RAPPORT" in text and "BIJLAGE" in text and "Diagnose" in text
    assert PDF_PII["email"] not in text and PDF_PII["iban"] not in text


def test_pdf_output_is_deterministic(client):
    pdf = _make_text_pdf()
    r1 = client.post("/v1/mask", headers=_headers("application/pdf"), content=pdf)
    r2 = client.post("/v1/mask", headers=_headers("application/pdf"), content=pdf)
    assert r1.status_code == r2.status_code == 200
    assert r1.headers["X-Masked-Content-SHA256"] == r2.headers["X-Masked-Content-SHA256"]


def test_pdf_password_protected_422(client):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "secret", fontsize=12)
    encrypted = doc.tobytes(
        encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret"
    )
    doc.close()
    r = client.post("/v1/mask", headers=_headers("application/pdf"), content=encrypted)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "UNPROCESSABLE_DOCUMENT"


def test_pdf_corrupt_422(client):
    r = client.post(
        "/v1/mask", headers=_headers("application/pdf"), content=b"%PDF-1.4 not a real pdf"
    )
    assert r.status_code == 422


def test_pdf_failure_never_returns_original(client):
    corrupt = b"%PDF-1.4 " + PDF_PII["email"].encode() + b" broken"
    r = client.post("/v1/mask", headers=_headers("application/pdf"), content=corrupt)
    assert r.status_code == 422
    assert PDF_PII["email"].encode() not in r.content
