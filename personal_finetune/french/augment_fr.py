"""
augment_fr.py -- French fork of personal_finetune/augmentation/augment_v4.py.

Transform mechanics kept unchanged (position/offset mechanics, not language
content): xf_casing, xf_ocr_noise, xf_diacritic_honorific, xf_mojibake,
xf_inline_mention, xf_org_context, xf_email_header, gen_non_medical, plus
the local remap_spans_through_edits/remap_via_transform helpers.

Verbatim pools replaced with Belgian-French (Walloon) equivalents -- kept
truly-national Belgian brands, swapped Flemish-only ones for Walloon
equivalents (De Lijn -> TEC, Telenet -> VOO), matching the same research
already done for pii_table_fr.py.

Since the known lessons (org/address adjacency variety, casing, OCR noise,
email-header hard negatives) are already baked into pii_table_fr.py's
templates and this file's pools, this runs as ONE comprehensive round
covering all 8 transforms at once, rather than repeating the Dutch
pipeline's 4 sequential discovery-driven rounds -- per the plan.

Usage:
    python3 augment_fr.py --input tamerbert_data_fr/train_filtered.jsonl \
        --out train_augmented_fr.jsonl
"""

import argparse
import json
import os
import random
import re


def load_docs(path):
    docs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            docs.append({"text": d["text"], "spans": [
                {"start": s["start"], "end": s["end"], "label": s["label"]} for s in d["spans"]
            ]})
    return docs


def remap_spans_through_edits(text, spans, edits):
    edits = sorted(edits, key=lambda e: e[0])
    out, cum_shift, last, shift = [], [], 0, 0
    for pos, ins in edits:
        out.append(text[last:pos])
        out.append(ins)
        shift += len(ins)
        cum_shift.append((pos, shift))
        last = pos
    out.append(text[last:])
    new_text = "".join(out)

    def remap(offset):
        s = 0
        for pos, cs in cum_shift:
            if pos <= offset:
                s = cs
            else:
                break
        return offset + s

    new_spans = [{"start": remap(sp["start"]), "end": remap(sp["end"]), "label": sp["label"]} for sp in spans]
    return new_text, new_spans


def remap_via_transform(doc, transform_fn):
    text = doc["text"]
    new_text = transform_fn(text)
    new_spans = []
    for sp in doc["spans"]:
        new_start = len(transform_fn(text[:sp["start"]]))
        new_end = len(transform_fn(text[:sp["end"]]))
        new_spans.append({"start": new_start, "end": new_end, "label": sp["label"]})
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# Casing -- language-agnostic, unchanged
# --------------------------------------------------------------------------- #
def xf_casing(doc, rng):
    fn = rng.choice([str.upper, str.lower, str.title])
    return {"text": fn(doc["text"]), "spans": [dict(s) for s in doc["spans"]]}


# --------------------------------------------------------------------------- #
# Non-medical negatives -- Belgian-French pools. Kept truly-national brands
# (Bpost, Colruyt, Proximus, Delhaize, Bol.com, Decathlon Belgique); swapped
# Flemish-only ones: De Lijn (Flemish transit) -> TEC (Walloon transit),
# Telenet (Flemish cable ISP) -> VOO (Walloon cable ISP); dropped Torfs/JBC
# (Flemish-only retail chains, no direct Walloon equivalent needed).
# --------------------------------------------------------------------------- #
_COMPANIES = ["Bpost", "Colruyt Group", "Proximus", "Delhaize", "VOO",
              "TEC", "Bol.com", "Decathlon Belgique", "Carrefour", "Base"]
_PRODUCTS = ["votre colis", "votre commande", "votre abonnement",
             "votre réservation", "votre billet"]
_TEMPLATES = [
    "Cher client,\n\nNous vous remercions pour {product} chez {company}. Celle-ci "
    "est actuellement en cours de traitement et sera finalisée dans les "
    "prochains jours ouvrables.\n\nPour toute question, notre service "
    "clientèle reste à votre disposition pendant les heures de bureau.\n\n"
    "Cordialement,\nService clientèle {company}\n",

    "Cher client,\n\nVotre abonnement chez {company} sera bientôt renouvelé "
    "automatiquement. Si vous ne le souhaitez pas, vous pouvez le résilier "
    "jusqu'à 14 jours avant la date d'échéance via votre compte en ligne.\n\n"
    "Cordialement,\nL'équipe {company}\n",

    "Cher visiteur,\n\nMerci pour votre intérêt envers notre événement. "
    "{product} est confirmée et vous recevrez prochainement plus "
    "d'informations par e-mail. Nous nous réjouissons de vous accueillir.\n\n"
    "Cordialement,\nLe comité organisateur\n",

    "Madame, Monsieur,\n\nSuite à votre prise de contact, nous souhaitons vous "
    "informer que {product} est actuellement en cours de traitement par "
    "notre service. Nous reprendrons contact avec vous dans les meilleurs "
    "délais.\n\nCordialement,\n{company}\n",
]


