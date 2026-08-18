"""
build_ood_set_fr_v2.py -- second French OOD stress-test battery, porting
over the categories discovered across the Dutch v2-v6 rounds that had ZERO
French equivalent (confirmed by cataloging all 45 hand-authored Dutch
categories across ood_stress_test/ through ood_stress_test_v6/ and diffing
against the French battery's 17 documents, which only mirrors Dutch v1 plus
one French-specific municipality-homograph addition).

Categories already covered on the AUGMENTATION side for French (casing via
xf_casing, diacritic/honorific via xf_diacritic_honorific, mojibake via
xf_mojibake) still get ONE fresh eval-only instance here, since a held-out
eval document must be independent of whatever the training augmentation
happened to sample -- that's the whole point of an eval set.

Same marker DSL as build_ood_set_fr.py (self-validating round-trip).
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

# 1. Multi-word Belgian surnames (tussenvoegsel-equivalent particles: de, du,
#    de la, van der carried into French-Belgian naming) -- Dutch v2_02.
DOCS.append(build(
    "fr_v2_01", "name_multiword_surname",
    "Multi-word Belgian surnames with particles, beyond the augmentation's curated pool.",
    """Patiente : [[NAME|Anne-Sophie du Bois-Lambert]], nee le [[DATE|14/02/1978]].
Medecin traitant : [[NAME|Dr Jean-Pierre de la Croix]].
Contact : [[PHONE|02 345 67 89]], domicile [[ADDRESS|Clos de la Chapelle 9, 1300 Wavre]].
"""
))

# 2. Partial redaction mixing -- some fields already redacted upstream,
#    others real PII, in the same document -- Dutch v2_05.
DOCS.append(build(
    "fr_v2_02", "partial_redaction",
    "Some fields pre-redacted by an upstream system, others still real PII.",
    """FICHE PATIENT (export partiellement anonymise)

Nom : [ANONYMISE]
Date de naissance : [[DATE|03/07/1965]]
INSZ : [REDACTED]
Adresse : [[ADDRESS|Rue Fabry 22, 4020 Liege]]
Telephone : [[PHONE|04 253 11 22]]
Medecin traitant : [[NAME|Dr Amina Bouzid]]
"""
))

# 3. Numeric-ID hard negatives -- dossier/invoice/portal numbers shaped like
#    INSZ/RIZIV/phone digit runs, sitting right next to real ones -- v2_07.
DOCS.append(build(
    "fr_v2_03", "numeric_id_hard_negatives",
    "Dossier/facture/portail IDs superficially shaped like INSZ/RIZIV/phone, beside real ones.",
    """Dossier n. 20250311-884  Facture n. FR-2025-006612  Identifiant portail patient : 77281193

Patient : [[NAME|Marc Delcroix]]
INSZ : [[INSZ|71051234567]]
RIZIV medecin : [[RIZIV|18734559003]]
Chambre n. 214  Lit n. 3
Telephone : [[PHONE|081 22 33 44]]
"""
))

# 4. Approximate sliding-window boundary stress -- a long, repetitive,
#    multi-entry log where a real span sits deep in the document rather
#    than near the top (the Dutch original used the actual tokenizer to hit
#    an exact stride offset; without that same MedRoBERTa-fr tokenizer
#    wired up here, this is a same-spirit approximation: enough repetitive
#    filler that any fixed-length sliding window WILL cut across at least
#    one entry, which is the property that actually matters for the test).
DOCS.append(build(
    "fr_v2_04", "window_boundary_approx",
    "Long repetitive multi-day log; real PII deep in the document, past likely window strides. "
    "APPROXIMATE (not tied to the exact tokenizer stride like the Dutch original -- see note).",
    "\n".join([
        f"Jour {i} : constantes stables, pas de plainte nouvelle, poursuite du traitement en cours."
        for i in range(1, 40)
    ]) + f"""

