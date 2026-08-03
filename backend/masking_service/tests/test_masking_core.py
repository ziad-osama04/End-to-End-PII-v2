"""Unit tests for masking_core.py -- the dependency-free masking engine.

These call the module directly (no HTTP, no TestClient); API/contract-level
behavior is covered separately in test_contract.py.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from masking_service import masking_core as core

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


# --------------------------------------------------------------------------- #
# normalize_media_type
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("text/plain", "text/plain"),
        ("APPLICATION/JSON", "application/json"),
        ("text/csv; charset=utf-8", "text/csv"),
        ("  text/plain  ", "text/plain"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_media_type(raw, expected):
    assert core.normalize_media_type(raw) == expected


# --------------------------------------------------------------------------- #
# mask_text / _find_spans
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("label,text", list(PII_SAMPLES.items()))
def test_every_pii_class_is_masked(label, text):
    masked, count = core.mask_text(text)
    assert f"<{label}>" in masked
    assert count >= 1


def test_supported_entities_all_have_a_sample():
    assert set(core.SUPPORTED_ENTITIES) == set(PII_SAMPLES)


def test_mask_text_preserves_non_pii_content():
    masked, _ = core.mask_text("Patient belde 0475123456 vandaag.")
    assert masked.startswith("Patient belde ") and masked.endswith(" vandaag.")


def test_mask_text_empty_string_is_untouched():
    assert core.mask_text("") == ("", 0)


def test_mask_text_no_pii_returns_original_unchanged():
    text = "Dit is een gewone Nederlandse zin zonder PII."
    assert core.mask_text(text) == (text, 0)


def test_mask_text_multiple_entities_all_masked():
    text = "Bel 0475123456 of mail jan@example.com, IBAN BE68539007547034."
    masked, count = core.mask_text(text)
    assert count == 3
    assert "<PHONE>" in masked and "<EMAIL>" in masked and "<IBAN>" in masked
    assert "0475123456" not in masked
    assert "jan@example.com" not in masked


def test_find_spans_are_non_overlapping_and_sorted():
    text = "Bel 0475123456 of mail jan@example.com."
    spans = core._find_spans(text)
    assert spans == sorted(spans, key=lambda s: s[0])
    for (s1, e1, _), (s2, e2, _) in zip(spans, spans[1:]):
        assert e1 <= s2


def test_mask_text_is_deterministic():
    text = "Bel 0475123456, mail jan@example.com, BMI 27.5, 45 jaar."
    assert core.mask_text(text) == core.mask_text(text)


# --------------------------------------------------------------------------- #
# Masker.mask_bytes -- TXT / CSV / JSON structure preservation
# --------------------------------------------------------------------------- #
@pytest.fixture
def masker():
    return core.Masker()


def test_mask_bytes_txt(masker):
    result = masker.mask_bytes(b"Patient belde 0475123456 vandaag.", core.TXT)
    assert result.content == b"Patient belde <PHONE> vandaag."
    assert result.entity_count == 1
    assert result.model_version == "regex-poc-1"
    assert result.sha256 == hashlib.sha256(result.content).hexdigest()


def test_mask_bytes_csv_preserves_header_and_column_count(masker):
    body = b"name,phone,note\nJan,0475123456,ok\nPiet,0475998877,fine\n"
    result = masker.mask_bytes(body, core.CSV)
    text = result.content.decode()
    lines = [ln for ln in text.splitlines() if ln]
    assert lines[0] == "name,phone,note"
    assert all(len(ln.split(",")) == 3 for ln in lines)
    assert "<PHONE>" in text
    assert result.entity_count == 2


def test_mask_bytes_json_preserves_structure_and_non_strings(masker):
    body = json.dumps({"patient": {"phone": "0475123456"}, "vals": [1, 2, "ok"]}).encode()
    result = masker.mask_bytes(body, core.JSON)
    parsed = json.loads(result.content)
    assert parsed["patient"]["phone"] == "<PHONE>"
    assert parsed["vals"] == [1, 2, "ok"]


def test_mask_bytes_json_preserves_key_order(masker):
    body = json.dumps({"z": "a", "a": "b", "m": "c"}).encode()
    result = masker.mask_bytes(body, core.JSON)
    assert list(json.loads(result.content).keys()) == ["z", "a", "m"]


def test_mask_bytes_is_byte_deterministic(masker):
    body = b"Bel 0475123456, mail jan@example.com"
    r1 = masker.mask_bytes(body, core.TXT)
    r2 = masker.mask_bytes(body, core.TXT)
    assert r1.content == r2.content
    assert r1.sha256 == r2.sha256


# --------------------------------------------------------------------------- #
# Error paths
# --------------------------------------------------------------------------- #
def test_mask_bytes_unsupported_media_type(masker):
    with pytest.raises(core.UnsupportedMediaType):
        masker.mask_bytes(b"<a/>", "application/xml")


def test_mask_bytes_empty_body_raises(masker):
    with pytest.raises(core.MaskingError):
        masker.mask_bytes(b"", core.TXT)


def test_mask_bytes_invalid_utf8_raises(masker):
    with pytest.raises(core.MaskingError):
        masker.mask_bytes(b"\xff\xfe not utf-8", core.TXT)


def test_mask_bytes_malformed_json_raises(masker):
    with pytest.raises(core.MaskingError):
        masker.mask_bytes(b"{not json", core.JSON)


def test_mask_bytes_over_max_size_raises(masker):
    big = b"a" * (core.MAX_BYTES + 1)
    with pytest.raises(core.MaskingError):
        masker.mask_bytes(big, core.TXT)


def test_mask_bytes_never_leaks_original_on_failure(masker):
    original = b'{"phone": "0475123456"'  # malformed: missing closing brace
    with pytest.raises(core.MaskingError):
        masker.mask_bytes(original, core.JSON)


# --------------------------------------------------------------------------- #
# Masker registry
# --------------------------------------------------------------------------- #
def test_registry_has_regex_poc_1_by_default():
    assert "regex-poc-1" in core.available_versions()
    assert core.get_masker("regex-poc-1").model_version == "regex-poc-1"


def test_registry_unknown_version_raises_keyerror():
    with pytest.raises(KeyError):
        core.get_masker("does-not-exist")


def test_register_adds_and_overwrites_by_model_version():
    class _Custom(core.Masker):
        model_version = "test-custom-1"

    core.register(_Custom())
    try:
        assert core.get_masker("test-custom-1").model_version == "test-custom-1"
        assert "test-custom-1" in core.available_versions()
    finally:
        core._REGISTRY.pop("test-custom-1", None)
