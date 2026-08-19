"""
build_ood_set_en_v3_novel_vocab.py -- targeted "does it generalize to
genuinely unseen VOCABULARY" battery for the English track.

Every prior OOD/eval battery (v1, v2, eval_real_en, eval_heldout_templates)
tests generalization to unseen TEMPLATE STRUCTURES -- new sentence shapes,
new document layouts. None of them isolate vocabulary novelty on its own:
whether the model can still correctly tag a NAME/ADDRESS/ORGANIZATION span
built from a city, hospital, or surname it has literally never seen in any
template, in any render, during training.

Design: every document below reuses a FAMILIAR, already-well-represented
sentence structure (the same shapes eval_heldout_templates.jsonl and the
v1/v2 OOD batteries already use) but populates it entirely with RESERVED
vocabulary -- real Belgian cities, real hospital names, and surnames --
confirmed absent from every pool in pii_table_en.py (BELGIAN_CITIES,
HOSPITAL_STANDALONE, HOSPITAL_STEM, all 7 NAMES origin pools) as of
2026-08-19. Isolating the variable this way means a failure here is
attributable to vocabulary novelty specifically, not template novelty
(which the OTHER batteries already cover).

Reserved vocabulary (verified via web search, sources noted inline;
none of it was added to any pii_table_en.py pool -- these entries exist
ONLY here, exclusively as an eval set, and must stay that way):

Cities (real, postal-code-verified):
  Flanders:  Ypres (8900, West Flanders), Poperinge (8970, West Flanders),
             Menen (8930, West Flanders), Wetteren (9230, East Flanders),
             Dilbeek (1700, Flemish Brabant)
  Wallonia:  Fleurus (6220, Hainaut), Perwez (1360, Brabant Wallon)

Hospitals (real, verified via web search):
  UZ Brussel (VUB-affiliated university hospital, Jette),
  Onze-Lieve-Vrouwziekenhuis Aalst (OLV Aalst -- note this is a different,
    longer real name than the generic "Onze-Lieve-Vrouw" STEM already in
    the pool, so it round-trips as a genuinely unseen exact string)

Surnames (broadening beyond each origin pool's current coverage, e.g.
anglophone_africa/anglophone_asia are Nigeria/India-only today -- these
intentionally reach into neighbouring communities the pool doesn't cover
yet, per the honest-small-list precedent: a handful of well-grounded
additions, not a forced-comprehensive list):
  Vandenbroucke (Flemish, common surname absent from the flemish pool),
  Fitzsimmons (UK/Ireland), Mensah (Ghanaian -- broadens anglophone_africa
    past its current Nigeria-only scope), Choudhury (Bangladeshi --
    broadens anglophone_asia past its current India-only scope)

Same marker DSL as build_ood_set_en.py / build_ood_set_en_v2.py
(self-validating round-trip).
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

# 1. Referral letter, familiar structure, entirely reserved city+surname.
DOCS.append(build(
    "en_nv01", "novel_vocab_referral",
    "Familiar referral-letter structure; patient name, address city, and referring "
    "physician surname all reserved (never in any training pool).",
    """Dear colleague,

I am referring my patient, [[NAME|Tobias Vandenbroucke]], born on [[DATE|22/03/1979]],
residing at [[ADDRESS|Ieperstraat 14, 8900 Ypres]], for specialist opinion.

Contact number: [[PHONE|057 33 22 11]]
National Registration No.: [[INSZ|79032210144]]

Referring physician: Dr Fitzsimmons

Kind regards,
Dr Fitzsimmons
"""
))

# 2. Letterhead + hospital name, reserved hospital never in HOSPITAL_STANDALONE/STEM.
DOCS.append(build(
    "en_nv02", "novel_vocab_hospital_letterhead",
    "Familiar letterhead structure with a real Flemish university hospital never in "
    "HOSPITAL_STANDALONE or HOSPITAL_STEM.",
    """[[ORGANIZATION|UZ Brussel]]
