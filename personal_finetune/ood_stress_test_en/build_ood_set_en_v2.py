"""
build_ood_set_en_v2.py -- second English OOD stress-test battery. Direct
structural port of
personal_finetune/ood_stress_test_fr/build_ood_set_fr_v2.py.

Categories already covered on the AUGMENTATION side for English (casing via
xf_casing, honorific variety via xf_diacritic_honorific, mojibake via
xf_mojibake) still get ONE fresh eval-only instance here, since a held-out
eval document must be independent of whatever the training augmentation
happened to sample -- that's the whole point of an eval set.

Two categories are authored fresh rather than translated, per the plan's
explicit Phase 9 instruction to author genuinely language/content-specific
categories rather than force-fitting a French pattern that doesn't apply:
  - name_multiword_surname (en_v2_01): French's particle surnames (du Bois,
    de la Croix) have no English analogue. The equivalent stress case for
    English's expat-driven name pools is multi-word/compound surnames from
    the SAME origin pools pii_table_en.py actually samples from -- British
    double-barrelled, Irish Mc/O'-prefixed, and Nigerian/Anglophone-African
    compound surnames.
  - foreign_phone_scope_probe (en_v2_06): adapted (not fresh) but reframed
    around the English track's own locked-in demographics decision -- a
    Belgian-registered patient with a UK/Irish family contact abroad is the
    direct, in-character equivalent of French's Belgian-patient/French-
    mobile probe, rather than an arbitrary substitution.

Same marker DSL as build_ood_set_en.py (self-validating round-trip).
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

# 1. ENGLISH-SPECIFIC: multi-word/compound surnames from the expat name
#    pools -- British double-barrelled, Irish Mc/O'-prefixed, Nigerian
#    compound surname, beyond the augmentation's curated pool.
DOCS.append(build(
    "en_v2_01", "name_multiword_surname",
    "Multi-word expat surnames (British double-barrelled, Irish Mc/O', Nigerian compound) "
    "beyond the augmentation's curated pool.",
    """Patient: [[NAME|Charlotte Fitzgerald-Whitmore]], born [[DATE|14/02/1978]].
