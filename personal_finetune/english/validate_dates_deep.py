#!/usr/bin/env python3
"""
validate_dates_deep.py -- deeper date-specific validation than
validate_consistency_en.py's check 0 (which only proves ordering "by
construction" from the arithmetic, on a 3000-doc sample of train_en.jsonl).

This script instead:
  1. Parses EVERY DATE-labeled span in the FULL (unsampled) train file back
     into a real calendar date against the exact set of format patterns
     fmt_date()/fmt_dob_marker() can produce, and flags any span that fails
     to parse under ANY known format -- this catches formatting-table bugs
     (e.g. an ambiguous month abbreviation), not just arithmetic bugs, and
     catches something validate_all_en.py's span-bounds check cannot see
     (that check only verifies the span's OFFSETS are valid, never that its
     CONTENT is a real, unambiguously-parseable date).
  2. Re-derives DATE_HISTORY < DATE_ENCOUNTER <= DATE_VALIDATION using
     PARSED date objects (not string comparison) across the FULL corpus,
     not a 3000-doc sample.
  3. Cross-checks DOB against the document's actual AGE-labelled span (not
     a naive whole-text word search -- see note on the first, buggy version
     of this check below) for every document: DOB not in the future, and
     the calendar age implied by DOB matches the stated AGE within the
     +/-1 year slack the generator's own "age*365 + randrange(0,365)"
     arithmetic allows.
  4. Repeats 1-3 on the French train file with French month names, and on
     both tracks' AUGMENTED files (post-transform, e.g. after casing/OCR
     noise) to confirm date content survives augmentation in a still-
     parseable form.

REAL BUG FOUND AND FIXED by an earlier draft of this exact script: French's
fmt_date() used a blanket MONTHS[d.month-1][:3] truncation for its
"text_abbr" format, which collapses "juin" (June) and "juillet" (July) to
the IDENTICAL abbreviation "jui" -- a genuine, previously-undiscovered
ambiguity (a date like "15 jui 1978" is unrecoverable between June/July).
Fixed in pii_table_fr.py using the verified real French convention (short
months mars/mai/juin/août stay unabbreviated; juillet -> "juil";
janvier/février need 4 letters -- "janv"/"févr" -- to stay distinct from
each other). English's blanket [:3] has no equivalent collision (Jan
through Dec are already pairwise distinct at 3 letters), so no fix was
needed there.

METHODOLOGY NOTE, since this script's own FIRST draft produced misleading
results before being fixed (the same "validation-methodology false
positive" class already documented in HANDOFF.md as bug 2.5f): a 2-digit
year is genuinely ambiguous in a corpus spanning patient ages 0-95 (a
"31" could be 1931 or 2031) -- a fixed century-pivot heuristic produced
100+ false "future DOB" flags on birth years like "60"/"53" that were
obviously meant as 1960/1953. Fixed by trying both centuries and preferring
whichever is not in the future. Likewise, the first AGE/DOB cross-check
searched the WHOLE document text for any "\\d+ years old"/"\\d+ ans"
pattern rather than anchoring to the real AGE span -- in French this
matched duration phrases having nothing to do with the patient's age
("depuis 10 ans" = "for 10 years"), producing 2,307 bogus "mismatches".
Fixed by reading the actual AGE-labelled span instead.

Usage: run with no arguments; it locates both tracks' train files by
relative path from this file's location.
"""
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
FR_DIR = os.path.join(os.path.dirname(HERE), "french")

# (full names, abbreviations) -- abbreviations must be the REAL ones each
# generator actually produces (see pii_table_{en,fr}.py's fmt_date), not
# re-derived here via a blanket truncation, since that's exactly what
# caused this script's own French false positives on the first pass.
MONTHS_EN = (
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"],
    ["jan", "feb", "mar", "apr", "may", "jun", "jul",
     "aug", "sep", "oct", "nov", "dec"],
)
MONTHS_FR = (
    ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
     "août", "septembre", "octobre", "novembre", "décembre"],
    ["janv", "févr", "mars", "avr", "mai", "juin", "juil",
     "août", "sept", "oct", "nov", "déc"],
)

