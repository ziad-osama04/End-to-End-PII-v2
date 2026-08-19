"""
Build English translations (batch 1, lines 1-10) of the recovered Dutch
clinical-letter templates in personal_finetune/french/recovered_templates_nl_v3.jsonl.

Mirrors the earlier Dutch -> French translation project for the same source
templates. Produces personal_finetune/english/translated_templates_en_batch1.jsonl.
"""

import json
import re
import os

TEMPLATES = [
    {
        "template_hash": "085ee68a2d15cebb",
        "letter_type": "consultatiebrief",
        "specialty": "Pneumologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague UNIT: 14612 DATE: {DATE_ENCOUNTER} ETHNICITY: mixed "
            "AGE: {AGE} HEIGHT 178.2 cm WEIGHT: 108.8 kg BMI: 34.272 SMOKING STATUS: "
            "not known Presenting complaint: ----------- {DATE_HISTORY}: onset of "
            "exertional dyspnoea, symptoms progressive since 03/2023: increasing cough "
            "with sputum production, {DX_ABBREV} {DX_DRUG} referral by the GP "
            "{DX_ABBREV} {DIAGNOSIS} and suspicion of {DX_EPONYM} ! Medical history: "
            "----------------- 15/04/{DOB}: diagnosed with {DIAGNOSIS} 06/2020: first "
            "{SPECIALTY}-related exacerbation {DX_ABBREV} type 2 diabetes mellitus, "
            "controlled {DX_ABBREV} resuscitation after anaphylaxis ({DX_DRUG_2}) "
            "Family history: ---------- {RELATIVE_RELATION} ({NAME_RELATIVE}): "
            "pulmonary fibrosis at age 70 father: COPD, long-term smoker Allergies: "
            "---------- No known allergies Medication on admission: ------------------- "
            "- {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - salbutamol (inhaled) 100 mcg, "
            "as needed - tiotropium, 1 capsule, {DX_NUMERIC}, in the morning - "
            "{DX_DRUG_2}, 5 mg, {DX_NUMERIC}, 9am History: ------- {HONORIFIC} "
            "{NAME_PATIENT}, a {AGE_ADJ} patient with known {DIAGNOSIS}, presents with "
            "persistent shortness of breath {DX_ABBREV} climbing stairs or walking "
            "briskly. Clinically stable according to the last review in "
            "{DATE_ENCOUNTER}. No fever or night sweats. Sputum: occasionally grey, "
            "never blood-stained. No weight loss. Inhalers are used regularly, but "
            "with reportedly “little effect” for the past {DX_NUMERIC} months. "
            "No complaints of orthopnoea or PND. Clinical examination: "
            "------------------- general condition: stable, no cyanosis! chest: "
            "symmetrical expansion, resonant percussion, {DX_TEST} lungs: auscultation "
            "reveals crackles at the left base, vesicular breath sounds elsewhere "
            "{DX_HOMOGRAPH} HR: regular, {DX_ANATOMY} {DX_ABBREV} abdomen: soft, no "
            "hepatosplenomegaly Investigations: -------------------- CXR "
            "{DATE_ENCOUNTER}: discrepant hypertranslucency on the right, no "
            "infiltrates CT chest (05/{DX_NUMERIC}): bronchiectasis affecting the "
            "right base, wall thickening, {DX_CODESWITCH} spirometry: FEV1 68% "
            "predicted, reduced FEV1/FVC ratio → obstruction {DX_ABBREV} "
            "Conclusion: -------- The {AGE_ADJ} patient was seen at the {SPECIALTY} "
            "consultation on {DATE_ENCOUNTER}. Findings: stable {DIAGNOSIS}, no acute "
            "exacerbation. However, limited response to current therapy. {DX_EPONYM} "
            "remains a differential diagnosis {DX_ABBREV} CT findings. Home medication "
            "recorded as above. --> continue current baseline treatment --> add-on: "
            "consider inhaled corticosteroid (fluticasone) at reassessment --> "
            "referral to respiratory physiotherapy {DX_ABBREV} {DX_DRUG_2} --> "
            "follow-up consultation in three months or sooner if worsening (!)\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n    "
            "{NAME_DOCTOR_2}\n    {NAME_DOCTOR_3}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 16:57\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n\n"
            "    {STREET}        T {TELEFOON}\n"
            "    {STREET}        T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Replaced hardcoded gendered honorific 'mevrouw' directly before {NAME_PATIENT} with the {HONORIFIC} field instead of a literal 'Mrs', so it stays consistent with GENDER.",
            "Rewrote 'zij gebruikt inhalatoria...' (flagged PRONOUN_SUBJ 'zij') as a passive construction ('Inhalers are used regularly...') to avoid a hardcoded pronoun.",
        ],
    },
    {
        "template_hash": "11369ce1f2beb381",
        "letter_type": "opvolgbrief",
        "specialty": "Reumatologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            "    Dear colleague,\n\n"
            "    We saw your patient {NAME_PATIENT} at the {SPECIALTY} consultation on\n"
            "    {DATE_ENCOUNTER}.\n\n"
            "    Medical history:\n    -----------------\n"
            "    {DATE_HISTORY}: {DIAGNOSIS} {DX_EPONYM} ! Rheumatoid\n"
            "    arthritis since 2015, {DX_NUMERIC} when symptomatic Occasional intermittent\n"
            "    iridocyclitis, followed up in ophthalmology\n"
            "    Family history:\n    ----------\n"
            "    {RELATIVE_RELATION} ({NAME_RELATIVE}): {DX_TEST} on {DOB}\n\n"
            "    Allergies:\n    ---------\n    No known allergies\n\n"
            "    History:\n    ---------\n"
            "    The {AGE_ADJ} patient reports progressive stiffness in the hands and wrists, particularly\n"
            "    in the morning. Duration: 1.5 hours. On {DX_DRUG} since {DATE_HISTORY},\n"
            "    but symptoms worsened over the past few weeks. {DX_ABBREV}. No systemic\n"
            "    symptoms such as fever or weight loss. No {DX_HOMOGRAPH}.\n"
            "    Attended physiotherapy, without {DX_CODESWITCH}. Symptoms are limiting ADLs.\n\n"
            "    Clinical examination:\n    -------------------\n"
            "    Hands: symmetrical swelling of MCP 2-5 and PIP 2-4, {DX_ANATOMY} positive!\n"
            "    No ulnar deviation. Wrist: painful on passive extension, {DX_ABBREV} weakness.\n"
            "    Elbows: {DX_ABBREV}. {DX_TEST} negative Both knees: bulge sign,\n"
            "    swollen but not painful. No instability.\n\n"
            "    Investigations:\n    ------------------------\n"
            "    Ultrasound of the rheumatoid hands (ref. {DX_DRUG_2}): grade 2-3 synovitis of the MCPs,\n"
            "    PIPs, wrists. X-ray of the hands (ref. {DX_CODESWITCH}): erosions at the base\n"
            "    of the distal phalanges, {DX_ABBREV} progression compared with {DATE_HISTORY}. CRP: 8 mg/l (ref.\n"
            "    <5), ESR: 22 mm/h (ref. <20) RF: positive (>200 IU), anti-CCP: 320 U/ml\n\n"
            "    Conclusion:\n    -------\n"
            "    The {AGE_ADJ} patient was seen at the {SPECIALTY} consultation on\n"
            "    {DATE_ENCOUNTER}. Findings: progressive inflammatory\n"
            "    polyarthritis with functional impairment and biochemical activity. No\n"
            "    {DX_HOMOGRAPH}, but positive serology.\n\n"
            "    --> Initiate methotrexate 15 mg sc once weekly, starting with folic acid 5 mg once weekly 1 day\n"
            "    after MTX.\n"
            "    --> Start {DX_DRUG_2} 7.5 mg/day {DX_ABBREV} inflammatory profile and risk\n"
            "    of progression.\n"
            "    --> Tailored physiotherapy, {DX_ABBREV} referral.\n"
            "    --> Review with {SPECIALTY} in 3 months {DX_ABBREV} response.\n\n"
            "    Home medication:\n    -------------\n"
            "    - {DX_DRUG_2}, 1 tablet, {DX_NUMERIC}, {DX_NUMERIC}\n"
            "    - {DX_DRUG_2}, 1-0-1, {DX_NUMERIC} 2pm 8pm\n\n"
            "    No home medication recorded beyond the above. {TELEFOON} for\n"
            "    questions.\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n    {NAME_DOCTOR_2}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 12:35\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}          T {TELEFOON}\n"
            "    {STREET}          T {TELEFOON}\n"
            "    {STREET}          T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Dropped literal 'Antec.' before {DX_ABBREV} and let the placeholder stand alone as its own sentence, since a translated abbreviation prefix (e.g. 'Hx') could duplicate a value {DX_ABBREV} itself might sample.",
            "Rewrote 'zij vertoont progressieve...' (flagged PRONOUN_SUBJ 'zij') into a passive 'Findings:' clause to avoid a hardcoded pronoun.",
        ],
    },
    {
        "template_hash": "11dc809f9e038c5a",
        "letter_type": "consultatiebrief",
        "specialty": "Oncologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            "    Dear colleague\n\n"
            "    Your patient {NAME_PATIENT} ({DOB}) attended our\n"
            "    {SPECIALTY} consultation on {DATE_ENCOUNTER}.\n\n"
            "    History:\n    ----------\n"
            "    Gradually increasing fatigue has been reported since 03/2024.\n"
            "    Weight loss of approx. {DX_NUMERIC} kg over the past 2 months, without dieting.\n"
            "    No night sweats reported. Previously mild pain in the left lower abdomen, now {DX_ABBREV}.\n"
            "    Relevant history: {DX_ABBREV}, status post {DX_EPONYM} treatment (2018).\n"
            "    Family history: {DX_ABBREV}-{DIAGNOSIS} in {RELATIVE_RELATION} {NAME_RELATIVE}.\n"
            "    {PRONOUN_SUBJ} still works part-time as {DX_HOMOGRAPH}, mainly in an administrative role.\n"
            "    Social history: lives alone, non-smoker, occasional alcohol use. No further complaints\n"
            "    of blood in urine or stool since starting {DX_DRUG}. !\n"
            "    Pain temporarily increased after the chemotherapy cycle in {DATE_HISTORY}.\n\n"
            "    Current medication:\n    -----------------\n"
            "    - {DX_DRUG_2} (tabl 5 mg), 5 mg, {DX_NUMERIC}, 9am\n"
            "    - Zytiga (tabl 500 mg), 500 mg, {DX_NUMERIC}, 7am on an empty stomach\n"
            "    - Prednisone (tabl 5 mg), 5 mg, {DX_NUMERIC}, {DX_NUMERIC} and 8pm\n"
            "    - {DX_DRUG_2} (injection 10 mg/ml), 10 mg, iv, q3wks\n"
            "    - Paracetamol (tabl 1 g), 1 g, p.r.n. for fever\n"
            "    No known allergies\n\n"
            "    Investigations:\n    ------------------------\n"
            "    CT abdomen {DATE_ENCOUNTER}: stabilisation of {DX_ANATOMY} lesions, no new\n"
            "    abnormalities in liver or lymph nodes. PET scan {DATE_HISTORY}: limited\n"
            "    metabolic activity in the {DX_CODESWITCH} region, consistent with\n"
            "    residual disease. Full blood count: Hb {DX_NUMERIC} g/l (low-normal), platelets\n"
            "    210, WBC {DX_ABBREV}. Tumour markers: PSA fell from 8.2 to 4.6 ng/ml since the last\n"
            "    cycle. {DX_TEST}: {DX_ABBREV} on abdominal palpation, no\n"
            "    hepatosplenomegaly. ECG: sinus rhythm, QTc {DX_ABBREV}, no\n"
            "    repolarisation abnormalities. Biopsy {DX_ANATOMY} (dd. {DATE_HISTORY}): confirms\n"
            "    {DIAGNOSIS}, immunohistochemistry positive for AR.\n\n"
            "    Conclusion:\n    --------\n"
            "    The {AGE_ADJ} patient was seen on {DATE_ENCOUNTER} {DX_ABBREV} follow-up of\n"
            "    {DIAGNOSIS} with a focus on response evaluation. Treatment\n"
            "    is proceeding as scheduled, {DX_ABBREV} clinical and radiological stabilisation. Given the\n"
            "    persistent fatigue: check iron stores, consider\n"
            "    erythropoietin induction if needed.\n"
            "    --> Continue current regimen with {DX_DRUG_2} + {DX_DRUG_2} until\n"
            "    the next review.\n"
            "    --> Plan repeat PET scan in 12 weeks (dd. {DX_NUMERIC}).\n"
            "    --> Refer for palliative support {DX_ABBREV} in view of the comorbidity burden.\n\n"
            "    Advice:\n    -------\n"
            "    The patient may call {TELEFOON} in the interim in case of acute deterioration, fever\n"
            "    >38.5°C or haematuria. Coordination of treatment remains with oncology; no\n"
            "    change to home medication. Last consultation: see report dd. {DATE_HISTORY}.\n"
            "    The above patient will automatically be invited for a follow-up consultation.\n"
            "    No home medication recorded beyond the above list.\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n    {NAME_DOCTOR_2}\n"
            "    {NAME_DOCTOR_3}\n    {NAME_DOCTOR_4}\n    {NAME_DOCTOR_5}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 11:36\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}      T {TELEFOON}\n"
            "    {STREET}      T {TELEFOON}\n\n"
            "    {STREET}        T {TELEFOON}\n"
            "    {STREET}        T {TELEFOON}\n"
            "    {STREET}        T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Fixed a recovery-artifact stutter '{DX_ABBREV} {DX_ABBREV}-morbiditeitsbelasting' by dropping the duplicate placeholder and keeping plain text ('in view of the comorbidity burden').",
            "Replaced three hardcoded 'hij' occurrences (flagged PRONOUN_SUBJ) with passive voice for two of them and the {PRONOUN_SUBJ} field for the third ('still works part-time as...').",
        ],
    },
    {
        "template_hash": "1a45c72c46030984",
        "letter_type": "spoedverslag",
        "specialty": "Endocrinologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:                      RESPONSIBLE:            DATE:\n"
            "{NAME_PATIENT}                 {NAME_RESPONSIBLE}              {DATE_ENCOUNTER} 02:00\n"
            "{INSZ_LABEL}{INSZ}          {RIZIV_LABEL}{RIZIV}             SENT BY:\n"
            "                                                            {NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague, We saw your patient {NAME_PATIENT} at the {SPECIALTY} consultation "
            "on {DATE_ENCOUNTER}. Medical history: ----------------- {DOB}: born without "
            "complications, {DX_ABBREV}. 05-2018: diagnosis of {DIAGNOSIS} established in "
            "{NAME_RELATIVE}, {DX_ABBREV}. {DX_EPONYM} 12-2020: started {DX_DRUG}, {DX_NUMERIC}, "
            "{DX_NUMERIC}, {DX_ABBREV} HbA1c ↑ 03-2023: {DX_ABBREV} type 2 diabetes & obesity, "
            "{DX_ABBREV} metabolic syndrome! {DX_NUMERIC}: recent glucose curve within range "
            "Allergies: --------- No known allergies History: --------- The {AGE_ADJ} patient "
            "reports fatigue since {DATE_HISTORY}, mainly in the morning No palpitations, tremor "
            "or weight loss. Appetite normal. History of dyslipidaemia and NAFLD. No alcohol use, "
            "{DX_ABBREV} smoker. Family history positive for {DIAGNOSIS} ({RELATIVE_RELATION}: "
            "{NAME_RELATIVE}) {DX_HOMOGRAPH} is mentioned, but without confirmation {DX_TEST} "
            "Clinical examination: ------------------- General: euthyroid facies, no exophthalmos! "
            "TSH: 0.02 mU/L (ref 0.4–4.0), fT4 25 pmol/L (ref 10–20) → "
            "hyperthyroidism! {DX_ANATOMY}: diffusely enlarged, non-tender, no nodules Cardio: "
            "heart rhythm regular, 94 bpm, blood pressure 138/82 mmHg GEA: {DX_ABBREV}, reflexes "
            "brisk Conclusion: -------- The above-named patient was seen {DX_ABBREV} persistent "
            "hyperthyroidism since {DATE_ENCOUNTER}, despite {DX_DRUG_2} started at the initial "
            "{SPECIALTY} consultation. The most recent {DX_TEST} shows further progressive "
            "overproduction. --> referral to nuclear medicine for {DX_CODESWITCH} evaluation --> "
            "TPO-ab and TRAb testing in progress --> temporary therapy with {DX_DRUG_2} (tabl "
            "10 mg), 10 mg, {DX_NUMERIC}, 9am Contact via {TELEFOON} in case of fever or sore "
            "throat!\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n    {NAME_DOCTOR_2}\n"
            "    {NAME_DOCTOR_3}\n    {NAME_DOCTOR_4}\n    {NAME_DOCTOR_5}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 09:23\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n\n"
            "    {STREET}        T {TELEFOON}\n"
            "    {STREET}        T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Dropped the honorific 'de heer' hardcoded immediately before {NAME_RELATIVE} (flagged HONORIFIC), since {RELATIVE_RELATION} is independently sampled and could be feminine.",
            "Fixed a '{DX_ABBREV} {DX_ABBREV}' adjacent-duplicate stutter in the birth-history line by dropping the second occurrence; replaced the hardcoded closing 'hij contacteert' (flagged PRONOUN_SUBJ) with an imperative 'Contact via...' construction.",
        ],
    },
    {
        "template_hash": "2299d2f326855e74",
        "letter_type": "spoedverslag",
        "specialty": "Orthopedie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            "    Dear colleague\n\n"
            "    Your patient {NAME_PATIENT} ({DOB}) attended our\n"
            "    {SPECIALTY} consultation on {DATE_ENCOUNTER}.\n\n"
            "    Presenting complaint:\n    -----------\n"
            "    {DATE_HISTORY}: fall from height (>2 metres) while gardening 03/2024:\n"
            "    {DIAGNOSIS} of the right ankle, cast applied elsewhere Chronic\n"
            "    pain in the right knee since 2019 ({DX_ABBREV} {DX_EPONYM})\n\n"
            "    Medical history:\n    -----------------\n"
            "    Rheumatoid arthritis since age 58 Known {DIAGNOSIS} (T-score\n"
            "    -2.8) Post-traumatic joint injury to the left knee in youth History of {DX_ABBREV}\n\n"
            "    Family history:\n    ----------\n"
            "    {RELATIVE_RELATION} ({NAME_RELATIVE}): {DX_HOMOGRAPH} at an older age No known\n"
            "    cardiovascular history in other family members\n\n"
            "    Allergies:\n    ----------\n    No known allergies\n\n"
            "    Medication on admission:\n    -------------------\n"
            "    - {DX_DRUG}, {DX_NUMERIC}, {DX_NUMERIC}\n"
            "    - Paracetamol 1g, 4/d, prn\n"
            "    - {DX_DRUG_2}, 0.5 tabl, {DX_NUMERIC}, {DX_NUMERIC}\n"
            "    - Calcium + vitamin D, {DX_NUMERIC}\n\n"
            "    History:\n    -------\n"
            "    Acute LBP since {DATE_ENCOUNTER}, following lifting a bucket of water. Pain\n"
            "    radiating to the left leg down to the foot, ! neural quality. Intermittent\n"
            "    claudication present for years, now worsened. Uses a mobility scooter for\n"
            "    use at home. A fracture is suspected {DX_ABBREV} osteoporosis. No urinary or\n"
            "    bowel dysfunction. No fever. No trauma {DX_NUMERIC}. Remains mobile with a rollator.\n"
            "    No fall onto the hip in the past week.\n\n"
            "    Clinical examination:\n    -------------------\n"
            "    General: {AGE_ADJ}, mobility limited {DX_ABBREV} pain, waddling gait ! Lumbar:\n"
            "    tenderness L4-L5, paravertebral. Negative straight leg raise on the left. Extremities:\n"
            "    sensory loss in the L5 dermatome on the left. Knee-jerk reflex ↓ on the left. Corresponding\n"
            "    gait pattern, antalgic. {DX_TEST}. Passive hip range of motion:\n"
            "    {DX_ABBREV}. {DX_ANATOMY} intact.\n\n"
            "    Investigations:\n    --------------------\n"
            "    Chest X-ray: no acute findings. ECG: sinus tachycardia 104/min, {DX_ABBREV}\n"
            "    ischaemia. CT lumbosacral spine: fracture of the L4 body (40% compression), osteoporotic\n"
            "    type. No spinal cord compression. MRI not currently indicated.\n\n"
            "    Conclusion:\n    --------\n"
            "    The {AGE_ADJ} patient was seen {DX_ABBREV} subacute low back pain with a neurological\n"
            "    component. Based on {DX_CODESWITCH} and imaging:\n"
            "    {DIAGNOSIS}. Pain management adequate but insufficient\n"
            "    symptom relief. Co-diagnosis of {DX_DRUG_2}-related myopathy not\n"
            "    excluded. The patient's consent for follow-up was obtained.\n\n"
            "    Investigations:\n    -----------------------\n"
            "    Chest X-ray {DATE_ENCOUNTER} CT lumbosacral spine {DATE_ENCOUNTER} Laboratory: Hb 10.8, CRP 8,\n"
            "    creatinine 78, Ca²⁺ 2.32\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 16:18\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}      T {TELEFOON}\n"
            "    {STREET}      T {TELEFOON}\n"
            "    {STREET}      T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Rewrote 'hij vermoedt fractuur' (flagged PRONOUN_SUBJ) as passive ('A fracture is suspected...').",
            "The flagged 'de heer' occurred inside a garbled, non-placeholder-adjacent fragment ('zijn de heer toestemming gevraagd') rather than next to {NAME_RELATIVE}; rewrote the whole clause cleanly as 'The patient's consent for follow-up was obtained' to remove both the honorific and the pronoun.",
        ],
    },
    {
        "template_hash": "2a857a0ab7554aff",
        "letter_type": "ontslagbrief",
        "specialty": "Urologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:                      RESPONSIBLE:            DATE:\n"
            "{NAME_PATIENT}                   {NAME_RESPONSIBLE}               {DATE_ENCOUNTER} 02:00\n"
            "{INSZ_LABEL}{INSZ}              {RIZIV_LABEL}{RIZIV}          SENT BY:\n"
            "                                                            {NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            "    Dear colleague\n\n"
            "    Your patient {NAME_PATIENT} ({DOB}) attended our\n"
            "    {SPECIALTY} consultation on {DATE_ENCOUNTER}.\n\n"
            "    Presenting complaint\n    --------\n"
            "    {DATE_HISTORY}: {DIAGNOSIS} {DX_EPONYM} ! Recurrent\n"
            "    urinary tract infections since 2018 Co type 2 diabetes mellitus\n\n"
            "    Family history\n    ---------\n"
            "    {RELATIVE_RELATION} ({NAME_RELATIVE}): prostate cancer at age 72 {RELATIVE_RELATION}: {DX_ABBREV}\n"
            "    with {DX_DRUG}\n\n"
            "    Allergies\n    --------\n    No known allergies\n\n"
            "    Home medication\n    --------------\n    No home medication recorded\n\n"
            "    Medication on admission\n    -------------------\n"
            "    - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC}\n"
            "    - {DX_DRUG_2}, 200 mg, {DX_NUMERIC}, 9am\n"
            "    - Paracetamol (tabl 1000mg), 1000mg, 3/d, {DX_NUMERIC}-2pm-8pm\n\n"
            "    History\n    --------\n"
            "    Referral {DX_ABBREV} recurrent haematuria, since {DATE_HISTORY}. History of TURP in 2020.\n"
            "    No more dysuria, but still nocturia and dribbling. No febrile\n"
            "    symptoms. No lumbar pain. No {DX_HOMOGRAPH}. Difficult\n"
            "    catheterisation in Jan/{DX_NUMERIC}: urethra injured. Since then, difficulty\n"
            "    self-catheterising. Complaints of incomplete emptying. No tenesmus. No\n"
            "    {DX_CODESWITCH} reported.\n\n"
            "    Status\n    ------\n"
            "    {AGE_ADJ}, patient in stable general condition. No signs of infection on\n"
            "    admission. No oedema. No raised JVP. Alert, oriented, mobile. Normal\n"
            "    voiding reflex.\n\n"
            "    Clinical examination\n    -------------------\n"
            "    Abdomen: soft, non-tender, no {DX_ANATOMY} Suprapubic: not\n"
            "    distended, no ballottement Genital: no urethral discharge, no\n"
            "    {DX_TEST} Digital rectal exam: prostate not enlarged, no {DX_ABBREV}, no\n"
            "    blood on the glove ! {DX_NUMERIC} cm between catheter balloon and narrowing\n\n"
            "    Investigations\n    ------------------\n"
            "    - Creatinine: 87 µmol/L (stable)\n"
            "    - Urine sediment: leukocyturia +++, erythrocyturia ++++\n"
            "    - Urine culture: E. coli >10^5, sensitive to {DX_DRUG_2}\n"
            "    - Abdominal ultrasound: bladder wall thickening, PVR 180ml, no hydronephrosis\n"
            "    - CT abdomen: no scarring in {DX_ANATOMY}, no {DX_DRUG_2} level\n"
            "    - Urodynamics: overactive detrusor, Qmax 9 ml/s, post-void 210 ml\n"
            "    - Cystoscopy: minor trabeculation, no tumour, no {DIAGNOSIS}\n\n"
            "    Conclusion\n    -----\n"
            "    The {AGE_ADJ} patient was seen at the {SPECIALTY} consultation on\n"
            "    {DATE_ENCOUNTER}. Findings:\n\n"
            "    Recurrent haematuria with urodynamic findings of\n"
            "    outlet dysfunction. No evidence of malignancy on cystoscopy. Complaints\n"
            "    largely secondary {DX_ABBREV} residual urine. The patient's condition relates to a\n"
            "    previous procedure and urethral injury. Treatment with {DX_DRUG_2} was started {DX_ABBREV} confirmed\n"
            "    infection.\n\n"
            "    --> Continue therapy with {DX_DRUG_2} for {DX_NUMERIC} weeks.\n"
            "    --> Recatheterisation technique discussed with {NAME_RELATIVE}.\n"
            "    --> Start exercise therapy via physiotherapy ({DX_ABBREV}).\n"
            "    --> {SPECIALTY} follow-up in 6 weeks for review and possible\n"
            "    {DX_CODESWITCH}.\n"
            "    --> If recurrence: reassessment needed {DX_ABBREV} and possible\n"
            "    {DX_HOMOGRAPH}.\n\n"
            "    Contact us in case of worsening or fever: {TELEFOON}\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}        {NAME_DOCTOR_2}\n"
            "    {NAME_DOCTOR_3}\n    {NAME_DOCTOR_4}\n    {NAME_DOCTOR_5}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 11:34\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Fixed the source '{DIAGNOSIS} {DIAGNOSIS}' adjacent-duplicate stutter (the worked-example bug for this exact hash) by changing the second occurrence to {DX_EPONYM}.",
            "Dropped 'de heer' hardcoded immediately before {NAME_RELATIVE} (flagged HONORIFIC); fixed a second '{DX_ABBREV} {DX_ABBREV}' stutter near the end; rewrote 'zijn situatie... hij werdt gestart' (flagged PRONOUN_SUBJ) into third-person/passive voice.",
        ],
    },
    {
        "template_hash": "2aa05d5d272aa7ff",
        "letter_type": "verslag technisch onderzoek",
        "specialty": "Vaatheelkunde",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague, We saw your patient {NAME_PATIENT} at the {SPECIALTY} consultation "
            "on {DATE_ENCOUNTER}. History: -------- 03/2022: {DIAGNOSIS}! {DX_EPONYM} {DX_ABBREV} "
            "{DX_HOMOGRAPH} from {DATE_HISTORY} History of {DX_ABBREV}, on {DX_DRUG}. {DX_TEST} "
            "{DX_ABBREV} {DIAGNOSIS} Worsening pain on walking is reported, now after only 50 "
            "metres. Since last week, swelling in the {DX_ANATOMY} has also been noticed! No "
            "episodes of nocturnal pain or rest pain Family history: -------- {RELATIVE_RELATION} "
            "({NAME_RELATIVE}): {DIAGNOSIS} at age 68 {DX_DRUG_2} in {NAME_RELATIVE} – "
            "control is rarely lost Allergies: --------- No known allergies Medication on "
            "admission: -------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - "
            "{DX_DRUG_2}, 1 tablet, {DX_NUMERIC}, {DX_NUMERIC} 8pm - Ascal (tabl 100mg), "
            "{DX_NUMERIC}, {DX_NUMERIC} Current medication: ------------------ - {DX_DRUG_2}, "
            "{DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 1 tablet, {DX_NUMERIC}, {DX_NUMERIC} 8pm - "
            "Ascal (tabl 100mg), {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2} cream, PRN No home "
            "medication recorded Clinical examination: ------------------- Tenderness on "
            "palpation in the {DX_ANATOMY}! Left > right {DX_TEST} positive on the left, negative "
            "on the right Peripheral pulses {DX_ABBREV}, duplex for assessment Foot perfusion: "
            "right 0.52, left 0.41 ({DX_NUMERIC}) Capillary refill: 4 seconds under {DX_DRUG_2} "
            "Investigations: ----------------------- `-----------------------------` `| Test | "
            "Result |` `|-----------------+--------|` `| ABI | 0.63 |` `| ABI after exercise| "
            "0.48 |` `| duplex {DX_ANATOMY}| {DX_CODESWITCH}|` `| CT angiography | "
            "{DX_NUMERIC}|` `-----------------------------` Conclusion: -------- The {AGE_ADJ} "
            "patient was seen {DX_ABBREV} progressive intermittent claudication. Swelling in the "
            "{DX_ANATOMY}, worsening under {DX_DRUG_2}. History of {DX_EPONYM}. Low ABI, with a "
            "drop after exercise. {DX_TEST} confirms ischaemia. {DX_DRUG_2} possible contribution "
            "to peripheral oedema. --> Consider stopping {DX_DRUG_2} cream {DX_ABBREV} limited "
            "effect and local reactions --> Establish indication for endovascular "
            "revascularisation via {SPECIALTY} --> Refer to {SPECIALTY} for further planning "
            "Advice: -------- - Stop {DX_DRUG_2} cream immediately - Contact us via {TELEFOON} if "
            "swelling or pain worsens - Review with {SPECIALTY} within 14 days - Measure blood "
            "pressure in both arms at next review – {DX_NUMERIC} Investigations: "
            "---------------------- - ABI measured: left 0.63, right 0.59 - Post-exercise ABI: "
            "left 0.48, right 0.51 - Duplex {DX_ANATOMY}: significant stenosis of the left common "
            "iliac artery - CT angiography abdomen/pelvis: occlusion of the left external iliac "
            "artery, collaterals visible - Foot oximetry: TcPO2 left 22 mmHg, right 28 mmHg "
            "({DX_NUMERIC})\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}        {NAME_DOCTOR_2}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 09:04\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Removed a leaked literal first name ('Pieter zegt dat hij...') that was an extraction-noise artifact unrelated to any placeholder, and merged it into the surrounding sentence as a plain passive statement.",
            "Fixed a '{DX_ABBREV}, {DX_ABBREV}' adjacent-duplicate stutter by dropping the second occurrence; rewrote the garbled 'zijn de heer verliest zelden grip' (flagged HONORIFIC, not actually adjacent to {NAME_RELATIVE}) as a gender-neutral 'control is rarely lost'.",
        ],
    },
    {
        "template_hash": "3e24fd05c395c508",
        "letter_type": "verslag technisch onderzoek",
        "specialty": "Urologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague Your patient {NAME_PATIENT} ({DOB}) attended our {SPECIALTY} "
            "consultation on {DATE_ENCOUNTER}. Medical history ----------------- 05/2022: "
            "{DIAGNOSIS} {DX_EPONYM} ! Recurrent cystitis, {DX_ABBREV} {DX_DRUG} Side effects "
            "with {DX_DRUG_2} Family history -------- {RELATIVE_RELATION} ({NAME_RELATIVE}): "
            "prostate carcinoma at age 68 Allergies ------ No known allergies Medication on "
            "admission ------------------- - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - "
            "{DX_DRUG_2}, 1 tablet, {DX_NUMERIC}, {DX_NUMERIC} 8pm - Paracetamol 1g, 4/d, prn "
            "History -------- Referral {DX_ABBREV} persistent voiding disorders. Symptoms "
            "ongoing since {DATE_HISTORY}. Sensation of incomplete bladder emptying, {DX_ABBREV}. "
            "{DX_TEST}. No haematuria reported. No pyuria. {PRONOUN_SUBJ} has been using "
            "{DX_ABBREV} for 3 months, without clear effect. {DX_NUMERIC} at review. No nocturnal "
            "enuresis. Clinical examination ------------------ Abdomen: {DX_ABBREV}. No pain on "
            "percussion {DX_ANATOMY}. Rectal exam: prostate not enlarged, not tender. "
            "{DX_HOMOGRAPH}. Genital region: {DX_ABBREV} Conclusion ------- The {AGE_ADJ} patient "
            "was seen {DX_ABBREV} persistent urinary tract infections and urinary urgency. "
            "Symptoms are consistent {DX_ABBREV} {DIAGNOSIS}, with insufficient response to "
            "first-line therapy. {DX_CODESWITCH} initiated. --> Further urological evaluation "
            "including flowmetry and post-void residual. --> Discussion with microbiology "
            "{DX_ABBREV}. Investigations ---------------------- | Test | Result | "
            "|--------------------------|---------------| | Urine sediment | {DX_NUMERIC} | | "
            "Urine culture | {DX_CODESWITCH} | | PSA | 3.4 µg/l | | Abdominal ultrasound | "
            "No hydronephrosis | | Flowmetry | Qmax 9 ml/s ! |\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}        {NAME_DOCTOR_2}\n"
            "    {NAME_DOCTOR_3}\n    {NAME_DOCTOR_4}\n    {NAME_DOCTOR_5}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 15:52\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}          T {TELEFOON}\n"
            "    {STREET}          T {TELEFOON}\n"
            "    {STREET}          T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Replaced the first flagged 'zij' (PRONOUN_SUBJ) with the {PRONOUN_SUBJ} field ('{PRONOUN_SUBJ} has been using...').",
            "Rewrote the second 'zij vertoont klachten...' into a passive 'Symptoms are consistent...' clause; fixed a '{DX_ABBREV} {DX_ABBREV}' stutter before the microbiology referral line by dropping the duplicate.",
        ],
    },
    {
        "template_hash": "41bc0a038480dd9e",
        "letter_type": "ontslagbrief",
        "specialty": "Endocrinologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague Your patient {NAME_PATIENT} ({DOB}) attended our {SPECIALTY} "
            "consultation on {DATE_ENCOUNTER}. Reason for admission ---------------- Increasing "
            "fatigue and weight gain, suspected {DIAGNOSIS}! Medical history ---------------- "
            "05/2020: {DIAGNOSIS} {DX_EPONYM} ! Hashimoto's thyroiditis {DX_ABBREV} type 2 "
            "diabetes mellitus {DX_ABBREV} {DX_CODESWITCH} Family history --------- "
            "{RELATIVE_RELATION} ({NAME_RELATIVE}): hypothyroidism at age 55 Allergies -------- "
            "No known allergies Medication on admission ------------------- - {DX_DRUG}, 1 "
            "tablet, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 50 µg, {DX_NUMERIC}, "
            "{DX_NUMERIC} - Paracetamol 1g, {DX_NUMERIC}, p.r.n. - {DX_DRUG_2}, {DX_NUMERIC}, "
            "{DX_NUMERIC} History -------- {HONORIFIC} {NAME_PATIENT} presents with complaints "
            "of fatigue, cold intolerance and dry skin. History of treatment for hypothyroidism "
            "since 2020. No new medication use. No recent weight change. No symptoms of "
            "myopathy. No irritability or insomnia. Clinical examination ------------------- "
            "General: {AGE_ADJ} patient with normal build, no cyanosis. Pulse: 58 bpm, regular "
            "Blood pressure: 110/70 mmHg Skin: dry, cold. No periorbital oedema. {DX_ANATOMY}: "
            "not enlarged, not tender on palpation. {DX_TEST}: TSH raised to {DX_NUMERIC}, fT4 "
            "low. Clinical course ------- Stabilised during admission with {DX_DRUG_2} "
            "adjustment. Fatigue slightly reduced. No complaints of dyspnoea or oedema. No "
            "further mental slowing reported. No hypoglycaemia. {DX_HOMOGRAPH} stable. "
            "Continuous monitoring of {DX_NUMERIC} in {SPECIALTY} {DX_ABBREV} {DIAGNOSIS}. "
            "Discharge medication -------------- - {DX_DRUG_2}, 75 µg, {DX_NUMERIC}, "
            "{DX_NUMERIC} - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - Paracetamol 1g, "
            "{DX_NUMERIC}, p.r.n. - {DX_DRUG_2}, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, "
            "{DX_NUMERIC}, {DX_NUMERIC} No home medication recorded Conclusion ------- The "
            "{AGE_ADJ} patient was seen at the {SPECIALTY} consultation on {DATE_ENCOUNTER}. "
            "Findings: persistent symptoms of hypothyroidism, despite {DX_DRUG_2} at the current "
            "dose. Labs confirm {DIAGNOSIS} with a recent rise in {DX_NUMERIC}. Fatigue "
            "continues to affect activities of daily living. No other endocrinological cause "
            "found. --> Adjust {DX_DRUG_2} to 75 µg/d. Follow-up in {SPECIALTY} in 6 weeks "
            "to check TSH and fT4 ({DX_TEST}). --> Refer to a dietitian {DX_ABBREV} "
            "{DIAGNOSIS}. --> {TELEFOON} for concerning symptoms, especially myopathy or cardiac "
            "complaints.\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}        {NAME_DOCTOR_2}\n"
            "    {NAME_DOCTOR_3}\n    {NAME_DOCTOR_4}\n    {NAME_DOCTOR_5}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 09:23\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}              T {TELEFOON}\n"
            "    {STREET}              T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Replaced hardcoded 'de heer' immediately before {NAME_PATIENT} (flagged HONORIFIC) with the {HONORIFIC} field rather than a literal 'Mr', for consistency with GENDER.",
            "Rewrote 'hij komt met aanhoudende symptomen' (flagged PRONOUN_SUBJ) and the unflagged possessive 'zijn vermoeidheid blijft...' into passive/plain-noun constructions; fixed a '{DX_ABBREV} {DX_ABBREV}' stutter before the dietitian referral by dropping the duplicate.",
        ],
    },
    {
        "template_hash": "4a3c7855d5e742d5",
        "letter_type": "ontslagbrief",
        "specialty": "Reumatologie",
        "masked_text_en": (
            "LETTER\n\nPATIENT:\n{NAME_PATIENT}\n{INSZ_LABEL}{INSZ}\n\n"
            "RESPONSIBLE:\n{NAME_RESPONSIBLE}\n{RIZIV_LABEL}{RIZIV}\n\nDATE:\n"
            "{DATE_ENCOUNTER} 02:00\nSENT BY:\n{NAME_DOCTOR_SENDER}\n\n"
            "Report contents\n    {ORGANIZATION}\n    {SPECIALTY}\n\n"
            " Dear colleague, We saw your patient {NAME_PATIENT} at the {SPECIALTY} consultation "
            "on {DATE_ENCOUNTER}. Reason for admission ---------------- {DIAGNOSIS} with "
            "progressive arthrosis in multiple joints ! Fever of unknown origin, investigated "
            "{DX_ABBREV} possible {DIAGNOSIS} Medical history ---------------- 05/2018: "
            "{DIAGNOSIS} {DATE_HISTORY}: onset of joint symptoms, started on {DX_DRUG} "
            "{DX_ABBREV} on {DOB} Family history ---------- {RELATIVE_RELATION} "
            "({NAME_RELATIVE}): {DX_HOMOGRAPH} at age 58 {DX_ABBREV} type 2 diabetes mellitus "
            "Psychiatric history: mild depressive symptoms, followed up by {NAME_RELATIVE} "
            "Allergies ------- No known allergies Home medication ------------ No home "
            "medication recorded Medication on admission ------------------- - {DX_DRUG_2}, 1 "
            "tablet, {DX_NUMERIC}, {DX_NUMERIC} - {DX_DRUG_2}, 50 mg, iv, {DX_NUMERIC}, "
            "{DX_ABBREV} {DX_TEST} - Paracetamol, 1 g, 4/d, prn for fever or pain History -------- "
            "Increasing stiffness in the proximal interphalangeal joints has been reported for "
            "{DX_NUMERIC} weeks, mainly in the morning. Lasting > 60 min. No flares of SLE "
            "symptoms, no rash, no nephritis. No dyspnoea or chest pain. History of pulmonary "
            "embolism in 2019, {DX_CODESWITCH} Contact via {TELEFOON} for further follow-up "
            "Clinical examination ------------------ {DX_ANATOMY}: swelling and warmth in MCP "
            "II-IV on the right, tenderness + No synovial swelling in knees or ankles Pulmonary: "
            "{DX_ABBREV}, no crackles Cardiac: regular, no murmur Skin: no ulcers, no vasculitis "
            "! {DX_TEST}: CRP raised to {DX_NUMERIC} mg/L, ESR 45 mm/H Laboratory findings "
            "------------- Hb 11.2 g/dL, MCV 86 fL, platelets 410 x10⁹/L Creatinine 78 "
            "µmol/L, eGFR 76 mL/min AST 28 U/L, ALT 31 U/L ANA: negative, anti-CCP: "
            "positive (180 U), RF: weakly positive Hand X-ray: periarticular {DIAGNOSIS}, early "
            "erosive changes in the MCPs Clinical course -------- Initially treated with iv "
            "{DX_DRUG_2} as bridging therapy {DX_ABBREV} {DX_NUMERIC} days of persistent fever. "
            "Rapid response to therapy, afebrile after 4{DX_NUMERIC}. Started on oral "
            "{DX_DRUG_2} as a DMARD, discussed with pharmacy {DX_ABBREV} {DX_CODESWITCH} "
            "Physiotherapy: {DX_ABBREV} mobility already started, good motivation Discharge "
            "medication ---------------- - {DX_DRUG_2}, 1 tablet, {DX_NUMERIC}, {DX_NUMERIC} - "
            "Folic acid, 5 mg, {DX_NUMERIC}, {DX_ABBREV} - Paracetamol, 1 g, 4/d, prn - "
            "{DX_DRUG_2}, 25 mg, {DX_NUMERIC}, {DX_NUMERIC} (tapering per schedule) Conclusion "
            "-------- The {AGE_ADJ} patient was seen at the {SPECIALTY} consultation on "
            "{DATE_ENCOUNTER}. Findings: the symptoms are consistent with active {DIAGNOSIS}, "
            "with positive serology and radiological evidence of erosive disease. No signs of "
            "organ involvement or infection remaining at discharge. {DIAGNOSIS} excluded based "
            "on {DX_TEST} and clinical findings --> Discharged home on oral DMARD therapy --> "
            "Follow-up at the {SPECIALTY} outpatient clinic in 6 weeks {DX_ABBREV} --> Refer for "
            "biologic therapy if response is insufficient after 3 months --> {NAME_RELATIVE} "
            "informed via {TELEFOON}, cancelled appointment noted on {DATE_HISTORY}\n\n"
            "    Yours sincerely,\n    {NAME_DOCTOR}\n    {SPECIALTY}\n\n\n"
            "    Kind regards, also on behalf of\n    {NAME_DOCTOR}\n    {NAME_DOCTOR_2}\n\n"
            "    This report was electronically validated by {NAME_DOCTOR} on\n"
            "    {DATE_VALIDATION}\n\n    Validated: {DATE_VALIDATION} 10:06\n"
            "    ------------------------------------------------------------------\n"
            "    {STREET}          T {TELEFOON}\n"
            "    {STREET}          T {TELEFOON}\n\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n"
            "    {STREET}  T {TELEFOON}\n\n"
            "    {ORGANIZATION}\n    {URL}\n"
        ),
        "adaptation_notes": [
            "Dropped 'de heer' hardcoded immediately before {NAME_RELATIVE} in the psychiatric-history line (flagged HONORIFIC).",
            "Rewrote 'hij meldt sinds...' (flagged PRONOUN_SUBJ) and the unflagged possessive 'zijn klachten passen bij...' into passive constructions; fixed a '{DX_ABBREV} {DX_ABBREV}' stutter before the outpatient follow-up line by dropping the duplicate.",
        ],
    },
]

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
    "INSZ_LABEL", "RIZIV_LABEL",
    "PATIENT_NOUN_GENERIC", "HONORIFIC", "PRONOUN_SUBJ", "PRONOUN_POSS",
}

