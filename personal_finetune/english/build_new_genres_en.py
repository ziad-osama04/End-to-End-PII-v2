# -*- coding: utf-8 -*-
"""
build_new_genres_en.py -- the 6 non-letter document GENRES, direct port of
personal_finetune/french/build_new_genres_fr.py +
personal_finetune/french/build_new_genres_fr_v2.py (built together here,
from round 1, per the plan's Phase 7 -- French only reached this full set
across two separate build passes; the OOD-ceiling-is-structural-diversity
lesson is already known, so there's no reason to defer any of the six):

  - genre_lab_report_en:      hematology/biochemistry results table.
  - genre_pharmacy_en:        pharmacy dispensing record (CNK codes).
  - genre_radiology_en:       Indication -> Technique -> Result -> Conclusion,
                               the confirmed (order-flexible) mandatory
                               skeleton for Belgian radiology reports.
  - genre_sick_note_en:       certificate of incapacity for work, modelled on
                               the real two-part INAMI/RIZIV form (Part 1
                               patient declaration / Part 2 "MEDICAL
                               CONFIDENTIAL" physician section).
  - genre_prescription_en:    proof of electronic prescription (Recip-e).
  - genre_discharge_meds_en:  discharge medication schema (full-regimen
                               carry-forward table).

Label-text convention carried over unchanged from the 50 translated letter
templates (see translated_templates_en.jsonl): every occurrence of {INSZ}/
{RIZIV} is immediately preceded by {INSZ_LABEL}/{RIZIV_LABEL} -- Case fields
sampled per-render from LABEL_POOL_INSZ/LABEL_POOL_RIZIV in pii_table_en.py,
not a hardcoded literal. This is the root fix for the INSZ positional-
rigidity issue validate_diversity_en.py flagged (originally 100% of
templates hardcoded the identical "National Registration No." with zero
variation) -- baking the variety into every render from generation, rather
than patching a fraction of documents afterward via augmentation.

Confidence notes mirror French's: the lab/pharmacy tabular formats and the
radiology four-section skeleton and the two-part sick-note structure are
HIGH CONFIDENCE (regulatory / public reference material, English official
terms researched in Phase 2 -- NIHDI, National Registration No.). Exact
prescription-sheet field wording and discharge-schema column layout are
MEDIUM CONFIDENCE (regulatory concept confirmed, exact layout inferred).

Bug classes proactively avoided from round 1 (all previously found LATE in
the French build, per the plan's Phase-7 instruction not to wait for a
"later round" to catch them again):
  - one-doctor-one-ID rule: only ONE physician per template carries {RIZIV}.
  - literal-prefix-collides-with-own-pool ("ATCD {DX_ABBREV}" class): the
    English DX_ABBREV pool is {PMHx, NAD, Rx, Hx, Dx, Tx, FHx, WNL, NKDA,
    c/o, o/e} -- so DX_ABBREV is always used standalone ("{DX_ABBREV}."),
    never after a hardcoded prefix like "Hx:" or "PMHx" that the pool
    itself could echo.
  - double-title ("Dr {NAME_DOCTOR}"): NAME_DOCTOR already renders as
    "Dr Surname" (see pii_table_en.py build_case), so every reference below
    is bare {NAME_DOCTOR}, never "Dr {NAME_DOCTOR}".
  - distinct-per-cell-value rule (DX_NUMERIC_2..9 class): every table row
    below uses a DIFFERENT DX_NUMERIC_n / indication field per row, never
    repeating one filler value across cells.
"""
import json