# Every regex mirrors one of fmt_date()'s / fmt_dob_marker()'s format keys.
NUMERIC_PATTERNS = [
    (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", "d/m/y"),
    (r"^(\d{1,2})-(\d{1,2})-(\d{4})$", "d-m-y"),
    (r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$", "d.m.y"),
    (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", "y-m-d"),
    (r"^(\d{1,2})/(\d{1,2})/(\d{2})$", "d/m/yy"),
    (r"^(\d{1,2})-(\d{1,2})-(\d{2})$", "d-m-yy"),
    (r"^(\d{1,2})\.(\d{1,2})\.(\d{2})$", "d.m.yy"),
    (r"^(\d{8})$", "yyyymmdd"),
    (r"^(\d{6})$", "yymmdd"),
]
PARTIAL_OK_PATTERNS = [
    r"^\d{1,2}/\d{1,2}$", r"^\d{1,2}-\d{1,2}$", r"^\d{1,2}\.\d{1,2}$",
    r"^\d{1,2}/\d{4}$", r"^\d{1,2}\.\d{4}$", r"^\d{4}$",
    r"^\d{4}-\d{1,2}$", r"^\d{4}/\d{1,2}$", r"^\d{4}\.\d{1,2}$",
]
RING_RE = re.compile(r"^[°º]")


def try_parse_full_date(s, months_pair, ref=date(2026, 8, 19)):
    """Return a date() if s is a FULLY-specified (day+month+year) date
    under any known format, else None. Partial dates (month/year only,
    year only) return None -- expected, not an error (fmt_date deliberately
    emits them). Returns the string "INVALID_CALENDAR_DATE" if a format
    matched but the resulting day/month/year isn't a real calendar date."""
    full_names, abbrevs = months_pair
    s = s.strip()
    s = RING_RE.sub("", s)

    for pat, kind in NUMERIC_PATTERNS:
        m = re.match(pat, s)
        if not m:
            continue
        g = m.groups()
        try:
            if kind in ("d/m/y", "d-m-y", "d.m.y"):
                d, mo, y = int(g[0]), int(g[1]), int(g[2])
                return date(y, mo, d)
            elif kind == "y-m-d":
                y, mo, d = int(g[0]), int(g[1]), int(g[2])
                return date(y, mo, d)
            elif kind in ("d/m/yy", "d-m-yy", "d.m.yy"):
                d, mo, yy = int(g[0]), int(g[1]), int(g[2])
            elif kind == "yyyymmdd":
                y, mo, d = int(g[0][:4]), int(g[0][4:6]), int(g[0][6:8])
                return date(y, mo, d)
            elif kind == "yymmdd":
                yy, mo, d = int(g[0][:2]), int(g[0][2:4]), int(g[0][4:6])
        except ValueError:
            return "INVALID_CALENDAR_DATE"

        # 2-digit-year branch: genuinely ambiguous -- try both centuries,
        # prefer whichever is not in the future (see module docstring).
        try:
            cand_2000 = date(2000 + yy, mo, d)
        except ValueError:
            cand_2000 = None
        try:
            cand_1900 = date(1900 + yy, mo, d)
        except ValueError:
            cand_1900 = None
        if cand_2000 is None and cand_1900 is None:
            return "INVALID_CALENDAR_DATE"
        if cand_2000 and cand_2000 <= ref:
            return cand_2000
        if cand_1900:
            return cand_1900
        return cand_2000

    # text_en/text_fr/text_abbr, e.g. "15 May 2026" / "15 mai 2026" /
    # "15 juil 2026". Full names checked before abbreviations, and within
    # each group longest-first, so no shorter form can shadow a longer one.
    low = s.lower()
    candidates = [(name, i) for i, name in enumerate(full_names)]
    candidates += [(ab, i) for i, ab in enumerate(abbrevs)]
    candidates.sort(key=lambda c: -len(c[0]))
    for form, i in candidates:
        m = re.match(rf"^(\d{{1,2}})\s+{re.escape(form)}\.?\s+(\d{{4}})$", low)
        if m:
            try:
                return date(int(m.group(2)), i + 1, int(m.group(1)))
            except ValueError:
                return "INVALID_CALENDAR_DATE"
    return None


def is_recognized_partial(s):
    s = s.strip()
    s = RING_RE.sub("", s)
    return any(re.match(p, s) for p in PARTIAL_OK_PATTERNS)


def check_file(path, months_pair, sample=None):
    n = 0
    unparseable = []
    invalid_calendar = []
    ordering_violations = []
    future_dobs = []
    age_mismatches = []

    with open(path, encoding="utf-8") as f:
        for line in f:
            n += 1
            if sample and n > sample:
                break
            r = json.loads(line)
            text = r["text"]
            by_slot = {}
            age_span_val = None
            for s in r["spans"]:
                slot = s.get("slot")
                label = s.get("label")
                if label == "AGE" and slot in (None, "AGE"):
                    age_span_val = text[s["start"]:s["end"]]
                if label != "DATE":
                    continue
                val = text[s["start"]:s["end"]]
                by_slot.setdefault(slot or label, []).append(val)

            all_date_spans = [v for vals in by_slot.values() for v in vals]
            for val in all_date_spans:
                parsed = try_parse_full_date(val, months_pair)
                if parsed == "INVALID_CALENDAR_DATE":
                    invalid_calendar.append((r.get("id", n), val))
                elif parsed is None and not is_recognized_partial(val):
                    unparseable.append((r.get("id", n), val))

            hist = by_slot.get("DATE_HISTORY", [None])[0]
            enc = by_slot.get("DATE_ENCOUNTER", [None])[0]
            val_ = by_slot.get("DATE_VALIDATION", [None])[0]
            dob = by_slot.get("DOB", [None])[0]

            ph = try_parse_full_date(hist, months_pair) if hist else None
            pe = try_parse_full_date(enc, months_pair) if enc else None
            pv = try_parse_full_date(val_, months_pair) if val_ else None
            pd_ = try_parse_full_date(dob, months_pair) if dob else None

            if isinstance(ph, date) and isinstance(pe, date) and not (ph < pe):
                ordering_violations.append((r.get("id", n), "HIST>=ENC", hist, enc))
            if isinstance(pe, date) and isinstance(pv, date) and not (pe <= pv):
                ordering_violations.append((r.get("id", n), "ENC>VAL", enc, val_))

            if isinstance(pd_, date):
                if pd_ > date(2026, 8, 19):
                    future_dobs.append((r.get("id", n), dob))
                if age_span_val and isinstance(pe, date):
                    digits = "".join(ch for ch in age_span_val if ch.isdigit())
                    if digits:
                        stated_age = int(digits)
                        computed_age = pe.year - pd_.year - ((pe.month, pe.day) < (pd_.month, pd_.day))
                        if abs(computed_age - stated_age) > 1:
                            age_mismatches.append((r.get("id", n), stated_age, computed_age, dob, enc))

    return {
        "n": n, "unparseable": unparseable, "invalid_calendar": invalid_calendar,
        "ordering_violations": ordering_violations, "future_dobs": future_dobs,
        "age_mismatches": age_mismatches,
    }


def report(label, result, expect_corrupted_text=False):
    """expect_corrupted_text=True for augmented files: xf_mojibake/xf_ocr_noise
    deliberately garble date text (that's their entire purpose), so
    'unparseable' there reflects the transform working, not a bug -- only
    the other four checks (which corruption doesn't intentionally break)
    indicate real problems in an augmented file."""
    real_bad = (len(result["invalid_calendar"]) + len(result["ordering_violations"])
                + len(result["future_dobs"]) + len(result["age_mismatches"]))
    total_bad = real_bad + (0 if expect_corrupted_text else len(result["unparseable"]))
    status = "PASS" if total_bad == 0 else "FAIL"
    print(f"--- [{status}] {label} ({result['n']} docs checked) ---")
    note = "  (EXPECTED -- xf_mojibake/xf_ocr_noise deliberately garble date text; " \
           "not a bug, see module docstring)" if expect_corrupted_text else ""
    print(f"  unparseable DATE spans:      {len(result['unparseable'])}{note}")
    for x in result["unparseable"][:10]:
        print(f"    {x}")
    print(f"  invalid-calendar DATE spans: {len(result['invalid_calendar'])}")
    for x in result["invalid_calendar"][:10]:
        print(f"    {x}")
    print(f"  ordering violations:         {len(result['ordering_violations'])}")
    for x in result["ordering_violations"][:10]:
        print(f"    {x}")
    print(f"  future DOBs:                 {len(result['future_dobs'])}")
    for x in result["future_dobs"][:10]:
        print(f"    {x}")
    print(f"  AGE/DOB mismatches (>1yr):   {len(result['age_mismatches'])}")
    for x in result["age_mismatches"][:10]:
        print(f"    {x}")
    print()


def main():
    print("=" * 90)
    print("DEEP DATE VALIDATION -- full corpus, both tracks, parsed-date ordering + AGE/DOB cross-check")
    print("=" * 90)
    print()

    r = check_file(os.path.join(HERE, "train_en.jsonl"), MONTHS_EN)
    report("train_en.jsonl (FULL, 7280 docs)", r)

    r = check_file(os.path.join(HERE, "train_augmented_en.jsonl"), MONTHS_EN)
    report("train_augmented_en.jsonl (FULL, post-transform)", r, expect_corrupted_text=True)

    r = check_file(os.path.join(FR_DIR, "train_fr.jsonl"), MONTHS_FR)
    report("train_fr.jsonl (FULL, 7280 docs)", r)

    r = check_file(os.path.join(FR_DIR, "train_augmented_fr.jsonl"), MONTHS_FR)
    report("train_augmented_fr.jsonl (FULL, post-transform)", r, expect_corrupted_text=True)


if __name__ == "__main__":
    main()
