"""Dutch medical-document PII detection -- the complete inference pipeline.

Combines a fine-tuned MedRoBERTa.nl token-classification model with a
regex/checksum layer for structured Belgian identifiers, merges both into
one set of non-overlapping PII spans per document. This is the exact
detection logic behind every result reported for this model -- extracted
here as a single, dependency-light module with no training/eval/Kaggle
scaffolding, meant to be handed directly to a consuming service.

Labels
------
Model-trained (the model predicts these directly):
    NAME, DATE, PHONE, ADDRESS, ORGANIZATION, AGE
Regex-only (checksum-validated, the model is never trained on these):
    INSZ, RIZIV, URL, EMAIL, BTW_EENHEID
Not produced by this pipeline at all:
    GENDER -- derive it from a detected INSZ's sequence-number parity
    (see backend/src/detection/dutch_regex.py's derive_gender()); there is
    no gender-shaped text span to find in these documents.

Model
-----
    farahelmashad/pii-medroberta-nl-v2               (fp32, ~502MB)
    farahelmashad/pii-medroberta-nl-v2-int8-onnx      (quantized, ~126MB,
                                                        ~1.5x faster on CPU,
                                                        no measurable
                                                        accuracy loss)
Both are public on HF Hub.

Usage (fp32, standard transformers)
------------------------------------
    from transformers import AutoModelForTokenClassification, AutoTokenizer
    from pii_pipeline import detect_pii

    model = AutoModelForTokenClassification.from_pretrained(
        "farahelmashad/pii-medroberta-nl-v2")
    tokenizer = AutoTokenizer.from_pretrained(
        "farahelmashad/pii-medroberta-nl-v2", add_prefix_space=True)

    spans = detect_pii("Patient Jan Janssens, geboren 12-05-1980...", model, tokenizer)
    # -> [{"start": 8, "end": 20, "label": "NAME"}, {"start": 31, "end": 41, "label": "DATE"}, ...]

Usage (quantized, ONNX Runtime) -- see detect_pii_onnx() at the bottom.

Dependencies: transformers, torch, numpy. (onnxruntime only if using the
quantized model via detect_pii_onnx().)
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np

MAX_LEN = 512
STRIDE = 128

# =========================================================================== #
# --- Unicode normalization -- applied before regex matching, never before   #
# --- the model (the model handles raw text fine; the regex patterns below   #
# --- assume ASCII-ish punctuation).                                         #
# =========================================================================== #
RING = "°º˚⁰ᵒ∘⚬"
DASHES = "-‐‑‒–—−﹣"
SPACES = "     　"
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


def fold(text):
    """Normalize degree-sign/dash/space/quote variants and strip invisible
    characters, so the patterns below don't need a dozen character-class
    variants for what is visually the same character."""
    return unicodedata.normalize("NFC", text).translate(_FOLD_TABLE)


# =========================================================================== #
# --- Regex patterns ---------------------------------------------------------#
# =========================================================================== #
P = {}
# Trailing lookahead is (?!\d) only, not (?![\d.\-/]) -- the wider set
# rejected a match whenever a sentence-final "." immediately followed the
# number, the single most common way a number ends in real prose.
P["INSZ"] = re.compile(r"(?<![\d.\-/])(\d{2})[.\-/ ]?(\d{2})[.\-/ ]?(\d{2})"
                       r"[-.\s]?(\d{3})[.\-/ ]?(\d{2})(?!\d)")
P["RIZIV"] = re.compile(r"(?<![\d.\-/])(\d)[-.\s]?(\d{5})[-.\s]?(\d{2})"
                        r"[-.\s]?(\d{3})(?!\d)")
# Belgian VAT / enterprise number (KBO/BCE): "BE" + 10 digits, first digit
# 0 or 1, mod-97 checksum on the last 2 digits vs the first 8.
P["BTW_EENHEID"] = re.compile(
    r"\bBE\s?([01])[.\s]?(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})(?!\d)", re.I)
P["EMAIL"] = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
P["URL"] = re.compile(
    r"\bhttps?://[^\s<>\"'\])]+|\bwww\.[\w-]+(?:\.[\w-]+)+(?:/[^\s<>\"'\])]*)?"
    r"|(?<![@\w.])\b[\w-]{2,}\.(?:be|nl|com|org|net|eu)(?:/[^\s<>\"'\])]*)?")
P["TELEFOON"] = re.compile(
    r"(?<!\d)(?:(?:\+32|0032|32)[\s./-]?(?:\(0\)[\s./-]?)?)?"
    r"(?:0?(?:4[5-9]\d(?:[\s./-]?\d){6}"
    r"|[2349](?:[\s./-]?\d){7}"
    r"|(?:1\d|5\d|6\d|7\d|8\d)(?:[\s./-]?\d){6}"
    r"|800(?:[\s./-]?\d){5}"
    r"|(?:70|78|900)(?:[\s./-]?\d){6}))"
    r"(?!\d)",
    re.IGNORECASE)
_MONTHS = (r"jan(?:uari)?|feb(?:ruari)?|m(?:rt|aa|aart)|apr(?:il)?|mei|jun(?:i)?"
           r"|jul(?:i)?|aug(?:ustus)?|sep(?:t|tember)?|okt(?:ober)?"
           r"|nov(?:ember)?|dec(?:ember)?")
_DATE_ANCHOR = r"\b(?:op|d\.d\.|datum:?)\s+"
# DOB (birth date) is a distinct visual marker in these documents (a ring/
# degree-sign glyph before the date, e.g. "° 12-05-1980") but maps to the
# same DATE label -- the taxonomy has no separate birth-date field.
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
P["DATE_ISO_SLASH"] = re.compile(r"(?<![\d/])((?:19|20)\d{2})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])(?![\d/])")
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
P["AGE"] = re.compile(
    r"\b(\d{1,3})\s*(?:jaar|jr\.?|j\.)(?!\w)"
    r"|\b(\d{1,3})\s?-?\s?jarig[e]?\b"
    r"|(?<=leeftijd:)\s?(\d{1,3})\b"
    r"|(?<=leeftijd)\s(\d{1,3})\b", re.I)


# =========================================================================== #
# --- Checksum / format validators -------------------------------------------#
# =========================================================================== #
def valid_insz(digits):
    """Belgian national register number: mod-97 checksum, tried against
    both 1900s and 2000s century assumptions (the raw digits alone don't
    say which), then sanity-checked month (bis-numbers use month+20/+40 for
    unknown sex/immigrants without a full ID) and sequence number."""
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


def valid_riziv(digits):
    """Healthcare provider number: mod-97 checksum on the first 6 digits
    vs. the next 2 check digits."""
    if len(digits) != 11:
        return False
    return 97 - (int(digits[:6]) % 97) == int(digits[6:8])


def valid_btw(digits):
    """Belgian VAT/enterprise number: mod-97 on the first 8 digits vs. the
    last 2 check digits; first digit must be 0 or 1."""
    if len(digits) != 10 or digits[0] not in "01":
        return False
    return 97 - (int(digits[:8]) % 97) == int(digits[8:])


def valid_phone(s):
    """Belgian phone number format check -- distinguishes mobile/landline/
    service numbers by prefix and enforces the correct digit count for
    each, rather than just "looks like enough digits"."""
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


def valid_date_parts(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if y < 100:
        y += 1900 if y > 30 else 2000
    if not (1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100):
        return False
    dim = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28,
           31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


def valid_date_parts_noyear(d, m):
    d, m = int(d), int(m)
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    dim = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


# =========================================================================== #
# --- Hard-negative rejection ------------------------------------------------#
# --- Keeps AGE/DATE-shaped numbers from firing on dosages, blood-pressure   #
# --- ratios, and lab-value tables -- the single biggest source of regex     #
# --- false positives on real clinical text.                                 #
# =========================================================================== #
NEGATIVE_CONTEXT = [
    re.compile(r"\b(?:BD|RR|HR|HF|SpO2|spo2|pols|temp|T)\s*[:=]\s*$", re.I),
    re.compile(r"\b\d+\s*(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg)\s*$", re.I),
    re.compile(r"\b(?:as|axis|hoek|flexie|extensie|abductie|rotatie|ROM)\s*$", re.I),
    re.compile(r"\b(?:FEV1|FVC|PEF|FEF|TLC|RV|VC|TGV|Raw|sGaw|TLco|Kco|Va)\b[^\n]{0,20}$"),
    # reference-range disclaimer phrasing ("niet gevalideerd/geëxtrapoleerd
    # boven/onder de N jaar") -- the number is a threshold in boilerplate,
    # not a patient's age.
    re.compile(r"\b(?:boven|onder)\s+de\s*$", re.I),
]
NEGATIVE_SURFACE = re.compile(
    r"^(?:\d{1,2}/\d{1,2}(?:/\d{1,2})?$"
    r"|\d+\s?[xX]$"
    r"|\d+\s?(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg|%)$"
    r")")
FREQ_RE = re.compile(r"^\d{1,2}\s*/\s*[dwmj]$", re.I)
BP_RE = re.compile(r"^\d{2,3}\s*/\s*\d{2,3}$")


def is_hard_negative(text, start, end, label=None):
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
    right = text[end:end + 8]
    if re.match(r"\s*(?:mg|mcg|ml|cc|kg|cm|mmHg|%|ie\b|E\b|graden)", right, re.I):
        return "followed by unit"
    return None


# Most specific first; DOB remapped to DATE (the taxonomy has no separate
# birth-date label -- it's scored as DATE).
ORDER = [
    ("INSZ", "INSZ"), ("RIZIV", "RIZIV"), ("BTW_EENHEID", "BTW_EENHEID"),
    ("EMAIL", "EMAIL"), ("URL", "URL"),
    ("TELEFOON", "PHONE"),
    ("DOB", "DATE"),
    ("DATE_ISO", "DATE"), ("DATE_ISO_SLASH", "DATE"), ("DATE_DMY", "DATE"), ("DATE_DMY_2YR", "DATE"),
    ("DATE_TEXT", "DATE"), ("DATE_YM_REV", "DATE"), ("DATE_MY", "DATE"),
    ("DATE_COMPACT", "DATE"), ("DATE_NOYEAR", "DATE"),
    ("AGE", "AGE"),
]


def patterns_detect(text):
    """Run every pattern over `text` (after unicode folding) and return
    validated, non-overlapping (start, end, label) hits, in document
    order. Earlier entries in ORDER consume their matched characters so a
    later, looser pattern can't re-match inside an already-claimed span."""
    src = fold(text)
    consumed = [False] * len(src)
    hits = []
    for pat_name, label in ORDER:
        for m in P[pat_name].finditer(src):
            s, e = m.start(), m.end()
            if any(consumed[s:e]):
                continue
            if is_hard_negative(src, s, e, label):
                continue
            surface = m.group()
            ok = True
            if label == "INSZ":
                ok, _, _ = valid_insz(re.sub(r"\D", "", surface))
            elif label == "RIZIV":
                digits = re.sub(r"\D", "", surface)
                ok = len(digits) == 11 and valid_riziv(digits)
            elif label == "BTW_EENHEID":
                digits = re.sub(r"\D", "", surface)[-10:]  # strip the "BE" letters
                ok = len(digits) == 10 and valid_btw(digits)
            elif label == "PHONE":
                ok, _ = valid_phone(surface)
            elif label == "DATE":
                g = m.groups()
                if pat_name == "DATE_DMY":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_ISO":
                    ok = valid_date_parts(g[2], g[1], g[0])
                elif pat_name == "DATE_ISO_SLASH":
                    ok = valid_date_parts(g[2], g[1], g[0])
                elif pat_name == "DATE_DMY_2YR":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_NOYEAR":
                    ok = valid_date_parts_noyear(g[0], g[2])
                elif pat_name == "DATE_COMPACT":
                    if g[0]:
                        ok = valid_date_parts(g[2], g[1], g[0])
                    else:
                        ok = valid_date_parts(g[5], g[4], g[3])
            elif label == "AGE":
                v = next((x for x in m.groups() if x), None)
                ok = v is not None and 0 <= int(v) <= 120

            if not ok:
                continue
            if label == "AGE":
                gi = next((i for i, g in enumerate(m.groups(), 1) if g), None)
                if gi and m.start(gi) >= 0:
                    gs, ge = m.span(gi)
                    tail = re.match(r"\s*(?:jaar|jr\.?|j\.|-?\s?jarige?)", src[ge:ge + 10], re.I)
                    s, e = gs, (ge + tail.end() if tail else ge)
            elif pat_name in ("DATE_NOYEAR", "DATE_COMPACT"):
                populated = [i for i, g in enumerate(m.groups(), 1) if g]
                s, e = m.start(populated[0]), m.end(populated[-1])
            elif pat_name == "DOB":
                populated = [i for i, g in enumerate(m.groups(), 1) if g]
                s, e = m.start(populated[0]), m.end(populated[-1])

            for i in range(s, e):
                consumed[i] = True
            hits.append((s, e, label))
    return sorted(hits, key=lambda h: h[0])


