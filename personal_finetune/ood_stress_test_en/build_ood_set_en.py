"""
build_ood_set_en.py -- first English OOD stress-test battery. Direct
structural port of personal_finetune/ood_stress_test_fr/build_ood_set_fr.py
(same marker DSL, same document-type-diversity philosophy: none of these 17
documents share template lineage with pii_table_en.py, so a good score here
is evidence of real generalization, not data-generator overlap).

No prior English OOD battery exists to seed categories 1-2 from (French had
the Dutch battery's ood04/ood05 to reuse) -- both are authored fresh here
instead, in the locked-in register ("Belgian doctor writing in English",
nationally distributed, British/international spelling, National
Registration No./NIHDI No. label terms, expat + native Belgian name mix).

Structural/mechanical categories (3-16) ported directly, content
re-authored in English/Belgian-national context. Category 17
(municipality_homograph_stress) is authored fresh for English -- French's
own Marche/Bouillon/Mons word-collisions don't translate, so this reuses the
independently-researched English-specific DISTRACTORS["municipality_homograph"]
pool already built into pii_table_en.py (Spa/Peer/Ways/Marche -- real
Belgian place names that are also ordinary English words), used here at
OOD-document density rather than the single-slot-per-document rate the
training augmentation applies.
"""
import json
import os
import re

MARKER = re.compile(r"\[\[([A-Z_]+)\|(.*?)\]\]", re.S)


def build(doc_id, category, note, raw_text):
    spans = []
    out = []
    pos = 0
    last_end = 0
    for m in MARKER.finditer(raw_text):
        out.append(raw_text[last_end:m.start()])
        pos += len(raw_text[last_end:m.start()])
        label, surface = m.group(1), m.group(2)
        start = pos
        out.append(surface)
        pos += len(surface)
        end = pos
        spans.append({"start": start, "end": end, "label": label})
        last_end = m.end()
    out.append(raw_text[last_end:])
    text = "".join(out)
    for sp in spans:
        surface = text[sp["start"]:sp["end"]]
        assert MARKER.search("[[" + sp["label"] + "|" + surface + "]]"), \
            f"{doc_id}: span text {surface!r} doesn't round-trip"
    return {"id": doc_id, "category": category, "note": note, "text": text, "spans": spans}


DOCS = []

# 1. Referral letter -- standard "Belgian doctor writing in English" register,
#    no seed battery to reuse (first English OOD battery), authored fresh.
DOCS.append(build(
    "en_ood01", "referral_letter",
    "Standard referral letter, structurally independent of the trained template bank.",
    """Dear colleague,

I am referring my patient, [[NAME|Isabelle Lefevre]], born on [[DATE|17/09/1982]],
residing at [[ADDRESS|Rue de la Loi 16, 5000 Namur]], for specialist opinion.

Contact number: [[PHONE|081 22 34 56]]
National Registration No.: [[INSZ|82091710110]]

I remain at your disposal for any further information.

Kind regards,
Dr Dubois
"""
))

# 2. Trilingual letterhead -- Brussels/Belgium is officially bilingual and
#    English-track documents are explicitly "English as lingua franca" per
#    the locked-in demographics decision, so a Dutch/French administrative
#    heading over otherwise-English prose is realistic, not contrived.
DOCS.append(build(
    "en_ood02", "trilingual_letterhead",
    "Dutch/French administrative heading, English clinical prose beneath it -- realistic "
    "for an expat patient at a Brussels-area hospital.",
    """MEDISCH VERSLAG / RAPPORT MEDICAL / MEDICAL REPORT

Patient: [[NAME|Sarah Van Damme]]
Date of birth: [[DATE|03-06-1969]]
Address: [[ADDRESS|Avenue Louise 210, 1050 Brussels]]
Tel: [[PHONE|02 640 12 34]]

Conclusion: patient stable, outpatient follow-up. Vervolgafspraak over 6 weken.
"""
))

# 3. Lab-result table -- distinct pipe-delimited layout from genre_lab_report_en
#    (fewer columns, no section headers) -- genuinely a novel table shape.
DOCS.append(build(
    "en_ood03", "lab_table",
    "Tabular lab report, compact 4-column layout distinct from the trained genre template.",
    """LABORATORY REPORT - Clinical Biology

| Patient          | Date of birth      | National Reg. No. | Collection date  |
|------------------|--------------------|--------------------|--------------------|
| [[NAME|Willem Rossi]] | [[DATE|03/11/1958]] | [[INSZ|58110310137]] | [[DATE|14-08-2025]] |

Contact: [[PHONE|+32 478 22 91 04]]
Address: [[ADDRESS|Rue de la Station 9, 5030 Gembloux]]

| Test        | Result    | Reference range |
|-------------|-----------|------------------|
| Haemoglobin | 13.4 g/dL | 13.0-17.0        |
| Glucose     | 5.6 mmol/L| 4.0-6.0          |
| Creatinine  | 0.9 mg/dL | 0.7-1.3          |

These reference ranges do not apply to patients over 90 years of age.
"""
))

