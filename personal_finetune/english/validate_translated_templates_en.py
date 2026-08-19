# -*- coding: utf-8 -*-
"""
Comprehensive final validation of translated_templates_en.jsonl (all 50
templates merged) -- closes out Phase 4. Mirrors the rigor of the French
track's validation scripts:
  1. Every placeholder is a valid Case field name.
  2. No adjacent-duplicate-placeholder stutters (DX_NUMERIC exempt as a
     pre-existing accepted pattern; NAME_DOCTOR_5 in the one real-letter
     hash with a deliberately-preserved garbled signature block).
  3. No literal-prefix-collides-with-its-own-distractor-pool risk (the
     ATCD/DX_ABBREV bug class) for every DX_* field against its pool.
  4. One-doctor-one-RIZIV rule: at most one NAME_DOCTOR* field pairs with
     {RIZIV} in the template text (checked via a simple heuristic: RIZIV
     should appear at most once per template, matching the source
     convention of a single "NIHDI No." header line).
  5. No literal title ("Dr") glued directly before any NAME_DOCTOR* field.
  6. No hardcoded honorific ("Mr"/"Ms"/"Mrs") directly before {NAME_RELATIVE}.
  7. Full render-test: every template rendered 30 times with different
     seeds, checking span/text alignment and absence of "Dr Dr" stutters.
"""
import json
import re
import sys
import random
import os

sys.path.insert(0, r"D:\Projects\pii-detection\End-to-End-PII-v2\personal_finetune\english")
sys.stdout.reconfigure(encoding="utf-8")
import pii_table_en as en
from faker import Faker

HERE = os.path.dirname(os.path.abspath(__file__))
templates = [json.loads(l) for l in open(os.path.join(HERE, "translated_templates_en.jsonl"), encoding="utf-8")]

VALID_FIELDS = {
    "NAME_PATIENT", "NAME_DOCTOR", "NAME_RESPONSIBLE", "NAME_DOCTOR_2", "NAME_DOCTOR_3",
    "NAME_DOCTOR_4", "NAME_DOCTOR_5", "NAME_DOCTOR_SENDER", "NAME_RELATIVE",
    "RELATIVE_RELATION", "AGE", "AGE_ADJ", "GENDER", "DATE_ENCOUNTER", "DATE_VALIDATION",
    "DATE_HISTORY", "DOB", "INSZ", "RIZIV", "IBAN", "CREDITCARDNUMBER", "STREET",
    "ZIPCODE", "CITY", "TELEFOON", "TELEFOON_MOBILE", "EMAIL", "URL", "ORGANIZATION",
    "SPECIALTY", "DIAGNOSIS", "DX_EPONYM", "DX_TEST", "DX_ANATOMY", "DX_DRUG",
    "DX_DRUG_2", "DX_HOMOGRAPH", "DX_NUMERIC", "DX_NUMERIC_2", "DX_NUMERIC_3",
    "DX_NUMERIC_4", "DX_NUMERIC_5", "DX_NUMERIC_6", "DX_NUMERIC_7", "DX_NUMERIC_8",
    "DX_NUMERIC_9", "DX_ABBREV", "DX_CODESWITCH", "DX_CNK", "DX_CNK_2", "DX_BELAC",
    "PATIENT_NOUN_GENERIC", "HONORIFIC", "PRONOUN_SUBJ", "PRONOUN_POSS",
    "INSZ_LABEL", "RIZIV_LABEL",
}
DOCTOR_FIELDS = ["NAME_DOCTOR", "NAME_DOCTOR_2", "NAME_DOCTOR_3", "NAME_DOCTOR_4",
                  "NAME_DOCTOR_5", "NAME_DOCTOR_SENDER", "NAME_RESPONSIBLE"]
POOL_MAP = {
    "DX_ABBREV": "abbreviation", "DX_EPONYM": "eponym_disease",
    "DX_TEST": "eponym_test", "DX_ANATOMY": "anatomy_latin",
    "DX_DRUG": "drug_brand", "DX_DRUG_2": "drug_brand",
    "DX_HOMOGRAPH": "municipality_homograph",
    "DX_CODESWITCH": "code_switch", "DX_NUMERIC": "numeric_lookalike",
}
PLACEHOLDER_RE = re.compile(r"\{([A-Z0-9_]+)\}")
HONORIFIC_WORDS = ["Mr", "Ms", "Mrs"]

