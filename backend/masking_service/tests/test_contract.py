"""Acceptance-evidence tests for the masking contract.

Covers the "Acceptance evidence from the AI team" checklist:
  * Unit tests for every supported PII class.
  * TXT/CSV/JSON structure-preservation tests.
  * Invalid-token, oversized, malformed, and version-mismatch tests.
  * Determinism test.
  * A test proving logs contain no request/response body or extracted PII.

Run from the backend/ directory:
    python -m pytest masking_service/tests -v
"""
from __future__ import annotations

import json
import logging
import os

import pytest

# Configure BEFORE importing the app so startup picks these up.
os.environ["MASKING_API_TOKEN"] = "test-secret-token"
os.environ["MASKING_MODEL_VERSION"] = "regex-poc-1"
os.environ.pop("MASKING_MODEL_URI", None)

from fastapi.testclient import TestClient  # noqa: E402

from masking_service import masking_core as core  # noqa: E402
from masking_service.app import app  # noqa: E402

TOKEN = "test-secret-token"
VERSION = "regex-poc-1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # context manager triggers startup (model load)
        yield c


def _headers(media_type="text/plain", **overrides):
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": media_type,
        "X-Request-ID": "req-123",
        "X-Source-Key": "bucket/key.txt",
        "X-Source-ETag": "etag-abc",
        "X-Model-Version": VERSION,
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
    assert lines[0] == "name,phone,note"          # header untouched
    assert all(len(ln.split(",")) == 3 for ln in lines)  # column count stable
    assert "<PHONE>" in r.text


def test_json_structure_preserved(client):
    body = json.dumps({"patient": {"phone": "0475123456"}, "vals": [1, 2, "ok"]})
    r = client.post("/v1/mask", headers=_headers("application/json"), content=body.encode())
    assert r.status_code == 200
    parsed = json.loads(r.text)                    # still valid JSON
    assert parsed["patient"]["phone"] == "<PHONE>"
    assert parsed["vals"] == [1, 2, "ok"]          # non-string leaves untouched


# --------------------------------------------------------------------------- #
# Response headers
# --------------------------------------------------------------------------- #
def test_success_headers(client):
    body = "bel 0475123456"
    r = client.post("/v1/mask", headers=_headers(), content=body.encode())
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "req-123"
    assert r.headers["X-Masking-Model-Version"] == VERSION
    assert int(r.headers["X-Masking-Entity-Count"]) == 1
    import hashlib

    assert r.headers["X-Masked-Content-SHA256"] == hashlib.sha256(r.content).hexdigest()
    assert r.headers["content-type"].startswith("text/plain")


# --------------------------------------------------------------------------- #
# Status contract
# --------------------------------------------------------------------------- #
def test_invalid_token_401(client):
    r = client.post("/v1/mask", headers=_headers(Authorization="Bearer wrong"), content=b"x")
    assert r.status_code == 401


def test_missing_metadata_400(client):
    h = _headers()
    del h["X-Source-ETag"]
    r = client.post("/v1/mask", headers=h, content=b"bel 0475123456")
    assert r.status_code == 400


def test_empty_body_400(client):
    r = client.post("/v1/mask", headers=_headers(), content=b"")
    assert r.status_code == 400


def test_unsupported_media_type_415(client):
    r = client.post("/v1/mask", headers=_headers("application/xml"), content=b"<a/>")
    assert r.status_code == 415


def test_version_mismatch_409(client):
    r = client.post(
        "/v1/mask",
        headers=_headers(**{"X-Model-Version": "some-other-version"}),
        content=b"bel 0475123456",
    )
    assert r.status_code == 409


def test_oversized_413(client):
    big = b"a" * (core.MAX_BYTES + 1)
    r = client.post("/v1/mask", headers=_headers(), content=big)
    assert r.status_code == 413


def test_malformed_json_422(client):
    r = client.post("/v1/mask", headers=_headers("application/json"), content=b"{not json")
    assert r.status_code == 422


def test_health_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "model_version": VERSION}


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
def test_deterministic_output(client):
    body = "bel 0475123456, mail jan@example.com, BE68539007547034"
    h = _headers()
    r1 = client.post("/v1/mask", headers=h, content=body.encode())
    r2 = client.post("/v1/mask", headers=h, content=body.encode())
    assert r1.content == r2.content
    assert r1.headers["X-Masked-Content-SHA256"] == r2.headers["X-Masked-Content-SHA256"]


# --------------------------------------------------------------------------- #
# Never return the original on failure
# --------------------------------------------------------------------------- #
def test_failure_never_returns_original(client):
    original = b'{"phone": "0475123456"'  # malformed JSON (missing brace)
    r = client.post("/v1/mask", headers=_headers("application/json"), content=original)
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