Treating physician: [[NAME|Dr Sean O'Callaghan-Byrne]].
Contact: [[PHONE|02 345 67 89]], home address [[ADDRESS|Clos de la Chapelle 9, 1300 Wavre]].
Next of kin: [[NAME|Chiamaka Nwosu-Adeyemi]].
"""
))

# 2. Partial redaction mixing -- some fields already redacted upstream,
#    others real PII, in the same document.
DOCS.append(build(
    "en_v2_02", "partial_redaction",
    "Some fields pre-redacted by an upstream system, others still real PII.",
    """PATIENT RECORD (partially anonymised export)

Name: [ANONYMISED]
Date of birth: [[DATE|03/07/1965]]
National Registration No.: [REDACTED]
Address: [[ADDRESS|Rue Fabry 22, 4020 Liege]]
Telephone: [[PHONE|04 253 11 22]]
Treating physician: [[NAME|Dr Amina Bouzid]]
"""
))

# 3. Numeric-ID hard negatives -- file/invoice/portal numbers shaped like
#    INSZ/RIZIV/phone digit runs, sitting right next to real ones.
DOCS.append(build(
    "en_v2_03", "numeric_id_hard_negatives",
    "File/invoice/portal IDs superficially shaped like INSZ/RIZIV/phone, beside real ones.",
    """File no. 20250311-884  Invoice no. EN-2025-006612  Patient portal ID: 77281193

Patient: [[NAME|Marc Delcroix]]
National Registration No.: [[INSZ|71051234567]]
Physician NIHDI No.: [[RIZIV|18734559003]]
Room no. 214  Bed no. 3
Telephone: [[PHONE|081 22 33 44]]
"""
))

# 4. Approximate sliding-window boundary stress -- a long, repetitive,
#    multi-entry log where a real span sits deep in the document rather
#    than near the top. Same-spirit approximation as the French port (not
#    tied to the exact base-model tokenizer stride).
DOCS.append(build(
    "en_v2_04", "window_boundary_approx",
    "Long repetitive multi-day log; real PII deep in the document, past likely window strides. "
    "APPROXIMATE (not tied to the exact tokenizer stride -- see note).",
    "\n".join([
        f"Day {i}: observations stable, no new complaints, current treatment continued."
        for i in range(1, 40)
    ]) + f"""

Day 40: discharge planned. Contact for arrangements: [[NAME|Veronique Hansen]],
reachable on [[PHONE|0473 22 11 09]], home address [[ADDRESS|Rue de la Sucrerie 6, 6001 Marcinelle]].
National Registration No.: [[INSZ|68022810178]].
"""
))

# 5. Quoted/forwarded email -- PII in both the new message and a quoted
#    reply chain below it.
DOCS.append(build(
    "en_v2_05", "quoted_email",
    "Forwarded email: PII in the new top message AND inside a quoted reply chain below.",
    """From: dr.simon@cliniquesaintluc.be
To: secretariat@chuliege.be
Subject: Fwd: file [[NAME|Farid Ouazzani]]

Hello,

Please forward the file below to the relevant department.

Kind regards,
Dr Simon

&gt; From: secretariat@chuliege.be
&gt; Subject: file [[NAME|Farid Ouazzani]]
&gt;
&gt; Patient [[NAME|Farid Ouazzani]], National Registration No. [[INSZ|82101210133]], reachable on
&gt; [[PHONE|04 227 88 99]], home address [[ADDRESS|Rue Sainte-Marie 18, 4000 Liege]].
"""
))

# 6. Foreign phone format alongside a valid Belgian INSZ -- scope probe,
#    reframed around the English track's own expat demographics decision:
#    a Belgian-registered patient with a family contact in the UK/Ireland.
DOCS.append(build(
    "en_v2_06", "foreign_phone_scope_probe",
    "Belgian-registered patient (valid National Registration No.) with a UK mobile number "
    "for a family contact abroad -- scope probe, in-character for the expat/international mix.",
    """Patient: [[NAME|Yannick Bertrand]], National Registration No. [[INSZ|90031510166]], home address
[[ADDRESS|Avenue Reine Astrid 4, 5000 Namur]].
Contact person (daughter, resident in the United Kingdom): [[NAME|Emma Bertrand]],
reachable on [[PHONE|+44 7911 123456]].
"""
))

# 7. Minimal document floor check.
DOCS.append(build(
    "en_v2_07", "minimal_doc",
    "Single short sentence -- robustness floor on extremely minimal documents.",
    "Contact: [[NAME|Jan Peeters]], [[PHONE|0470 11 22 33]]."
))

# 8. Homoglyph substitution -- Cyrillic lookalike character defeating exact
#    string matching. Uses Cyrillic а (U+0430) for Latin a.
DOCS.append(build(
    "en_v2_08", "homoglyph",
    "Cyrillic 'а' (U+0430) substituted for Latin 'a' in the patient's name.",
    """Patient: [[NAME|Kаrel Peeters]]
Home address: [[ADDRESS|Rue Neuve 3, 5000 Namur]]
Telephone: [[PHONE|081 55 66 77]]
"""
))

# 9. Email header with From:/To:-style labels -- EMAIL span validation.
#    The French track found ALL standing eval surfaces had zero EMAIL gold
#    spans before this doc existed -- checked and confirmed the same gap
#    exists here (eval_real_en.jsonl/eval_hard_extraction_en.jsonl/
#    eval_heldout_templates.jsonl carry no EMAIL-labelled span; only
#    train_augmented_en.jsonl's xf_email_header transform produces any).
DOCS.append(build(
    "en_v2_09", "email_header_validation",
    "Email header with From:/To: addresses labeled EMAIL -- first dedicated EMAIL-label eval case "
    "outside the augmented training file.",
    """From: [[EMAIL|secretariat.cardiology@chrcitadelle.be]]
To: [[EMAIL|dr.lemaire@medicalpractice.be]]
Subject: Results for patient [[NAME|Odette Lemaire]]

Dear Doctor,

Please find attached the results for your patient. For any questions,
you can reach me directly at [[EMAIL|m.dupuis@chrcitadelle.be]] or on
[[PHONE|04 225 66 10]].

Kind regards,
"""
))

# 10. Organization + VAT/company number -- a Belgian VAT number (BTW/TVA,
#     BCE/KBO) is a BUSINESS identifier, not personal PII -- there is no
#     English-track label for it either, so this is deliberately framed as
#     a hard NEGATIVE the model must learn to leave untagged, the same way
#     CNK codes are O-tagged in the pharmacy genre template.
DOCS.append(build(
    "en_v2_10", "organization_and_vat_hard_negative",
    "Letterhead org name + Belgian VAT/company number -- hard negative, not personal PII, "
    "must not be tagged as INSZ/RIZIV/PHONE despite the digit-heavy shape.",
    """[[ORGANIZATION|Clinique Saint-Luc]]
Avenue Hippocrate 10, 1200 Woluwe-Saint-Lambert
VAT number: BE 0403.170.701

Re: [[NAME|Michel Lacroix]]

The patient was seen today. Contact details: [[ADDRESS|Rue de la Paix 8, 1200 Brussels]],
tel [[PHONE|02 764 11 11]].

[[ORGANIZATION|Clinique Saint-Luc]] - Secretariat
"""
))

# 11-13. Letterhead/address structural adjacency -- org name doc-initial,
#     address on the very next line with NO blank-line separator;
#     abbreviated org prefix; same-line comma form.
DOCS.append(build(
    "en_v2_11", "letterhead_adjacency_newline",
    "ORGANIZATION at doc position 0, single newline, then full address -- no blank-line separator.",
    """[[ORGANIZATION|CHU de Liege]]
[[ADDRESS|Avenue de l'Hopital 1, 4000 Liege]]
Re: appointment for [[NAME|Sabine Toussaint]] on [[DATE|12/09/2025]].
"""
))
DOCS.append(build(
    "en_v2_12", "letterhead_adjacency_abbreviation",
    "Abbreviated org name at doc-initial position, immediately followed by ADDRESS.",
    """[[ORGANIZATION|CHR Citadelle]]
[[ADDRESS|Boulevard du XIIe de Ligne 1, 4000 Liege]]
Patient: [[NAME|Willy Dumont]], tel [[PHONE|04 225 74 74]].
"""
))
DOCS.append(build(
    "en_v2_13", "letterhead_adjacency_sameline",
    "Org name and address on the SAME line, joined by a comma.",
    """[[ORGANIZATION|Clinique Sainte-Elisabeth]], [[ADDRESS|Place Louise Godin 15, 5000 Namur]]
Re: [[NAME|Fatima El Habti]], National Registration No. [[INSZ|85040210144]].
"""
))

# 14. Honorific generalization beyond the augmentation's curated
#     Mr/Mrs/Ms/Dr pool.
DOCS.append(build(
    "en_v2_14", "honorific_generalization",
    "Honorifics beyond the augmentation's curated pool (Mr/Mrs/Ms/Dr).",
    """[[NAME|Miss Sara Van Reeth]] was seen in consultation today.
[[NAME|Prof. Willy Dumont]] accompanied her. Contact: [[PHONE|010 22 33 44]],
home address [[ADDRESS|Rue des Combattants 5, 1400 Nivelles]].
"""
))

# 15. Fresh casing-sweep eval instance (all_caps) -- xf_casing already
#     covers this in training augmentation, but an eval document must stay
#     independent of what augmentation happened to sample.
DOCS.append(build(
    "en_v2_15", "all_caps_eval",
    "Fresh all-caps document for EVAL (independent of the training augmentation's own sampling).",
    """CONSULTATION REPORT

PATIENT: [[NAME|GHISLAIN PETIT]]
DATE OF BIRTH: [[DATE|04/11/1972]]
HOME ADDRESS: [[ADDRESS|RUE DE LA STATION 21, 7000 MONS]]
TELEPHONE: [[PHONE|065 33 22 11]]

REASON FOR VISIT: ROUTINE CHECK-UP. NO NEW COMPLAINTS.
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_en_v2.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} English OOD-v2 stress documents to {OUT_PATH}")