errors = []
seen_hashes = set()

for t in templates:
    h = t["template_hash"]
    text = t["masked_text_en"]
    if h in seen_hashes:
        errors.append(f"{h}: DUPLICATE hash")
    seen_hashes.add(h)

    # 1. valid fields
    fields_used = set(PLACEHOLDER_RE.findall(text))
    invalid = fields_used - VALID_FIELDS
    if invalid:
        errors.append(f"{h}: invalid placeholder fields {invalid}")

    # 2. adjacent stutters (with documented exemptions)
    exempt = {"DX_NUMERIC"}
    if h == "a733c617b8ae2b93":
        exempt |= {"NAME_DOCTOR_5"}
    for m in re.finditer(r"\{([A-Z0-9_]+)\}([ ,]*)\{\1\}", text):
        if m.group(1) not in exempt:
            errors.append(f"{h}: adjacent duplicate placeholder {{{m.group(1)}}}")

    # 3. literal-prefix-collision risk against each field's own pool
    for m in re.finditer(r"(\S+)\s*\{(DX_\w+)\}", text):
        literal, field = m.group(1), m.group(2)
        pool_key = POOL_MAP.get(field)
        if pool_key:
            cleaned = literal.strip(".,!:;\u2013-")
            if cleaned in en.DISTRACTORS.get(pool_key, []):
                errors.append(f"{h}: COLLISION RISK literal '{literal}' before {{{field}}} "
                               f"also in DISTRACTORS['{pool_key}']")

    # 4. one-doctor-one-RIZIV: RIZIV should appear at most once
    riziv_count = text.count("{RIZIV}")
    if riziv_count > 1:
        errors.append(f"{h}: {{RIZIV}} appears {riziv_count} times, expected at most 1")
    insz_count = text.count("{INSZ}")
    if insz_count > 1:
        errors.append(f"{h}: {{INSZ}} appears {insz_count} times, expected at most 1")

    # 5. no literal "Dr" glued before a doctor field
    for field in DOCTOR_FIELDS:
        if re.search(r"\bDr\.?\s*\{" + field + r"\}", text):
            errors.append(f"{h}: literal 'Dr' before {{{field}}} (double-title risk)")

    # 6. no hardcoded honorific before NAME_RELATIVE
    for w in HONORIFIC_WORDS:
        if re.search(re.escape(w) + r"\.?\s*\{NAME_RELATIVE\}", text):
            errors.append(f"{h}: hardcoded honorific '{w}' before {{NAME_RELATIVE}}")

print(f"Static checks: {len(templates)} templates, {len(seen_hashes)} unique hashes, {len(errors)} errors")
for e in errors:
    print(f"  [FAIL] {e}")

# 7. full render-test, 30 seeds per template
print(f"\nRunning render-test (30 seeds x {len(templates)} templates)...")
rng = random.Random(2026)
fake = Faker("en_GB"); fake.seed_instance(2026)
render_errors = 0
for t in templates:
    for i in range(30):
        case = en.build_case(i, rng, fake, cities=en.BELGIAN_CITIES)
        text, spans = en.render(t["masked_text_en"], case, scheme=en.MERGED)
        bad = [s for s in spans if text[s["start"]:s["end"]] != s["text"]]
        if bad:
            print(f"  [FAIL] {t['template_hash']} seed{i}: MISALIGNED {bad[:2]}")
            render_errors += 1
        if "Dr Dr" in text:
            print(f"  [FAIL] {t['template_hash']} seed{i}: DOUBLE TITLE")
            render_errors += 1

total_renders = len(templates) * 30
print(f"\nRender-test: {total_renders} renders, {render_errors} errors")

grand_total = len(errors) + render_errors
print(f"\n{'='*60}\nGRAND TOTAL ERRORS: {grand_total}\n{'='*60}")
if grand_total == 0:
    print(f"[PASS] translated_templates_en.jsonl is fully validated: {len(templates)}/{len(templates)} templates, 0 errors.")