def gen_non_medical(rng, n):
    out = []
    for _ in range(n):
        tmpl = rng.choice(_TEMPLATES)
        text = tmpl.format(company=rng.choice(_COMPANIES), product=rng.choice(_PRODUCTS))
        out.append({"text": text, "spans": []})
    return out


_INLINE_ADDRESS_TEMPLATES = [
    "Le patient habite {v} et en a été informé.\n",
    "La correspondance est envoyée à {v}.\n",
    "Le patient reste joignable à l'adresse {v}.\n",
]
_INLINE_PHONE_TEMPLATES = [
    "Pour toute question urgente, le patient est joignable au {v}.\n",
    "La prise de contact peut se faire par téléphone au {v}.\n",
    "Le patient a communiqué le {v} comme numéro de contact.\n",
]


def xf_inline_mention(doc, rng):
    candidates = [s for s in doc["spans"] if s["label"] in ("ADDRESS", "PHONE")]
    if not candidates:
        return None
    sp = rng.choice(candidates)
    value = doc["text"][sp["start"]:sp["end"]]
    tmpl = rng.choice(_INLINE_ADDRESS_TEMPLATES if sp["label"] == "ADDRESS" else _INLINE_PHONE_TEMPLATES)
    sentence_before_value, sentence_after_value = tmpl.split("{v}")
    insert_at = len(doc["text"])
    new_span_start = insert_at + len(sentence_before_value)
    new_span = {"start": new_span_start, "end": new_span_start + len(value), "label": sp["label"]}
    new_text = doc["text"] + sentence_before_value + value + sentence_after_value
    return {"text": new_text, "spans": [dict(s) for s in doc["spans"]] + [new_span]}


# --------------------------------------------------------------------------- #
# OCR noise -- language-agnostic, unchanged
# --------------------------------------------------------------------------- #
def xf_ocr_noise(doc, rng, rate=0.08):
    text = doc["text"]
    edits = []
    for i, ch in enumerate(text):
        if ch.isalpha() and i > 0 and text[i - 1].isalpha() and rng.random() < rate:
            edits.append((i, " "))
    new_text, new_spans = remap_spans_through_edits(text, doc["spans"], edits)
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# Diacritic / honorific -- diacritic names mostly reusable as-is (already
# multi-origin, not Dutch-specific); honorifics forked to French.
# --------------------------------------------------------------------------- #
_DIACRITIC_NAMES = ["Müller", "Amélie Dupont", "François Léger", "José Fernández",
                     "Ürkan Yildiz", "Renée Vaes", "André Piérard", "Björn Andersson",
                     "Céline Wéry", "Łukasz Kowalski", "Zoë Delcourt",
                     "Nuñez Garcia", "Sørensen Delvaux"]
_HONORIFICS = ["monsieur ", "madame ", "m. ", "mme ", "mlle "]


def xf_diacritic_honorific(doc, rng):
    candidates = [i for i, s in enumerate(doc["spans"]) if s["label"] == "NAME"]
    if not candidates:
        return None
    idx = rng.choice(candidates)
    sp = doc["spans"][idx]
    old_val = doc["text"][sp["start"]:sp["end"]]
    if old_val.startswith("dr. "):
        new_val = rng.choice(_HONORIFICS) + old_val[4:]
    else:
        new_val = rng.choice(_DIACRITIC_NAMES)
        if rng.random() < 0.4:
            new_val = rng.choice(_HONORIFICS) + new_val
    delta = len(new_val) - len(old_val)
    new_text = doc["text"][:sp["start"]] + new_val + doc["text"][sp["end"]:]
    new_spans = []
    for i, s in enumerate(doc["spans"]):
        if i == idx:
            new_spans.append({"start": sp["start"], "end": sp["start"] + len(new_val), "label": "NAME"})
        elif s["start"] >= sp["end"]:
            new_spans.append({"start": s["start"] + delta, "end": s["end"] + delta, "label": s["label"]})
        else:
            new_spans.append(dict(s))
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# Mojibake -- language-agnostic, unchanged
# --------------------------------------------------------------------------- #
def mojibake(s):
    return s.encode("utf-8").decode("latin-1")