TEMPLATES = [
{
"template_hash": "genre_lab_report_en",
"letter_type": "laboratory_report",
"specialty": "",
"masked_text_en": """CLINICAL LABORATORY

{ORGANIZATION}
{STREET}
T {TELEFOON}

Patient: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}
Date of birth: {DOB}

Requesting physician: {NAME_DOCTOR}
{RIZIV_LABEL}{RIZIV}

Collected: {DATE_HISTORY}
Received: {DATE_ENCOUNTER}
Report: {DATE_VALIDATION}

HAEMATOLOGY

| Parameter | Result | Unit | Reference range |
|---|---|---|---|
| Haemoglobin | {DX_NUMERIC} | g/dL | 12.0-16.0 |
| Leukocytes | {DX_NUMERIC_2} | x10(9)/L | 4.0-10.0 |
| Platelets | {DX_NUMERIC_3} | x10(9)/L | 150-400 |
| ESR | {DX_NUMERIC_4} | mm/h | <20 |

BIOCHEMISTRY

| Parameter | Result | Unit | Reference range |
|---|---|---|---|
| Creatinine | {DX_NUMERIC_5} | umol/L | 60-110 |
| CRP | {DX_NUMERIC_6} | mg/L | <5 |
| Fasting glucose | {DX_NUMERIC_7} | mg/dL | 70-110 |
| AST | {DX_NUMERIC_8} | U/L | <40 |
| ALT | {DX_NUMERIC_9} | U/L | <41 |
| {DX_EPONYM} | {DX_ABBREV} | - | {DX_HOMOGRAPH} |

Biologist's comment: profile consistent with {DIAGNOSIS}. {DX_ABBREV}.
{DX_CODESWITCH}. Clinical correlation advised if symptoms persist.

Validated electronically on {DATE_VALIDATION} by {NAME_DOCTOR_2}, accredited biologist.

Laboratory accredited ISO 15189
{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "New document GENRE (not a translated Dutch template), direct English port of genre_lab_report_fr: a genuinely tabular (pipe-delimited markdown, matching what the real extraction pipeline's table.to_markdown() produces for a correctly-detected ruled table) format, structurally very different from the 50 letter-style templates.",
    "Reuses only existing Case fields -- DX_NUMERIC intentionally fills every lab VALUE cell (numeric hard-negative stress test: a model must learn these cells are clinical results, not phone/INSZ digits, purely from table structure and column headers, not narrative context).",
    "Only NAME_DOCTOR (requesting physician) carries {RIZIV}; NAME_DOCTOR_2 (validating biologist) deliberately does not, per the one-doctor-one-ID rule.",
    "British/international spelling per the locked-in register decision: Haemoglobin, Leukocytes (not Leucocytes -- kept as the standard English lab term), Haematology.",
]},

{
"template_hash": "genre_pharmacy_en",
"letter_type": "pharmacy_dispensing_record",
"specialty": "",
"masked_text_en": """PHARMACY {ORGANIZATION}
{STREET}
T {TELEFOON}

PHARMACY DISPENSING RECORD

Patient: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}

Prescriber: {NAME_DOCTOR}
{RIZIV_LABEL}{RIZIV}

Date dispensed: {DATE_ENCOUNTER}

| Medicine | CNK | Dosage | Quantity |
|---|---|---|---|
| {DX_DRUG} | {DX_CNK} | {DX_NUMERIC} | 1 box |
| {DX_DRUG_2} | {DX_CNK_2} | {DX_NUMERIC_2} | 1 box |

Generic substitution offered: {DX_ABBREV}
Interaction checked: {DX_CODESWITCH}
Allergy reported: none

Pharmacist: {NAME_DOCTOR_2}

Total price: {DX_NUMERIC_3} EUR
Third-party payment applied: {DX_ABBREV}

Repeat dispensing possible until: {DATE_VALIDATION}
{TELEFOON} for any questions.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "New document GENRE, direct English port of genre_pharmacy_fr: compact, form-like, no narrative prose -- structurally distinct from both the clinical letters and the lab report.",
    "CNK (Code National / Nationaal Kenmerk -- the real 7-digit Belgian national drug identification code, national and not tied to any one language community) reused unchanged, same DISTRACTORS['cnk_code'] pool and DX_CNK/DX_CNK_2 fields already in pii_table_en.py.",
    "Only NAME_DOCTOR (prescriber) carries {RIZIV}; NAME_DOCTOR_2 (pharmacist) does not -- Belgian pharmacists are NIHDI/RIZIV-registered too in reality, but the Case model has a single per-case RIZIV value, so attaching it to a second named person here would repeat the DIAGNOSIS/DX_EPONYM-style logical-consistency bug this pipeline already found and fixed once.",
]},