# 4. Prescription slip -- terse, form-like, near-zero prose.
DOCS.append(build(
    "en_ood04", "prescription_slip",
    "Minimal prescription form; near-zero surrounding prose context.",
    """PRESCRIPTION
Name: [[NAME|Sylvie Marchal]]
Date of birth: [[DATE|22.04.1990]]
Prescriber NIHDI No.: [[RIZIV|18734559003]]
---
Amoxicillin 500mg, 3x/day, 7 days
Paracetamol 1g as needed, max 4x/day
---
Pharmacist contact: [[PHONE|081/22.44.56]]
"""
))

# 5. Discharge summary, bullet sections -- different structure/sign-off.
DOCS.append(build(
    "en_ood05", "discharge_bullets",
    "Bullet-structured discharge note, different section order/sign-off style.",
    """DISCHARGE SUMMARY

Patient: [[NAME|Karel Toussaint]]
Date of birth: [[DATE|9 May 1975]]

Reason for admission:
- Chest pain, admitted on [[DATE|Thursday 14 August 2025]]

Findings:
- ECG normal
- Troponin negative

Follow-up:
- Cardiology review in 2 weeks
- Reachable on [[PHONE|0032 495 11 22 33]]
- Home address: [[ADDRESS|Rue du Moulin 4, 6000 Charleroi]]

Kind regards,
Dr Georges, Cardiology
"""
))

# 6. SMS-register reminder -- extremely short, dense, no letterhead at all.
DOCS.append(build(
    "en_ood06", "sms_reminder",
    "SMS-style reminder; ultra-short dense register.",
    """Reminder: appt for [[NAME|Anne Wery]] on [[DATE|21/08]] at 2.30pm with dr. Simon.
Call [[PHONE|0470989898]] to cancel. Nat. Reg. No 91..: [[INSZ|91052010181]]"""
))

# 7. Health-fund reimbursement claim form -- Belgian "mutualiteit"/"mutuelle"
#    sickness fund, expat-relevant since these funds do issue English-
#    language correspondence to international members.
DOCS.append(build(
    "en_ood07", "insurance_form",
    "Health-fund reimbursement claim form, pure key:value fields.",
    """REIMBURSEMENT CLAIM - Solidaris Health Fund

Claimant name: [[NAME|Rita Fontaine]]
Date of birth: [[DATE|1955-12-01]]
National Registration No.: [[INSZ|55120110141]]
Address: [[ADDRESS|PO Box 44, 7800 Ath]]
Telephone number: [[PHONE|068/40.55.66]]
Treating physician NIHDI No.: [[RIZIV|11223393003]]
Amount: EUR 84.50
Status: Under review
"""
))

# 8. OCR-noisy scan-derived text -- broken words, irregular spacing.
DOCS.append(build(
    "en_ood08", "ocr_noise",
    "OCR-artifact text: broken words, irregular spacing.",
    """PATI ENT  DATA

Name :  [[NAME|Philippe  Delcour t]]
Da te of bi rth :  [[DATE|11 -02-1988]]
Add ress :  [[ADDRESS|Rue du Chene  7 ,  5300  Andenne]]
Tel ephon e :   [[PHONE|085- 58 91 02]]

Dia gnos is :  hyper tension,  well  contro lled.
Nex t  cons ultat ion  in  3  months.
"""
))

# 9. Multi-patient tabular record -- row-correct entity attribution.
DOCS.append(build(
    "en_ood09", "multi_patient_table",
    "Two patients in one table -- tests row-correct entity attribution.",
    """EMERGENCY ADMISSIONS SUMMARY

1. [[NAME|Joseph Lambert]], [[DATE|02/1948]], [[ADDRESS|Rue de l'Eglise 3, 7700 Mouscron]], tel [[PHONE|056 360 12 12]]
   Complaint: shortness of breath

2. [[NAME|Nadia El Amrani]], [[DATE|14/03/1993]], [[ADDRESS|Chaussee de Charleroi 88, 6000 Charleroi]], tel [[PHONE|+32489556677]]
   Complaint: abdominal pain
"""
))

# 10. Email correspondence with signature block.
DOCS.append(build(
    "en_ood10", "email_signature",
    "Email with PII in signature block, not letter body.",
    """From: secretariat@chuliege.be
To: gp@practice.be
Subject: file for [[NAME|Thomas Servais]]

Dear colleague,

Please find attached the file for the above-named patient (National Registration No. [[INSZ|75041010138]]).

Kind regards,

--
Mrs K. Bertrand
Cardiology Secretariat
[[ADDRESS|Rue de la Citadelle 1, 4000 Liege]]
Tel: [[PHONE|04 12 34 56]] | Direct: [[PHONE|0472 33 44 55]]
"""
))