def xf_mojibake(doc, rng):
    with_diacritic = xf_diacritic_honorific(doc, rng)
    if with_diacritic is None or not any(ord(c) > 127 for c in with_diacritic["text"]):
        return None
    return remap_via_transform(with_diacritic, mojibake)


# --------------------------------------------------------------------------- #
# Email header hard negative -- Walloon hospital-domain convention
# (chu*/chr*/clinique*) instead of Flemish az*/uz*; role words in French.
# --------------------------------------------------------------------------- #
_EMAIL_LOCALS = ["dr.dubois", "dr.lambert", "secretariat", "dr.simon",
                 "medecin.referent", "dr.leonard", "accueil", "dr.gerard"]
_EMAIL_DOMAINS = ["chuliege.be", "chrcitadelle.be", "cliniquesaintluc.be", "chwapi.be"]


def xf_email_header(doc, rng):
    a, b = rng.sample(_EMAIL_LOCALS, 2)
    da, db = rng.choice(_EMAIL_DOMAINS), rng.choice(_EMAIL_DOMAINS)
    email_a, email_b = f"{a}@{da}", f"{b}@{db}"
    prefix = f"De : {email_a}\nÀ : {email_b}\nObjet : dossier patient\n\n"
    email_spans = [
        {"start": prefix.index(email_a), "end": prefix.index(email_a) + len(email_a), "label": "EMAIL"},
        {"start": prefix.index(email_b), "end": prefix.index(email_b) + len(email_b), "label": "EMAIL"},
    ]
    shifted = [{"start": s["start"] + len(prefix), "end": s["end"] + len(prefix), "label": s["label"]}
               for s in doc["spans"]]
    return {"text": prefix + doc["text"], "spans": email_spans + shifted}


# --------------------------------------------------------------------------- #
# Org/address context -- structure unchanged (4 variants + optional
# signature mention, per the Dutch round-4 design). French sign-offs and
# department names substituted.
# --------------------------------------------------------------------------- #
def build_value_pool(originals, label):
    vals = set()
    for d in originals:
        for s in d["spans"]:
            if s["label"] == label:
                vals.add(d["text"][s["start"]:s["end"]])
    return sorted(vals)


_SIGNOFFS = ["Cordialement,", "Bien à vous,", "Bien confraternellement,"]
_DEPTS = ["Service de Radiologie", "Service de Cardiologie", "Service d'Orthopédie",
          "Service des Urgences", "Service de Médecine Interne"]


def xf_org_context(doc, rng, org_pool, addr_pool):
    org_val = rng.choice(org_pool)
    addr_val = rng.choice(addr_pool)
    variant = rng.choice(["plain", "hard_negative", "same_line", "org_alone"])

    if variant == "plain":
        prefix = f"{org_val}\n{addr_val}\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"},
                         {"start": len(org_val) + 1, "end": len(org_val) + 1 + len(addr_val), "label": "ADDRESS"}]
    elif variant == "hard_negative":
        prefix = f"{org_val}\n{addr_val}\nwww.{org_val.split()[0].lower()}.be\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"}]
    elif variant == "same_line":
        prefix = f"{org_val}, {addr_val}\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"},
                         {"start": len(org_val) + 2, "end": len(org_val) + 2 + len(addr_val), "label": "ADDRESS"}]
    else:  # org_alone
        prefix = f"{org_val}\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"}]

    shifted = [{"start": s["start"] + len(prefix), "end": s["end"] + len(prefix), "label": s["label"]}
               for s in doc["spans"]]
    text = prefix + doc["text"]
    spans = prefix_spans + shifted

    if rng.random() < 0.5:
        signoff = rng.choice(_SIGNOFFS)
        dept = rng.choice(_DEPTS)
        suffix = f"\n\n{signoff}\n{org_val} - {dept}\n"
        sig_start = len(text) + suffix.index(org_val)
        spans.append({"start": sig_start, "end": sig_start + len(org_val), "label": "ORGANIZATION"})
        text = text + suffix

    return {"text": text, "spans": spans}