{
"template_hash": "genre_radiology_en",
"letter_type": "radiology_report",
"specialty": "",
"masked_text_en": """{ORGANIZATION}
MEDICAL IMAGING DEPARTMENT
{STREET}
T {TELEFOON}

RADIOLOGY REPORT

Patient: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}
Date of birth: {DOB} ({AGE})

Requesting physician: {NAME_DOCTOR_SENDER}

Date of examination: {DATE_ENCOUNTER}

INDICATION
{DIAGNOSIS} in a {AGE_ADJ} patient. {DX_ABBREV}.
Query {DX_EPONYM}? Prior examination from {DATE_HISTORY} available for
comparison.

TECHNIQUE
Standard acquisition, routine views. {DX_CODESWITCH}.

RESULT
{DX_ANATOMY}: preserved morphology, no focal lesion identified.
{DX_HOMOGRAPH}. {DX_TEST}. No evidence to support {DX_EPONYM}. {DX_NUMERIC}.

CONCLUSION
Examination showing no significant abnormality in relation to the clinical
history reported by {NAME_DOCTOR_SENDER}. Clinical correlation recommended
if symptoms persist. Diagnostic certainty: probable.

{NAME_DOCTOR}, radiologist
{RIZIV_LABEL}{RIZIV}
Report validated electronically on {DATE_VALIDATION} by {NAME_DOCTOR_2}.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "HIGH CONFIDENCE structure (same web research as French: the Indication -> Technique -> Result -> Conclusion skeleton is described as mandatory for Belgian radiology reports, order can vary but all four elements must appear) -- English medical-register wording, not a literal translation.",
    "New document GENRE, narrative but structurally distinct from the 50 letter templates via fixed section headers (INDICATION/TECHNIQUE/RESULT/CONCLUSION).",
    "Only NAME_DOCTOR (signing radiologist) carries {RIZIV}; NAME_DOCTOR_SENDER (referring physician) and NAME_DOCTOR_2 (co-signing/validating) deliberately do not, per the one-doctor-one-ID rule.",
    "DX_ABBREV used standalone, never after a hardcoded prefix -- avoids the French 'ATCD {DX_ABBREV}' collision class from round 1 (English pool has no exact analogue but the same discipline is applied preemptively).",
    "NAME_DOCTOR is never preceded by a literal 'Dr' (it already renders 'Dr Surname') -- avoids French's double-title bug from round 1.",
]},

{
"template_hash": "genre_sick_note_en",
"letter_type": "incapacity_certificate",
"specialty": "",
"masked_text_en": """CERTIFICATE OF INCAPACITY FOR WORK

{ORGANIZATION}
{STREET}
T {TELEFOON}

PART 1 -- PATIENT DECLARATION

Name: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}
Address: {STREET}
Status: [X] employee  [ ] worker  [ ] self-employed  [ ] unemployed
Nature: [X] initial  [ ] extension
Cause: [X] illness  [ ] accident  [ ] occupational illness  [ ] other

PART 2 -- MEDICAL CONFIDENTIAL (to be completed by the treating physician)

I, the undersigned {NAME_DOCTOR}, certify having examined {HONORIFIC}
{NAME_PATIENT}, {AGE_ADJ}, on {DATE_ENCOUNTER}, and confirm an incapacity
for work due to {DIAGNOSIS}. {DX_ABBREV}. {DX_HOMOGRAPH}.
{DX_CODESWITCH}.

Duration of incapacity: from {DATE_ENCOUNTER} to {DATE_VALIDATION} inclusive.

Treating physician: {NAME_DOCTOR}
{RIZIV_LABEL}{RIZIV}
Date: {DATE_VALIDATION}
Signature:

{ORGANIZATION}
""",
"adaptation_notes": [
    "HIGH CONFIDENCE structure (same web research as French, grounded in the actual public INAMI/RIZIV blank-form reference document): a two-part form -- Part 1 filled by the patient (identity, employment status, initial-vs-extension, cause checkboxes), Part 2 explicitly headed 'MEDICAL CONFIDENTIAL' filled by the physician. This models the salaried-employee variant, mirroring French's choice.",
    "New document GENRE: form-like (not letter, not table) -- the [X]/[ ] checkbox-style lines are a genuinely distinct visual pattern, and a realistic PyMuPDF-extraction target (checkbox glyphs often survive as literal bracket/box characters in extracted text).",
    "One checkbox per line is fixed to a representative marked state, same known low-cost realism gap already flagged and accepted in the French build -- not a new decision, just carried over.",
    "Only NAME_DOCTOR carries {RIZIV} (same one-doctor-one-ID-field rule as every other new template).",
    "{HONORIFIC} correctly resolves to 'Mr'/'Ms' per pii_table_en.py's build_case -- no hardcoded gendered word was introduced here.",
]},

{
"template_hash": "genre_prescription_en",
"letter_type": "proof_of_electronic_prescription",
"specialty": "",
"masked_text_en": """PROOF OF ELECTRONIC PRESCRIPTION (RECIP-E)

