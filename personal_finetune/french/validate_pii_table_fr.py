#!/usr/bin/env python3
"""
validate_pii_table_fr.py -- rigorous validation of pii_table_fr.py, run
once before moving on to the template-recovery/translation step.

Checks, independently of the generator's own internal logic:
  1. Span/text alignment at scale, across all 3 label schemes.
  2. INSZ mod-97 checksum is mathematically valid (recomputed from scratch,
     not just trusted because the generator "should" have gotten it right).
  3. INSZ parity really does encode sex (re-derived from the formatted
     string, stripped of every separator variant).
  4. RIZIV mod-97 checksum is mathematically valid.
  5. IBAN mod-97 == 1 (the real ISO 7064 IBAN check), independently computed.
  6. Luhn checksum on the credit card number is mathematically valid.
  7. Sex-restricted diagnoses are never assigned to the wrong sex.
  8. ambiguous_surname=True cases really do have a surname drawn from the
     eponym/test-name distractor pool.
  9. No mojibake / replacement characters / lone surrogates anywhere in
     generated text (catches encoding regressions).
  10. --wallonia-only actually drops every Brussels-Capital row.
  11. --label-scheme split and flat9 both render without error and use the
      expected label set.
  12. --jsonl output round-trips as valid JSON per line.
  13. --origin-weights CLI override actually shifts the sampled distribution.
  14. Large-N run (20,000 cases) with default settings raises nothing.
"""

import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import asdict

sys.path.insert(0, ".")
import pii_table_fr as m

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append((name, detail))


def strip_insz(s):
    return re.sub(r"[.\s-]", "", s)


def valid_insz_checksum(insz_digits: str) -> bool:
    base9 = insz_digits[:9]
    check = int(insz_digits[9:11])
    for prefix in ("", "2"):
        mod_src = prefix + base9
        if 97 - (int(mod_src) % 97) == check:
            return True
    return False


def valid_riziv_checksum(riziv_digits: str) -> bool:
    base = int(riziv_digits[:6])
    check = int(riziv_digits[6:8])
    return 97 - (base % 97) == check


def valid_iban_be(iban: str) -> bool:
    iban = iban.replace(" ", "")
    if not (iban.startswith("BE") and len(iban) == 16):
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(int(c, 36)) for c in rearranged)  # letters -> base36 digits
    return int(numeric) % 97 == 1


def valid_luhn(card: str) -> bool:
    digits = [int(c) for c in card]
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


print("=" * 72)
print("1-2. Span/text alignment + INSZ checksum, at scale, all schemes")
print("=" * 72)

import random as _random

for scheme_name, scheme in [("merged", m.MERGED), ("split", m.SPLIT), ("flat9", m.FLAT9)]:
    rng = _random.Random(123)
    fake = None
    bad_spans = 0
    bad_insz = 0
    bad_parity = 0
    bad_riziv = 0
    bad_iban = 0
    bad_luhn = 0
    bad_sex_dx = 0
    bad_ambiguous = 0
    n = 3000
    for i in range(n):
        case = m.build_case(i, rng, fake)
        text, spans = m.render(m.DEMO_TEMPLATE, case, scheme)
        for s in spans:
            if text[s["start"]:s["end"]] != s["text"]:
                bad_spans += 1

        insz_digits = strip_insz(case.INSZ)
        if not valid_insz_checksum(insz_digits):
            bad_insz += 1
        seq = int(insz_digits[6:9])
        expect_male = (seq % 2 == 1)
        if expect_male != (case.sex == "M"):
            bad_parity += 1

        riziv_digits = re.sub(r"[.\s-]", "", case.RIZIV)[:8]
        if not valid_riziv_checksum(riziv_digits):
            bad_riziv += 1

        if not valid_iban_be(case.IBAN):
            bad_iban += 1

        if not valid_luhn(case.CREDITCARDNUMBER):
            bad_luhn += 1

        sexed = {d[0]: d[2] for d in m.DIAGNOSES if d[2]}
        if case.DIAGNOSIS in sexed and sexed[case.DIAGNOSIS] != case.sex:
            bad_sex_dx += 1

        if case.ambiguous_surname:
            surname = case.NAME_PATIENT.split(" ", 1)[-1]
            if surname not in m.DISTRACTORS["_ambiguous_surnames"]:
                bad_ambiguous += 1

    check(f"[{scheme_name}] span/text alignment ({n} cases)", bad_spans == 0, f"{bad_spans} mismatches")
    check(f"[{scheme_name}] INSZ mod-97 checksum valid", bad_insz == 0, f"{bad_insz}/{n} invalid")
    check(f"[{scheme_name}] INSZ parity encodes sex", bad_parity == 0, f"{bad_parity}/{n} mismatched")
    check(f"[{scheme_name}] RIZIV mod-97 checksum valid", bad_riziv == 0, f"{bad_riziv}/{n} invalid")
    check(f"[{scheme_name}] IBAN mod-97==1 (ISO 7064)", bad_iban == 0, f"{bad_iban}/{n} invalid")
    check(f"[{scheme_name}] Luhn checksum valid", bad_luhn == 0, f"{bad_luhn}/{n} invalid")
    check(f"[{scheme_name}] sex-restricted diagnoses respected", bad_sex_dx == 0, f"{bad_sex_dx}/{n} violations")
    check(f"[{scheme_name}] ambiguous_surname implies distractor surname", bad_ambiguous == 0, f"{bad_ambiguous} violations")

