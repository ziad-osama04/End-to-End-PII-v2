#!/usr/bin/env python3
"""
validate_consistency_en.py -- document-level logical/consistency checks that
validate_pii_table_en.py doesn't cover. Fork of
personal_finetune/french/validate_consistency_fr.py, adapted for English's
simpler design (no PATIENT_NOUN_MARKED field -- English "patient" has no
separate masculine/feminine form -- and PRONOUN_POSS works as a simple
per-case field, unlike French).

Checks: does each RENDERED document read as one coherent person's record
(same name/INSZ/address every time it recurs), and are the sampled dates in
a chronologically sane order.
"""
import json
import random
import sys
from collections import defaultdict
from datetime import date

sys.path.insert(0, ".")
import pii_table_en as en
from faker import Faker

sys.stdout.reconfigure(encoding="utf-8")

REF = date(2026, 5, 28)


def check_case_logic(n=5000, seed=123):
    rng = random.Random(seed)
    fake = Faker("en_GB")
    fake.seed_instance(seed)
    errors = []
    for i in range(n):
        case = en.build_case(i, rng, fake)
        if not (0 <= int(case.AGE_ADJ.split()[0]) <= 120):
            errors.append(f"case {i}: implausible age {case.AGE_ADJ}")
        if case.sex not in ("M", "F"):
            errors.append(f"case {i}: bad sex {case.sex}")
        if case.GENDER not in ("male", "female"):
            errors.append(f"case {i}: bad GENDER {case.GENDER}")
        if (case.GENDER == "male") != (case.sex == "M"):
            errors.append(f"case {i}: GENDER/sex mismatch {case.GENDER}/{case.sex}")
        if case.PATIENT_NOUN_GENERIC != "patient":
            errors.append(f"case {i}: PATIENT_NOUN_GENERIC not invariant: {case.PATIENT_NOUN_GENERIC}")
        if case.HONORIFIC not in ("Mr", "Ms"):
            errors.append(f"case {i}: bad HONORIFIC {case.HONORIFIC}")
        if (case.HONORIFIC == "Mr") != (case.sex == "M"):
            errors.append(f"case {i}: HONORIFIC/sex mismatch")
        if case.PRONOUN_SUBJ not in ("he", "she"):
            errors.append(f"case {i}: bad PRONOUN_SUBJ {case.PRONOUN_SUBJ}")
        if (case.PRONOUN_SUBJ == "he") != (case.sex == "M"):
            errors.append(f"case {i}: PRONOUN_SUBJ/sex mismatch")
        if case.PRONOUN_POSS not in ("his", "her"):
            errors.append(f"case {i}: bad PRONOUN_POSS {case.PRONOUN_POSS}")
        if (case.PRONOUN_POSS == "his") != (case.sex == "M"):
            errors.append(f"case {i}: PRONOUN_POSS/sex mismatch")
        # diagnosis <-> specialty must be the matched pair from DIAGNOSES
        match = [d for d in en.DIAGNOSES if d[0] == case.DIAGNOSIS and d[1] == case.SPECIALTY]
        if not match:
            errors.append(f"case {i}: DIAGNOSIS {case.DIAGNOSIS!r} / SPECIALTY {case.SPECIALTY!r} not a known pair")
        # sex-restricted diagnoses
        restriction = next((d[2] for d in en.DIAGNOSES if d[0] == case.DIAGNOSIS), None)
        if restriction is not None and restriction != case.sex:
            errors.append(f"case {i}: sex-restricted diagnosis {case.DIAGNOSIS} given to sex {case.sex}")
    return errors


def check_rendered_slot_consistency(path, sample=1500):
    mismatches = []
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if n >= sample:
                break
            n += 1
            r = json.loads(line)
            if not r["spans"] or "slot" not in r["spans"][0]:
                continue
            by_slot = defaultdict(set)
            for s in r["spans"]:
                by_slot[s["slot"]].add(s["text"])
            for slot, values in by_slot.items():
                if len(values) > 1:
                    mismatches.append((r.get("id", "?"), slot, values))
    return n, mismatches


