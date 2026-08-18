"""
build_ood_set_fr.py -- first French/Walloon OOD stress-test battery.

Same marker DSL and structural-diversity philosophy as the Dutch original
(personal_finetune/ood_stress_test/build_ood_set.py): none of these
documents share template lineage with pii_table_fr.py, so a good score
here is evidence of real generalization, not data-generator overlap.

Seeded with ood04/ood05 from the Dutch battery -- both were already
hand-authored French/bilingual documents, deliberately excluded from
Dutch-only scoring via OUT_OF_SCOPE_CATEGORIES and left as a breadcrumb
for exactly this task. They are now first-class in-scope cases.

Covers the same dimensions the Dutch v1-v6 batteries found valuable
(document-type diversity, casing, hard-negative ID shapes, sliding-window
boundary stress, organization/address ambiguity) but authored fresh for
Walloon content -- especially the municipality-homograph hard negatives,
which cannot be translated from Dutch (Asse/Mol/Geel have no French
equivalent) and are pii_table_fr.py's own still-expanding starter set
(Marche/Bouillon/Mons/Ath).
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

# 1. Seeded from the Dutch battery's ood04 -- already French, already
#    correctly span-annotated, already excluded from Dutch-only scoring as
#    a deliberate breadcrumb. Now first-class in-scope.
DOCS.append(build(
    "fr_ood01", "referral_seed_from_nl_battery",
    "Reused from Dutch battery's ood04 (was deliberately out-of-scope there).",
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

# 2. Bilingual FR/NL -- Brussels is officially bilingual; realistic for a
#    Brussels-area hospital. Adapted from ood05's structure/idea, not a
#    literal copy (different names/values, and FR is now the primary
#    language of the surrounding prose, matching our track's own language).
DOCS.append(build(
    "fr_ood02", "bilingual_fr_nl",
    "Mixed French/Dutch within one document, realistic for Brussels.",
    """RAPPORT MEDICAL / MEDISCH VERSLAG

Patient(e) / Patient: [[NAME|Sophie Van Damme]]
Date de naissance / Geboortedatum: [[DATE|03-06-1969]]
Adresse / Adres: [[ADDRESS|Avenue Louise 210, 1050 Bruxelles]]
Tel: [[PHONE|02 640 12 34]]

Conclusion: patiente stable, suivi ambulatoire.
Vervolgafspraak over 6 weken.
"""
))

# 3. Lab-result table -- pipe-delimited, training data has no tables.
DOCS.append(build(
    "fr_ood03", "lab_table",
    "Tabular lab report; markdown-pipe layout never seen in training.",
    """RAPPORT DE LABORATOIRE - Biologie Clinique

| Patient          | Date de naissance | INSZ            | Date prelevement |
|------------------|--------------------|-----------------|--------------------|
| [[NAME|Willem Rossi]] | [[DATE|03/11/1958]] | [[INSZ|58110310137]] | [[DATE|14-08-2025]] |

Contact: [[PHONE|+32 478 22 91 04]]
Adresse: [[ADDRESS|Rue de la Station 9, 5030 Gembloux]]

| Test        | Resultat  | Valeur de reference |
|-------------|-----------|----------------------|
| Hemoglobine | 13.4 g/dL | 13.0-17.0            |
| Glucose     | 5.6 mmol/L| 4.0-6.0               |
| Creatinine  | 0.9 mg/dL | 0.7-1.3               |

Ces valeurs de reference ne s'appliquent pas aux patients de plus de 90 ans.
"""
))

# 4. Prescription slip -- terse, form-like, near-zero prose.
DOCS.append(build(
    "fr_ood04", "prescription_slip",
    "Minimal prescription form; near-zero surrounding prose context.",
    """ORDONNANCE
Nom : [[NAME|Sylvie Marchal]]
Ne(e) le : [[DATE|22.04.1990]]
RIZIV medecin : [[RIZIV|18734559003]]
---
Amoxicilline 500mg, 3x/jour, 7 jours
Paracetamol 1g si besoin, max 4x/jour
---
Contact pharmacien : [[PHONE|081/22.44.56]]
"""
))

# 5. Discharge summary, bullet sections -- different structure/sign-off.
DOCS.append(build(
    "fr_ood05", "discharge_bullets",
    "Bullet-structured discharge note, different section order/sign-off style.",
    """RAPPORT DE SORTIE

Patient : [[NAME|Karel Toussaint]]
Date de naissance : [[DATE|9 mai 1975]]