Jour 40 : sortie prevue. Contact pour organisation : [[NAME|Veronique Hansen]],
joignable au [[PHONE|0473 22 11 09]], domicile [[ADDRESS|Rue de la Sucrerie 6, 6001 Marcinelle]].
INSZ : [[INSZ|68022810178]].
"""
))

# 5. Quoted/forwarded email -- PII in both the new message and a quoted
#    reply chain below it -- Dutch v4d_02.
DOCS.append(build(
    "fr_v2_05", "quoted_email",
    "Forwarded email: PII in the new top message AND inside a quoted reply chain below.",
    """De : dr.simon@cliniquesaintluc.be
A : secretariat@chuliege.be
Objet : Tr : dossier [[NAME|Farid Ouazzani]]

Bonjour,

Merci de transmettre le dossier ci-dessous au service concerne.

Cordialement,
Dr Simon

&gt; De : secretariat@chuliege.be
&gt; Objet : dossier [[NAME|Farid Ouazzani]]
&gt;
&gt; Patient [[NAME|Farid Ouazzani]], INSZ [[INSZ|82101210133]], joignable au
&gt; [[PHONE|04 227 88 99]], domicile [[ADDRESS|Rue Sainte-Marie 18, 4000 Liege]].
"""
))

# 6. Foreign phone format alongside a valid Belgian INSZ -- scope probe,
#    Dutch v4d_03 (patient is Belgian, family contact uses a French mobile).
DOCS.append(build(
    "fr_v2_06", "foreign_phone_scope_probe",
    "Belgian patient (valid INSZ) with a French mobile number for a family contact -- scope probe.",
    """Patient : [[NAME|Yannick Bertrand]], INSZ [[INSZ|90031510166]], domicile
[[ADDRESS|Avenue Reine Astrid 4, 5000 Namur]].
Personne de contact (fille, residant en France) : [[NAME|Celine Bertrand]],
joignable au [[PHONE|+33 6 12 34 56 78]].
"""
))

# 7. Minimal document floor check -- Dutch v4d_04.
DOCS.append(build(
    "fr_v2_07", "minimal_doc",
    "Single short sentence -- robustness floor on extremely minimal documents.",
    "Contact : [[NAME|Jan Peeters]], [[PHONE|0470 11 22 33]]."
))

# 8. Homoglyph substitution -- Cyrillic lookalike character defeating exact
#    string matching -- Dutch v4d_05. Uses Cyrillic а (U+0430) for Latin a.
DOCS.append(build(
    "fr_v2_08", "homoglyph",
    "Cyrillic 'а' (U+0430) substituted for Latin 'a' in the patient's name.",
    """Patient : [[NAME|Kаrel Peeters]]
Domicile : [[ADDRESS|Rue Neuve 3, 5000 Namur]]
Telephone : [[PHONE|081 55 66 77]]
"""
))

# 9. Email header with Van:/Aan:-style FR labels -- EMAIL span validation.
#    Dutch v5_04 found that ALL standing eval surfaces had zero EMAIL gold
#    spans before this doc existed -- same gap almost certainly exists here.
DOCS.append(build(
    "fr_v2_09", "email_header_validation",
    "Email header with De:/A: addresses labeled EMAIL -- first dedicated EMAIL-label eval case.",
    """De : [[EMAIL|secretariat.cardiologie@chrcitadelle.be]]
A : [[EMAIL|dr.lemaire@cabinet-medical.be]]
Objet : Resultats patient [[NAME|Odette Lemaire]]

Bonjour Docteur,

Veuillez trouver ci-joint les resultats de votre patiente. Pour toute question,
vous pouvez me joindre directement a [[EMAIL|m.dupuis@chrcitadelle.be]] ou au
[[PHONE|04 225 66 10]].