Prescriber: {NAME_DOCTOR}
{RIZIV_LABEL}{RIZIV}
{ORGANIZATION}
{STREET}
T {TELEFOON}

RID: {DX_NUMERIC}
Date created: {DATE_ENCOUNTER}
Valid until: {DATE_VALIDATION}

Patient: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}
Date of birth: {DOB}

Clinical indication: {DIAGNOSIS}. {DX_ABBREV}.

PRESCRIPTION CONTENTS

1. {DX_DRUG}
   Dosage: {DX_NUMERIC_2}
   Reimbursement category: B

2. {DX_DRUG_2}
   Dosage: {DX_NUMERIC_3}
   Reimbursement category: C

{DX_CODESWITCH}.

Qualified electronic signature
{ORGANIZATION}
""",
"adaptation_notes": [
    "MEDIUM CONFIDENCE (same web research as French: electronic prescribing is mandatory in Belgium since ~2020 with narrow exceptions; a printed A4 'proof of electronic prescription' is routinely produced). Exact reimbursement-category letter and dosage-line wording is an inferred, plausible rendering of a confirmed regulatory concept (A/B/C reimbursement tiers are real; exact on-sheet phrasing not independently verified).",
    "New document GENRE, distinct from both genre_pharmacy_en (point-of-dispensing record, pharmacist-written, includes CNK) and genre_discharge_meds_en (full regimen carry-forward) -- this is the physician-issued source document, deliberately WITHOUT a CNK code (the doctor prescribes a drug/INN, not a specific reimbursement package -- CNK is assigned at dispensing time).",
    "RID uses {DX_NUMERIC} purely as an alphanumeric-shaped filler occupying that structural position -- not meant to resemble Recip-e's real RID format (not independently confirmed), only to exercise the model on an unlabelled-by-training-data identifier sitting directly next to real INSZ/NIHDI values.",
]},

{
"template_hash": "genre_discharge_meds_en",
"letter_type": "discharge_medication_schema",
"specialty": "",
"masked_text_en": """{ORGANIZATION}
DISCHARGE MEDICATION SCHEMA
{STREET}
T {TELEFOON}

Patient: {NAME_PATIENT}
{INSZ_LABEL}{INSZ}
Date of birth: {DOB}

Responsible physician: {NAME_DOCTOR}
{RIZIV_LABEL}{RIZIV}

Discharged on: {DATE_ENCOUNTER}

| Medicine | Dosage | Frequency | Indication |
|---|---|---|---|
| {DX_DRUG} | {DX_NUMERIC} | {DX_NUMERIC_2} | {DIAGNOSIS} |
| {DX_DRUG_2} | {DX_NUMERIC_3} | {DX_NUMERIC_4} | {DX_EPONYM} |

This schema replaces any prior treatment as of {DATE_HISTORY}. {DX_ABBREV}.
{DX_CODESWITCH}.

To be handed to the GP and the pharmacist.

Validated on {DATE_VALIDATION} by {NAME_DOCTOR_2}.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "MEDIUM-HIGH CONFIDENCE (same web research as French): a 'medication schema' is a real, NIHDI/RIZIV-defined official concept -- an updated overview of all medications a patient is on, produced alongside the discharge letter. Exact column layout is a reasonable inferred rendering, not independently verified against a real form.",
    "Genuine pipe-delimited markdown table, same real-extraction-pipeline grounding as genre_lab_report_en and genre_pharmacy_en.",
    "The two table rows deliberately use DIFFERENT indication values (DIAGNOSIS vs DX_EPONYM) rather than repeating one value across rows -- the distinct-per-cell-value rule (DX_NUMERIC_2..9 class) applied from round 1, not found late as it was in the original French lab report/pharmacy drafts.",
    "Only NAME_DOCTOR carries {RIZIV}; NAME_DOCTOR_2 (validating physician) does not.",
]},
]

def main():
    out_path = "new_genres_en.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} new-genre templates -> {out_path}")

if __name__ == "__main__":
    main()