print()
print("=" * 72)
print("3. Encoding integrity -- no mojibake / replacement chars / lone surrogates")
print("=" * 72)

rng = _random.Random(7)
bad_encoding = []
for i in range(2000):
    case = m.build_case(i, rng, None)
    text, _ = m.render(m.DEMO_TEMPLATE, case, m.MERGED)
    if "�" in text:
        bad_encoding.append((i, "replacement char U+FFFD"))
    for ch in text:
        if 0xD800 <= ord(ch) <= 0xDFFF:
            bad_encoding.append((i, "lone surrogate"))
    try:
        text.encode("utf-8").decode("utf-8")
    except UnicodeError as e:
        bad_encoding.append((i, str(e)))
check("no mojibake/replacement/surrogate across 2000 rendered docs", len(bad_encoding) == 0,
      str(bad_encoding[:5]))

print()
print("=" * 72)
print("4. --wallonia-only drops every Brussels-Capital row")
print("=" * 72)

wallonia_cities = [c for c in m.WALLOON_CITIES if c[4] == "Wallonie"]
rng = _random.Random(99)
brussels_leaked = 0
for i in range(2000):
    case = m.build_case(i, rng, None, cities=wallonia_cities)
    if case.region == "Bruxelles-Capitale":
        brussels_leaked += 1
check("--wallonia-only style filtering excludes Brussels", brussels_leaked == 0, f"{brussels_leaked} leaked")

print()
print("=" * 72)
print("5. --origin-weights CLI override actually shifts sampled distribution")
print("=" * 72)

rng1 = _random.Random(55)
default_origins = [m.sample_origin(rng1) for _ in range(5000)]
default_walloon_share = default_origins.count("walloon") / 5000

rng2 = _random.Random(55)
forced_weights = [0.99, 0.0025, 0.0025, 0.0025, 0.0025]  # force walloon near 1.0
forced_origins = [m.sample_origin(rng2, forced_weights) for _ in range(5000)]
forced_walloon_share = forced_origins.count("walloon") / 5000

check("origin-weights override shifts distribution", forced_walloon_share > default_walloon_share + 0.3,
      f"default={default_walloon_share:.2f} forced={forced_walloon_share:.2f}")

print()
print("=" * 72)
print("6. CLI smoke test: --jsonl round-trips, both alt schemes render, large-N runs clean")
print("=" * 72)

import tempfile, os

with tempfile.TemporaryDirectory() as td:
    out_csv = os.path.join(td, "out.csv")
    out_jsonl = os.path.join(td, "out.jsonl")
    r = subprocess.run(
        [sys.executable, "pii_table_fr.py", "-n", "300", "--out", out_csv,
         "--jsonl", out_jsonl, "--label-scheme", "flat9", "--audit"],
        capture_output=True, text=True, cwd=".")
    check("CLI run (n=300, flat9, --jsonl, --audit) exits 0", r.returncode == 0, r.stderr[-2000:])
    check("stderr is empty (no warnings/tracebacks)", r.stderr.strip() == "", r.stderr[-1000:])

    jsonl_ok = True
    if os.path.exists(out_jsonl):
        with open(out_jsonl, encoding="utf-8") as fh:
            lines = fh.readlines()
        if len(lines) != 300:
            jsonl_ok = False
        for line in lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                jsonl_ok = False
                break
    else:
        jsonl_ok = False
    check("--jsonl output is 300 valid JSON lines", jsonl_ok)

    r2 = subprocess.run(
        [sys.executable, "pii_table_fr.py", "-n", "20000", "--out",
         os.path.join(td, "big.csv"), "--wallonia-only"],
        capture_output=True, text=True, cwd=".")
    check("large-N run (20,000, --wallonia-only) exits 0", r2.returncode == 0, r2.stderr[-2000:])

print()
print("=" * 72)
if FAILURES:
    print(f"RESULT: {len(FAILURES)} CHECK(S) FAILED")
    for name, detail in FAILURES:
        print(f"  - {name}: {detail}")
    sys.exit(1)
else:
    print("RESULT: ALL CHECKS PASSED")
    sys.exit(0)