Cordialement,
"""
))

# 10. Organization + VAT/company number -- Dutch v5_06's BTW_EENHEID probe.
#     A Belgian VAT number (numero de TVA / numero d'entreprise, BCE/KBO) is
#     a BUSINESS identifier, not personal PII -- there is no French-track
#     label for it (no french_regex.py exists yet, and pii_table_fr.py never
#     generates one), so this is deliberately framed as a hard NEGATIVE the
#     model must learn to leave untagged, the same way CNK codes are O-tagged
#     in the new pharmacy template, rather than introducing a new label
#     category mid-project.
DOCS.append(build(
    "fr_v2_10", "organization_and_vat_hard_negative",
    "Letterhead org name + Belgian VAT/company number (numero de TVA) -- hard negative, "
    "not personal PII, must not be tagged as INSZ/RIZIV/PHONE despite the digit-heavy shape.",
    """[[ORGANIZATION|Clinique Saint-Luc]]
Avenue Hippocrate 10, 1200 Woluwe-Saint-Lambert
Numero de TVA : BE 0403.170.701

Objet : [[NAME|Michel Lacroix]]

Le patient a ete vu ce jour. Coordonnees : [[ADDRESS|Rue de la Paix 8, 1200 Bruxelles]],
tel [[PHONE|02 764 11 11]].

[[ORGANIZATION|Clinique Saint-Luc]] - Secretariat
"""
))

# 11-13. Letterhead/address structural adjacency -- the exact bug class
#     found in Dutch v6 (org name doc-initial, address on the very next line
#     with NO blank-line separator; abbreviated org prefix; same-line comma
#     form). Three variants of the same underlying blind spot.
DOCS.append(build(
    "fr_v2_11", "letterhead_adjacency_newline",
    "ORGANIZATION at doc position 0, single newline, then full address -- no blank-line separator.",
    """[[ORGANIZATION|CHU de Liege]]
[[ADDRESS|Avenue de l'Hopital 1, 4000 Liege]]
Objet : convocation de [[NAME|Sabine Toussaint]] le [[DATE|12/09/2025]].
"""
))
DOCS.append(build(
    "fr_v2_12", "letterhead_adjacency_abbreviation",
    "Abbreviated org name at doc-initial position, immediately followed by ADDRESS.",
    """[[ORGANIZATION|CHR Citadelle]]
[[ADDRESS|Boulevard du XIIe de Ligne 1, 4000 Liege]]
Patient : [[NAME|Willy Dumont]], tel [[PHONE|04 225 74 74]].
"""
))
DOCS.append(build(
    "fr_v2_13", "letterhead_adjacency_sameline",
    "Org name and address on the SAME line, joined by a comma.",
    """[[ORGANIZATION|Clinique Sainte-Elisabeth]], [[ADDRESS|Place Louise Godin 15, 5000 Namur]]
Concerne : [[NAME|Fatima El Habti]], INSZ [[INSZ|85040210144]].
"""
))

# 14. Honorific generalization beyond the augmentation's curated
#     monsieur/madame/m./mme/mlle pool -- Dutch v5_02.
DOCS.append(build(
    "fr_v2_14", "honorific_generalization",
    "Honorifics beyond the augmentation's curated pool (monsieur/madame/m./mme/mlle).",
    """[[NAME|Mademoiselle Sara Van Reeth]] a ete recue en consultation ce jour.
[[NAME|Le sieur Willy Dumont]] l'accompagnait. Contact : [[PHONE|010 22 33 44]],
domicile [[ADDRESS|Rue des Combattants 5, 1400 Nivelles]].
"""
))

# 15. Fresh casing-sweep eval instance (all_caps) -- xf_casing already
#     covers this in training augmentation, but an eval document must stay
#     independent of what augmentation happened to sample.
DOCS.append(build(
    "fr_v2_15", "all_caps_eval",
    "Fresh all-caps document for EVAL (independent of the training augmentation's own sampling).",
    """RAPPORT DE CONSULTATION

PATIENT : [[NAME|GHISLAIN PETIT]]
NE LE : [[DATE|04/11/1972]]
DOMICILE : [[ADDRESS|RUE DE LA STATION 21, 7000 MONS]]
TELEPHONE : [[PHONE|065 33 22 11]]

MOTIF : CONTROLE DE ROUTINE. AUCUNE PLAINTE NOUVELLE.
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_fr_v2.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} French OOD-v2 stress documents to {OUT_PATH}")