Motif d'admission :
- Douleur thoracique, admis le [[DATE|jeudi 14 aout 2025]]

Constatations :
- ECG normal
- Troponine negative

Suivi :
- Controle chez le cardiologue dans 2 semaines
- Joignable au [[PHONE|0032 495 11 22 33]]
- Domicile : [[ADDRESS|Rue du Moulin 4, 6000 Charleroi]]

Bien confraternellement,
Dr. Georges, cardiologie
"""
))

# 6. SMS-register reminder -- extremely short, dense, no letterhead at all.
DOCS.append(build(
    "fr_ood06", "sms_reminder",
    "SMS-style reminder; ultra-short dense register.",
    """Rappel : rdv [[NAME|Anne Wery]] le [[DATE|21/08]] a 14h30 chez dr. Simon.
Appelez le [[PHONE|0470989898]] pour annuler. INSZ 91..: [[INSZ|91052010181]]"""
))

# 7. Insurance / mutuelle claim form -- colon key:value fields, no prose.
DOCS.append(build(
    "fr_ood07", "insurance_form",
    "Insurance claim form, pure key:value fields.",
    """DEMANDE DE REMBOURSEMENT - Mutualite Solidaris

Nom du demandeur : [[NAME|Rita Fontaine]]
Date de naissance : [[DATE|1955-12-01]]
Numero INSZ : [[INSZ|55120110141]]
Adresse : [[ADDRESS|Boite postale 44, 7800 Ath]]
Numero de telephone : [[PHONE|068/40.55.66]]
Medecin traitant RIZIV : [[RIZIV|11223393003]]
Montant : EUR 84,50
Statut : En cours de traitement
"""
))

# 8. OCR-noisy scan-derived text -- broken words, irregular spacing.
DOCS.append(build(
    "fr_ood08", "ocr_noise",
    "OCR-artifact text: broken words, irregular spacing.",
    """DON NEES  PATIENT

Nom :  [[NAME|Philippe  Delcour t]]
Da te de nai ssance :  [[DATE|11 -02-1988]]
Adr esse :  [[ADDRESS|Rue du Chene  7 ,  5300  Andenne]]
Tel ephon e :   [[PHONE|085- 58 91 02]]

Dia gnos tic :  hyper tension,  bien  regl ee  sous  contro le.
Proc haine  cons ultat ion  dan s  3  mois.
"""
))

# 9. Multi-patient tabular record -- row-correct entity attribution.
DOCS.append(build(
    "fr_ood09", "multi_patient_table",
    "Two patients in one table -- tests row-correct entity attribution.",
    """RECAPITULATIF ADMISSIONS URGENCES

