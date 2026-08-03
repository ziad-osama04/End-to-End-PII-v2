"""Unit tests for src/detection/dutch_regex.py -- the Presidio pattern recognizers
that back the medroberta-nl-1 masker's structured-identifier detection.

Tests the compiled regex directly rather than going through Presidio's
AnalyzerEngine (which would require the spaCy NLP engine); that keeps these
tests fast and focused on what this module actually owns: the patterns.
"""
from __future__ import annotations

import re

import pytest

from src.detection.dutch_regex import get_dutch_regex_recognizers

EXPECTED_ENTITIES = {
    "DATE", "AGE", "HEIGHT", "WEIGHT", "BMI", "RACE", "DEPT",
    "HOSPITAL", "NATIONAL_ID", "PROVIDER_ID", "PHONE", "IBAN", "ADDRESS",
}

# One (entity, matching sample) pair per recognizer.
POSITIVE_SAMPLES = {
    "DATE": "geboren 12-03-2024",
    "AGE": "45 jaar",
    "HEIGHT": "180 cm",
    "WEIGHT": "80 kg",
    "BMI": "BMI 27.5",
    "RACE": "patiënt is kaukasisch",
    "DEPT": "afdeling A-123",
    "HOSPITAL": "AZORG campus",
    "NATIONAL_ID": "insz 85.07.30-033.61",
    "PROVIDER_ID": "riziv 1-12345-67-890",
    "PHONE": "bel 0475123456",
    # This pattern requires an alphabetic bank code (\b(?:NL|BE)\d{2}\s?[A-Z]{4}...),
    # so it matches a Dutch-style IBAN but not a real Belgian one with a numeric
    # bank code (see test_iban_pattern_only_matches_alpha_bank_code below).
    "IBAN": "NL91 ABNA 0417 1643 00",
    "ADDRESS": "Kerkstraat 12, 9000 Gent",
}


@pytest.fixture(scope="module")
def recognizers():
    return get_dutch_regex_recognizers()


def test_returns_one_recognizer_per_expected_entity(recognizers):
    entities = {r.supported_entities[0] for r in recognizers}
    assert entities == EXPECTED_ENTITIES


def test_all_recognizers_are_dutch(recognizers):
    assert all(r.supported_language == "nl" for r in recognizers)


@pytest.mark.parametrize("entity,sample", list(POSITIVE_SAMPLES.items()))
def test_pattern_matches_its_sample(recognizers, entity, sample):
    recognizer = next(r for r in recognizers if r.supported_entities[0] == entity)
    pattern = recognizer.patterns[0].regex
    assert re.search(pattern, sample, re.IGNORECASE), f"{entity} pattern missed {sample!r}"


def test_phone_pattern_rejects_short_numbers(recognizers):
    recognizer = next(r for r in recognizers if r.supported_entities[0] == "PHONE")
    pattern = recognizer.patterns[0].regex
    assert re.search(pattern, "bel 047512") is None  # below the 6-digit tail minimum


def test_iban_pattern_requires_country_prefix(recognizers):
    recognizer = next(r for r in recognizers if r.supported_entities[0] == "IBAN")
    pattern = recognizer.patterns[0].regex
    assert re.search(pattern, "ABNA 0417 1643 00") is None


def test_iban_pattern_only_matches_alpha_bank_code(recognizers):
    """A real Belgian IBAN uses a numeric bank code, which this pattern misses.

    Documents actual behavior, not a requirement: masking_core.py's own IBAN
    regex is alnum-based and would catch this where dutch_regex.py's does not.
    """
    recognizer = next(r for r in recognizers if r.supported_entities[0] == "IBAN")
    pattern = recognizer.patterns[0].regex
    assert re.search(pattern, "BE68 5390 0754 7034") is None


def test_national_id_and_provider_id_are_distinct_shapes(recognizers):
    national_id = next(r for r in recognizers if r.supported_entities[0] == "NATIONAL_ID")
    provider_id = next(r for r in recognizers if r.supported_entities[0] == "PROVIDER_ID")
    assert re.search(national_id.patterns[0].regex, "85.07.30-033.61")
    assert re.search(provider_id.patterns[0].regex, "1-12345-67-890")
