# -*- coding: utf-8 -*-
"""
build_ood_set_fr_v3_novel_vocab.py -- targeted "does it generalize to
genuinely unseen VOCABULARY" battery for the French track. Direct
structural counterpart to
personal_finetune/ood_stress_test_en/build_ood_set_en_v3_novel_vocab.py.

Every prior French OOD/eval battery (v1, v2, eval_real_fr,
eval_heldout_templates) tests generalization to unseen TEMPLATE
STRUCTURES. None of them isolate vocabulary novelty on its own: whether the
model can still correctly tag a NAME/ADDRESS/ORGANIZATION span built from a
city, hospital, or surname it has literally never seen in any template, in
any render, during training.

Design: every document below reuses a FAMILIAR, already-well-represented
sentence structure but populates it entirely with RESERVED vocabulary --
confirmed absent from every pool in pii_table_fr.py (WALLOON_CITIES,
HOSPITAL_STANDALONE, HOSPITAL_STEM, all 5 NAMES origin pools) as of
2026-08-19.

Reserved vocabulary (verified via web search; kept EXCLUSIVELY here, never
added to any pii_table_fr.py pool):

Cities (real, postal-code-verified, Wallonia-only per this track's
established scope -- same two additions reserved on the English side too,
since French's own pool has no Flemish cities to draw novel Flemish
vocabulary from in the first place):
  Fleurus (6220, Hainaut), Perwez (1360, Brabant Wallon)

Hospital (real, verified via web search): Centre médical Général Larrey, a
real Grand Hôpital de Charleroi satellite consultation site IN Fleurus --
geographically coherent with the reserved city above, and a genuinely
different string from anything in the existing 83-name HOSPITAL_STANDALONE
list (no second reserved hospital added beyond this one: French's list is
already far deeper than English's was, so the marginal research value of
finding a second untouched real name is low -- the honest-small-list
precedent applies here too).

Surnames (broadening beyond each origin pool's current coverage, same
principle as the English battery -- a handful of well-grounded additions
reaching into neighbouring communities each pool doesn't cover yet, not a
forced-comprehensive list):
  Lecomte (Walloon, absent from the current walloon surname pool),
  Moretti (Italian, absent from southern_european despite its Italian lean),
  Belhaj (Tunisian-style, broadens maghrebi past its current Morocco-heavy
    list), Kanyinda (Congolese, broadens central_african), Kowalczyk
    (Polish -- deliberately close in shape to the pool's existing
    "Kowalski", a genuine near-miss stress case for exact-string
    memorization rather than shape-based generalization)

Same marker DSL as build_ood_set_fr.py / build_ood_set_fr_v2.py
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
    "fr_nv01", "novel_vocab_referral",
    "Familiar referral-letter structure; patient name, address city, and referring "
    "physician surname all reserved (never in any training pool).",
    """Cher confrère,

Je vous adresse mon patient, [[NAME|Maxime Lecomte]], né le [[DATE|22/03/1979]],
domicilié [[ADDRESS|Rue de la Guinguette 12, 6220 Fleurus]], pour avis spécialisé.

Numéro de contact : [[PHONE|071 39 22 11]]
Numéro INSZ : [[INSZ|79032210144]]

Médecin référent : Dr Moretti

Bien confraternellement,
Dr Moretti
"""
))

# 2. Letterhead + hospital name, reserved real satellite site never in
#    HOSPITAL_STANDALONE, geographically coherent with the reserved city.
DOCS.append(build(
    "fr_nv02", "novel_vocab_hospital_letterhead",
    "Familiar letterhead structure with a real Grand Hôpital de Charleroi satellite "
    "site never in HOSPITAL_STANDALONE or HOSPITAL_STEM.",
    """[[ORGANIZATION|Centre médical Général Larrey]]
Rue de la Guinguette 72, 6220 Fleurus

Objet : [[NAME|Amara Kanyinda]]

Cher confrère,

Votre patiente a été vue dans notre service. Coordonnées :
[[ADDRESS|Rue du Try 5, 1360 Perwez]], tél [[PHONE|081 65 44 20]].

Bien confraternellement,
[[ORGANIZATION|Centre médical Général Larrey]]
"""
))

# 3. Discharge-style note, reserved city + reserved surname (Tunisian-style,
#    broadening the maghrebi pool past its current Morocco-heavy scope).
DOCS.append(build(
    "fr_nv03", "novel_vocab_discharge",
    "Familiar discharge-note structure; Wallonia city and Tunisian-style surname "
    "both reserved, broadening the maghrebi pool past its current Morocco-heavy scope.",
    """RAPPORT DE SORTIE

Patient : [[NAME|Sami Belhaj]]
Date de naissance : [[DATE|5 juin 1988]]

Motif d'admission :
- Douleur abdominale, admis le [[DATE|mardi 3 mars 2026]]

Suivi :
- Contrôle chez le médecin traitant dans 2 semaines
- Joignable au [[PHONE|071 22 45 60]]
- Domicile : [[ADDRESS|Rue de Charleroi 18, 6220 Fleurus]]

Bien confraternellement,
Dr Kanyinda, médecine générale
"""
))

# 4. Lab-report letterhead, reserved surname stress-testing a NEAR-MISS
#    shape (Kowalczyk vs the pool's existing Kowalski) rather than a
#    completely unfamiliar shape -- a harder, more specific test.
DOCS.append(build(
    "fr_nv04", "novel_vocab_near_miss_surname",
    "Reserved surname 'Kowalczyk' deliberately shares a shape/prefix with the "
    "eastern_european pool's existing 'Kowalski' -- tests whether the model matches "
    "on genuine name-token boundaries rather than a memorized near-identical string.",
    """LABORATOIRE CLINIQUE

Patient : [[NAME|Aleksandra Kowalczyk]]
Numéro INSZ : [[INSZ|88112310177]]

Médecin prescripteur : Dr Lecomte

Adresse au dossier : [[ADDRESS|Rue du Try 8, 1360 Perwez]]
Contact : [[PHONE|081 65 77 12]]
"""
))

# 5. Inline mid-sentence mention, no label cue -- reserved city + surname,
#    mirrors the inline_address category from build_ood_set_fr.py but with
#    entirely reserved vocabulary instead of pool-drawn vocabulary.
DOCS.append(build(
    "fr_nv05", "novel_vocab_inline",
    "Address and name embedded mid-sentence with no label cue, using only reserved "
    "vocabulary -- tests whether positional/contextual cues alone (not memorized "
    "strings) drive detection.",
    """Je vous écris car mon père, [[NAME|Antoine Moretti]], qui habite
[[ADDRESS|Rue de la Guinguette 3 à Fleurus]], se sent mal depuis la semaine dernière.
Vous pouvez le joindre au [[PHONE|071 39 88 21]] ou me joindre moi-même au
[[PHONE|0471 12 98 44]]. Son numéro INSZ est [[INSZ|55081410163]].
"""
))

# 6. Form-register document, reserved city + surname throughout.
DOCS.append(build(
    "fr_nv06", "novel_vocab_form",
    "Familiar form-register structure (identity block + narrative line), entirely "
    "reserved vocabulary throughout.",
    """DÉCLARATION DU PATIENT

Nom : [[NAME|Divine Kanyinda]]
Numéro INSZ : [[INSZ|91042210198]]
Adresse : [[ADDRESS|Place Communale 2, 1360 Perwez]]
Téléphone : [[PHONE|081 65 44 20]]

Médecin traitant : Dr Belhaj, vu le [[DATE|14/02/2026]].
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_fr_v3_novel_vocab.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} French novel-vocabulary OOD documents to {OUT_PATH}")
