# -*- coding: utf-8 -*-
"""
build_new_genres_fr_v2.py -- four more document GENRES, grounded in a
web-research pass on real Belgian document conventions (see chat history /
PR notes for the research summary; sources: INAMI/SPF Sante public
reference material, Recip-e regulatory pages, BELAC/ISO 15189 accreditation
rules, UCLouvain radiology teaching material, the actual public INAMI
"certificat d'incapacite de travail" blank form):

  - genre_radiology_fr:      Motif/Indication -> Technique -> Resultat ->
                              Conclusion structure, confirmed as the
                              mandatory (order-flexible) skeleton for
                              Belgian radiology reports.
  - genre_sick_note_fr:      certificat d'incapacite de travail, modelled
                              on the real two-part INAMI form (Volet 1
                              patient declaration / Volet 2 "SECRET MEDICAL"
                              physician section) -- a structurally distinct,
                              form-like (not letter, not table) genre.
  - genre_prescription_fr:   "preuve de prescription electronique" (Recip-e)
                              -- the printed proof-of-e-prescription sheet
                              Belgian pharmacies actually scan (RID/barcode,
                              creation + validity dates, prescriber INAMI in
                              digits form).
  - genre_discharge_meds_fr: "schema de medication" -- an INAMI-defined
                              official discharge concept, a full-regimen
                              table distinct in purpose (multi-drug carry-
                              forward overview) from the existing pharmacy
                              dispensing-record template (single
                              transaction).

Confidence notes (see adaptation_notes per template): the four-section
radiology skeleton and the two-volet sick-note structure are high-confidence
(regulatory / public reference document). Exact prescription-sheet field
wording and discharge-schema column layout are medium-confidence
(regulatory concept confirmed, exact layout inferred) -- reasonable
placeholder-template renderings of a real, confirmed structure.
"""
import json