# =========================================================================== #
# --- Model / regex merge ----------------------------------------------------#
# =========================================================================== #
# AGE/DATE/PHONE are the only labels both the model and regex can produce.
# INSZ/RIZIV/URL/EMAIL/BTW_EENHEID are pure regex (never model-trained).
# NAME/ADDRESS/ORGANIZATION are pure model (no competing regex pattern).
REGEX_PERMANENT_LABELS = ("INSZ", "RIZIV", "URL", "EMAIL", "BTW_EENHEID")
HYBRID_LABELS = {"AGE", "DATE", "PHONE"}
_LABEL_PRIORITY = {"INSZ": 9, "RIZIV": 9, "URL": 10, "EMAIL": 10, "BTW_EENHEID": 9,
                    "DATE": 8, "PHONE": 7, "AGE": 5, "NAME": 4, "ORGANIZATION": 4, "ADDRESS": 6}


def merge_drop_all(model_spans, regex_spans):
    """Regex is excluded entirely for AGE/DATE/PHONE -- the model owns
    those outright (a direct ablation showed naive merging on these three
    actively hurts full-pipeline F1). Overlaps elsewhere are resolved by
    label priority, then span length."""
    filtered_regex = [s for s in regex_spans if s[2] not in HYBRID_LABELS]
    combined = [tuple(s) for s in model_spans] + filtered_regex

    def rank(sp):
        return (_LABEL_PRIORITY.get(sp[2], 1), sp[1] - sp[0])

    covered, kept = set(), []
    for sp in sorted(combined, key=rank, reverse=True):
        span_range = range(sp[0], sp[1])
        if all(i in covered for i in span_range):
            continue
        kept.append(sp)
        covered.update(span_range)
    return sorted(kept, key=lambda s: s[0])


