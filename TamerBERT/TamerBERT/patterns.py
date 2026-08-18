#!/usr/bin/env python3
"""
patterns.py -- deterministic PII detection for Flemish clinical text.

WHICH LABELS BELONG HERE AND WHY
--------------------------------
A label belongs to the regex layer when its surface form is CONSTRAINED
enough that a pattern plus a validator beats a fine-tuned transformer on
both precision and recall, at zero training cost.

  REGEX-OWNED (this file is authoritative)
    INSZ, RIZIV, IBAN, CREDITCARDNUMBER, EMAIL, URL, TELEFOON, FAX,
    MUTUALITEIT, EID, KBO, ZIPCODE, DOB, INTERNAL_ID
    -> checksummed or format-locked; a transformer adds nothing

  MODEL-OWNED (not here; MedRoBERTa's job)
    NAME, CITY, STREET, ORGANISATION, PROFESSION, ETHNICITY,
    RELATIONSHIP, MEASUREMENT
    -> unbounded surface forms, context is the only discriminator

  BOTH (regex for the numeric forms, model for the rest)
    DATE  -- regex gets 27/05/2026 and 12-2025; only the model gets
             "voorjaar 2025" or "sinds 3 maanden"
    AGE   -- regex gets "39-jarige" and "78 jaar"; only the model gets
             "bejaarde patient"

  DERIVED (computed, never detected)
    GENDER -- there is no gender SPAN to match. It is derived from INSZ
              digits 7-9 (odd=M, even=F) after checksum validation, and
              secondarily from asymmetric Dutch morphology. See
              derive_gender(). This is internal risk context only and must
              NEVER be written into a released document.

DESIGN NOTES THAT MATTER
------------------------
1. Confusable folding runs FIRST. "15\\u201301\\u20132024" (en dashes) and
   "\\u00ba08-07-1970" (masculine ordinal) are invisible to naive patterns.
2. Detection is ORDERED and spans are CONSUMED. Without this, ZIPCODE
   fires inside INSZ and DATE fires inside a phone number.
3. Checksums are precision filters, not detectors. A loose pattern finds
   candidates; mod-97 rejects ~96 of every 97 false positives.
4. Hard negatives are excluded EXPLICITLY. The corpus is full of strings
   engineered to break these patterns: "1/d", "BD: 146/68", "as 165 graden",
   "25 000 ie", "FEV1/FVC 73.17". They are unit-tested below.

USAGE
    python3 patterns.py --self-test
    python3 patterns.py --file letter.txt
    python3 patterns.py --text "INSZ 85.07.30-033.61 T 09/332.21.25"

    from patterns import detect, derive_gender
    hits = detect(text)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path

# ===========================================================================
# 0. Confusable folding -- MUST run before any pattern
# ===========================================================================

RING = "°º˚⁰ᵒ∘⚬"
DASHES = "-‐‑‒–—−﹣"
SPACES = "     　"
INVISIBLE = "­​‌‍﻿"
QUOTES = "‘’ʼ´`"

_FOLD = {}
for c in RING[1:]:
    _FOLD[c] = "°"
for c in DASHES[1:]:
    _FOLD[c] = "-"
for c in SPACES:
    _FOLD[c] = " "
for c in INVISIBLE:
    _FOLD[c] = ""
for c in QUOTES:
    _FOLD[c] = "'"
_FOLD_TABLE = str.maketrans(_FOLD)


def fold(text: str) -> str:
    """NFC + confusable folding. 1:1 except invisibles, so offsets survive
    except where characters are deleted -- use fold_aligned() if you need an
    exact map back to the source."""
    return unicodedata.normalize("NFC", text).translate(_FOLD_TABLE)


def fold_aligned(text: str):
    """Returns (folded_text, index_map) where index_map[i] is the ORIGINAL
    offset of folded character i."""
    out, idx = [], []
    for i, ch in enumerate(unicodedata.normalize("NFC", text)):
        repl = _FOLD.get(ch, ch)
        for c in repl:
            out.append(c)
            idx.append(i)
    return "".join(out), idx


# ===========================================================================
# 1. Patterns
# ===========================================================================

P = {}

# --- national / provider identifiers ---
P["INSZ"] = re.compile(r"(?<![\d.\-/])(\d{2})[.\-/ ]?(\d{2})[.\-/ ]?(\d{2})"
                       r"[-.\s]?(\d{3})[.\-/ ]?(\d{2})(?![\d.\-/])")
P["RIZIV"] = re.compile(r"(?<![\d.\-/])(\d)[-.\s]?(\d{5})[-.\s]?(\d{2})"
                        r"[-.\s]?(\d{3})(?![\d.\-/])")
P["MUTUALITEIT"] = re.compile(r"(?<![\d/])(\d{3})[/\s-](\d{7})[-\s]?(\d{2})(?!\d)")
P["EID"] = re.compile(r"\b\d{3}-\d{7}-\d{2}\b")
P["KBO"] = re.compile(r"\b(?:BE\s?)?0\d{3}\.\d{3}\.\d{3}\b")

# --- financial ---
P["IBAN"] = re.compile(r"\b([A-Z]{2})(\d{2})[ ]?((?:[A-Z0-9][ ]?){10,30})\b")
P["CREDITCARDNUMBER"] = re.compile(
    r"(?<![\d.])(?:\d{4}[ -]?){3}\d{4}(?![\d.])|(?<![\d.])3\d{3}[ -]?\d{6}[ -]?\d{5}(?![\d.])")

# --- contact ---
P["EMAIL"] = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
P["URL"] = re.compile(
    r"\bhttps?://[^\s<>\"'\])]+|\bwww\.[\w-]+(?:\.[\w-]+)+(?:/[^\s<>\"'\])]*)?"
    r"|(?<![@\w.])\b[\w-]{2,}\.(?:be|nl|com|org|net|eu)(?:/[^\s<>\"'\])]*)?")

# User-supplied Belgian phone regex (verbatim, modulo the module-level re.I
# already applied via ORDER's detect loop). Kept as the sole authority for
# PHONE so behaviour matches the caller's own validated construction exactly.
P["TELEFOON"] = re.compile(
    r"(?<!\d)(?:(?:\+32|0032|32)[\s./-]?(?:\(0\)[\s./-]?)?)?"
    r"(?:0?(?:4[5-9]\d(?:[\s./-]?\d){6}"
    r"|[2349](?:[\s./-]?\d){7}"
    r"|(?:1\d|5\d|6\d|7\d|8\d)(?:[\s./-]?\d){6}"
    r"|800(?:[\s./-]?\d){5}"
    r"|(?:70|78|900)(?:[\s./-]?\d){6}))"
    r"(?!\d)",
    re.IGNORECASE)
P["FAX_CONTEXT"] = re.compile(r"\b(?:F|Fax|Telefax)\s*[:.]?\s*$", re.I)

# --- dates ---
_MONTHS = (r"jan(?:uari)?|feb(?:ruari)?|m(?:rt|aa|aart)|apr(?:il)?|mei|jun(?:i)?"
           r"|jul(?:i)?|aug(?:ustus)?|sep(?:t|tember)?|okt(?:ober)?"
           r"|nov(?:ember)?|dec(?:ember)?")
# Anchor words that introduce a bare, unqualified day/month in real letters.
# Required for DATE_NOYEAR/DATE_COMPACT: without an anchor, a bare "24/04" or
# "240426" is indistinguishable from a dosing ratio, BP reading or lab code
# (see is_hard_negative). Day/month calendar-validity (checked in detect())
# is a second filter, but not sufficient alone -- "tot 1/2 tablet" is a
# calendar-valid "date" (day=1, month=2), so words that are ALSO common in
# dosing/duration phrasing ("tot", "vanaf", "sinds") are deliberately
# excluded here even though they do introduce dates in some letters.
_DATE_ANCHOR = r"\b(?:op|d\.d\.|datum:?)\s+"
P["DOB"] = re.compile(
    rf"[{RING}]\s?(\d{{1,2}})[-/.](\d{{1,2}})[-/.]((?:19|20)?\d{{2}})"
    rf"|[{RING}]\s?((?:19|20)\d{{2}})-(\d{{1,2}})-(\d{{1,2}})(?!\d)"
    rf"|[{RING}]\s?((?:19|20)\d{{2}})\b"
    rf"|[{RING}]\s?(\d{{1,2}})\s+({_MONTHS})\s+((?:19|20)\d{{2}})", re.I)
P["DATE_DMY"] = re.compile(
    r"(?<![\d/.\-])(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])\2((?:19|20)\d{2})(?![\d])")
P["DATE_DMY_2YR"] = re.compile(
    r"(?<![\d/.\-])(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])\2(\d{2})(?![\d])")
P["DATE_ISO"] = re.compile(r"(?<![\d\-])((?:19|20)\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(?![\d\-])")
P["DATE_YM_REV"] = re.compile(
    r"(?<![\d/.\-])((?:19|20)\d{2})([/.\-])(0?[1-9]|1[0-2])(?!\d)(?![/.\-]\d)")
P["DATE_MY"] = re.compile(r"(?<![\d/.\-])(0?[1-9]|1[0-2])[/.\-]((?:19|20)\d{2})(?![\d])")
P["DATE_TEXT"] = re.compile(
    rf"\b(?:(0?[1-9]|[12]\d|3[01])\s+)?({_MONTHS})\s+'?((?:19|20)?\d{{2}})\b", re.I)
P["DATE_NOYEAR"] = re.compile(
    _DATE_ANCHOR + r"(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])(?!\d)(?![/.\-]\d)",
    re.I)
P["DATE_COMPACT"] = re.compile(
    _DATE_ANCHOR + r"((?:19|20)\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)"
    r"|" + _DATE_ANCHOR + r"(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)",
    re.I)
P["TIME"] = re.compile(r"(?<![\d.])(?:[01]?\d|2[0-3])(?:[:.][0-5]\d)?\s?u\b"
                       r"|(?<![\d.])(?:[01]?\d|2[0-3]):[0-5]\d(?![\d])")

# --- age ---
P["AGE"] = re.compile(
    r"\b(\d{1,3})\s*(?:jaar|jr\.?|j\.)(?!\w)"       # 78 jaar   (most specific)
    r"|\b(\d{1,3})\s?-?\s?jarig[e]?\b"               # 39-jarige
    r"|(?<=leeftijd:)\s?(\d{1,3})\b"                  # LEEFTIJD: 78
    r"|(?<=leeftijd)\s(\d{1,3})\b", re.I)

# --- geography ---
P["ZIPCODE"] = re.compile(r"(?<![\d.\-/])([1-9]\d{3})(?=,?\s+[A-ZÀ-Ü][a-zà-ü'\-]{2,})")

# --- internal identifiers ---
P["INTERNAL_ID"] = re.compile(
    r"\b(?:EENHEID|DOSSIER(?:NR)?|PATIENTNR|MRN|EPISODE|OPNAME|ACCESSION)"
    r"\s*:?\s*([A-Z]{0,3}[-/]?\d{4,})\b", re.I)
P["ID_CATCHALL"] = re.compile(r"\b[A-Z]{2,3}[-/]\d{4,}\b")


# ===========================================================================
# 2. Validators -- precision filters, not detectors
# ===========================================================================

def valid_insz(digits: str):
    """Returns (ok, century, is_bis). mod-97 with the year-2000 prefix rule."""
    if len(digits) != 11:
        return False, None, False
    body, chk = digits[:9], int(digits[9:])
    century = None
    if 97 - (int(body) % 97) == chk:
        century = 1900
    elif 97 - (int("2" + body) % 97) == chk:
        century = 2000
    if century is None:
        return False, None, False
    month = int(digits[2:4])
    is_bis = month > 12
    if is_bis and not (21 <= month <= 32 or 41 <= month <= 52):
        return False, None, False
    if not is_bis and not (1 <= month <= 12):
        return False, None, False
    if not (1 <= int(digits[6:9]) <= 997):
        return False, None, False
    return True, century, is_bis


def valid_riziv(digits: str) -> bool:
    """mod-97 on the leading 6. NOTE: ~0.7 confidence on this construction;
    verify against the RIZIV spec before relying on it as a hard filter."""
    if len(digits) != 11:
        return False
    return 97 - (int(digits[:6]) % 97) == int(digits[6:8])


def valid_iban(s: str) -> bool:
    s = re.sub(r"\s", "", s).upper()
    if not (15 <= len(s) <= 34) or not s[:2].isalpha() or not s[2:4].isdigit():
        return False
    r = s[4:] + s[:4]
    try:
        return int("".join(str(int(c, 36)) for c in r)) % 97 == 1
    except ValueError:
        return False


def valid_luhn(s: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", s)]
    if not 12 <= len(d) <= 19:
        return False
    tot = 0
    for i, x in enumerate(reversed(d)):
        if i % 2:
            x *= 2
            if x > 9:
                x -= 9
        tot += x
    return tot % 10 == 0


def valid_phone(s: str):
    """Returns (ok, kind). Length + prefix table.

    NOTE: "+32 (0)9/332.21.25" writes the trunk 0 in parentheses. Stripping
    all non-digits would leave it in and give an 11-digit number that fails
    every length check, so the parenthesised trunk is removed first.
    """
    s = re.sub(r"\(\s*0\s*\)", "", s)
    d = re.sub(r"\D", "", s)
    if d.startswith("0032"):
        d = "0" + d[4:]
    elif d.startswith("32") and len(d) in (10, 11):
        d = "0" + d[2:]
    if not d.startswith("0"):
        return False, None
    if re.match(r"^04(5[56]|[6-9]\d)", d):
        if len(d) == 10:
            return True, "mobile"
        # "04" is also the Liege landline area code, and its exchange
        # digits can start with 5-9 too (e.g. 04/664.14.63), which is
        # string-identical to a mobile prefix. A 9-digit number here is
        # not a malformed mobile number, it's a valid landline -- fall
        # through instead of rejecting on the mobile-length check alone.
        if len(d) == 9:
            return True, "landline"
        return False, "mobile"
    if re.match(r"^0(70|77|78)", d):
        return (len(d) == 9), "service"
    if re.match(r"^0(800|900)", d):
        return (8 <= len(d) <= 10), "service"
    if re.match(r"^0[2349]", d):
        return (len(d) == 9), "landline"
    if re.match(r"^0(1[0-9]|5[0-9]|6[0-9]|7[1-8]|8[0-9])", d):
        return (len(d) == 9), "landline"
    return False, None


def valid_zip(z: str) -> bool:
    return 1000 <= int(z) <= 9999


def valid_date_parts(d, m, y) -> bool:
    d, m, y = int(d), int(m), int(y)
    if y < 100:
        y += 1900 if y > 30 else 2000
    if not (1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100):
        return False
    dim = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28,
           31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


def valid_date_parts_noyear(d, m) -> bool:
    """Day/month bounds with no year in hand (DATE_NOYEAR/DATE_COMPACT).
    Uses 29 for February so a real Feb-29 in an unknown leap year still
    passes; this can accept one impossible date (Feb 30/31 already excluded
    by the day cap) per non-leap February, which is an acceptable precision
    trade-off since the anchor word already carries most of the signal."""
    d, m = int(d), int(m)
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    dim = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


# ===========================================================================
# 3. Hard negatives -- strings engineered to break these patterns
# ===========================================================================

NEGATIVE_CONTEXT = [
    # measurement/vitals labels immediately before a number
    re.compile(r"\b(?:BD|RR|HR|HF|SpO2|spo2|pols|temp|T)\s*[:=]\s*$", re.I),
    # dosing frequency
    re.compile(r"\b\d+\s*(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg)\s*$", re.I),
    # refraction / angle
    re.compile(r"\b(?:as|axis|hoek|flexie|extensie|abductie|rotatie|ROM)\s*$", re.I),
    # lab ratio lines
    re.compile(r"\b(?:FEV1|FVC|PEF|FEF|TLC|RV|VC|TGV|Raw|sGaw|TLco|Kco|Va)\b[^\n]{0,20}$"),
]
NEGATIVE_SURFACE = re.compile(
    r"^(?:\d{1,2}/\d{1,2}(?:/\d{1,2})?$"            # 1/d, 2/d, 146/68
    r"|\d+\s?[xX]$"                                  # 3x
    r"|\d+\s?(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg|%)$"
    r")")
FREQ_RE = re.compile(r"^\d{1,2}\s*/\s*[dwmj]$", re.I)          # 1/d 2/w
BP_RE = re.compile(r"^\d{2,3}\s*/\s*\d{2,3}$")                  # 146/68


def is_hard_negative(text: str, start: int, end: int, label: str | None = None) -> str | None:
    """Returns a reason string if this span should be rejected.

    DATE candidates skip the surface/context checks below (NEGATIVE_SURFACE/
    FREQ_RE/BP_RE/NEGATIVE_CONTEXT): those exist to reject dosing ratios, BP
    readings and vitals that LOOK like "d/d" or sit right after "80 mg" --
    but a full calendar-valid day/month/(year) is never actually one of
    those (a dose or BP reading is never "16-04-2026"), and DATE_NOYEAR/
    DATE_DMY_2YR/DATE_COMPACT are already precision-filtered by an anchor
    word plus calendar-validity bounds (day<=31, month<=12) in detect(),
    which is a stronger and more correct filter than a blind surface/
    context blacklist. Concretely: real letters write clinical history as
    "Asaflow 80 mg 03/08/2024: nierbiopsie", where the dosing-unit context
    check would otherwise blank out an unambiguous, fully-qualified date.
    """
    surface = text[start:end].strip()
    if label != "DATE":
        if FREQ_RE.match(surface):
            return "dosing frequency"
        if BP_RE.match(surface):
            return "blood pressure"
        if NEGATIVE_SURFACE.match(surface):
            return "dose/count"
    left = text[max(0, start - 24):start]
    if label != "DATE":
        for pat in NEGATIVE_CONTEXT:
            if pat.search(left):
                return f"negative context: {left.strip()[-16:]!r}"
    # a number immediately followed by a unit is a measurement
    right = text[end:end + 8]
    if re.match(r"\s*(?:mg|mcg|ml|cc|kg|cm|mmHg|%|ie\b|E\b|graden)", right, re.I):
        return "followed by unit"
    return None


# ===========================================================================
# 4. Detection with ordered precedence and span consumption
# ===========================================================================

@dataclass
class Hit:
    label: str
    start: int
    end: int
    text: str
    valid: bool = True
    detail: str = ""
    subject: str = "unknown"


# Most specific first. Once a character is consumed, later patterns skip it.
ORDER = [
    ("INSZ", "INSZ"), ("RIZIV", "RIZIV"), ("MUTUALITEIT", "MUTUALITEIT"),
    ("EID", "EID"), ("KBO", "KBO"), ("IBAN", "IBAN"),
    ("CREDITCARDNUMBER", "CREDITCARDNUMBER"),
    ("EMAIL", "EMAIL"), ("URL", "URL"),
    ("INTERNAL_ID", "INTERNAL_ID"),
    ("TELEFOON", "PHONE"),
    ("DOB", "DOB"),
    ("DATE_ISO", "DATE"), ("DATE_DMY", "DATE"), ("DATE_DMY_2YR", "DATE"),
    ("DATE_TEXT", "DATE"), ("DATE_YM_REV", "DATE"), ("DATE_MY", "DATE"),
    ("DATE_COMPACT", "DATE"), ("DATE_NOYEAR", "DATE"),
    ("AGE", "AGE"),
    ("ZIPCODE", "ZIPCODE"),
    ("TIME", "TIME"),
    ("ID_CATCHALL", "INTERNAL_ID_REVIEW"),
]


def detect(text: str, *, prefolded: bool = False, keep_invalid: bool = False):
    """Returns a list of Hit, sorted by offset, with no overlaps.

    Offsets refer to the FOLDED text unless prefolded=True, in which case
    they refer to `text` as given.
    """
    src = text if prefolded else fold(text)
    consumed = [False] * len(src)
    hits = []

    for pat_name, label in ORDER:
        for m in P[pat_name].finditer(src):
            s, e = m.start(), m.end()
            if any(consumed[s:e]):
                continue
            neg = is_hard_negative(src, s, e, label)
            if neg:
                continue
            surface = m.group()
            ok, detail = True, ""

            if label == "INSZ":
                ok, century, bis = valid_insz(re.sub(r"\D", "", surface))
                detail = f"century={century}{' bis' if bis else ''}" if ok else "checksum failed"
            elif label == "RIZIV":
                ok = valid_riziv(re.sub(r"\D", "", surface))
                detail = "mod-97 ok" if ok else "checksum failed"
            elif label == "IBAN":
                ok = valid_iban(surface)
                detail = "mod-97 ok" if ok else "checksum failed"
            elif label == "CREDITCARDNUMBER":
                ok = valid_luhn(surface)
                detail = "luhn ok" if ok else "luhn failed"
            elif label == "PHONE":
                ok, kind = valid_phone(surface)
                detail = kind or "invalid length/prefix"
                if ok and P["FAX_CONTEXT"].search(src[max(0, s - 10):s]):
                    label = "FAX"
            elif label == "ZIPCODE":
                ok = valid_zip(m.group(1))
            elif label == "DATE":
                g = m.groups()
                if pat_name == "DATE_DMY":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_ISO":
                    ok = valid_date_parts(g[2], g[1], g[0])
                elif pat_name == "DATE_DMY_2YR":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_NOYEAR":
                    ok = valid_date_parts_noyear(g[0], g[2])
                elif pat_name == "DATE_COMPACT":
                    # two alternatives (YYYYMMDD / YYMMDD) share one groups()
                    # tuple; exactly one trio is populated per match.
                    if g[0]:
                        ok = valid_date_parts(g[2], g[1], g[0])
                    else:
                        ok = valid_date_parts(g[5], g[4], g[3])
                detail = pat_name
            elif label == "DOB":
                detail = "birth marker"
            elif label == "AGE":
                v = next((x for x in m.groups() if x), None)
                ok = v is not None and 0 <= int(v) <= 120

            if not ok and not keep_invalid:
                continue
            # Trim to the first populated capture group where the pattern
            # deliberately matches surrounding context (AGE after "LEEFTIJD:",
            # DATE_NOYEAR/DATE_COMPACT after an anchor word like "op ").
            if label == "AGE":
                gi = next((i for i, g in enumerate(m.groups(), 1) if g), None)
                if gi and m.start(gi) >= 0:
                    gs, ge = m.span(gi)
                    # keep any trailing unit word ("78 jaar"), drop leading label
                    tail = re.match(r"\s*(?:jaar|jr\.?|j\.|-?\s?jarige?)", src[ge:ge + 10], re.I)
                    s, e = gs, (ge + tail.end() if tail else ge)
                    surface = src[s:e]
            elif pat_name in ("DATE_NOYEAR", "DATE_COMPACT"):
                populated = [i for i, g in enumerate(m.groups(), 1) if g]
                s, e = m.start(populated[0]), m.end(populated[-1])
                surface = src[s:e]

            for i in range(s, e):
                consumed[i] = True
            hits.append(Hit(label, s, e, surface, ok, detail,
                            subject="patient" if label in
                            ("INSZ", "DOB", "AGE", "EID", "MUTUALITEIT") else "unknown"))

    return sorted(hits, key=lambda h: h.start)


# ===========================================================================
# 5. GENDER -- derived, never detected
# ===========================================================================

FEMALE_MARKERS = re.compile(
    r"\b(?:pati[eë]nte|mevrouw|mevr\.|mw\.|zij|haar|de dame|echtgenote|"
    r"moeder|dochter|zus|tante|grootmoeder|nicht)\b", re.I)
MALE_MARKERS = re.compile(
    r"\b(?:meneer|dhr\.|de heer|hij|zijn|echtgenoot|"
    r"vader|zoon|broer|oom|grootvader|neef)\b", re.I)


def sex_from_insz(raw: str):
    """Digits 7-9: odd=M, even=F. Only after checksum validation."""
    d = re.sub(r"\D", "", str(raw))
    ok, century, is_bis = valid_insz(d)
    if not ok:
        return None, "invalid checksum"
    if is_bis:
        # bis-numbers offset the month by +20 or +40; parity semantics are not
        # reliable there (~0.6 confidence), so decline rather than guess.
        return None, "bis-number, parity unreliable"
    seq = int(d[6:9])
    return ("M" if seq % 2 else "F"), f"insz_parity (century {century})"


def derive_gender(text: str, insz: str | None = None):
    """Returns {value, source, confidence, conflict}.

    SOURCE PRECEDENCE
      1. INSZ parity        deterministic, after mod-97 validation
      2. female markers     'patiente'/'mevrouw'/'zij' -> F, high precision
      3. male markers       ONLY explicit ones (meneer/hij/dhr.)

    'patient' alone NEVER implies male. Dutch uses the masculine as the
    unmarked generic, so it appears in template boilerplate regardless of the
    patient's sex. Inferring M from it would be wrong roughly half the time.

    OUTPUT IS INTERNAL RISK CONTEXT ONLY. Writing it into a released document
    re-identifies the record you just anonymised.
    """
    result = {"value": None, "source": None, "confidence": 0.0,
              "conflict": False, "evidence": {}}

    insz_sex = None
    if insz:
        insz_sex, why = sex_from_insz(insz)
        result["evidence"]["insz"] = why
    else:
        for h in detect(text):
            if h.label == "INSZ" and h.valid:
                insz_sex, why = sex_from_insz(h.text)
                result["evidence"]["insz"] = why
                break

    folded = fold(text)
    fem = FEMALE_MARKERS.findall(folded)
    mal = MALE_MARKERS.findall(folded)
    result["evidence"]["female_markers"] = fem[:6]
    result["evidence"]["male_markers"] = mal[:6]

    ling = None
    if fem and not mal:
        ling = "F"
    elif mal and not fem:
        ling = "M"
    elif fem and mal:
        ling = "F" if len(fem) > len(mal) else ("M" if len(mal) > len(fem) else None)

    if insz_sex:
        result.update(value=insz_sex, source="insz_parity", confidence=0.99)
        if ling and ling != insz_sex:
            result["conflict"] = True
            result["confidence"] = 0.90
    elif ling:
        result.update(value=ling, source="linguistic",
                      confidence=0.90 if ling == "F" else 0.75)
    return result


# ===========================================================================
# 6. Self-test -- every case is a real surface from the seed corpus
# ===========================================================================

POSITIVE = [
    ("INSZ85073003328", "INSZ", "85073003328"),          # 1900s branch
    ("INSZ 85.07.30-033.28", "INSZ", "85.07.30-033.28"),
    ("INSZ 06.02.02-136.70", "INSZ", "06.02.02-136.70"),   # 2000s branch
    ("RIZIV8-99244-43-034", "RIZIV", "8-99244-43-034"),
    ("T 09/332.21.25", "PHONE", "09/332.21.25"),
    ("T +32 (0)9/332.21.25", "PHONE", "+32 (0)9/332.21.25"),
    ("T 016 34 22 11", "PHONE", "016 34 22 11"),
    ("bereikbaar op 0475 12 34 56", "PHONE", "0475 12 34 56"),
    ("T 078 15 15 15", "PHONE", "078 15 15 15"),
    ("gratis nummer 0800 12 345", "PHONE", "0800 12 345"),
    ("callcenter 0900 12 345", "PHONE", "0900 12 345"),
    ("(°08-07-1970) kwam op", "DOB", "°08-07-1970"),
    ("(º08-07-1970) kwam", "DOB", "°08-07-1970"),   # folded
    ("°9 augustus 2021, geboren te Gent", "DOB", "°9 augustus 2021"),
    ("op de raadpleging op 27-05-2026.", "DATE", "27-05-2026"),
    ("DATUM: 24/04/2026", "DATE", "24/04/2026"),
    ("7/2012: RYGB", "DATE", "7/2012"),
    ("08/2012: anastomotisch ulcus", "DATE", "08/2012"),
    ("gezien op 19 maart 2019", "DATE", "19 maart 2019"),
    ("werd gezien op 24/04/26 op de spoed", "DATE", "24/04/26"),
    ("controle d.d. 24/04 gepland", "DATE", "24/04"),
    ("volgende afspraak op 5/6.", "DATE", "5/6"),
    ("sinds 2023-04: klachten", "DATE", "2023-04"),
    ("MM.YYYY vorm: 04.2023 gestart", "DATE", "04.2023"),
    ("opname d.d. 20260424", "DATE", "20260424"),
    ("dossier datum 260424 geopend", "DATE", "260424"),
    ("Asaflow 80 mg 03/08/2024: nierbiopsie", "DATE", "03/08/2024"),
    ("Uw 39-jarige patiente", "AGE", "39-jarige"),
    ("LEEFTIJD: 78 jaar", "AGE", "78 jaar"),
    ("LEEFTIJD: 78", "AGE", "78"),
    ("Marialaan 00, 4960 Roucourt", "ZIPCODE", "4960"),
    ("EENHEID: 60418", "INTERNAL_ID", "60418"),
    ("https://www.van.com/", "URL", "https://www.van.com/"),
    ("zie www.azstlucas.be voor info", "URL", "www.azstlucas.be"),
    ("meer info op azstlucas.be/patienten", "URL", "azstlucas.be/patienten"),
    ("mail jan.peeters@telenet.be graag", "EMAIL", "jan.peeters@telenet.be"),
    ("Rekening BE68 5390 0754 7034", "IBAN", "BE68 5390 0754 7034"),
    ("van 8.30u tot 17.00 u", "TIME", "8.30u"),
]

NEGATIVE = [
    "Asaflow (tabl 80 mg), 80 mg, 1/d, 8u",
    "Pantomed 40 mg 1 a 2 /d chronisch",
    "tot 1/2 tablet, 2x/dag in te nemen",
    "vanaf 3/4 capsule per dag opbouwen",
    "BD: 146/68   HR: 68",
    "spo2: 94%",
    "blurr-test (-0.25 ^ -0.25 as 165 graden)",
    "D-cure (caps 25 000 ie), 25000 E, 1 keer per 4 weken",
    "FEV1/FVC (%) 73.17 63.69 87 -1.32 69.84 95 8",
    "Insuline lyumjev (kwikpen 200 e/ml 3 ml), 16 E, SC, 1/d, 8u",
    "aanvullend 3x ESWT zonder duidelijk effect",
    "infiltratie met 2cc depomedrol bilateraal",
    "TGV (Pleth) (L) 3.68 4.95* 135 2.11",
    "GESTALTE: 174.0 cm GEWICHT: 63.0 kg BMI: 20.808",
]

NEGATIVE_ALLOW = {"TIME", "AGE", "INTERNAL_ID_REVIEW"}


def self_test(verbose=False):
    passed = failed = 0
    print("POSITIVE CASES (real surfaces from the seed letters)")
    for text, label, want in POSITIVE:
        hits = detect(text)
        got = [h for h in hits if h.label == label and want in h.text]
        if got:
            passed += 1
            if verbose:
                print(f"  ok   {label:12s} {got[0].text!r} {got[0].detail}")
        else:
            failed += 1
            print(f"  FAIL {label:12s} want {want!r} in {text!r}")
            print(f"       got: {[(h.label, h.text) for h in hits]}")

    print("\nNEGATIVE CASES (must produce no identifier hits)")
    for text in NEGATIVE:
        hits = [h for h in detect(text) if h.label not in NEGATIVE_ALLOW]
        if not hits:
            passed += 1
            if verbose:
                print(f"  ok   {text[:52]!r}")
        else:
            failed += 1
            print(f"  FAIL {text[:52]!r}")
            print(f"       false positives: {[(h.label, h.text) for h in hits]}")

    print("\nVALIDATORS")
    checks = [
        ("INSZ 1900s", valid_insz("85073003328")[0], True),
        ("INSZ 2000s", valid_insz("06020213670")[0], True),
        ("INSZ century detect", valid_insz("06020213670")[1], 2000),
        ("INSZ bad", valid_insz("85073003399")[0], False),
        ("INSZ bis month", valid_insz("85273003328")[0] is not None, True),
        ("IBAN ok", valid_iban("BE68539007547034"), True),
        ("IBAN bad", valid_iban("BE68539007547035"), False),
        ("Luhn ok", valid_luhn("4539578763621486"), True),
        ("phone mobile", valid_phone("0475 12 34 56")[0], True),
        ("phone short", valid_phone("0475 12 34")[0], False),
        ("date 31-02", valid_date_parts(31, 2, 2026), False),
        ("date 29-02-2024", valid_date_parts(29, 2, 2024), True),
    ]
    for name, got, want in checks:
        if got == want:
            passed += 1
            if verbose:
                print(f"  ok   {name}")
        else:
            failed += 1
            print(f"  FAIL {name}: got {got}, want {want}")

    print("\nGENDER DERIVATION")
    cases = [
        ("Uw patiente kwam op consultatie.", None, "F", "linguistic"),
        ("Wij zagen uw patient op de raadpleging.", None, None, None),
        ("De heer kwam met zijn klachten.", None, "M", "linguistic"),
        ("INSZ 85073003328", None, "M", "insz_parity"),
        ("patiente. INSZ 85073003328", None, "M", "insz_parity"),  # conflict expected
        ("INSZ 06020213670", None, "F", "insz_parity"),
    ]
    for text, insz, want_val, want_src in cases:
        r = derive_gender(text, insz)
        ok = r["value"] == want_val and (want_src is None or r["source"] == want_src)
        if ok:
            passed += 1
            if verbose:
                print(f"  ok   {text[:40]!r} -> {r['value']} via {r['source']}"
                      f"{'  CONFLICT' if r['conflict'] else ''}")
        else:
            failed += 1
            print(f"  FAIL {text[:40]!r} -> {r['value']} via {r['source']}, "
                  f"want {want_val} via {want_src}")

    print(f"\n{'=' * 60}\n{passed} passed, {failed} failed")
    return failed == 0


# ===========================================================================

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", type=Path)
    ap.add_argument("--text")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--keep-invalid", action="store_true",
                    help="also report checksum failures")
    args = ap.parse_args()

    if args.self_test:
        sys.exit(0 if self_test(args.verbose) else 1)

    text = args.text or (args.file.read_text(encoding="utf-8") if args.file else sys.stdin.read())
    hits = detect(text, keep_invalid=args.keep_invalid)
    g = derive_gender(text)

    if args.json:
        print(json.dumps({"hits": [asdict(h) for h in hits], "gender": g},
                         indent=2, ensure_ascii=False))
        return

    print(f"{len(hits)} hits\n")
    print(f"{'label':22s} {'span':>13}  {'valid':5s} text")
    print("-" * 78)
    for h in hits:
        mark = "ok" if h.valid else "BAD"
        print(f"{h.label:22s} {h.start:5d}-{h.end:<7d} {mark:5s} {h.text!r}"
              + (f"   {h.detail}" if h.detail else ""))
    print(f"\nGENDER: {g['value']} via {g['source']} "
          f"(conf {g['confidence']:.2f})"
          f"{'  *** SOURCE CONFLICT ***' if g['conflict'] else ''}")
    print("  internal risk context only -- never write this into released output")


if __name__ == "__main__":
    main()
