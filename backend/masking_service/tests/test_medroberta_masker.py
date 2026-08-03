"""Unit tests for medroberta_masker.py.

Mocks only the expensive part -- the transformer-based analyzer -- so these
tests run in milliseconds with no torch/network access. The real
presidio_anonymizer.AnonymizerEngine is used unmocked, so the KEEP_VISIBLE
filtering and operator-config wiring are exercised faithfully, not just
"was it called".
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

from masking_service.medroberta_masker import MedRobertaMasker


def _stub_ensure(masker, fake_results):
    """Return a replacement for MedRobertaMasker._ensure that skips the real
    (heavy) analyzer but wires up the same _keep_visible/_operator_config the
    real one would, plus a real AnonymizerEngine.
    """

    def _ensure():
        if masker._detector is None:
            masker._keep_visible = {"CLINICAL_NOTE", "MEDICATION"}
            masker._operator_config = OperatorConfig
            masker._detector = SimpleNamespace(
                analyzer=SimpleNamespace(analyze=lambda text, language: fake_results),
                anonymizer=AnonymizerEngine(),
            )
        return masker._detector

    return _ensure


@pytest.fixture
def masker():
    return MedRobertaMasker()


def test_mask_string_replaces_detected_entity(masker, monkeypatch):
    text = "patient Dirk Willaert belde"
    results = [RecognizerResult("PATIENT_NAME", 8, 21, 0.95)]
    monkeypatch.setattr(masker, "_ensure", _stub_ensure(masker, results))

    masked, count = masker.mask_string(text)
    assert masked == "patient <PATIENT_NAME> belde"
    assert count == 1


def test_mask_string_keeps_clinical_content_visible(masker, monkeypatch):
    text = "diagnose: hypertensie, patient Jan Peeters"
    results = [
        RecognizerResult("CLINICAL_NOTE", 0, 21, 0.9),   # KEEP_VISIBLE
        RecognizerResult("PATIENT_NAME", 31, 42, 0.9),
    ]
    monkeypatch.setattr(masker, "_ensure", _stub_ensure(masker, results))

    masked, count = masker.mask_string(text)
    assert "diagnose: hypertensie" in masked  # untouched
    assert "<PATIENT_NAME>" in masked
    assert "Jan Peeters" not in masked
    assert count == 1  # only the non-keep-visible entity is counted


def test_mask_string_no_entities_returns_original(masker, monkeypatch):
    monkeypatch.setattr(masker, "_ensure", _stub_ensure(masker, []))
    assert masker.mask_string("niets bijzonders hier") == ("niets bijzonders hier", 0)


def test_mask_string_all_keep_visible_returns_original_text_but_zero_count(masker, monkeypatch):
    text = "diagnose: hypertensie"
    results = [RecognizerResult("CLINICAL_NOTE", 0, len(text), 0.9)]
    monkeypatch.setattr(masker, "_ensure", _stub_ensure(masker, results))

    masked, count = masker.mask_string(text)
    assert masked == text
    assert count == 0


@pytest.mark.parametrize("blank", ["", "   ", "\n\t"])
def test_mask_string_blank_input_short_circuits_without_loading_model(masker, blank):
    def _boom():
        raise AssertionError("model should not load for blank input")

    masker._ensure = _boom
    assert masker.mask_string(blank) == (blank, 0)


def test_detect_spans_filters_keep_visible_and_returns_tuples(masker, monkeypatch):
    text = "diagnose: astma, patient Dirk Willaert"
    results = [
        RecognizerResult("CLINICAL_NOTE", 0, 15, 0.9),
        RecognizerResult("PATIENT_NAME", 25, 38, 0.9),
    ]
    monkeypatch.setattr(masker, "_ensure", _stub_ensure(masker, results))

    spans = masker.detect_spans(text)
    assert spans == [(25, 38, "PATIENT_NAME")]


def test_detect_spans_blank_input_returns_empty_list(masker):
    masker._ensure = lambda: (_ for _ in ()).throw(AssertionError("should not load"))
    assert masker.detect_spans("") == []


def test_model_version_is_medroberta_nl_1(masker):
    assert masker.model_version == "medroberta-nl-1"