# =========================================================================== #
# --- Model inference: sliding-window tokenization + BIO decode -------------#
# =========================================================================== #
def _tokenize_windows(text, tokenizer):
    tok = tokenizer([text], truncation=True, max_length=MAX_LEN, stride=STRIDE,
                     return_overflowing_tokens=True, return_offsets_mapping=True,
                     padding="max_length", return_tensors=None)
    offset_batch = tok.pop("offset_mapping")
    tok.pop("overflow_to_sample_mapping")
    return tok, offset_batch


def _decode_bio(pred_ids_per_window, offset_batch, id2label):
    """Merge per-window BIO tag predictions back into character-offset
    spans in the ORIGINAL document (windows overlap by STRIDE tokens;
    overlapping span candidates are resolved by keeping the longest)."""
    spans = []
    for ids, offsets in zip(pred_ids_per_window, offset_batch):
        cur_label = cur_start = cur_end = None
        for tok_idx, (a, b) in enumerate(offsets):
            if a == 0 and b == 0:
                lab, prefix = None, None
            else:
                tag = id2label[int(ids[tok_idx])]
                lab = None if tag == "O" else tag[2:]
                prefix = tag[:1] if tag != "O" else None
            if lab is None:
                if cur_label is not None:
                    spans.append((cur_start, cur_end, cur_label))
                    cur_label = None
                continue
            if prefix == "B" or cur_label != lab:
                if cur_label is not None:
                    spans.append((cur_start, cur_end, cur_label))
                cur_label, cur_start, cur_end = lab, a, b
            else:
                cur_end = b
        if cur_label is not None:
            spans.append((cur_start, cur_end, cur_label))

    ents = sorted(spans, key=lambda x: (-(x[1] - x[0]), x[0]))
    kept = []
    for e in ents:
        if any(not (e[1] <= k[0] or e[0] >= k[1]) for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda x: x[0])


