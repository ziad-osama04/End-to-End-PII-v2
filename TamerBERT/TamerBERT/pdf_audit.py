#!/usr/bin/env python3
"""
pdf_audit.py -- extraction + normalization diagnostics for AZORG-style clinical letters.

Purpose: surface the character-level and layout-level edge cases that silently
break downstream regex and NER, BEFORE you write any patterns against them.

Headline features
  1. Codepoint audit: every non-ASCII character with its exact U+XXXX value,
     Unicode name, count, and sample contexts. This is what tells you whether
     the birth marker is U+00B0 DEGREE SIGN or U+00BA MASCULINE ORDINAL
     INDICATOR -- they are visually identical and a regex on the wrong one
     silently misses every date of birth.
  2. Ring-glyph disambiguation: classifies each degree-like character as
     BIRTH_MARKER / ANGLE / TEMPERATURE / ORDINAL / UNKNOWN from context.
  3. Font-size profile: pre-masked placeholder spans render smaller than body
     text, so a size histogram labels them automatically.
  4. Wrap-column detection, block classification, padding-gap detection.
  5. Normalization with a full alignment map (original <-> normalized offsets).

Usage
  python3 pdf_audit.py letter.pdf                 # full report to stdout
  python3 pdf_audit.py letter.pdf --json out.json # machine-readable
  python3 pdf_audit.py *.pdf --codepoints-only    # just the character audit

Requires: pymupdf
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from statistics import median

try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("pip install pymupdf")


# ---------------------------------------------------------------------------
# Confusable groups. Each group is a set of codepoints that render alike but
# are distinct characters. Any regex written against one member silently
# misses the others.
# ---------------------------------------------------------------------------

CONFUSABLES = {
    "ring / degree": [
        "\u00B0",  # DEGREE SIGN            <- expected birth marker
        "\u00BA",  # MASCULINE ORDINAL INDICATOR
        "\u02DA",  # RING ABOVE
        "\u2070",  # SUPERSCRIPT ZERO
        "\u1D52",  # MODIFIER LETTER SMALL O
        "\u2218",  # RING OPERATOR
        "\u26AC",  # MEDIUM SMALL WHITE CIRCLE
        "\u2103",  # DEGREE CELSIUS
        "\u2109",  # DEGREE FAHRENHEIT
    ],
    "hyphen / dash": [
        "\u002D",  # HYPHEN-MINUS           <- the one your date regex expects
        "\u2010",  # HYPHEN
        "\u2011",  # NON-BREAKING HYPHEN
        "\u2012",  # FIGURE DASH
        "\u2013",  # EN DASH
        "\u2014",  # EM DASH
        "\u2212",  # MINUS SIGN
        "\uFE63",  # SMALL HYPHEN-MINUS
    ],
    "apostrophe / quote": [
        "\u0027", "\u2018", "\u2019", "\u02BC", "\u00B4", "\u0060",
        "\u0022", "\u201C", "\u201D",
    ],
    "space": [
        "\u0020",  # SPACE
        "\u00A0",  # NO-BREAK SPACE         <- breaks \s+ assumptions
        "\u2007",  # FIGURE SPACE
        "\u2009",  # THIN SPACE
        "\u202F",  # NARROW NO-BREAK SPACE
        "\u200A",  # HAIR SPACE
        "\u3000",  # IDEOGRAPHIC SPACE
    ],
    "invisible": [
        "\u00AD",  # SOFT HYPHEN            <- invisible, splits words
        "\u200B",  # ZERO WIDTH SPACE
        "\u200C", "\u200D", "\uFEFF",
    ],
    "slash": ["\u002F", "\u2044", "\u2215"],
    "digit-lookalike": ["\u0130", "\u01C0", "\u2170", "\u04CF"],
}

RING_CHARS = "".join(CONFUSABLES["ring / degree"])
DASH_CHARS = "".join(CONFUSABLES["hyphen / dash"])
SPACE_CHARS = "".join(CONFUSABLES["space"])

# Dutch/Belgian letters that must survive normalization untouched.
EXPECTED_LATIN = set("àáâäèéêëìíîïòóôöùúûüçñÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÇÑ")


def cp(ch: str) -> str:
    return f"U+{ord(ch):04X}"


def uname(ch: str) -> str:
    try:
        return unicodedata.name(ch)
    except ValueError:
        cat = unicodedata.category(ch)
        return f"<unnamed, category {cat}>"


# ---------------------------------------------------------------------------
# Extraction with geometry
# ---------------------------------------------------------------------------

@dataclass
class Span:
    page: int
    text: str
    size: float
    font: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class Line:
    page: int
    text: str
    y: float
    x0: float
    spans: list = field(default_factory=list)

    @property
    def sizes(self):
        return [s.size for s in self.spans]


def extract(path: Path):
    """Returns (metadata, spans, lines). Never uses pdftotext."""
    doc = fitz.open(path)
    meta = dict(doc.metadata or {})
    meta["page_count"] = doc.page_count
    meta["is_form"] = doc.is_form_pdf
    meta["has_toc"] = bool(doc.get_toc())
    try:
        meta["embedded_files"] = doc.embfile_names()
    except Exception:
        meta["embedded_files"] = []
    # Tagged PDF? If present, the element tree carries original HTML structure.
    try:
        meta["has_struct_tree"] = "/StructTreeRoot" in doc.xref_object(doc.pdf_catalog())
    except Exception:
        meta["has_struct_tree"] = None
    # Scanned or digital? Digital pages have real text; scanned pages have images.
    meta["pages_with_text"] = 0
    meta["pages_with_images"] = 0

    spans, lines = [], []
    for pno in range(doc.page_count):
        page = doc[pno]
        if page.get_text("text").strip():
            meta["pages_with_text"] += 1
        if page.get_images(full=True):
            meta["pages_with_images"] += 1

        d = page.get_text("dict")
        for block in d.get("blocks", []):
            for ln in block.get("lines", []):
                lspans = []
                for sp in ln.get("spans", []):
                    s = Span(
                        page=pno + 1,
                        text=sp["text"],
                        size=round(sp["size"], 2),
                        font=sp["font"],
                        x0=round(sp["bbox"][0], 1), y0=round(sp["bbox"][1], 1),
                        x1=round(sp["bbox"][2], 1), y1=round(sp["bbox"][3], 1),
                    )
                    spans.append(s)
                    lspans.append(s)
                if lspans:
                    lines.append(Line(
                        page=pno + 1,
                        text="".join(s.text for s in lspans),
                        y=round(lspans[0].y0, 1),
                        x0=round(min(s.x0 for s in lspans), 1),
                        spans=lspans,
                    ))
    doc.close()
    return meta, spans, lines


# ---------------------------------------------------------------------------
# 1. Codepoint audit -- the headline diagnostic
# ---------------------------------------------------------------------------

def codepoint_audit(text: str, context: int = 32):
    """Every non-ASCII codepoint with count and sample contexts."""
    counts = Counter(ch for ch in text if ord(ch) > 127)
    samples = defaultdict(list)
    for m in re.finditer(r"[^\x00-\x7F]", text):
        ch = m.group()
        if len(samples[ch]) < 4:
            lo = max(0, m.start() - context)
            hi = min(len(text), m.end() + context)
            snippet = text[lo:hi].replace("\n", "\\n")
            samples[ch].append({"offset": m.start(), "context": snippet})

    rows = []
    for ch, n in counts.most_common():
        rows.append({
            "char": ch,
            "codepoint": cp(ch),
            "name": uname(ch),
            "category": unicodedata.category(ch),
            "count": n,
            "expected_dutch": ch in EXPECTED_LATIN,
            "confusable_group": next(
                (g for g, chars in CONFUSABLES.items() if ch in chars), None
            ),
            "samples": samples[ch],
        })
    return rows


def confusable_collisions(text: str):
    """Which confusable groups have MORE THAN ONE member present.

    This is the actionable finding: if both U+00B0 and U+00BA appear, any
    regex matching only one of them is silently incomplete.
    """
    out = {}
    for group, chars in CONFUSABLES.items():
        present = {c: text.count(c) for c in chars if c in text}
        if len(present) > 1:
            out[group] = {cp(c): {"name": uname(c), "count": n}
                          for c, n in present.items()}
    return out


# ---------------------------------------------------------------------------
# 2. Ring-glyph disambiguation: birth marker vs angle vs temperature
# ---------------------------------------------------------------------------

RING_CLASS = [
    # (name, pattern applied to the window around the ring char)
    ("BIRTH_MARKER",
     re.compile(rf"[{RING_CHARS}]\s?\d{{1,2}}[{DASH_CHARS}/.]\d{{1,2}}[{DASH_CHARS}/.]\d{{2,4}}")),
    ("BIRTH_MARKER_YEAR_ONLY",
     re.compile(rf"[{RING_CHARS}]\s?(?:19|20)\d{{2}}\b")),
    ("TEMPERATURE",
     re.compile(rf"\d+([.,]\d+)?\s?[{RING_CHARS}]\s?[CF]\b")),
    ("ANGLE",
     re.compile(rf"\b(?:as|axis|hoek|flexie|extensie|abductie|rotatie|ROM)\b[^\n]{{0,20}}?\d+\s?[{RING_CHARS}]",
                re.I)),
    ("ANGLE_BARE",
     re.compile(rf"(?<![\d,.])\d{{1,3}}\s?[{RING_CHARS}](?!\s?\d)")),
    ("ORDINAL",
     re.compile(rf"\bn[{RING_CHARS}]\s?\d+", re.I)),
]


def ring_report(text: str, window: int = 60):
    hits = []
    for m in re.finditer(rf"[{RING_CHARS}]", text):
        lo, hi = max(0, m.start() - window), min(len(text), m.end() + window)
        win = text[lo:hi]
        local = text[max(0, m.start() - 12): m.start() + 24]

        label = "UNKNOWN"
        for name, pat in RING_CLASS:
            if pat.search(local) or pat.search(win):
                label = name
                break

        hits.append({
            "offset": m.start(),
            "char": m.group(),
            "codepoint": cp(m.group()),
            "name": uname(m.group()),
            "classification": label,
            "context": win.replace("\n", " | "),
            "is_pii": label.startswith("BIRTH"),
        })
    return hits


# ---------------------------------------------------------------------------
# 3. Font-size profile -> pre-masked placeholder detection
# ---------------------------------------------------------------------------

def font_profile(spans, min_count: int = 3):
    by_size = defaultdict(list)
    for s in spans:
        if s.text.strip():
            by_size[s.size].append(s)

    if not by_size:
        return {"sizes": [], "body_size": None, "candidate_mask_size": None}

    body_size = max(by_size, key=lambda k: sum(len(s.text) for s in by_size[k]))

    rows = []
    for size in sorted(by_size, reverse=True):
        group = by_size[size]
        if len(group) < min_count:
            continue
        texts = [s.text.strip() for s in group if s.text.strip()]
        rows.append({
            "size": size,
            "span_count": len(group),
            "char_count": sum(len(t) for t in texts),
            "is_body": size == body_size,
            "smaller_than_body": size < body_size,
            "fonts": sorted({s.font for s in group}),
            "samples": texts[:8],
        })

    # Placeholder heuristic: smaller than body, and its text looks like a token.
    token_re = re.compile(r"^\[?[A-ZÀ-Ü_]{2,}[ _]?[A-Z]{0,2}\]?$|^X{4,}$|^dr\.\s*\w+$")
    cand = None
    for r in rows:
        if r["smaller_than_body"]:
            hits = sum(bool(token_re.match(t)) for t in r["samples"])
            if hits >= max(1, len(r["samples"]) // 2):
                cand = r["size"]
                break

    return {"sizes": rows, "body_size": body_size, "candidate_mask_size": cand}


def prior_masks(spans, mask_size):
    """Spans rendered at the placeholder size = already masked by a prior tool."""
    if mask_size is None:
        return []
    return [{"page": s.page, "text": s.text.strip(), "size": s.size,
             "bbox": [s.x0, s.y0, s.x1, s.y1]}
            for s in spans if s.size == mask_size and s.text.strip()]


# ---------------------------------------------------------------------------
# 4. Layout diagnostics
# ---------------------------------------------------------------------------

def wrap_profile(lines):
    """Modal character width -> the hard-wrap column of the source buffer."""
    lens = [len(l.text.rstrip()) for l in lines if len(l.text.strip()) > 20]
    if not lens:
        return {"modal_wrap": None, "median_len": None, "histogram": {}}
    hist = Counter(lens)
    # The wrap column is the longest length that recurs; short lines are
    # paragraph ends, not wraps.
    recurring = [L for L, n in hist.items() if n >= 2]
    return {
        "modal_wrap": max(recurring) if recurring else None,
        "median_len": median(lens),
        "max_len": max(lens),
        "histogram": dict(sorted(hist.items())[-12:]),
    }


def classify_blocks(lines):
    """prose | list | table | ruler | header | signature | blank"""
    ruler_re = re.compile(rf"^\s*[{DASH_CHARS}=_~*]{{3,}}\s*$")
    seg_ruler_re = re.compile(rf"^\s*(?:[{DASH_CHARS}]{{2,}}\s+){{2,}}[{DASH_CHARS}]{{2,}}\s*$")
    header_re = re.compile(r"^\s*[A-ZÀ-Ü][\w \-/.()]{1,50}:\s*$")
    bullet_re = re.compile(rf"^\s*(?:[*\u2022]|[{DASH_CHARS}]\s|\d+[.)]\s)")

    out = []
    for i, l in enumerate(lines):
        t = l.text.rstrip()
        toks = t.split()
        numeric = sum(bool(re.fullmatch(r"-?\d+(?:[.,]\d+)?\*?", tk)) for tk in toks)
        ratio = numeric / len(toks) if toks else 0.0

        if not t.strip():
            kind = "blank"
        elif seg_ruler_re.match(t):
            kind = "column_ruler"       # DO NOT STRIP: encodes table columns
        elif ruler_re.match(t):
            kind = "ruler"              # decoration, safe to strip
        elif header_re.match(t):
            kind = "header"
        elif bullet_re.match(t):
            kind = "list"
        elif ratio >= 0.5 and len(toks) >= 3:
            kind = "table_row"
        elif re.match(r"^\s*dr\.\s", t, re.I):
            kind = "signature"
        else:
            kind = "prose"

        out.append({"page": l.page, "index": i, "kind": kind,
                    "numeric_ratio": round(ratio, 2), "x0": l.x0,
                    "len": len(t), "text": t})
    return out


def padding_gaps(lines, min_gap: int = 3):
    """Runs of 2+ spaces inside prose = offset-preservation artifacts.

    The gap width is proportional to the ORIGINAL (unmasked) string length,
    which is itself a re-identification channel.
    """
    out = []
    for l in lines:
        for m in re.finditer(r"\S(\s{%d,})\S" % min_gap, l.text):
            out.append({
                "page": l.page,
                "gap_chars": len(m.group(1)),
                "before": l.text[max(0, m.start() - 30):m.start() + 1],
                "after": l.text[m.end() - 1:m.end() + 30],
            })
    return out


def column_blocks(lines, tol: float = 3.0):
    """x0 clustering: lines sharing a left edge are space-aligned columns.

    These must NOT have their whitespace collapsed.
    """
    buckets = defaultdict(list)
    for l in lines:
        key = round(l.x0 / tol) * tol
        buckets[key].append(l)
    return {k: len(v) for k, v in sorted(buckets.items()) if len(v) >= 3}


# ---------------------------------------------------------------------------
# Extraction-artifact repairs, derived from real extracted seed text
# ---------------------------------------------------------------------------

PAGE_FURNITURE = re.compile(r"\s*Pagina\s+\d+\s*/\s*\d+\s*")


def strip_page_furniture(text: str):
    """Remove "Pagina N/M" -- which lands MID-SENTENCE, not at line ends.

    Observed in the real extractions:
        "Stoelgangspatroon Pagina 1/3 genormaliseerd."
        "M. Biceps caput longum Pagina 1/3 - Normaal voorkomen"
        "elektronisch gevalideerd op Pagina 2/3 28-05-2026"

    The third case splits a DATE. This MUST run before any tokenisation,
    sentence splitting, or NER, or entities are cut in half.
    """
    hits = [(m.start(), m.group().strip()) for m in PAGE_FURNITURE.finditer(text)]
    return PAGE_FURNITURE.sub(" ", text), hits


# "M e t c o l l e g i a l e g roeten" / "M e d e n a mens"
LETTERSPACED = re.compile(
    r"(?:(?<=\s)|^)((?:[A-Za-zÀ-ÿ] ){3,}[A-Za-zÀ-ÿ])(?=\s|$)")


def repair_letterspacing(text: str, lexicon=None):
    """Rejoin PDF letter-spacing artifacts.

    Justified or letter-spaced runs extract as single characters separated by
    spaces. Observed on the closing salutations in every seed letter:

        "M e t c o l l e g i a l e g roeten,"   -> "Met collegiale groeten,"
        "M e d e n a mens"                      -> "Mede namens"

    Note the spacing STOPS MID-WORD ("g roeten"), so the repair must also
    consume the trailing fragment, otherwise you get "groeten roeten".
    Unrepaired, "M e t c o l l e g i a l e" becomes ~13 junk tokens and the
    boilerplate/signature detector never fires.
    """
    lexicon = lexicon or ["Met collegiale hoogachting", "Met collegiale groeten",
                          "Mede namens", "Inhoud van het verslag",
                          "Validatie", "Dit verslag werd door"]
    squash = lambda x: re.sub(r"\s+", "", x).lower()
    out, repairs, pos = [], [], 0

    for m in LETTERSPACED.finditer(text):
        if m.start() < pos:
            continue
        joined = m.group(1).replace(" ", "")
        target, consumed_extra = None, 0
        for phrase in lexicon:
            sq = squash(phrase)
            if not sq.startswith(squash(joined)):
                continue
            remainder = sq[len(squash(joined)):]
            # walk forward through the source, ignoring spaces, until the
            # remaining characters of the phrase are accounted for
            j, got = m.end(), ""
            while j < len(text) and len(got) < len(remainder):
                ch = text[j]
                if not ch.isspace():
                    if ch.lower() != remainder[len(got)]:
                        break
                    got += ch.lower()
                j += 1
            if got == remainder:
                target, consumed_extra = phrase, j - m.end()
                break
        repl = target if target else joined
        out.append(text[pos:m.start()])
        out.append(repl)
        repairs.append({"offset": m.start(),
                        "raw": text[m.start():m.end() + consumed_extra],
                        "repaired": repl})
        pos = m.end() + consumed_extra

    out.append(text[pos:])
    return "".join(out), repairs


# ---------------------------------------------------------------------------
# Glyph-spacing damage: the worst artifact in this corpus
# ---------------------------------------------------------------------------
# The HTML-to-PDF renderer positions glyphs individually in tables and
# justified text. Extractors insert a space wherever the inter-glyph gap
# exceeds a threshold, so whole regions come out as single characters:
#
#     "D A T U M : 2 4 - 0 4 - 2 0 2 6"   <- an ENCOUNTER DATE, unfindable
#     "FVC ( L ) 3 .65 3 .86 1 0 6 0 .34"
#     "G E W ICHT: 63.0 kg B M I: 20.808"
#
# SOME of this is repairable from text alone. Most of the numeric table is
# NOT: "1 0 6 0 .34" is truly "106" then "0.34", and only the x-coordinates
# say where the column boundary falls. Anything that guesses will silently
# merge two measurements into one.
#
# So: repair what is provably safe, FLAG the rest, and fix it upstream by
# extracting with geometry (PyMuPDF spans/rawdict) instead of flat text.

DIGIT_RUN = re.compile(r"(?<![\w.])\d(?:\s+[\d.\-])+(?![\w])")
SPACED_DATE = re.compile(r"(?<![\d\w])(?:\d\s+){1,2}\d\s*[-/.]\s*(?:\d\s*){1,2}\s*[-/.]\s*(?:\d\s*){2,4}(?![\d])")
PAREN_PAD = re.compile(r"\(\s+([^()]{1,12}?)\s+\)")
DEC_GAP = re.compile(r"(?<=\d)\s+(?=\.\d)")


def spacing_damage(text: str, threshold: float = 0.35):
    """Per-line share of single-character tokens. High = glyph-spacing damage."""
    rows = []
    for i, line in enumerate(text.split("\n")):
        toks = line.split()
        if len(toks) < 4:
            continue
        singles = sum(1 for t in toks if len(t) == 1)
        ratio = singles / len(toks)
        if ratio >= threshold:
            rows.append({"line": i, "ratio": round(ratio, 2),
                         "n_tokens": len(toks), "text": line[:90],
                         "numeric_row": sum(bool(re.fullmatch(r"-?[\d.]+\*?", t))
                                            for t in toks) / len(toks) > 0.4})
    return rows


def recover_spaced_dates(text: str):
    """Collapse glyph-spaced dates. SAFE: the result must still parse as a date.

    "D A T U M : 2 4 - 0 4 - 2 0 2 6" -> "D A T U M : 24-04-2026"
    """
    fixed, hits = text, []
    for m in list(SPACED_DATE.finditer(text)):
        cand = re.sub(r"\s+", "", m.group())
        if re.fullmatch(r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", cand):
            hits.append({"raw": m.group(), "repaired": cand})
    for h in hits:
        fixed = fixed.replace(h["raw"], h["repaired"], 1)
    return fixed, hits


def repair_safe_spacing(text: str):
    """Only transformations that cannot merge two distinct values.

    - "( L )"  -> "(L)"          padding inside parentheses
    - "3 .65"  -> "3.65"         a space before a decimal point is never real
    - spaced dates (shape-validated)
    Numeric column runs are deliberately NOT touched.
    """
    out = PAREN_PAD.sub(lambda m: f"({m.group(1).strip()})", text)
    out = DEC_GAP.sub("", out)
    out, dates = recover_spaced_dates(out)
    return out, {"dates_recovered": dates}


def flag_unrecoverable(text: str):
    """Numeric runs that cannot be repaired from characters alone."""
    return [{"offset": m.start(), "text": m.group(),
             "reason": "column boundary needs x-coordinates"}
            for m in DIGIT_RUN.finditer(text)
            if len(re.findall(r"(?<!\S)\d(?!\S)", m.group())) >= 2]


def repair_extraction(text: str):
    """Run both repairs. Returns (text, report)."""
    t, pages = strip_page_furniture(text)
    t, spaced = repair_letterspacing(t)
    t, safe = repair_safe_spacing(t)
    return t, {"page_furniture_removed": pages,
               "letterspacing_repaired": spaced,
               "dates_recovered": safe["dates_recovered"],
               "damaged_lines": spacing_damage(t),
               "unrecoverable": flag_unrecoverable(t)}


# ---------------------------------------------------------------------------
# 5. Normalization with alignment map
# ---------------------------------------------------------------------------

class Aligned:
    """Text plus an offset map back to the original.

    Every edit records (orig_start, orig_end) -> (new_start, new_end) so a
    span predicted on the normalized text can be redacted in the source.
    """

    def __init__(self, text: str):
        self.orig = text
        self.chars = list(text)
        self.map = list(range(len(text)))  # normalized index -> original index

    @property
    def text(self):
        return "".join(self.chars)

    def replace_span(self, start: int, end: int, new: str):
        self.chars[start:end] = list(new)
        src = self.map[start] if start < len(self.map) else (self.map[-1] if self.map else 0)
        self.map[start:end] = [src] * len(new)

    def to_original(self, i: int) -> int:
        return self.map[i] if 0 <= i < len(self.map) else -1

    def span_to_original(self, s: int, e: int):
        return (self.to_original(s), self.to_original(max(s, e - 1)) + 1)


def normalize(text: str, *, fold_confusables: bool = True) -> Aligned:
    """Structural normalization only. Entity surfaces are left untouched.

    fold_confusables=True maps every confusable variant to its canonical form
    so ONE regex works. Set False to keep the raw glyphs for the transformer.
    """
    a = Aligned(text)

    if fold_confusables:
        canon = {}
        for c in CONFUSABLES["space"][1:]:
            canon[c] = " "
        for c in CONFUSABLES["invisible"]:
            canon[c] = ""
        for c in CONFUSABLES["hyphen / dash"][1:]:
            canon[c] = "-"
        for c in CONFUSABLES["apostrophe / quote"][1:6]:
            canon[c] = "'"
        for c in CONFUSABLES["ring / degree"][1:]:
            canon[c] = "\u00B0"          # every ring glyph -> DEGREE SIGN
        for i, ch in enumerate(a.chars):
            if ch in canon:
                a.replace_span(i, i + 1, canon[ch])

    a.chars = list(unicodedata.normalize("NFC", a.text))
    if len(a.chars) != len(a.map):        # NFC changed length; rebuild coarsely
        a.map = (a.map + [a.map[-1]] * len(a.chars))[:len(a.chars)]

    return a


def unwrap_prose(lines_classified, wrap_col):
    """Join hard-wrapped prose lines. Prose blocks only."""
    if not wrap_col:
        return [l["text"] for l in lines_classified]

    out, buf = [], ""
    for l in lines_classified:
        t = l["text"].rstrip()
        if l["kind"] != "prose":
            if buf:
                out.append(buf); buf = ""
            out.append(t)
            continue
        if not buf:
            buf = t
            continue
        prev_open = not re.search(r"[.:;!?]\s*$", buf)
        near_wrap = abs(len(buf) - wrap_col) <= 6
        cont = bool(re.match(r"^[a-zà-ü(]|^\d", t))
        if prev_open and near_wrap and cont:
            buf = buf + " " + t
        else:
            out.append(buf); buf = t
    if buf:
        out.append(buf)
    return out


def compare_extractors(path):
    """Run every available extractor on page 1 and score glyph-spacing damage.

    Use this to find out whether the "D A T U M : 2 4 - 0 4 - 2 0 2 6" damage
    is in the PDF or in the extractor you happened to use.
    """
    results = {}

    # PyMuPDF, span-based (what this script uses)
    try:
        d = fitz.open(path)
        results["pymupdf_text"] = d[0].get_text("text")
        # rawdict gives per-CHARACTER positions -> rebuild with our own threshold
        raw = d[0].get_text("rawdict")
        lines = []
        for b in raw.get("blocks", []):
            for ln in b.get("lines", []):
                buf, prev_x1 = "", None
                for sp in ln.get("spans", []):
                    for ch in sp.get("chars", []):
                        x0, x1 = ch["bbox"][0], ch["bbox"][2]
                        w = x1 - x0
                        if prev_x1 is not None and (x0 - prev_x1) > w * 0.45:
                            buf += " "
                        buf += ch["c"]
                        prev_x1 = x1
                lines.append(buf)
        results["pymupdf_rawdict"] = "\n".join(lines)
        d.close()
    except Exception as e:                                   # noqa: BLE001
        results["pymupdf_text"] = f"<error: {e}>"

    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            for tol in (1.0, 2.0, 3.0):
                results[f"pdfplumber_xtol{tol}"] = (
                    pdf.pages[0].extract_text(x_tolerance=tol) or "")
    except ImportError:
        results["pdfplumber"] = "<not installed: pip install pdfplumber>"
    except Exception as e:                                   # noqa: BLE001
        results["pdfplumber"] = f"<error: {e}>"

    try:
        from pypdf import PdfReader
        results["pypdf"] = PdfReader(path).pages[0].extract_text() or ""
    except ImportError:
        results["pypdf"] = "<not installed: pip install pypdf>"
    except Exception as e:                                   # noqa: BLE001
        results["pypdf"] = f"<error: {e}>"

    import subprocess
    for flag, name in [([], "pdftotext_raw"), (["-layout"], "pdftotext_layout")]:
        try:
            out = subprocess.run(["pdftotext", *flag, "-f", "1", "-l", "1",
                                  str(path), "-"],
                                 capture_output=True, text=True, timeout=30)
            results[name] = out.stdout
        except Exception as e:                               # noqa: BLE001
            results[name] = f"<error: {e}>"

    scored = {}
    for name, text in results.items():
        if text.startswith("<"):
            scored[name] = {"status": text}
            continue
        toks = text.split()
        singles = sum(1 for t in toks if len(t) == 1)
        scored[name] = {
            "chars": len(text),
            "tokens": len(toks),
            "single_char_share": round(singles / max(1, len(toks)), 3),
            "damaged_lines": len(spacing_damage(text)),
            "dates_found": len(re.findall(
                r"(?<!\d)\d{1,2}[-/.]\d{1,2}[-/.](?:19|20)\d{2}(?!\d)", text)),
            "sample": " ".join(text.split())[:110],
        }
    return scored


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_report(path: Path):
    meta, spans, lines = extract(path)
    raw = "\n".join(l.text for l in lines)

    fp = font_profile(spans)
    blocks = classify_blocks(lines)
    wrap = wrap_profile(lines)

    return {
        "file": str(path),
        "metadata": meta,
        "scanned_likely": meta["pages_with_text"] == 0 and meta["pages_with_images"] > 0,
        "codepoints": codepoint_audit(raw),
        "confusable_collisions": confusable_collisions(raw),
        "ring_glyphs": ring_report(raw),
        "font_profile": fp,
        "prior_masks": prior_masks(spans, fp["candidate_mask_size"]),
        "wrap": wrap,
        "block_counts": dict(Counter(b["kind"] for b in blocks)),
        "column_rulers": [b for b in blocks if b["kind"] == "column_ruler"],
        "padding_gaps": padding_gaps(lines),
        "column_blocks": column_blocks(lines),
        "_lines": blocks,
        "_raw": raw,
    }


def print_report(r):
    W = 78
    def hdr(t): print("\n" + "=" * W + f"\n{t}\n" + "=" * W)

    hdr(f"FILE: {r['file']}")
    m = r["metadata"]
    for k in ("producer", "creator", "page_count", "has_struct_tree",
              "embedded_files", "pages_with_text", "pages_with_images"):
        print(f"  {k:20s} {m.get(k)}")
    if r["scanned_likely"]:
        print("  !! NO TEXT LAYER -- likely scanned. OCR corrupts checksum digits.")

    hdr("1. CODEPOINT AUDIT (non-ASCII)")
    if not r["codepoints"]:
        print("  (none -- pure ASCII)")
    for c in r["codepoints"]:
        flag = "" if c["expected_dutch"] else "  <-- CHECK"
        grp = f"  [{c['confusable_group']}]" if c["confusable_group"] else ""
        print(f"  {c['codepoint']}  {c['char']!r:6}  x{c['count']:<4} {c['name']}{grp}{flag}")
        if not c["expected_dutch"]:
            for s in c["samples"][:2]:
                print(f"        @{s['offset']}: ...{s['context']}...")

    hdr("2. CONFUSABLE COLLISIONS  (>1 variant present = regex will miss some)")
    if not r["confusable_collisions"]:
        print("  none -- each confusable group uses a single codepoint")
    for grp, members in r["confusable_collisions"].items():
        print(f"  {grp}:")
        for c, info in members.items():
            print(f"      {c}  x{info['count']:<4} {info['name']}")
        print("      -> your regex character class must include ALL of the above")

    hdr("3. RING GLYPHS  (degree sign / birth marker disambiguation)")
    if not r["ring_glyphs"]:
        print("  none found")
    for h in r["ring_glyphs"]:
        tag = "*** PII ***" if h["is_pii"] else "           "
        print(f"  {tag} {h['codepoint']} {h['classification']:22s} @{h['offset']}")
        print(f"              ...{h['context'].strip()}...")

    hdr("4. FONT PROFILE  (smaller-than-body spans = pre-existing masks)")
    fpr = r["font_profile"]
    print(f"  body size: {fpr['body_size']}   candidate mask size: {fpr['candidate_mask_size']}")
    for s in fpr["sizes"]:
        mark = " <== BODY" if s["is_body"] else (" <== MASK?" if s["size"] == fpr["candidate_mask_size"] else "")
        print(f"    {s['size']:6.2f}pt  spans={s['span_count']:<5} chars={s['char_count']:<6}{mark}")
        print(f"             {s['samples'][:5]}")
    if r["prior_masks"]:
        print(f"\n  {len(r['prior_masks'])} pre-masked spans detected:")
        for p in r["prior_masks"][:15]:
            print(f"    p{p['page']}  {p['text']!r}")

    hdr("5. LAYOUT")
    w = r["wrap"]
    print(f"  modal wrap column : {w['modal_wrap']}  (median line {w['median_len']}, max {w['max_len']})")
    print(f"  block counts      : {r['block_counts']}")
    if r["column_rulers"]:
        print(f"  column rulers     : {len(r['column_rulers'])}  DO NOT STRIP -- encode table columns")
        for cr in r["column_rulers"][:3]:
            print(f"      {cr['text']!r}")
    if r["padding_gaps"]:
        print(f"  padding gaps      : {len(r['padding_gaps'])} (offset-preservation artifacts)")
        for g in r["padding_gaps"][:5]:
            print(f"      {g['gap_chars']:>3} spaces: ...{g['before'].strip()!r} <> {g['after'].strip()!r}...")
    cb = r["column_blocks"]
    if cb:
        print(f"  x0 clusters       : {cb}")
        print("      lines sharing a left edge are space-aligned; do NOT collapse their whitespace")


def _resolve_inputs(raw_args):
    """Expand globs (cmd.exe does not) and warn loudly about unquoted paths."""
    import glob as _glob
    out, missing = [], []
    for a in raw_args:
        s = str(a)
        if any(c in s for c in "*?["):
            hits = [Path(h) for h in sorted(_glob.glob(s))]
            if hits:
                out.extend(hits)
            else:
                missing.append(s)
        elif Path(s).is_dir():
            out.extend(sorted(Path(s).glob("*.pdf")))
        elif Path(s).exists():
            out.append(Path(s))
        else:
            missing.append(s)

    if missing:
        print("\n!! NOT FOUND:", file=sys.stderr)
        for m in missing:
            print(f"     {m}", file=sys.stderr)
        if len(missing) > 1 and not any(c in m for m in missing for c in "*?["):
            print("\n   Several missing paths at once usually means a path containing a", file=sys.stderr)
            print("   SPACE was not quoted. The shell split it into separate arguments.", file=sys.stderr)
            print('   Fix:  python3 pdf_audit.py "C:\\path\\with space.pdf"', file=sys.stderr)
        print(file=sys.stderr)
    return out


def main():
    # Windows consoles default to cp1252 and will raise UnicodeEncodeError on
    # the degree sign, diaeresis, and curly apostrophe this tool exists to find.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdfs", nargs="+")
    ap.add_argument("--json", type=Path, help="write machine-readable report")
    ap.add_argument("--codepoints-only", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="benchmark every available extractor on page 1 "
                         "and score glyph-spacing damage")
    ap.add_argument("--text-out", type=Path, help="write normalized text")
    args = ap.parse_args()

    inputs = _resolve_inputs(args.pdfs)
    if not inputs:
        print("No readable PDFs. Nothing to do.", file=sys.stderr)
        return 2
    print(f"Processing {len(inputs)} file(s): {[p.name for p in inputs]}\n")

    reports = []
    for p in inputs:
        if not p.exists():
            print(f"missing: {p}", file=sys.stderr); continue
        r = build_report(p)
        reports.append(r)

        if args.compare:
            print(f"\n=== EXTRACTOR COMPARISON: {p.name} (page 1) ===")
            print(f"{'extractor':24s} {'tokens':>7} {'1-char':>7} {'damaged':>8} {'dates':>6}")
            print("-" * 78)
            for name, m in compare_extractors(p).items():
                if "status" in m:
                    print(f"  {name:22s} {m['status']}")
                    continue
                flag = "  <-- DAMAGED" if m["single_char_share"] > 0.25 else ""
                print(f"  {name:22s} {m['tokens']:7d} {m['single_char_share']:7.1%} "
                      f"{m['damaged_lines']:8d} {m['dates_found']:6d}{flag}")
                print(f"      {m['sample']}")
            print("\n  Highest 'dates' with lowest '1-char' wins. If they all show damage,")
            print("  it is in the PDF and you need the column-ruler table parser.")
            continue

        if args.codepoints_only:
            print(f"\n=== {p.name} ===")
            for c in r["codepoints"]:
                print(f"  {c['codepoint']}  {c['char']!r:6} x{c['count']:<4} {c['name']}")
            for grp, members in r["confusable_collisions"].items():
                print(f"  COLLISION [{grp}]: {list(members)}")
        else:
            print_report(r)

        if args.text_out:
            a = normalize(r["_raw"], fold_confusables=True)
            joined = unwrap_prose(r["_lines"], r["wrap"]["modal_wrap"])
            out = args.text_out if len(args.pdfs) == 1 else args.text_out.with_stem(
                f"{args.text_out.stem}_{p.stem}")
            out.write_text("\n".join(joined), encoding="utf-8", newline="\n")
            print(f"\n  normalized text -> {out.resolve()}  (alignment map len {len(a.map)})")

    if args.json:
        slim = [{k: v for k, v in r.items() if not k.startswith("_")} for r in reports]
        args.json.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nJSON -> {args.json.resolve()}")

    if not (args.json or args.text_out):
        print("\n(Report printed to stdout only. Use --json / --text-out to save,")
        print(" or append  > report.txt  to capture this text.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
