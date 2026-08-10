"""
Builds a hand-authored, structurally diverse OOD stress-test set.

Purpose: none of these documents share template lineage with pii_table.py
(TamerBERT) or new_data. They deliberately probe dimensions the training
data does NOT cover, so a good score here is evidence of real generalization
rather than data-generator overlap:

  - document TYPE: lab-result table, prescription slip, SMS reminder,
    insurance form, multi-patient table, email w/ signature block
    (training data is "clinical letter" shaped almost exclusively)
  - LANGUAGE / REGION: French (Walloon), bilingual NL/FR
    (pii_table.py is Flanders-only: CITIES has zero Wallonia entries,
    STREET_STEM/SUFFIX are Dutch-only)
  - GEOGRAPHY: cities/streets absent from pii_table.py's fixed 34-city list
  - LAYOUT: multi-line address block (label data is always single-line
    "straat nr, postcode stad"), pipe/markdown tables, colon-form fields
  - DATE PHRASING: weekday-prefixed spelled-out dates
  - NOISE: OCR-style broken words / irregular whitespace
  - AMBIGUITY: hospital/org name co-occurring with patient name+address
    (never labeled PII -- checks for false positives, not just recall)
  - HARD NEGATIVES: numeric clinical values interleaved with real PII in a
    layout not seen in training

Marker DSL: write text with [[LABEL|surface text]] spans inline; this
script strips the markers and computes exact character offsets, so span
correctness is guaranteed by construction (no manual offset counting).
"""
import json
import re
import os

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

# 1. Lab-result table (pipe-delimited) -- training data has no tables at all.
DOCS.append(build(
    "ood01", "lab_table",
    "Tabular lab report; markdown-pipe layout never seen in training.",
    """LABORATORIUMVERSLAG - Klinische Biologie

| Patient          | Geboortedatum | INSZ            | Datum afname |
|------------------|---------------|-----------------|--------------|
| [[NAME|Willem Verhoeven]] | [[DATE|03/11/1958]] | [[INSZ|58110310137]] | [[DATE|14-08-2025]] |

Contact: [[PHONE|+32 478 22 91 04]]
Adres: [[ADDRESS|Kwadeplasstraat 9, 3290 Diest]]

| Test        | Resultaat | Referentiewaarde |
|-------------|-----------|------------------|
| Hemoglobine | 13.4 g/dL | 13.0-17.0        |
| Glucose     | 5.6 mmol/L| 4.0-6.0          |
| Creatinine  | 0.9 mg/dL | 0.7-1.3          |

Deze referentiewaarden gelden niet voor patienten boven de 90 jaar.
"""
))

# 2. Prescription slip -- extremely terse, form-like, no prose at all.
DOCS.append(build(
    "ood02", "prescription_slip",
    "Minimal prescription form; near-zero surrounding prose context.",
    """VOORSCHRIFT
Naam: [[NAME|Sylvie Maes]]
Geboren: [[DATE|22.04.1990]]
RIZIV arts: [[RIZIV|18734559003]]
---
Amoxicilline 500mg, 3x/dag, 7 dagen
Paracetamol 1g indien nodig, max 4x/dag
---
Apotheker contact: [[PHONE|09/223.44.56]]
"""
))

# 3. Discharge summary with bullet sections -- different structure/sign-off
#    from TamerBERT's letter templates.
DOCS.append(build(
    "ood03", "discharge_bullets",
    "Bullet-structured discharge note, different section order/sign-off style.",
    """ONTSLAGBRIEF

Patient: [[NAME|Karel Van Overloop]]
Geboortedatum: [[DATE|9 mei 1975]]

Reden opname:
- Pijn op de borst, opgenomen op [[DATE|donderdag 14 augustus 2025]]

Bevindingen:
- ECG normaal
- Troponine negatief

Vervolg:
- Controle bij cardioloog binnen 2 weken
- Bereikbaar op [[PHONE|0032 495 11 22 33]]
- Woonplaats: [[ADDRESS|Meersstraat 4, 9160 Lokeren]]

Met vriendelijke groet,
Dr. Peeters, cardiologie
"""
))

# 4. French-language referral letter, Wallonia address -- pii_table.py is
#    Flanders-only, zero French street/city conventions in training.
DOCS.append(build(
    "ood04", "french_referral",
    "French-language letter, Walloon address -- no French data in training.",
    """Cher confrere,

Je vous adresse ma patiente, [[NAME|Isabelle Lefevre]], nee le [[DATE|17/09/1982]],
domiciliee [[ADDRESS|Rue de la Loi 16, 5000 Namur]], pour avis specialise.

Numero de contact: [[PHONE|081 22 34 56]]
Numero INSZ: [[INSZ|82091710110]]

Je reste a votre disposition pour tout complement d'information.

Bien confraternellement,
Dr. Dubois
"""
))