def detect_pii(text, model, tokenizer):
    """End-to-end PII detection: model inference + regex layer + merge.

    Parameters
    ----------
    text : str
    model : transformers.AutoModelForTokenClassification (or ORTModelForTokenClassification)
    tokenizer : transformers.AutoTokenizer, loaded with add_prefix_space=True

    Returns
    -------
    list[dict] -- [{"start": int, "end": int, "label": str}, ...], sorted
    by start offset, non-overlapping.
    """
    import torch

    id2label = model.config.id2label
    tok, offset_batch = _tokenize_windows(text, tokenizer)
    with torch.no_grad():
        logits = model(**{k: torch.tensor(v) for k, v in tok.items()}).logits
    pred_ids = logits.argmax(dim=-1).cpu().numpy()

    model_spans = _decode_bio(pred_ids, offset_batch, id2label)
    regex_spans = patterns_detect(text)
    merged = merge_drop_all(model_spans, regex_spans)
    return [{"start": s, "end": e, "label": lab} for s, e, lab in merged]


def detect_pii_onnx(text, onnx_session, tokenizer, id2label):
    """Same pipeline, for the quantized ONNX model via onnxruntime.

    Parameters
    ----------
    text : str
    onnx_session : onnxruntime.InferenceSession, loaded from the exported
        model.onnx (see farahelmashad/pii-medroberta-nl-v2-int8-onnx)
    tokenizer : transformers.AutoTokenizer, loaded with add_prefix_space=True
    id2label : dict[int, str] -- from the ONNX model's config.json
        (`{int(k): v for k, v in config["id2label"].items()}`)
    """
    tok, offset_batch = _tokenize_windows(text, tokenizer)
    onnx_input_names = {i.name for i in onnx_session.get_inputs()}
    batch = {k: np.array(v, dtype=np.int64) for k, v in tok.items() if k in onnx_input_names}
    logits = onnx_session.run(None, batch)[0]
    pred_ids = np.argmax(logits, axis=2)

    model_spans = _decode_bio(pred_ids, offset_batch, id2label)
    regex_spans = patterns_detect(text)
    merged = merge_drop_all(model_spans, regex_spans)
    return [{"start": s, "end": e, "label": lab} for s, e, lab in merged]
