"""GPU-free regex hardening test suite for the personal track.

Tests the exact patterns from get_dutch_regex_recognizers() (mirrored from
backend/src/detection/dutch_regex.py as of the taxonomy overhaul) against
hand-built edge cases: valid format variations, near-miss lookalikes from
OTHER label types (the real risk -- see the RIZIV/secondary_record_id
collision found via corpus analysis), and boundary conditions.

Each case declares expect="match" (the pattern's span must cover exactly the
marked ~text~ region) or expect="no_match" (nothing in the recognizer's
patterns should fire anywhere in the text). Does not touch/import the team's
backend/ package -- patterns are inlined here on purpose, personal track only.
"""
from __future__ import annotations

import re

_MONTHS_NL = (
    "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|"
    "november|december"
)

PATTERNS = {
    "DATE": [
        ("date_numeric", r"(?<![\d./-])(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]\d{2,4}(?!\d)"),
        ("month_year", r"\b(?:0?[1-9]|1[0-2])[-/]\d{4}\b"),
        ("date_written", r"\b\d{1,2}\s+(?:" + _MONTHS_NL + r")(?:\s+\d{4})?\b"),
        ("clock_time", r"\b[0-2]?\d:[0-5]\d\b"),
    ],
    "AGE": [("age", r"\b\d{1,3}\s*(?:jaar|jr|j\.|-?jarige?)\b")],
    "PHONE": [("phone", r"(?:\+32|\+31|0)[\s./-]?\d(?:[\s./-]?\d){7,8}\b")],
    "INSZ": [("insz", r"(?<![\d+])\d{2}[.\-]?\d{2}[.\-]?\d{2}[.\-]?\d{3}[.\-]?\d{2}(?!\d)")],
    "RIZIV": [
        ("riziv_formatted", r"\b\d[.\-]\d{5}[.\-]\d{2}[.\-]\d{3}\b"),
        ("riziv_bare8", r"(?<![\d.\-])\d{8}(?![\d.\-])"),
    ],
    "BTW_EENHEID": [("btw", r"\bBE\s?0\d{3}[.\s]?\d{3}[.\s]?\d{3}\b")],
    "EMAIL": [("email", r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")],
    "URL": [("url", r"\b(?:https?://|www\.)\S+")],
    "IBAN": [("iban", r"\b(?:NL|BE)\d{2}\s?(?:[A-Z0-9]{4}\s?){2,}[A-Z0-9]{1,4}\b")],
    "ZIP_CODE": [("zip_city", r"\b[1-9]\d{3}(?=\s+[A-ZÀ-Ý])")],
    "STREET": [("street", r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[a-zà-ÿ]+)*(?:straat|laan|weg|plein|dreef|steenweg|baan|lei|kaai|markt)\b")],
}


def _mark(text_with_markers):
    """`~span~` in the source marks the expected match; returns (clean_text, start, end)."""
    idx = text_with_markers.find("~")
    if idx == -1:
        return text_with_markers, None, None
    end_idx = text_with_markers.find("~", idx + 1)
    clean = text_with_markers.replace("~", "", 2)
    start = idx
    end = end_idx - 1
    return clean, start, end


CASES = {
    "INSZ": [
        ("standard dotted", "patiëntnummer INSZ: ~74.04.07-865.22~ genoteerd", "match"),
        ("no separators", "INSZ ~74040786522~ in dossier", "match"),
        ("mixed dash/dot", "rijksregisternummer ~74.04.07.865-22~", "match"),
        ("too short (10 digits)", "nummer 7404078652 niet valide", "no_match"),
        ("too long (12 digits)", "nummer 740407865221 niet valide", "no_match"),
        ("phone number, not INSZ", "bel ons op 0470 12 34 56 voor info", "no_match"),
        ("preceded by plus (exclude)", "totaal: +74040786522 eenheden", "no_match"),
    ],
    "RIZIV": [
        ("standard formatted", "behandelend arts RIZIV ~1-23456-78-901~", "match"),
        ("bare 8 digit fallback", "providernummer ~12345678~ toegekend", "match"),
        ("secondary_record_id collision (known ambiguity)",
         "dossier ref ~7-82073-73-329~ (niet-RIZIV, zie diagnose_riziv2.py bevinding)", "match"),
        ("7 digits (too short)", "code 1234567 onbekend", "no_match"),
        ("9 bare digits (too long)", "waarde 123456789 los", "no_match"),
        ("adjacent to other digits (excluded by lookaround)", "12345678-9 reeks", "no_match"),
    ],
    "BTW_EENHEID": [
        ("standard spaced", "ondernemingsnummer ~BE 0123.456.789~", "match"),
        ("no spaces", "btw ~BE0123456789~ eenheid", "match"),
        ("NL vat (should not match BE-only pattern)", "vat NL123456789B01 niet van toepassing", "no_match"),
        ("missing leading 0", "BE123.456.789 fout formaat", "no_match"),
    ],
    "EMAIL": [
        ("standard", "contact: ~jan.devries@ziekenhuis.be~", "match"),
        ("plus-tag", "stuur naar ~patient+ref123@kliniek.nl~", "match"),
        ("no TLD (invalid)", "gebruiker@lokaal geen geldig adres", "no_match"),
        ("missing @ (invalid)", "jandevries.ziekenhuis.be geen email", "no_match"),
    ],
    "URL": [
        ("https", "portaal: ~https://patient.ziekenhuis.be/login~", "match"),
        ("www without scheme", "zie ~www.ziekenhuis.be/resultaten~", "match"),
        ("bare domain, no www/scheme (should not match)", "ziekenhuis.be is de website", "no_match"),
    ],
    "PHONE": [
        ("mobile with spaces", "bel ~0470 12 34 56~ voor info", "match"),
        ("landline with dots", "tel. ~09.123.45.67~", "match"),
        ("international +32", "internationaal ~+32 470 12 34 56~", "match"),
        ("bridges across two unrelated ID numbers (known collision)",
         "insz 92.02.07-861.02 | 7-82073-73-329 riziv", "no_match_ideally"),
        ("short 4-digit extension (too short)", "toestel 1234 intern", "no_match"),
    ],
    "DATE": [
        ("numeric dd-mm-yyyy", "geboren op ~13/10/2025~", "match"),
        ("written with month name", "consult op ~14 maart 2025~", "match"),
        ("clock time (own sub-pattern)", "afspraak om ~14:30~ uur", "match"),
        ("month/year only", "geldig ~03-2026~", "match"),
        ("zip+city 4-digit not a date (should not match)", "9000 Gent is geen datum", "no_match"),
    ],
    "AGE": [
        ("jaar suffix", "patiënt van ~65 jaar~ oud", "match"),
        ("jarige suffix", "een ~72-jarige~ vrouw", "match"),
        ("jr abbreviation", "leeftijd ~8 jr~", "match"),
        ("bare number, no suffix (should not match)", "kamer 65 bezet", "no_match"),
    ],
    "ZIP_CODE": [
        ("zip followed by capitalized city", "~9000~ Gent, Belgium", "match"),
        ("zip followed by lowercase word (should not match)", "9000 patiënten behandeld", "no_match"),
        ("4-digit year, not zip (ambiguous -- known DATE collision)", "in 2024 Gent bezocht", "match_ideally_no"),
    ],
    "STREET": [
        ("straat suffix", "wonende in de ~Kerkstraat~ 12", "match"),
        ("dreef suffix, multi-word", "adres: ~Vogelzangdreef~ 8", "match"),
        ("lowercase start (should not match, requires capital)", "een straat verderop", "no_match"),
    ],
}


# ZIP_CODE and STREET deliberately use [A-ZÀ-Ý] to require a capital letter
# (that's the whole mechanism distinguishing a proper noun / city name from
# ordinary lowercase text) -- running them case-insensitively silently defeats
# that check. Every other pattern here is digit/symbol-based, where case
# doesn't carry meaning, so IGNORECASE is safe there.
CASE_SENSITIVE_LABELS = {"ZIP_CODE", "STREET"}


def run():
    total = passed = 0
    failures = []
    for label, cases in CASES.items():
        pats = PATTERNS.get(label, [])
        flags = 0 if label in CASE_SENSITIVE_LABELS else re.IGNORECASE
        for name, marked, expect in cases:
            text, exp_start, exp_end = _mark(marked)
            hits = []
            for pname, pat in pats:
                for m in re.finditer(pat, text, flags):
                    hits.append((m.start(), m.end(), pname))
            total += 1
            if expect == "match":
                ok = any(a == exp_start and b == exp_end for a, b, _ in hits)
            elif expect == "no_match":
                ok = len(hits) == 0
            else:
                # documented known-ambiguous cases: report status, don't fail the suite
                ok = True
            status = "PASS" if ok else "FAIL"
            if ok:
                passed += 1
            else:
                failures.append((label, name, text, expect, hits))
            marker = "" if expect in ("match", "no_match") else f"  [informational: {expect}, hits={hits}]"
            print(f"[{status}] {label:12s} {name:55s}{marker}")

    print(f"\n{passed}/{total} strict pass/fail cases passed")
    if failures:
        print("\nFAILURES:")
        for label, name, text, expect, hits in failures:
            print(f"  {label} / {name}: expected {expect}, text={text!r}, regex_hits={hits}")
    return failures


if __name__ == "__main__":
    run()
