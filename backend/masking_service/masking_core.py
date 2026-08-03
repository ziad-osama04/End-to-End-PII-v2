"""Deterministic PII masking core.

This module is the single source of truth for *how bytes get masked*. It is:

  * Dependency-free  -- only the Python standard library. This guarantees the
    ``regex-poc-1`` model version can always load (it is the model version named
    in the frozen API contract) regardless of whether torch/transformers/spaCy
    are installed.
  * Deterministic    -- the same input bytes + model version always produce the
    same output bytes (contract: "Produce deterministic output for the same
    input and model version"). No randomness, no wall-clock, no ordering by set.
  * Structure-preserving for UTF-8 TXT / CSV / JSON.
  * Self-validating  -- on any masking or output-validation failure it raises
    ``MaskingError`` and never returns the original bytes (contract: "Never
    return the original input when masking or output validation fails").

The heavier fine-tuned MedRoBERTa detector can be registered as an additional,
optional model version (see ``register_medroberta``) without changing this file.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Tuple

# --------------------------------------------------------------------------- #
# Media types
# --------------------------------------------------------------------------- #
TXT = "text/plain"
CSV = "text/csv"
JSON = "application/json"
# PDF is handled outside this dependency-free core (see pdf_masking.py), so it is
# intentionally NOT in SUPPORTED_MEDIA_TYPES, which drives the UTF-8 text path.
PDF = "application/pdf"
SUPPORTED_MEDIA_TYPES = (TXT, CSV, JSON)

MAX_BYTES = 10 * 1024 * 1024  # 10 MiB, per contract


class MaskingError(Exception):
    """Raised when input is malformed or output validation fails (-> HTTP 422)."""


class UnsupportedMediaType(Exception):
    """Raised for a media type outside SUPPORTED_MEDIA_TYPES (-> HTTP 415)."""


# --------------------------------------------------------------------------- #
# Regex PII patterns (deterministic).  Ordered longest/most-specific first so
# that overlap resolution prefers the more specific entity.
# Patterns are adapted from backend/src/detection/dutch_regex.py but applied
# directly (no Presidio/spaCy) to keep this core dependency-free.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class _Pat:
    label: str
    regex: "re.Pattern[str]"


def _compile(patterns: List[Tuple[str, str]]) -> List[_Pat]:
    return [_Pat(label, re.compile(rx)) for label, rx in patterns]


# NOTE: order matters for overlap resolution (see _find_spans). More specific /
# longer identifiers come before generic numeric ones.
_PATTERNS: List[_Pat] = _compile([
    # Structured identifiers ------------------------------------------------- #
    ("EMAIL", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    # IBAN (NL/BE), with or without spacing, generic post-checksum grouping.
    ("IBAN", r"\b(?:NL|BE)\d{2}\s?(?:[A-Z0-9]{4}\s?){2,}[A-Z0-9]{1,4}\b"),
    # Phone before NATIONAL_ID so a +32/+31 number is not mis-tagged as an ID.
    # No leading \b: it fails before a '+'. Use a digit look-behind instead.
    ("PHONE", r"(?<!\d)(?:\+(?:32|31)|0)[\s-]?\d[\s-]?\d{6,8}(?!\d)"),
    ("NATIONAL_ID", r"\b\d{2}[.-]?\d{2}[.-]?\d{2}[- ]?\d{3}[.-]?\d{2}\b"),  # Belgian INSZ
    ("PROVIDER_ID", r"\b\d{1}[-]?\d{5}[-]?\d{2}[-]?\d{3}\b"),               # RIZIV
    ("ADDRESS",
     r"\b[A-Z][a-zA-Zëéèï]+"
     r"(?:\s+[a-zA-Zëéèï]+)*\s*"
     r"(?:straat|laan|weg|plein|dreef|steenweg|baan)\s+\d{1,4}[a-zA-Z]?"
     r"(?:,\s*\d{4}\s+[A-Z][a-zA-Zëéèï]+)?\b"),
    ("HOSPITAL", r"\bAZORG\b"),
    # Quasi-identifiers ------------------------------------------------------ #
    ("BMI", r"\bBMI[\s:]*\d{2}[.,]?\d{0,2}\b"),
    ("DATE", r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b"),
    ("AGE", r"\b\d{1,3}\s*(?:jaar|jr|j\.|-?jarige?)\b"),
    ("HEIGHT", r"\b\d{2,3}\s*(?:cm|meter|m)\b"),
    ("WEIGHT", r"\b\d{2,3}\s*(?:kg|kilo)\b"),
])

# Entity classes the regex-poc-1 masker supports (used by tests + docs).
SUPPORTED_ENTITIES: Tuple[str, ...] = tuple(dict.fromkeys(p.label for p in _PATTERNS))


# --------------------------------------------------------------------------- #
# Core text masking
# --------------------------------------------------------------------------- #
def _find_spans(text: str) -> List[Tuple[int, int, str]]:
    """Return non-overlapping (start, end, label) spans, deterministically.

    All patterns are matched, then overlaps are resolved by a stable rule:
    sort by start ascending, then by span length descending, then by pattern
    order; greedily keep a match only if it does not overlap one already kept.
    """
    candidates: List[Tuple[int, int, int, str]] = []
    for order, pat in enumerate(_PATTERNS):
        for m in pat.regex.finditer(text):
            if m.end() > m.start():
                candidates.append((m.start(), m.end(), order, pat.label))

    # Deterministic priority: earliest start, then longest, then pattern order.
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0]), c[2]))

    kept: List[Tuple[int, int, str]] = []
    last_end = -1
    for start, end, _order, label in candidates:
        if start >= last_end:
            kept.append((start, end, label))
            last_end = end
    return kept


def mask_text(text: str) -> Tuple[str, int]:
    """Mask a single text string. Returns (masked_text, entity_count)."""
    if not text:
        return text, 0
    spans = _find_spans(text)
    if not spans:
        return text, 0
    # Replace right-to-left so earlier indices stay valid.
    out = text
    for start, end, label in sorted(spans, key=lambda s: s[0], reverse=True):
        out = out[:start] + "<" + label + ">" + out[end:]
    return out, len(spans)


# --------------------------------------------------------------------------- #
# Structure-preserving maskers per media type
# --------------------------------------------------------------------------- #
# Type of a text-masking function: str -> (masked_str, entity_count).
TextMasker = Callable[[str], Tuple[str, int]]


def _mask_txt(raw: str, mask_fn: TextMasker) -> Tuple[str, int]:
    return mask_fn(raw)


def _mask_csv(raw: str, mask_fn: TextMasker) -> Tuple[str, int]:
    reader = csv.reader(io.StringIO(raw))
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise MaskingError("csv parse error") from exc

    total = 0
    masked_rows: List[List[str]] = []
    col_counts = set()
    for row in rows:
        col_counts.add(len(row))
        masked_cells = []
        for cell in row:
            masked, n = mask_fn(cell)
            total += n
            masked_cells.append(masked)
        masked_rows.append(masked_cells)

    buf = io.StringIO()
    # lineterminator="\n" keeps output byte-deterministic across platforms.
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerows(masked_rows)
    out = buf.getvalue()

    # Output validation: same number of rows and stable column shape.
    check = list(csv.reader(io.StringIO(out)))
    if len(check) != len(masked_rows):
        raise MaskingError("csv row count changed after masking")
    if col_counts and set(len(r) for r in check) != col_counts:
        raise MaskingError("csv column shape changed after masking")
    return out, total


def _mask_json(raw: str, mask_fn: TextMasker) -> Tuple[str, int]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise MaskingError("json parse error") from exc

    counter = {"n": 0}

    def walk(obj):
        if isinstance(obj, dict):
            # Preserve key order; mask values only, not keys.
            return {k: walk(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [walk(v) for v in obj]
        if isinstance(obj, str):
            masked, n = mask_fn(obj)
            counter["n"] += n
            return masked
        return obj

    masked = walk(data)
    out = json.dumps(masked, ensure_ascii=False, separators=(",", ":"))

    # Output validation: result must still be valid JSON with the same shape.
    reparsed = json.loads(out)
    if _shape(reparsed) != _shape(data):
        raise MaskingError("json structure changed after masking")
    return out, counter["n"]


def _shape(obj):
    """Structural fingerprint that ignores leaf string values (which we mask)."""
    if isinstance(obj, dict):
        return {k: _shape(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_shape(v) for v in obj]
    if isinstance(obj, str):
        return "str"
    return type(obj).__name__


_MEDIA_DISPATCH: Dict[str, Callable[[str, TextMasker], Tuple[str, int]]] = {
    TXT: _mask_txt,
    CSV: _mask_csv,
    JSON: _mask_json,
}


# --------------------------------------------------------------------------- #
# Masker registry (keyed by immutable model version)
# --------------------------------------------------------------------------- #
@dataclass
class MaskResult:
    content: bytes
    entity_count: int
    model_version: str
    sha256: str


class Masker:
    """Base masker: fixed model_version, deterministic byte-in/byte-out.

    Subclasses override ``mask_string`` to change *how* a single text string is
    masked; TXT/CSV/JSON structure preservation and output validation are shared
    here and reused unchanged.
    """

    model_version = "regex-poc-1"

    def mask_string(self, text: str) -> Tuple[str, int]:
        """Mask one text string -> (masked, entity_count). Default: regex."""
        return mask_text(text)

    def detect_spans(self, text: str) -> List[Tuple[int, int, str]]:
        """Return detected PII spans (start, end, label) for evaluation."""
        return _find_spans(text)

    def mask_bytes(self, raw: bytes, media_type: str) -> MaskResult:
        media_type = normalize_media_type(media_type)
        if media_type not in SUPPORTED_MEDIA_TYPES:
            raise UnsupportedMediaType(media_type)
        if not raw:
            raise MaskingError("empty body")
        if len(raw) > MAX_BYTES:
            # Defense in depth; the API layer also enforces this as 413.
            raise MaskingError("body exceeds 10 MiB")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MaskingError("input is not valid UTF-8") from exc

        masked_text, count = _MEDIA_DISPATCH[media_type](text, self.mask_string)

        try:
            out = masked_text.encode("utf-8")
        except UnicodeEncodeError as exc:  # pragma: no cover - defensive
            raise MaskingError("masked output is not valid UTF-8") from exc

        if count < 0:  # pragma: no cover - defensive
            raise MaskingError("negative entity count")

        return MaskResult(
            content=out,
            entity_count=count,
            model_version=self.model_version,
            sha256=hashlib.sha256(out).hexdigest(),
        )


_REGISTRY: Dict[str, Masker] = {}


def register(masker: Masker) -> None:
    _REGISTRY[masker.model_version] = masker


def get_masker(model_version: str) -> Masker:
    try:
        return _REGISTRY[model_version]
    except KeyError as exc:
        raise KeyError(model_version) from exc


def available_versions() -> Tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


# Register the always-available deterministic POC masker.
register(Masker())


def normalize_media_type(value: str) -> str:
    """Strip parameters/charset and lowercase, e.g. 'application/json; charset=utf-8'."""
    if not value:
        return ""
    return value.split(";", 1)[0].strip().lower()