# --------------------------------------------------------------------------- #
# PyMuPDF recursive-XY-cut extraction noise -- NOT hypothetical. Found by
# running the real extraction script (extract_pdf_text.py, provided by the
# team) against the 5 actual HealthOne Nova PDFs (TamerBERT/TamerBERT/org_data/
# *.pdf) and diffing the raw output against the clean reference text. Two
# distinct, confirmed failure modes:
#
# 1. xf_header_table_garble: the 3-column PATIENT/RESPONSABLE/DATE letterhead
#    gets misdetected by page.find_tables() as a ruled table in 3 of the 5 real
#    PDFs (NOVA2, NOVA3, NOVA4). table.to_markdown() then renders it as garbled
#    pipe syntax with the patient name duplicated across all 3 "columns" and a
#    literal "<br>" HTML tag leaking into the RIZIV cell (confirmed verbatim in
#    the raw extraction: "|RIZIV<br>|XXXXXXXXXXX|"). This is the MOST COMMON of
#    the two failure modes (3/5 real letters) so it's weighted higher below.
#
# 2. xf_midword_splice: an absolutely-positioned letterhead element (address)
#    that MuPDF's own line-grouping merges into the same internal "line" as
#    unrelated body text gets concatenated with ZERO separator by
#    _line_fragments()'s naive "".join(span.text for span in spans) -- unlike
#    assemble_region(), which DOES check the gap before inserting a space.
#    Confirmed verbatim in NOVA1's raw extraction: "bursa subacromiodeltoïdeale
#    p[ADRES] nd bij bursitis" -- an address spliced into the middle of the
#    Dutch word "passend". The already-shipped Dutch model's OWN training data
#    has an identical artifact baked into all 93 documents of one template
#    (found earlier via derender_templates_v3.py), independently confirming
#    this is a real, recurring failure mode of this exact document format --
#    not a one-off.
# --------------------------------------------------------------------------- #

def xf_header_table_garble(doc, rng):
    text = doc["text"]
    marker = "Contenu du rapport"
    header_end = text.find(marker)
    if header_end == -1:
        return None
    header_spans = [s for s in doc["spans"] if s["end"] <= header_end]
    names = [s for s in header_spans if s["label"] == "NAME"]
    insz = [s for s in header_spans if s["label"] == "INSZ"]
    riziv = [s for s in header_spans if s["label"] == "RIZIV"]
    dates = [s for s in header_spans if s["label"] == "DATE"]
    if len(names) != 3 or len(insz) != 1 or len(riziv) != 1 or len(dates) != 1:
        return None  # header doesn't match the expected 3-name/INSZ/RIZIV/DATE shape

    patient, responsible, sender = (text[s["start"]:s["end"]] for s in names)
    insz_val = text[insz[0]["start"]:insz[0]["end"]]
    riziv_val = text[riziv[0]["start"]:riziv[0]["end"]]
    date_val = text[dates[0]["start"]:dates[0]["end"]]

    # Build incrementally, recording each value's exact position as it's
    # placed -- avoids any str.index() ambiguity if e.g. one all-digit ID
    # value happened to be a substring of another.
    parts = []
    new_spans = []

    def emit(literal):
        parts.append(literal)

    def emit_value(value, label):
        pos = sum(len(p) for p in parts)
        new_spans.append({"start": pos, "end": pos + len(value), "label": label})
        parts.append(value)

    emit("PATIENT : RESPONSABLE : DATE :\n")
    emit_value(date_val, "DATE")
    emit("\n|PATIENT :|Col2|Col3|\n|---|---|---|\n|")
    emit_value(patient, "NAME")
    emit("|")
    emit_value(patient, "NAME")
    emit("|")
    emit_value(patient, "NAME")
    emit("|\n|INSZ|")
    emit_value(insz_val, "INSZ")
    emit("||\n|")
    emit_value(responsible, "NAME")
    emit("|Col2|\n|---|---|\n|RIZIV<br>|")
    emit_value(riziv_val, "RIZIV")
    emit("|\nENVOYÉ PAR\n:\n")
    emit_value(sender, "NAME")
    emit("\n")
    garbled = "".join(parts)

    delta = len(garbled) - header_end
    tail_spans = [{"start": s["start"] + delta, "end": s["end"] + delta, "label": s["label"]}
                  for s in doc["spans"] if s["start"] >= header_end]
    new_text = garbled + text[header_end:]
    return {"text": new_text, "spans": new_spans + tail_spans}