Laarbeeklaan 101, 1090 Jette
www.uzbrussel.be

Re: [[NAME|Chidera Mensah]]

Dear colleague,

Your patient was seen in our department. Patient contact details:
[[ADDRESS|Kerkstraat 9, 8970 Poperinge]], tel [[PHONE|057 44 12 09]].

Kind regards,
[[ORGANIZATION|UZ Brussel]] - Cardiology Department
"""
))

# 3. Discharge-style note, reserved city (Wallonia) + reserved surname.
DOCS.append(build(
    "en_nv03", "novel_vocab_discharge",
    "Familiar discharge-note structure; Wallonia city and Bangladeshi-origin surname "
    "both reserved, broadening the anglophone_asia pool past its current India-only scope.",
    """DISCHARGE SUMMARY

Patient: [[NAME|Rafiq Choudhury]]
Date of birth: [[DATE|5 June 1988]]

Reason for admission:
- Abdominal pain, admitted on [[DATE|Tuesday 3 March 2026]]

Follow-up:
- GP review in 2 weeks
- Reachable on [[PHONE|071 22 45 60]]
- Home address: [[ADDRESS|Rue de Charleroi 18, 6220 Fleurus]]

Kind regards,
Dr Mensah, General Medicine
"""
))

# 4. Lab report letterhead, reserved hospital (Flemish, longer real full name
#    distinct from the generic "Onze-Lieve-Vrouw" STEM already in the pool).
DOCS.append(build(
    "en_nv04", "novel_vocab_lab_letterhead",
    "Familiar lab-report letterhead; hospital's full real name (OLV Aalst) is a "
    "genuinely different string from the generic 'Onze-Lieve-Vrouw' stem the pool "
    "already produces, so this specifically probes the FULL-NAME variant, not the stem.",
    """[[ORGANIZATION|Onze-Lieve-Vrouwziekenhuis Aalst]]
CLINICAL LABORATORY

Patient: [[NAME|Ines Vandenbroucke]]
National Registration No.: [[INSZ|88112310177]]

Requesting physician: Dr Choudhury

Address on file: [[ADDRESS|Zavelstraat 6, 9230 Wetteren]]
Contact: [[PHONE|09 365 77 12]]
"""
))

# 5. Inline mid-sentence mention, no label cue -- reserved city + surname,
#    mirrors the inline_address category from build_ood_set_en.py but with
#    entirely reserved vocabulary instead of pool-drawn vocabulary.
DOCS.append(build(
    "en_nv05", "novel_vocab_inline",
    "Address and name embedded mid-sentence with no label cue, using only reserved "
    "vocabulary -- tests whether positional/contextual cues alone (not memorized "
    "strings) drive detection.",
    """I am writing because my father, [[NAME|Patrick Fitzsimmons]], who lives at
[[ADDRESS|Brusselsestraat 45 in Dilbeek]], has been feeling unwell since last week.
You can reach him on [[PHONE|02 569 88 21]] or reach me on [[PHONE|0470 12 98 44]].
His National Registration No. is [[INSZ|55081410163]].
"""
))

# 6. Sick-note-style form, reserved Wallonia city + surname, checkbox register
#    (mirrors genre_sick_note_en's structure without reusing its literal text).
DOCS.append(build(
    "en_nv06", "novel_vocab_form",
    "Familiar form-register structure (identity block + narrative line), entirely "
    "reserved vocabulary throughout.",
    """PATIENT DECLARATION

Name: [[NAME|Efua Mensah]]
National Registration No.: [[INSZ|91042210198]]
Address: [[ADDRESS|Place Communale 2, 1360 Perwez]]
Telephone: [[PHONE|081 65 44 20]]

Treating physician: Dr Vandenbroucke, seen on [[DATE|14/02/2026]].
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_en_v3_novel_vocab.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} English novel-vocabulary OOD documents to {OUT_PATH}")
