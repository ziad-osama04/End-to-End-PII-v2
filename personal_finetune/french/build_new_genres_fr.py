# -*- coding: utf-8 -*-
"""
build_new_genres_fr.py -- two new document GENRES beyond the clinical-letter
templates: a lab report and a pharmacy dispensing record. Both use genuine
pipe-delimited markdown tables (not ASCII art), matching what the real
extraction pipeline's table.to_markdown() actually produces for a correctly
DETECTED ruled table -- these are dense, tabular, numeric-heavy documents,
structurally very different from the 50 letter-style templates, and are
exactly the kind of layout a QA team would test that the existing corpus
doesn't cover at all.
"""
import json

TEMPLATES = [
{
"template_hash": "genre_lab_report_fr",
"letter_type": "rapport_laboratoire",
"specialty": "",
"masked_text_fr": """LABORATOIRE CLINIQUE

{ORGANIZATION}
{STREET}
T {TELEFOON}

Patient : {NAME_PATIENT}
NISS : {INSZ}
Né(e) le : {DOB}

Médecin prescripteur : {NAME_DOCTOR}
INAMI prescripteur : {RIZIV}

Prélèvement : {DATE_HISTORY}
Réception : {DATE_ENCOUNTER}
Rapport : {DATE_VALIDATION}

HÉMATOLOGIE

| Paramètre | Résultat | Unité | Valeurs de référence |
|---|---|---|---|
| Hémoglobine | {DX_NUMERIC} | g/dL | 12,0-16,0 |
| Leucocytes | {DX_NUMERIC_2} | x10⁹/L | 4,0-10,0 |
| Plaquettes | {DX_NUMERIC_3} | x10⁹/L | 150-400 |
| VS | {DX_NUMERIC_4} | mm/h | <20 |

BIOCHIMIE

| Paramètre | Résultat | Unité | Valeurs de référence |
|---|---|---|---|
| Créatinine | {DX_NUMERIC_5} | µmol/L | 60-110 |
| CRP | {DX_NUMERIC_6} | mg/L | <5 |
| Glycémie à jeun | {DX_NUMERIC_7} | mg/dL | 70-110 |
| ASAT | {DX_NUMERIC_8} | U/L | <40 |
| ALAT | {DX_NUMERIC_9} | U/L | <41 |
| {DX_EPONYM} | {DX_ABBREV} | - | {DX_HOMOGRAPH} |

Commentaire du biologiste : Profil compatible avec {DIAGNOSIS}. {DX_ABBREV}.
{DX_CODESWITCH}. Corrélation clinique recommandée en cas de persistance des
symptômes.

Validé électroniquement le {DATE_VALIDATION} par {NAME_DOCTOR_2}, biologiste agréé.

Laboratoire agréé ISO 15189
{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "New document GENRE (not a translated Dutch template): a lab-report format, structurally very different from the 50 letter-style templates -- genuinely tabular (pipe-delimited markdown, matching what the real extraction pipeline's table.to_markdown() produces for a correctly-detected ruled table) rather than a narrative letter with an embedded ASCII table.",
    "Reuses only existing Case fields (no template-specific new PII fields needed) -- DX_NUMERIC intentionally fills every lab VALUE cell, since lab reports are the ideal place to stress-test numeric hard negatives (a model must learn these numeric-shaped cells are clinical results, not phone/INSZ digits, purely from table structure and column headers, not from narrative context).",
]},

{
"template_hash": "genre_pharmacy_fr",
"letter_type": "delivrance_pharmaceutique",
"specialty": "",
"masked_text_fr": """PHARMACIE {ORGANIZATION}
{STREET}
T {TELEFOON}

DÉLIVRANCE PHARMACEUTIQUE

Patient : {NAME_PATIENT}
NISS : {INSZ}

Prescripteur : {NAME_DOCTOR}
INAMI prescripteur : {RIZIV}

Date de délivrance : {DATE_ENCOUNTER}

| Médicament | CNK | Posologie | Quantité |
|---|---|---|---|
| {DX_DRUG} | {DX_CNK} | {DX_NUMERIC} | 1 boîte |
| {DX_DRUG_2} | {DX_CNK_2} | {DX_NUMERIC_2} | 1 boîte |

Substitution générique proposée : {DX_ABBREV}
Interaction vérifiée : {DX_CODESWITCH}
Allergie signalée : aucune

Pharmacien(ne) : {NAME_DOCTOR_2}

Prix total : {DX_NUMERIC_3} EUR
Tiers payant appliqué : {DX_ABBREV}

Renouvellement possible jusqu'au : {DATE_VALIDATION}
{TELEFOON} pour toute question.

{ORGANIZATION}
{URL}
""",
"adaptation_notes": [
    "New document GENRE: a pharmacy dispensing record, structurally distinct from both the clinical letters and the lab report (compact, form-like, no narrative prose at all).",
    "Introduces CNK codes (Code National -- the real 7-digit Belgian national drug identification code printed on every pharmacy dispensing record) as a new DISTRACTORS['cnk_code'] pool / DX_CNK+DX_CNK_2 Case fields -- a genuinely realistic Belgian-specific hard negative: purely numeric, same length class as a phone extension or partial ID, distinguished from real PII only by the 'CNK' column header, not by shape.",
]},
]

def main():
    out_path = "new_genres_fr.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"wrote {len(TEMPLATES)} new-genre templates -> {out_path}")

if __name__ == "__main__":
    main()
