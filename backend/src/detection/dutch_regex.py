"""Regex recognizers for structured Belgian/Dutch PII, aligned to the v2 taxonomy.

The fine-tuned model handles the open-set entities (NAME, ORGANIZATION, CITY,
STREET, BUILDING_NUMBER, DATE, AGE, PHONE). This module adds the structured
identifiers that are reliably parseable and verifiable:

    INSZ / NISS      national register number (checksum + gender derivation)
    RIZIV / INAMI    healthcare provider number (format)
    BTW_EENHEID      Belgian enterprise / VAT number (BE0...)
    EMAIL, URL       contact identifiers
    IBAN             bank account number
    PHONE, DATE, AGE, ZIP_CODE, STREET   structured assists to the model

GENDER is DERIVED from the INSZ (see ``derive_gender``), never string-matched, so
a stray "M"/"V" is never tagged.

Removed vs. the previous version: HEIGHT, WEIGHT, BMI, RACE and DEPT recognizers.
They are clinical measurements, not identifiers, and the broad DEPT pattern
(``[A-Z]{1,4}-?\\d{1,4}``) was the source of the spirometry-table false positives.
"""
from __future__ import annotations

import re

from presidio_analyzer import Pattern, PatternRecognizer

# Dutch month names for written dates such as "3 mei 2026".
_MONTHS_NL = (
    "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|"
    "november|december"
)


def get_dutch_regex_recognizers():
    """Return the list of structured-PII PatternRecognizers (v2 taxonomy)."""
    recognizers = []

    # DATE — numeric (dd-mm-yyyy), month-year, written (3 mei 2026), and clock
    # times. Times use ':' only so a decimal such as "0.34" is not read as a time.
    date_patterns = [
        Pattern(name="date_numeric", regex=r"\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b", score=0.6),
        Pattern(name="month_year", regex=r"\b(?:0?[1-9]|1[0-2])[-/]\d{4}\b", score=0.6),
        Pattern(name="date_written", regex=r"\b\d{1,2}\s+(?:" + _MONTHS_NL + r")(?:\s+\d{4})?\b", score=0.75),
        Pattern(name="clock_time", regex=r"\b[0-2]?\d:[0-5]\d\b", score=0.5),
    ]
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="DATE", patterns=date_patterns,
        context=["datum", "geboren", "geboortedatum", "validatie"]))

    # AGE
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="AGE",
        patterns=[Pattern(name="age", regex=r"\b\d{1,3}\s*(?:jaar|jr|j\.|-?jarige?)\b", score=0.6)],
        context=["leeftijd", "oud"]))

    # PHONE (BE/NL): +32/+31/0 then 8-9 more digits with optional separators.
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="PHONE",
        patterns=[Pattern(name="phone", regex=r"(?:\+32|\+31|0)[\s./-]?\d(?:[\s./-]?\d){7,8}\b", score=0.7)]))

    # INSZ / NISS — national register number.
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="INSZ",
        patterns=[Pattern(name="insz", regex=r"\b\d{2}[.\- ]?\d{2}[.\- ]?\d{2}[.\- ]?\d{3}[.\- ]?\d{2}\b", score=0.85)],
        context=["insz", "niss", "rijksregister"]))

    # RIZIV / INAMI — provider number.
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="RIZIV",
        patterns=[Pattern(name="riziv", regex=r"\b\d[.\- ]?\d{5}[.\- ]?\d{2}[.\- ]?\d{3}\b", score=0.8)],
        context=["riziv", "inami"]))

    # BTW-EENHEID / enterprise number: BE0 + 9 digits.
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="BTW_EENHEID",
        patterns=[Pattern(name="btw", regex=r"\bBE\s?0\d{3}[.\s]?\d{3}[.\s]?\d{3}\b", score=0.9)],
        context=["btw", "ondernemingsnummer", "eenheid"]))

    # EMAIL
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="EMAIL",
        patterns=[Pattern(name="email", regex=r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", score=0.9)]))

    # URL
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="URL",
        patterns=[Pattern(name="url", regex=r"\b(?:https?://|www\.)\S+", score=0.85)]))

    # IBAN (NL/BE)
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="IBAN",
        patterns=[Pattern(name="iban", regex=r"\b(?:NL|BE)\d{2}\s?(?:[A-Z0-9]{4}\s?){2,}[A-Z0-9]{1,4}\b", score=0.9)]))

    # ZIP_CODE — Belgian 4-digit postcode immediately followed by a City name.
    # The lookahead keeps ordinary 4-digit numbers (lab values, years) from matching.
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="ZIP_CODE",
        patterns=[Pattern(name="zip_city", regex=r"\b[1-9]\d{3}(?=\s+[A-ZÀ-Ý])", score=0.5)]))

    # STREET — a capitalised name ending in a Dutch street suffix (assists model).
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="STREET",
        patterns=[Pattern(name="street", regex=r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[a-zà-ÿ]+)*(?:straat|laan|weg|plein|dreef|steenweg|baan|lei|kaai|markt)\b", score=0.6)]))

    return recognizers


# --------------------------------------------------------------------------- #
# INSZ verification + gender derivation
# --------------------------------------------------------------------------- #
_INSZ_FIND = re.compile(r"\b\d{2}[.\- ]?\d{2}[.\- ]?\d{2}[.\- ]?\d{3}[.\- ]?\d{2}\b")


def _insz_digits(insz: str) -> str | None:
    digits = re.sub(r"\D", "", insz)
    return digits if len(digits) == 11 else None


def insz_checksum_valid(insz: str) -> bool:
    """Return whether the Belgian national number's check digits are valid.

    The last two digits equal ``97 - (first-9-digits mod 97)``. People born from
    2000 onward have a leading ``2`` prepended before the modulus is taken.
    """
    digits = _insz_digits(insz)
    if not digits:
        return False
    base, check = int(digits[:9]), int(digits[9:])
    return check in (97 - (base % 97), 97 - (int("2" + digits[:9]) % 97))


def gender_from_insz(insz: str) -> str | None:
    """Return ``'M'``/``'V'`` from the INSZ sequence number (odd=male, even=female)."""
    digits = _insz_digits(insz)
    if not digits:
        return None
    seq = int(digits[6:9])
    if seq == 0:
        return None
    return "M" if seq % 2 else "V"


def derive_gender(text: str, *, require_valid_checksum: bool = False):
    """Find INSZ numbers in *text* and derive gender from each.

    Returns a list of ``(start, end, insz, gender, checksum_ok)``. Gender comes
    from the sequence-number parity so it also works on synthetic INSZ whose
    check digits are random; set ``require_valid_checksum=True`` to keep only
    numbers whose checksum verifies.
    """
    out = []
    for m in _INSZ_FIND.finditer(text):
        raw = m.group()
        ok = insz_checksum_valid(raw)
        if require_valid_checksum and not ok:
            continue
        gender = gender_from_insz(raw)
        if gender:
            out.append((m.start(), m.end(), raw, gender, ok))
    return out