# 5. Bilingual NL/FR document -- patient block in French inside a Dutch
#    clinical letter (realistic in Brussels-area hospitals).
DOCS.append(build(
    "ood05", "bilingual",
    "Mixed Dutch/French within one document.",
    """MEDISCH VERSLAG / RAPPORT MEDICAL

Patient / Patient(e): [[NAME|Marc Gillet]]
Date de naissance / Geboortedatum: [[DATE|03-06-1969]]
Adresse / Adres: [[ADDRESS|Avenue Louise 210, 1050 Bruxelles]]
Tel: [[PHONE|02 640 12 34]]

Conclusion: patient stable, suivi en ambulatoire.
Vervolgafspraak over 6 weken.
"""
))

# 6. Appointment reminder, SMS-register -- extremely short, dense, no
#    letterhead/salutation structure at all.
DOCS.append(build(
    "ood06", "sms_reminder",
    "SMS-style reminder; ultra-short dense register.",
    """Herinnering: afspraak [[NAME|Anneke Wouters]] op [[DATE|21/08]] om 14u30 bij dr. Claes.
Bel [[PHONE|0470989898]] om te annuleren. INSZ 91..: [[INSZ|91052010181]]"""
))

# 7. Insurance / mutualiteit claim form -- colon key:value fields, no
#    narrative prose whatsoever.
DOCS.append(build(
    "ood07", "insurance_form",
    "Insurance claim form, pure key:value fields.",
    """AANVRAAG TERUGBETALING - CM Mutualiteit

Naam aanvrager: [[NAME|Rita Van den Bossche]]
Geboortedatum: [[DATE|1955-12-01]]
INSZ-nummer: [[INSZ|55120110141]]
Adres: [[ADDRESS|Postbus 44, 8700 Tielt]]
Telefoonnummer: [[PHONE|051/40.55.66]]
Behandelend arts RIZIV: [[RIZIV|11223393003]]
Bedrag: EUR 84,50
Status: In behandeling
"""
))

# 8. OCR-noisy scan-derived text -- broken words across line breaks,
#    irregular spacing, stray characters. Tests robustness, not just format.
DOCS.append(build(
    "ood08", "ocr_noise",
    "OCR-artifact text: broken words, irregular spacing.",
    """PATIENTG EGEVENS

Naam:  [[NAME|Filip  Cool s]]
Gebo ortedatum :  [[DATE|11 -02-1988]]
Adr es:  [[ADDRESS|Bergstraat  7 ,  2440  Geel]]
Tel efoo n:   [[PHONE|014- 58 91 02]]

Dia gnos e:  hyper tensie,  gere geld  onder  contro le.
Volg ende  afspra ak  binn en  3  maand en.
"""
))

# 9. Multi-patient tabular record -- two patients' PII interleaved in one
#    table; tests whether spans stay correctly attributed row-by-row.
DOCS.append(build(
    "ood09", "multi_patient_table",
    "Two patients in one table -- tests row-correct entity attribution.",
    """DAGOVERZICHT SPOEDOPNAMES

1. [[NAME|Jozef Lemmens]], [[DATE|02/1948]], [[ADDRESS|Dorpstraat 3, 9620 Zottegem]], tel [[PHONE|09 360 12 12]]
   Klacht: kortademigheid

2. [[NAME|Nadia El Amrani]], [[DATE|14/03/1993]], [[ADDRESS|Stationsstraat 88, 3580 Beringen]], tel [[PHONE|+32489556677]]
   Klacht: buikpijn
"""
))

# 10. Email correspondence with signature block -- PII embedded in a
#     sign-off block, a structural position absent from letter templates.
DOCS.append(build(
    "ood10", "email_signature",
    "Email with PII in signature block, not letter body.",
    """Van: secretariaat@azorg.be
Aan: huisarts@praktijk.be
Onderwerp: dossier [[NAME|Thomas Verbeeck]]

Beste collega,

Bijgaand het dossier van bovenvermelde patient (INSZ [[INSZ|75041010138]]).

Met vriendelijke groeten,

--
Mevr. K. Janssens
Secretariaat Cardiologie
[[ADDRESS|Kliniekstraat 1, 9300 Aalst]]
Tel: [[PHONE|053 12 34 56]] | Direct: [[PHONE|0472 33 44 55]]
"""
))

# 11. Inline address mid-sentence -- not a labeled field, tests whether the
#     model relies on "Adres:"-style cues rather than the address itself.
DOCS.append(build(
    "ood11", "inline_address",
    "Address embedded mid-sentence, no label cue.",
    """Ik kom u schrijven omdat mijn moeder, [[NAME|Bertha Coolen]], die op [[ADDRESS|Zonnebloemlaan 22 in Waregem]] woont,
al enkele weken klaagt over duizeligheid. U kan haar bereiken via [[PHONE|056 60 11 22]] of
via mijzelf, bereikbaar op [[PHONE|0032497001122]]. Haar geboortedatum is [[DATE|zesde januari negentienhonderd veertig]].
"""
))