1. [[NAME|Joseph Lambert]], [[DATE|02/1948]], [[ADDRESS|Rue de l'Eglise 3, 7700 Mouscron]], tel [[PHONE|056 360 12 12]]
   Plainte : essoufflement

2. [[NAME|Nadia El Amrani]], [[DATE|14/03/1993]], [[ADDRESS|Chaussee de Charleroi 88, 6000 Charleroi]], tel [[PHONE|+32489556677]]
   Plainte : douleur abdominale
"""
))

# 10. Email correspondence with signature block.
DOCS.append(build(
    "fr_ood10", "email_signature",
    "Email with PII in signature block, not letter body.",
    """De : secretariat@chuliege.be
A : medecin.traitant@cabinet.be
Objet : dossier [[NAME|Thomas Servais]]

Cher confrere,

Ci-joint le dossier du patient susmentionne (INSZ [[INSZ|75041010138]]).

Bien confraternellement,

--
Mme K. Bertrand
Secretariat Cardiologie
[[ADDRESS|Rue de la Citadelle 1, 4000 Liege]]
Tel : [[PHONE|04 12 34 56]] | Direct : [[PHONE|0472 33 44 55]]
"""
))

# 11. Inline address mid-sentence -- no label cue.
DOCS.append(build(
    "fr_ood11", "inline_address",
    "Address embedded mid-sentence, no label cue.",
    """Je vous ecris car ma mere, [[NAME|Bertha Collard]], qui habite [[ADDRESS|Avenue des Tilleuls 22 a Wavre]],
se plaint depuis plusieurs semaines de vertiges. Vous pouvez la joindre au [[PHONE|010 60 11 22]] ou
me joindre moi-meme au [[PHONE|0032497001122]]. Sa date de naissance est le [[DATE|six janvier mille neuf cent quarante]].
"""
))

# 12. Hospital/org-name ambiguity -- real Walloon hospital, org name labeled
#     in letterhead+signature per the finalized taxonomy (see
#     personal_finetune README's ORGANIZATION-split-from-NAME note).
DOCS.append(build(
    "fr_ood12", "org_ambiguity",
    "Real Walloon hospital name in letterhead+signature, labeled ORGANIZATION.",
    """[[ORGANIZATION|CHR de la Citadelle]]
Boulevard du Douzieme de Ligne 1, 4000 Liege
www.chrcitadelle.be

Objet : [[NAME|Louis Halleux]]

Madame, Monsieur,

Votre patient a ete vu dans notre service. Coordonnees du patient :
[[ADDRESS|Rue des Ecoles 12, 4000 Liege]], tel [[PHONE|04 386 77 88]].

Bien confraternellement,
[[ORGANIZATION|CHR de la Citadelle]] - Service de Cardiologie
"""
))

# 13. Numeric-heavy hard-negative stress in a novel layout.
DOCS.append(build(
    "fr_ood13", "numeric_hard_negatives",
    "Dense numeric hard negatives (dosage/BP/ratio) beside real PII, new layout.",
    """Patient [[NAME|Omar Benali]] (INSZ [[INSZ|88030210159]]) a recu 2x par jour 500mg,
tension arterielle 130/85 mmHg, frequence cardiaque 72/min, ratio AST/ALT 0.8, poids 82 kg pour 178 cm.
Prochain controle le [[DATE|03/09/2025]]. Contact : [[PHONE|0468 12 34 56]].
Habite [[ADDRESS|Rue Haute 61, 6460 Chimay]].
"""
))

# 14. Multi-line address block -- training renders address as one
#     comma-joined line; real letters often split street / postcode+city.
DOCS.append(build(
    "fr_ood14", "multiline_address",
    "Address split across two lines, unlike training's single-line format.",
    """A l'attention de [[NAME|Pierre Cornet]]
[[ADDRESS|Rue des Bouleaux 8]]
[[ADDRESS|6900 Marche-en-Famenne]]

Date de naissance : [[DATE|1962/07/30]]
Telephone : [[PHONE|084 71 22 33]]

Objet : convocation pour controle annuel.
"""
))

# 15. Title+surname-only coreference after formal intro.
DOCS.append(build(
    "fr_ood15", "informal_reference",
    "Formal full-name intro, then title+surname-only references later.",
    """Patiente : [[NAME|Griet Delvaux]], nee le [[DATE|12/07/1980]].

[[NAME|Mme Delvaux]] est venue en consultation pour un controle de routine. [[NAME|Mme Delvaux]] a indique
se sentir bien. Nous conseillons a [[NAME|mme Delvaux]] de planifier une consultation de suivi.
Joignable au [[PHONE|+32 (0)4 234 56 78]], adresse [[ADDRESS|Place Saint-Nicolas 5, 4800 Verviers]].
"""
))

# 16. Age phrasing + reference-range disclaimer hard negative.
DOCS.append(build(
    "fr_ood16", "age_phrasing",
    "Unusual age phrasing plus reference-range disclaimer hard negative.",
    """Patient [[NAME|Hendrik Georges]] est age de [[AGE|67 ans]] et a ete traite pour arthrose.
Les valeurs de reference pour la densite osseuse ne sont pas validees en dessous de 18 ans ou au-dessus de 85 ans.
Contact : [[PHONE|03 771 22 33]], INSZ [[INSZ|58092710179]].
"""
))

# 17. NEW, French-specific: municipality-homograph stress -- deliberately
#     dense use of pii_table_fr.py's still-small homograph starter set
#     (Marche/Bouillon/Mons/Ath), since this is the category flagged as
#     needing the most expansion for the French track specifically.
DOCS.append(build(
    "fr_ood17", "municipality_homograph_stress",
    "Dense use of real Walloon-municipality/French-word homographs, French-specific "
    "(no Dutch equivalent to translate -- Asse/Mol/Geel have no French cognate).",
    """Patient [[NAME|Andre Piette]] (INSZ [[INSZ|60031553505]]) presente une reprise de la marche
sans aide depuis la semaine derniere. Bouillon de culture positif a l'hemoculture. Examen du
mons pubis sans particularite. Pose d'un catheter sous-clavier realisee sans complication.
Domicile : [[ADDRESS|Rue de Namur 14, 6800 Libramont-Chevigny]], tel [[PHONE|061 22 33 44]].
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_fr.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} French OOD stress documents to {OUT_PATH}")