def xf_midword_splice(doc, rng):
    text = doc["text"]
    addr_spans = [s for s in doc["spans"] if s["label"] == "ADDRESS"]
    if not addr_spans:
        return None
    sp = rng.choice(addr_spans)
    addr_val = text[sp["start"]:sp["end"]]

    # candidate victim words: plain alphabetic runs of >=6 chars, fully
    # outside any existing span, so the splice never corrupts a real entity.
    covered = [(s["start"], s["end"]) for s in doc["spans"]]
    candidates = []
    for m in re.finditer(r"[A-Za-zÀ-ÿ]{6,}", text):
        if not any(a < m.end() and m.start() < b for a, b in covered):
            candidates.append(m)
    if not candidates:
        return None
    word = rng.choice(candidates)
    # split 1-3 chars from the start of the word, matching the real
    # "p" + ADDRESS + "nd" (from "passend") ratio
    cut = rng.randint(1, min(3, len(word.group()) - 2))
    insert_at = word.start() + cut

    edits = [(insert_at, addr_val)]
    new_text, new_spans = remap_spans_through_edits(text, doc["spans"], edits)
    new_spans.append({"start": insert_at, "end": insert_at + len(addr_val), "label": "ADDRESS"})
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# NISS/INAMI label-phrasing diversity -- every rendered document currently
# writes the exact same "NISS{value}" / "INAMI{value}" label immediately
# before these two identifiers (confirmed by validate_diversity_fr.py: 34%
# and 26% of ALL occurrences share that single literal preceding context --
# by far the most positionally rigid label in the corpus). This is exactly
# the "anything after PHONE:" trap described directly: swap in one of several
# real alternate phrasings a Belgian clinical document might use for the same
# identifier, so the model can't shortcut on a fixed label string.
# --------------------------------------------------------------------------- #
_NISS_LABELS = ["NISS", "N° NISS", "Numéro NISS", "N° de registre national",
                "Numéro de registre national"]
_INAMI_LABELS = ["INAMI", "N° INAMI", "Numéro INAMI", "N° INAMI du prestataire",
                 "Numéro INAMI du médecin"]


def xf_id_label_variant(doc, rng):
    text = doc["text"]
    insz_spans = [s for s in doc["spans"] if s["label"] == "INSZ"]
    riziv_spans = [s for s in doc["spans"] if s["label"] == "RIZIV"]
    if not insz_spans and not riziv_spans:
        return None

    edits = []
    for s in insz_spans:
        before = text[max(0, s["start"] - 4):s["start"]]
        if before == "NISS":
            new_label = rng.choice(_NISS_LABELS)
            if new_label != "NISS":
                edits.append((s["start"] - 4, s["start"], new_label))
    for s in riziv_spans:
        before = text[max(0, s["start"] - 5):s["start"]]
        if before == "INAMI":
            new_label = rng.choice(_INAMI_LABELS)
            if new_label != "INAMI":
                edits.append((s["start"] - 5, s["start"], new_label))
    if not edits:
        return None

    edits.sort(key=lambda e: e[0])
    out, last, cum_shift = [], 0, 0
    span_shift_points = []
    for start, end, replacement in edits:
        out.append(text[last:start])
        out.append(replacement)
        cum_shift += len(replacement) - (end - start)
        span_shift_points.append((end, cum_shift))
        last = end
    out.append(text[last:])
    new_text = "".join(out)

    def remap(offset):
        s = 0
        for pos, cs in span_shift_points:
            if pos <= offset:
                s = cs
            else:
                break
        return offset + s

    new_spans = [{"start": remap(sp["start"]), "end": remap(sp["end"]), "label": sp["label"]}
                 for sp in doc["spans"]]
    return {"text": new_text, "spans": new_spans}