TEMPLATES = [
{
"template_hash": "genre_radiology_fr",
"letter_type": "compte_rendu_radiologique",
"specialty": "",
"masked_text_fr": """{ORGANIZATION}
SERVICE D'IMAGERIE MEDICALE
{STREET}
T {TELEFOON}

COMPTE-RENDU RADIOLOGIQUE

Patient : {NAME_PATIENT}
NISS : {INSZ}
Ne(e) le : {DOB} ({AGE})

Medecin demandeur : {NAME_DOCTOR_SENDER}

Date de l'examen : {DATE_ENCOUNTER}

INDICATION
{DIAGNOSIS} chez un(e) patient(e) de {AGE_ADJ}. {DX_ABBREV}.
Recherche de {DX_EPONYM} ? Examen anterieur du {DATE_HISTORY} pour
comparaison.

TECHNIQUE
Acquisition standard, incidences habituelles. {DX_CODESWITCH}.

RESULTAT
{DX_ANATOMY} : morphologie conservee, pas de lesion focale identifiee.
{DX_HOMOGRAPH}. {DX_TEST}. Absence d'argument pour {DX_EPONYM}. {DX_NUMERIC}.

CONCLUSION
Examen ne montrant pas d'anomalie significative en rapport avec la clinique
rapportee par {NAME_DOCTOR_SENDER}. Correlation clinique recommandee en cas
de persistance des symptomes. Certitude diagnostique : probable.

{NAME_DOCTOR}, radiologue
INAMI : {RIZIV}
Rapport valide electroniquement le {DATE_VALIDATION} par {NAME_DOCTOR_2}.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "HIGH CONFIDENCE structure (web research, UCLouvain radiology teaching material): the Motif/Indication -> Technique -> Resultat -> Conclusion skeleton is described as mandatory for Belgian radiology reports (order can vary, all four elements must appear).",
    "New document GENRE, narrative (not tabular) but structurally distinct from the 50 clinical-letter templates via its fixed section headers (INDICATION/TECHNIQUE/RESULTAT/CONCLUSION) -- a QA tester who only knows the letter format would very plausibly probe this shape.",
    "Only ONE doctor (NAME_DOCTOR, the signing radiologist) carries the {RIZIV} placeholder -- NAME_DOCTOR_SENDER (referring physician) and NAME_DOCTOR_2 (co-signing/validating) deliberately do NOT get their own INAMI shown, since Case has a single per-case RIZIV value and attaching it to two different named physicians would be the same kind of logical-consistency bug already found and fixed once in this pipeline (the DIAGNOSIS/DX_EPONYM collision).",
    "First draft literally wrote 'ATCD {DX_ABBREV}' and 'Dr {NAME_DOCTOR}' -- caught via the render smoke test producing 'ATCD ATCD.' (DX_ABBREV's pool literally contains the string 'ATCD') and 'Dr dr. Leonard' (NAME_DOCTOR already includes a 'dr. ' prefix). Fixed here; the ATCD collision turned out to be a PRE-EXISTING, previously-uncaught bug in 23 of the original 50 translated templates (same literal-prefix-collides-with-sampled-value class as the earlier DIAGNOSIS/DX_EPONYM stutter) and was patched retroactively across the whole bank at the same time.",
]},

{
"template_hash": "genre_sick_note_fr",
"letter_type": "certificat_incapacite",
"specialty": "",
"masked_text_fr": """CERTIFICAT D'INCAPACITE DE TRAVAIL

{ORGANIZATION}
{STREET}
T {TELEFOON}

VOLET 1 -- DECLARATION DU PATIENT

Nom, prenom : {NAME_PATIENT}
NISS : {INSZ}
Adresse : {STREET}
Statut : [X] employe  [ ] ouvrier  [ ] independant  [ ] chomeur
Nature : [X] debut  [ ] prolongation
Cause : [X] maladie  [ ] accident  [ ] maladie professionnelle  [ ] autre

VOLET 2 -- SECRET MEDICAL (a remplir par le medecin traitant)

Je soussigne(e) {NAME_DOCTOR}, certifie avoir examine {HONORIFIC}
{NAME_PATIENT}, {AGE_ADJ}, le {DATE_ENCOUNTER}, et constate une incapacite
de travail pour cause de {DIAGNOSIS}. {DX_ABBREV}. {DX_HOMOGRAPH}.
{DX_CODESWITCH}.

Duree de l'incapacite : du {DATE_ENCOUNTER} au {DATE_VALIDATION} inclus.

Medecin traitant : {NAME_DOCTOR}
INAMI : {RIZIV}
Date : {DATE_VALIDATION}
Signature :

{ORGANIZATION}
""",
"adaptation_notes": [
    "HIGH CONFIDENCE structure (web research, actual public INAMI blank-form reference document): real Belgian sick notes are a two-part form -- Volet 1 filled by the patient (identity, employment status, begin-vs-prolongation, cause checkboxes), Volet 2 explicitly headed 'SECRET MEDICAL' filled by the physician (diagnosis, date range, INAMI ID block, signature). Near-identical separate forms exist for salaried vs self-employed patients -- this template models the salaried-employee variant.",
    "New document GENRE: form-like (not letter, not table) -- the [X]/[ ] checkbox-style lines are a genuinely distinct visual pattern from every other template in the bank, and a realistic PyMuPDF-extraction target (checkbox glyphs often survive as literal bracket/box characters in extracted text).",
    "One checkbox per line is fixed to a representative marked state ([X] employe / debut / maladie) rather than varying per render -- adding a Case field purely to vary which box is checked would be a new PII-irrelevant field for no detection-accuracy benefit; the frozen choice is flagged here as a known, low-cost realism gap rather than silently left unexplained.",
    "Only NAME_DOCTOR carries {RIZIV} (same one-doctor-one-ID-field rule as the other new templates).",
]},

{
"template_hash": "genre_prescription_fr",
"letter_type": "preuve_prescription_electronique",
"specialty": "",
"masked_text_fr": """PREUVE DE PRESCRIPTION ELECTRONIQUE (RECIP-E)

Prescripteur : {NAME_DOCTOR}
INAMI : {RIZIV}
{ORGANIZATION}
{STREET}
T {TELEFOON}

RID : {DX_NUMERIC}
Date de creation : {DATE_ENCOUNTER}
Valable jusqu'au : {DATE_VALIDATION}

Patient : {NAME_PATIENT}
NISS : {INSZ}
Ne(e) le : {DOB}

Indication clinique : {DIAGNOSIS}. {DX_ABBREV}.

CONTENU DE LA PRESCRIPTION

1. {DX_DRUG}
   Posologie : {DX_NUMERIC_2}
   Categorie de remboursement : B

2. {DX_DRUG_2}
   Posologie : {DX_NUMERIC_3}
   Categorie de remboursement : C

{DX_CODESWITCH}.

Signature electronique qualifiee
{ORGANIZATION}
""",
"adaptation_notes": [
    "MEDIUM CONFIDENCE (web research, Recip-e/SPF Sante regulatory pages): electronic prescribing is mandatory in Belgium since ~2020 with narrow exceptions, but a printed A4 'proof of electronic prescription' is routinely produced -- showing prescriber name+INAMI (in digits, plus a barcode not represented here since it's a non-text image element PyMuPDF text-extraction would never surface), a RID code, creation date, and default 3-month validity date. Multiple products can appear per sheet. Exact reimbursement-category letter and posology-line wording is an inferred, plausible rendering of a confirmed regulatory concept (A/B/C reimbursement tiers are real; their exact on-sheet phrasing was not independently verified).",
    "New document GENRE, distinct from both genre_pharmacy_fr (point-of-dispensing record, written by the pharmacist, includes CNK) and genre_discharge_meds_fr (full regimen carry-forward) -- this is the physician-issued source document the pharmacist scans, deliberately WITHOUT a CNK code (the doctor prescribes a drug/DCI, not a specific reimbursement package -- CNK is assigned at dispensing time).",
    "RID uses {DX_NUMERIC} purely as an alphanumeric-shaped filler occupying that structural position -- it is not meant to resemble Recip-e's real RID format (not independently confirmed), only to exercise the model on a document shape with an unlabelled-by-training-data identifier sitting directly next to real INSZ/INAMI values.",
]},

{
"template_hash": "genre_discharge_meds_fr",
"letter_type": "schema_medication",
"specialty": "",
"masked_text_fr": """{ORGANIZATION}
SCHEMA DE MEDICATION DE SORTIE
{STREET}
T {TELEFOON}

Patient : {NAME_PATIENT}
NISS : {INSZ}
Ne(e) le : {DOB}

Medecin responsable : {NAME_DOCTOR}
INAMI : {RIZIV}

Sortie le : {DATE_ENCOUNTER}

| Medicament | Posologie | Frequence | Indication |
|---|---|---|---|
| {DX_DRUG} | {DX_NUMERIC} | {DX_NUMERIC_2} | {DIAGNOSIS} |
| {DX_DRUG_2} | {DX_NUMERIC_3} | {DX_NUMERIC_4} | {DX_EPONYM} |

Ce schema remplace tout traitement anterieur au {DATE_HISTORY}. {DX_ABBREV}.
{DX_CODESWITCH}.

A remettre au medecin traitant et au pharmacien.

Valide le {DATE_VALIDATION} par {NAME_DOCTOR_2}.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "MEDIUM-HIGH CONFIDENCE (web research): 'schema de medication' is a real, INAMI-defined official concept -- an updated overview of all medications a patient is on, produced alongside the discharge letter, meant to be carried to every subsequent GP/pharmacist/hospital visit. Exact column layout (drug/dosage/frequency/indication) is a reasonable inferred rendering; not independently verified against a real form.",
    "Genuine pipe-delimited markdown table (matching table.to_markdown() output for a correctly-detected ruled table), same real-extraction-pipeline grounding as genre_lab_report_fr and genre_pharmacy_fr.",
    "The two table rows deliberately use DIFFERENT indication values (DIAGNOSIS vs DX_EPONYM) rather than repeating one value across rows -- this is the exact repeated-identical-filler bug already found and fixed once in genre_lab_report_fr's/genre_pharmacy_fr's first drafts (DX_NUMERIC_2..9 were added for the same reason).",
    "Only NAME_DOCTOR carries {RIZIV}; NAME_DOCTOR_2 (validating physician) does not.",
]},
]

def main():
    out_path = "new_genres_fr_v2.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} new-genre templates -> {out_path}")

if __name__ == "__main__":
    main()