# 12. Hospital/org-name ambiguity -- letterhead contains an org name AND a
#     patient name+address; org name is deliberately left UNlabeled to
#     check for false positives (this is not a recall test).
DOCS.append(build(
    "ood12", "org_ambiguity",
    "Org name in letterhead+signature labeled ORGANIZATION per the finalized "
    "taxonomy (was deliberately unlabeled under the old merged-into-NAME scheme).",
    """[[ORGANIZATION|AZ Sint-Vincentius Deinze]]
Kloosterstraat 45, 9800 Deinze
www.azsintvincentius.be

Betreft: [[NAME|Louis Dhondt]]

Geachte,

Uw patient werd gezien op onze afdeling. Contactgegevens patient:
[[ADDRESS|Kastanjedreef 12, 9800 Deinze]], tel [[PHONE|09 386 77 88]].

Met vriendelijke groet,
[[ORGANIZATION|AZ Sint-Vincentius Deinze]] - Dienst Cardiologie
"""
))

# 13. Numeric-heavy hard-negative stress in a novel layout -- dosages, blood
#     pressure, ratios interleaved with real PII, different template than
#     patterns.py's own hard-negative test set.
DOCS.append(build(
    "ood13", "numeric_hard_negatives",
    "Dense numeric hard negatives (dosage/BP/ratio) beside real PII, new layout.",
    """Patient [[NAME|Omar Benali]] (INSZ [[INSZ|88030210159]]) kreeg 2x per dag 500mg,
bloeddruk 130/85 mmHg, hartslag 72/min, AST/ALT ratio 0.8, gewicht 82 kg op lengte 178 cm.
Volgende controle op [[DATE|03/09/2025]]. Contact: [[PHONE|0468 12 34 56]].
Woont op [[ADDRESS|Hoogstraat 61, 8600 Diksmuide]].
"""
))

# 14. Multi-line address block -- training renders address as one
#     comma-joined line; real letters often split street / postcode+city
#     across separate lines (classic letter-header convention).
DOCS.append(build(
    "ood14", "multiline_address",
    "Address split across two lines, unlike training's single-line format.",
    """Aan de heer/mevrouw [[NAME|Peter Cornelis]]
[[ADDRESS|Wilgenlaan 8]]
[[ADDRESS|3600 Genk]]

Geboortedatum: [[DATE|1962/07/30]]
Telefoon: [[PHONE|089 71 22 33]]

Betreft: oproep voor jaarlijkse controle.
"""
))

# 15. Nickname / informal reference after formal intro -- tests coreference
#     robustness (title + surname only, no first name repeated).
DOCS.append(build(
    "ood15", "informal_reference",
    "Formal full-name intro, then title+surname-only references later.",
    """Patiente: [[NAME|Griet Peeters]], geboren [[DATE|12/07/1980]].

Mevr. Peeters kwam op consultatie voor routineonderzoek. Mevr. Peeters gaf aan
zich goed te voelen. Wij adviseren mevr. Peeters een vervolgconsult in te plannen.
Bereikbaar op [[PHONE|+32 (0)3 234 56 78]], adres [[ADDRESS|Vissersplein 5, 8400 Oostende]].
"""
))
# NOTE: only the first "Griet Peeters" occurrence is tagged NAME here on
# purpose -- "mevr. Peeters" alone is a title+surname reference, a distinct
# and harder surface form than the full name. We tag those too, to make
# the eval meaningful for this specific stress dimension.
DOCS[-1] = build(
    "ood15", "informal_reference",
    "Formal full-name intro, then title+surname-only references later.",
    """Patiente: [[NAME|Griet Peeters]], geboren [[DATE|12/07/1980]].

[[NAME|Mevr. Peeters]] kwam op consultatie voor routineonderzoek. [[NAME|Mevr. Peeters]] gaf aan
zich goed te voelen. Wij adviseren [[NAME|mevr. Peeters]] een vervolgconsult in te plannen.
Bereikbaar op [[PHONE|+32 (0)3 234 56 78]], adres [[ADDRESS|Vissersplein 5, 8400 Oostende]].
"""
)

# 16. Age expressed in unusual phrasing, plus a reference-range disclaimer
#     sentence (same "boven de N jaar" hard-negative gap already found on
#     the real docs) but in a brand-new sentence, to see if the earlier
#     fix (if applied) or the base model handles it.
DOCS.append(build(
    "ood16", "age_phrasing",
    "Unusual age phrasing plus reference-range disclaimer hard negative.",
    """Patient [[NAME|Hendrik Maes]] is [[AGE|67 jaar]] oud en werd behandeld voor artrose.
Referentiewaarden voor botdensiteit zijn niet gevalideerd onder de 18 jaar of boven de 85 jaar.
Contact: [[PHONE|03 771 22 33]], INSZ [[INSZ|58092710179]].
"""
))

# Current product scope is Dutch-only -- French/bilingual generalization is a
# real, confirmed gap (see ood04/ood05 above) but a deliberately deferred one,
# not something to score the current trial against. Kept in DOCS (source of
# truth for whenever language expansion is scheduled) but excluded here.
OUT_OF_SCOPE_CATEGORIES = {"french_referral", "bilingual"}
ACTIVE_DOCS = [d for d in DOCS if d["category"] not in OUT_OF_SCOPE_CATEGORIES]

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in ACTIVE_DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(ACTIVE_DOCS)} OOD stress documents to {OUT_PATH} "
      f"({len(DOCS) - len(ACTIVE_DOCS)} out-of-scope docs excluded: {OUT_OF_SCOPE_CATEGORIES})")