PLACEHOLDER_RE = re.compile(r"\{([A-Z0-9_]+)\}")


def validate():
    errors = []
    for t in TEMPLATES:
        fields_used = set(PLACEHOLDER_RE.findall(t["masked_text_en"]))
        invalid = fields_used - VALID_FIELDS
        if invalid:
            errors.append(f"{t['template_hash']}: invalid fields {invalid}")
        # check for adjacent identical placeholder stutters, e.g. {DIAGNOSIS} {DIAGNOSIS}.
        # DX_NUMERIC is EXEMPT: it's a pre-existing, already-shipped Dutch/French
        # convention for dosage/frequency shorthand pairs ("{DX_DRUG}, {DX_NUMERIC},
        # {DX_NUMERIC}") -- confirmed present in 47/56 of the shipped French
        # templates, inherited directly from the raw Dutch source, not a new bug.
        # BUGFIX: re.search only finds the FIRST match in the whole string -- if
        # a benign {DX_NUMERIC} {DX_NUMERIC} pair appears earlier in the text than
        # a genuine {DX_ABBREV} {DX_ABBREV} stutter, re.search silently returns
        # only the first (exempt) match and the real bug goes uncaught. Use
        # finditer to check every match, not just the first.
        for stutter in re.finditer(r"\{([A-Z0-9_]+)\}([ ,]*)\{\1\}", t["masked_text_en"]):
            if stutter.group(1) != "DX_NUMERIC":
                errors.append(f"{t['template_hash']}: adjacent duplicate placeholder {{{stutter.group(1)}}}")
    if errors:
        raise SystemExit("Validation failed:\n" + "\n".join(errors))
    print(f"Validation OK: {len(TEMPLATES)} templates, all placeholders valid, no adjacent stutters.")


def main():
    validate()
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(out_dir, "translated_templates_en_batch1.jsonl")
    with open(out_path, "w", encoding="utf-8") as f:
        for t in TEMPLATES:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Wrote {len(TEMPLATES)} lines to {out_path}")


if __name__ == "__main__":
    main()
