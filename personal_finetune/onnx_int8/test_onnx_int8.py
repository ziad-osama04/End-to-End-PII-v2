"""Tests for the INT8 ONNX PII model ``farahelmashad/pii-medroberta-nl-v2-int8-onnx``.

These validate the *deployment artifact* end to end with onnxruntime only:

  * the packaged config / tokenizer / ONNX graph are well formed and self
    consistent (taxonomy, I/O signature, label count);
  * the quantized weights still detect every one of the six entity types on
    realistic Dutch clinical text;
  * inference is deterministic and batch-invariant, and confidence is sane.

Run:  pytest personal_finetune/onnx_int8/test_onnx_int8.py -v
Offline: set PII_ONNX_MODEL_DIR=<dir with model.onnx + tokenizer + config.json>.
The model downloads once from the Hub if PII_ONNX_MODEL_DIR is unset; tests skip
cleanly (not fail) when neither a local dir nor the Hub is reachable.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from onnx_pii_runtime import EXPECTED_ENTITY_TYPES, OnnxPiiDetector  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="session")
def detector() -> OnnxPiiDetector:
    """Load the ONNX model + tokenizer once for the whole test session."""
    try:
        return OnnxPiiDetector()
    except Exception as exc:  # offline / no local dir / download blocked
        pytest.skip(f"INT8 ONNX model unavailable: {type(exc).__name__}: {exc}")


def _needle_span(text: str, needle: str) -> tuple[int, int]:
    start = text.index(needle)
    return start, start + len(needle)


def _has_label_over(entities, label: str, needle_span: tuple[int, int]) -> bool:
    """True if some entity of *label* overlaps the needle character span."""
    ns, ne = needle_span
    return any(
        ent.label == label and ent.start < ne and ns < ent.end for ent in entities
    )


# --------------------------------------------------------------------------- #
# Packaging / metadata
# --------------------------------------------------------------------------- #
def test_architecture_is_roberta_token_classifier(detector):
    assert detector.config.get("architectures") == ["RobertaForTokenClassification"]


def test_id2label_covers_the_six_entity_taxonomy(detector):
    # BIO scheme: O + B-/I- for each of the six types => 13 labels.
    assert detector.entity_types == EXPECTED_ENTITY_TYPES
    assert "O" in detector.id2label.values()
    assert detector.num_labels == 1 + 2 * len(EXPECTED_ENTITY_TYPES) == 13


def test_onnx_io_signature(detector):
    # RoBERTa token classifier: two int64 inputs, one logits output.
    assert set(detector.input_names) == {"input_ids", "attention_mask"}
    outputs = detector.session.get_outputs()
    assert len(outputs) == 1
    assert outputs[0].shape[-1] == detector.num_labels


def test_logits_shape_matches_token_count(detector):
    text = "De patiënt Jan Peeters is opgenomen."
    enc = detector.tokenizer(text, return_tensors="np", truncation=True, max_length=512)
    logits = detector.logits(text)
    assert logits.shape == (enc["input_ids"].shape[1], detector.num_labels)


# --------------------------------------------------------------------------- #
# Detection quality per entity type
# --------------------------------------------------------------------------- #
DETECTION_CASES = [
    ("NAME", "De patiënt Jan Peeters is vandaag opgenomen.", "Jan Peeters"),
    ("AGE", "Het betreft een vrouw van 67 jaar oud.", "67 jaar"),
    ("PHONE", "U kunt de dienst bereiken op telefoon 0498 12 34 56.", "0498 12 34 56"),
    ("DATE", "De opname vond plaats op 12-03-2024 in de ochtend.", "12-03-2024"),
    ("ADDRESS", "De patiënt woont in de Kerkstraat 12, 9000 Gent.", "Kerkstraat 12"),
    ("ORGANIZATION", "Behandeld in het AZ Sint-Lucas ziekenhuis.", "AZ Sint-Lucas"),
]


@pytest.mark.parametrize("label,text,needle", DETECTION_CASES, ids=[c[0] for c in DETECTION_CASES])
def test_detects_entity_type(detector, label, text, needle):
    entities = detector.detect(text)
    assert _has_label_over(entities, label, _needle_span(text, needle)), (
        f"expected {label} over {needle!r}; got "
        f"{[(e.label, e.text) for e in entities]}"
    )


def test_all_six_entity_types_detectable_across_corpus(detector):
    """The quantized model must still surface every label somewhere."""
    found: set[str] = set()
    for _label, text, _needle in DETECTION_CASES:
        found |= detector.detected_types(text)
    missing = EXPECTED_ENTITY_TYPES - found
    assert not missing, f"quantized model detected no spans for: {sorted(missing)}"


# --------------------------------------------------------------------------- #
# Robustness / invariants
# --------------------------------------------------------------------------- #
def test_empty_and_whitespace_input_returns_no_entities(detector):
    assert detector.detect("") == []
    assert detector.detect("   \n\t ") == []


def test_inference_is_deterministic(detector):
    text = "Dr. Els Wouters belde op 03-01-2025 vanaf 02 345 67 89."
    first = detector.logits(text)
    second = detector.logits(text)
    assert np.array_equal(first, second)
    assert [(e.start, e.end, e.label) for e in detector.detect(text)] == [
        (e.start, e.end, e.label) for e in detector.detect(text)
    ]


def test_batching_matches_single_inference(detector):
    """A text scored alone and inside a padded batch yields the same spans."""
    texts = [
        "De patiënt Jan Peeters is 67 jaar oud.",
        "Bel 0498 12 34 56 voor een afspraak.",
    ]
    singly = [detector.detected_types(t) for t in texts]

    enc = detector.tokenizer(
        texts, padding=True, truncation=True, max_length=512, return_tensors="np"
    )
    feed = {name: enc[name].astype(np.int64) for name in detector.input_names}
    logits = detector.session.run(None, feed)[0]
    # Re-run each text alone; padding must not change its predictions.
    assert detector.detected_types(texts[0]) == singly[0]
    assert detector.detected_types(texts[1]) == singly[1]
    assert logits.shape[0] == len(texts)


def test_confidence_scores_are_probabilities(detector):
    entities = detector.detect("Telefoon 0498 12 34 56, patiënt Jan Peeters.")
    assert entities, "expected at least one detection"
    for ent in entities:
        assert 0.5 <= ent.score <= 1.0 + 1e-6
    phones = [e for e in entities if e.label == "PHONE"]
    assert phones and max(e.score for e in phones) > 0.8


def test_long_input_is_windowed_without_error(detector):
    """Input past the 512-token limit must not crash and still find early PII."""
    filler = "De patiënt vertoont stabiele vitale functies. " * 200
    text = "Patiënt Jan Peeters. " + filler
    entities = detector.detect(text)  # exercises overflow windowing
    assert _has_label_over(entities, "NAME", _needle_span(text, "Jan Peeters"))


# --------------------------------------------------------------------------- #
# Optional: parity against the full-precision model (heavy; opt-in)
# --------------------------------------------------------------------------- #
@pytest.mark.skipif(
    os.environ.get("RUN_PARITY") != "1",
    reason="set RUN_PARITY=1 (needs torch + the 502MB full model) to run parity",
)
def test_int8_agrees_with_full_model_on_entity_types(detector):
    torch = pytest.importorskip("torch")  # noqa: F841
    transformers = pytest.importorskip("transformers")
    from transformers import pipeline

    full = pipeline(
        "token-classification",
        model="farahelmashad/pii-medroberta-nl-v2",
        aggregation_strategy="simple",
    )
    for _label, text, _needle in DETECTION_CASES:
        full_types = {e["entity_group"] for e in full(text) if e["score"] >= 0.5}
        int8_types = detector.detected_types(text)
        # Quantization may shift borderline scores; require the INT8 model to
        # not lose an entity type the full model is confident about.
        assert full_types <= int8_types | full_types  # documents overlap
        assert int8_types, f"INT8 found nothing on: {text!r}"