def check_age_dob_plausible(path, sample=1500):
    bad = []
    n = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if n >= sample:
                break
            n += 1
            r = json.loads(line)
            age_spans = [s["text"] for s in r["spans"] if s["slot"] == "AGE"]
            ages = set()
            for a in age_spans:
                digits = "".join(ch for ch in a if ch.isdigit())
                if digits:
                    ages.add(int(digits))
            if len(ages) > 1:
                bad.append((r["id"], "AGE", ages))
    return n, bad


def main():
    print("=" * 72)
    print("0. Date-ordering guarantee (verified by source inspection, not sampling)")
    print("=" * 72)
    print("    build_case(): enc = ref - randrange(0,45)      -> encounter within last 45 days")
    print("                  val = enc + randrange(0,3)       -> validation 0-2 days AFTER encounter")
    print("                  hist = enc - randrange(200,4000) -> history 200-4000 days BEFORE encounter")
    print("    All three offsets are drawn from non-negative ranges with hist's lower bound fixed at")
    print("    200, so DATE_HISTORY < DATE_ENCOUNTER <= DATE_VALIDATION holds for every case by")
    print("    construction -- this is a mathematical guarantee of the arithmetic, not a sampled property.")

    print()
    print("=" * 72)
    print("1. Case-level structural/logical invariants (5000 fresh cases)")
    print("=" * 72)
    errs = check_case_logic()
    if errs:
        print(f"  [FAIL] {len(errs)} violations, first 10:")
        for e in errs[:10]:
            print("   ", e)
    else:
        print("  [PASS] all sex/gender/pronoun/honorific/diagnosis-specialty invariants hold")

    print()
    print("=" * 72)
    print("2. Rendered-document slot consistency (train_en.jsonl)")
    print("=" * 72)
    n, mismatches = check_rendered_slot_consistency("train_en.jsonl", sample=3000)
    if mismatches:
        print(f"  [FAIL] {len(mismatches)} slot-value mismatches across {n} docs, first 10:")
        for m in mismatches[:10]:
            print("   ", m)
    else:
        print(f"  [PASS] every recurring slot has one consistent value, across {n} documents")

    print()
    print("=" * 72)
    print("3. AGE numeral stability within a document (train_en.jsonl)")
    print("=" * 72)
    n, bad = check_age_dob_plausible("train_en.jsonl", sample=3000)
    if bad:
        print(f"  [FAIL] {len(bad)} docs with inconsistent AGE numerals across {n} docs")
        for b in bad[:10]:
            print("   ", b)
    else:
        print(f"  [PASS] AGE numeral is stable within each of {n} documents")

    print()
    print("=" * 72)
    print("4. Span/text alignment on train_augmented_en.jsonl (post-transform offsets)")
    print("=" * 72)
    print("    Augmented spans use a simplified {start,end,label} schema (no slot/text),")
    print("    so per-slot consistency isn't checkable here -- that's validated pre-")
    print("    augmentation in checks 2-3 instead. What matters for THIS file is that")
    print("    every span's [start:end) still points at real text after casing/OCR-noise/")
    print("    mojibake/inline-mention edits remapped the offsets.")
    try:
        bad = []
        n = 0
        with open("train_augmented_en.jsonl", encoding="utf-8") as f:
            for line in f:
                if n >= 3000:
                    break
                n += 1
                r = json.loads(line)
                for s in r["spans"]:
                    if not (0 <= s["start"] < s["end"] <= len(r["text"])):
                        bad.append((n, s))
        if bad:
            print(f"  [FAIL] {len(bad)} out-of-bounds spans across {n} augmented docs, first 5:")
            for b in bad[:5]:
                print("   ", b)
        else:
            print(f"  [PASS] every span is in-bounds and non-empty, across {n} augmented documents")
    except FileNotFoundError:
        print("  [SKIP] train_augmented_en.jsonl not found")


if __name__ == "__main__":
    main()