def sanity_check(tag, doc):
    for sp in doc["spans"]:
        assert 0 <= sp["start"] < sp["end"] <= len(doc["text"]), \
            f"{tag}: bad span {sp} text={doc['text'][max(0,sp['start']-5):sp['end']+5]!r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join("tamerbert_data_fr", "train_filtered.jsonl"))
    ap.add_argument("--out", default="train_augmented_fr.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    originals = load_docs(args.input)
    print(f"loaded {len(originals)} original training documents")

    augmented = []

    n_casing = int(len(originals) * 0.20)
    for doc in rng.sample(originals, min(n_casing, len(originals))):
        d = xf_casing(doc, rng)
        sanity_check("casing", d)
        augmented.append(d)
    print(f"casing: +{n_casing}")

    n_nonmed = 180
    nonmed_docs = gen_non_medical(rng, n_nonmed)
    augmented.extend(nonmed_docs)
    print(f"non_medical: +{n_nonmed}")

    n_inline = int(len(originals) * 0.12)
    made = 0
    for doc in rng.sample(originals, min(n_inline, len(originals))):
        d = xf_inline_mention(doc, rng)
        if d is None:
            continue
        sanity_check("inline_mention", d)
        augmented.append(d)
        made += 1
    print(f"inline_mention: +{made}")

    n_ocr = int(len(originals) * 0.22)
    for doc in rng.sample(originals, min(n_ocr, len(originals))):
        d = xf_ocr_noise(doc, rng)
        sanity_check("ocr_noise", d)
        augmented.append(d)
    print(f"ocr_noise: +{n_ocr}")

    n_diac = int(len(originals) * 0.10)
    made = 0
    for doc in rng.sample(originals, min(n_diac, len(originals))):
        d = xf_diacritic_honorific(doc, rng)
        if d is None:
            continue
        sanity_check("diacritic_honorific", d)
        augmented.append(d)
        made += 1
    print(f"diacritic_honorific: +{made}")

    n_moji = int(len(originals) * 0.06)
    made = 0
    for doc in rng.sample(originals, min(n_moji, len(originals))):
        d = xf_mojibake(doc, rng)
        if d is None:
            continue
        sanity_check("mojibake", d)
        augmented.append(d)
        made += 1
    print(f"mojibake: +{made}")

    n_email = int(len(originals) * 0.08)
    for doc in rng.sample(originals, min(n_email, len(originals))):
        d = xf_email_header(doc, rng)
        sanity_check("email_header", d)
        augmented.append(d)
    print(f"email_header: +{n_email}")

    org_pool = build_value_pool(originals, "ORGANIZATION")
    addr_pool = build_value_pool(originals, "ADDRESS")
    print(f"org_context value pools: {len(org_pool)} distinct org names, {len(addr_pool)} distinct addresses")
    n_org_ctx = int(len(originals) * 0.10)
    if org_pool and addr_pool:
        for doc in rng.sample(originals, min(n_org_ctx, len(originals))):
            d = xf_org_context(doc, rng, org_pool, addr_pool)
            sanity_check("org_context", d)
            augmented.append(d)
        print(f"org_context: +{n_org_ctx}")
    else:
        print("org_context: skipped (empty ORGANIZATION or ADDRESS pool -- "
              "check label scheme matches FLAT9, not MERGED)")

    # PyMuPDF recursive-XY-cut extraction noise -- empirically grounded in the
    # 5 real HealthOne Nova PDFs (see the block comment above the transforms).
    # header_table_garble is weighted higher (5%) since it was the dominant
    # real failure mode (3/5 letters); midword_splice is rarer but more
    # severe when it happens (1/5 letters, but can land anywhere in body text).
    n_header_garble = int(len(originals) * 0.05)
    made = 0
    for doc in rng.sample(originals, min(n_header_garble, len(originals))):
        d = xf_header_table_garble(doc, rng)
        if d is None:
            continue
        sanity_check("header_table_garble", d)
        augmented.append(d)
        made += 1
    print(f"header_table_garble: +{made}")

    n_midword = int(len(originals) * 0.03)
    made = 0
    for doc in rng.sample(originals, min(n_midword, len(originals))):
        d = xf_midword_splice(doc, rng)
        if d is None:
            continue
        sanity_check("midword_splice", d)
        augmented.append(d)
        made += 1
    print(f"midword_splice: +{made}")

    n_id_label = int(len(originals) * 0.25)
    made = 0
    for doc in rng.sample(originals, min(n_id_label, len(originals))):
        d = xf_id_label_variant(doc, rng)
        if d is None:
            continue
        sanity_check("id_label_variant", d)
        augmented.append(d)
        made += 1
    print(f"id_label_variant: +{made}")

    total = originals + augmented
    rng.shuffle(total)
    with open(args.out, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