# 11. Inline address mid-sentence -- no label cue.
DOCS.append(build(
    "en_ood11", "inline_address",
    "Address embedded mid-sentence, no label cue.",
    """I am writing because my mother, [[NAME|Bertha Collard]], who lives at [[ADDRESS|Avenue des Tilleuls 22 in Wavre]],
has been complaining of dizziness for several weeks. You can reach her on [[PHONE|010 60 11 22]] or
reach me on [[PHONE|0032497001122]]. Her date of birth is the [[DATE|sixth of January nineteen forty]].
"""
))

# 12. Hospital/org-name ambiguity -- real Belgian hospital, letterhead+signature.
DOCS.append(build(
    "en_ood12", "org_ambiguity",
    "Real Belgian hospital name in letterhead+signature, labeled ORGANIZATION.",
    """[[ORGANIZATION|CHR de la Citadelle]]
Boulevard du Douzieme de Ligne 1, 4000 Liege
www.chrcitadelle.be

Re: [[NAME|Louis Halleux]]

Dear colleague,

Your patient was seen in our department. Patient contact details:
[[ADDRESS|Rue des Ecoles 12, 4000 Liege]], tel [[PHONE|04 386 77 88]].

Kind regards,
[[ORGANIZATION|CHR de la Citadelle]] - Cardiology Department
"""
))

# 13. Numeric-heavy hard-negative stress in a novel layout.
DOCS.append(build(
    "en_ood13", "numeric_hard_negatives",
    "Dense numeric hard negatives (dosage/BP/ratio) beside real PII, new layout.",
    """Patient [[NAME|Omar Benali]] (National Registration No. [[INSZ|88030210159]]) received 500mg twice daily,
blood pressure 130/85 mmHg, heart rate 72/min, AST/ALT ratio 0.8, weight 82 kg for a height of 178 cm.
Next review on [[DATE|03/09/2025]]. Contact: [[PHONE|0468 12 34 56]].
Lives at [[ADDRESS|Rue Haute 61, 6460 Chimay]].
"""
))

# 14. Multi-line address block -- training renders address as one
#     comma-joined line; real letters often split street / postcode+city.
DOCS.append(build(
    "en_ood14", "multiline_address",
    "Address split across two lines, unlike training's single-line format.",
    """For the attention of [[NAME|Pierre Cornet]]
[[ADDRESS|Rue des Bouleaux 8]]
[[ADDRESS|6900 Marche-en-Famenne]]

Date of birth: [[DATE|1962/07/30]]
Telephone: [[PHONE|084 71 22 33]]

Re: invitation for annual check-up.
"""
))

# 15. Title+surname-only coreference after formal intro.
DOCS.append(build(
    "en_ood15", "informal_reference",
    "Formal full-name intro, then title+surname-only references later.",
    """Patient: [[NAME|Griet Delvaux]], born [[DATE|12/07/1980]].

[[NAME|Ms Delvaux]] attended for a routine check-up. [[NAME|Ms Delvaux]] reported
feeling well. We advise [[NAME|ms Delvaux]] to schedule a follow-up appointment.
Reachable on [[PHONE|+32 (0)4 234 56 78]], address [[ADDRESS|Place Saint-Nicolas 5, 4800 Verviers]].
"""
))

# 16. Age phrasing + reference-range disclaimer hard negative.
DOCS.append(build(
    "en_ood16", "age_phrasing",
    "Unusual age phrasing plus reference-range disclaimer hard negative.",
    """Patient [[NAME|Hendrik Georges]] is [[AGE|67 years of age]] and was treated for osteoarthritis.
Reference values for bone density are not validated below 18 years of age or above 85 years of age.
Contact: [[PHONE|03 771 22 33]], National Registration No. [[INSZ|58092710179]].
"""
))

# 17. English-specific municipality-homograph stress -- dense use of the
#     independently-researched real Belgian place names that are also
#     ordinary English words (Spa/Peer/Ways/Marche -- see
#     pii_table_en.py DISTRACTORS["municipality_homograph"]), used here at
#     eval-document density (four collisions in one short document) rather
#     than the training augmentation's one-slot-per-document rate.
DOCS.append(build(
    "en_ood17", "municipality_homograph_stress",
    "Dense use of real Belgian-municipality/English-word homographs (Spa/Peer/Ways/Marche), "
    "the English-specific equivalent of French's Marche/Bouillon/Mons stress case.",
    """Patient [[NAME|Andre Piette]] (National Registration No. [[INSZ|60031553505]]) was referred
for a spa treatment course and reviewed by a peer prior to discharge. Several treatment ways were
explored before the patient will march to full recovery. No complaints on catheter insertion.
Home address: [[ADDRESS|Rue de Namur 14, 6800 Libramont-Chevigny]], tel [[PHONE|061 22 33 44]].
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_en.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} English OOD stress documents to {OUT_PATH}")
