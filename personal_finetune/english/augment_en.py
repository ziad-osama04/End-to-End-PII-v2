"""
augment_en.py -- English fork of personal_finetune/french/augment_fr.py.

Transform mechanics kept unchanged (position/offset mechanics, not language
content): xf_casing, xf_ocr_noise, xf_diacritic_honorific, xf_mojibake,
xf_inline_mention, xf_org_context, xf_email_header, gen_non_medical, and the
two real-extraction-pipeline-grounded transforms (xf_header_table_garble,
xf_midword_splice).

NOTE on INSZ/RIZIV label-phrasing diversity: this file used to carry an
xf_id_label_variant augmentation transform (added from round 1, after
validate_diversity_en.py caught INSZ at 100% top-context share on the very
first draft -- every one of the 50 templates hardcoded the identical literal
"National Registration No." with zero variation). That transform is REMOVED
now: augmentation can only ADD transformed copies on top of unmodified
originals, so no matter how high its rate was pushed (it reached 90%), the
achievable floor stayed bounded by the fraction of untouched originals still
in the corpus -- INSZ only got to 63.9%, still far off French's 28.4%. Fixed
at the ROOT instead, in pii_table_en.py: INSZ_LABEL/RIZIV_LABEL are now
per-case sampled fields (LABEL_POOL_INSZ/LABEL_POOL_RIZIV), and every one of
the 56 templates renders {INSZ_LABEL}{INSZ}/{RIZIV_LABEL}{RIZIV} instead of
a hardcoded literal -- so the variety now applies to 100% of the corpus from
generation, not a fraction of augmented copies.

Pools: kept truly-national Belgian brands; since English is NATIONALLY
DISTRIBUTED (not one region), BOTH Flemish and Walloon regional-brand
variants are kept side by side (De Lijn AND TEC; Telenet AND VOO) rather
than picking one, matching the locked-in geography decision.

Belgian doctor writing in English register note: NAME_DOCTOR already
includes "Dr " (3 chars, no period) baked in by pii_table_en.py -- NOT
Dutch/French's "dr. "/"dr. " (4 chars, with period) -- so
xf_diacritic_honorific's prefix-detection differs from the French version.

Usage:
    python3 augment_en.py --input tamerbert_data_en/train_filtered.jsonl \
        --out train_augmented_en.jsonl
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
# Non-medical negatives -- national Belgian brands. Since English is
# nationally distributed (not one region), BOTH regional variants are kept
# side by side rather than picking one (unlike French, which is Walloon-only
# and dropped Flemish-only brands).
# --------------------------------------------------------------------------- #
_COMPANIES = ["Bpost", "Colruyt Group", "Proximus", "Delhaize", "VOO", "TEC",
              "De Lijn", "Telenet", "Bol.com", "Decathlon Belgium",
              "Carrefour", "Base"]
_PRODUCTS = ["your parcel", "your order", "your subscription",
             "your reservation", "your ticket"]
_TEMPLATES = [
    "Dear customer,\n\nThank you for {product} with {company}. It is "
    "currently being processed and will be finalised within the next few "
    "working days.\n\nFor any questions, our customer service remains "
    "available during office hours.\n\nKind regards,\n{company} Customer "
    "Service\n",

    "Dear customer,\n\nYour subscription with {company} will be "
    "automatically renewed shortly. If you do not wish this to happen, you "
    "can cancel it up to 14 days before the renewal date via your online "
    "account.\n\nKind regards,\nThe {company} team\n",

    "Dear visitor,\n\nThank you for your interest in our event. {product} "
    "is confirmed and you will shortly receive further information by "
    "email. We look forward to welcoming you.\n\nKind regards,\nThe "
    "organising committee\n",

    "Dear Sir or Madam,\n\nFollowing your enquiry, we would like to inform "
    "you that {product} is currently being processed by our department. We "
    "will get back to you as soon as possible.\n\nKind regards,\n{company}\n",
]


def gen_non_medical(rng, n):
    out = []
    for _ in range(n):
        tmpl = rng.choice(_TEMPLATES)
        text = tmpl.format(company=rng.choice(_COMPANIES), product=rng.choice(_PRODUCTS))
        out.append({"text": text, "spans": []})
    return out


_INLINE_ADDRESS_TEMPLATES = [
    "The patient lives at {v} and has been informed of this.\n",
    "Correspondence is sent to {v}.\n",
    "The patient remains reachable at the address {v}.\n",
]
_INLINE_PHONE_TEMPLATES = [
    "For any urgent question, the patient can be reached on {v}.\n",
    "Contact can be made by telephone on {v}.\n",
    "The patient provided {v} as a contact number.\n",
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
# Diacritic / honorific -- diacritic names kept broadly international (tests
# Unicode-normalization robustness generally, not tied to one origin pool).
# Honorifics forked to English. NOTE: NAME_DOCTOR renders as "Dr Surname"
# (3-char "Dr " prefix, no period) in pii_table_en.py, NOT French/Dutch's
# "dr. " (4 chars, with period) -- the prefix-strip length differs.
# --------------------------------------------------------------------------- #
_DIACRITIC_NAMES = ["Müller", "Amélie Dupont", "François Léger", "José Fernández",
                     "Ürkan Yildiz", "Renée Vaes", "André Piérard", "Björn Andersson",
                     "Céline Wéry", "Łukasz Kowalski", "Zoë Delcourt",
                     "Nuñez Garcia", "Sørensen Delvaux"]
_HONORIFICS = ["Mr ", "Mrs ", "Ms ", "Dr "]


def xf_diacritic_honorific(doc, rng):
    candidates = [i for i, s in enumerate(doc["spans"]) if s["label"] == "NAME"]
    if not candidates:
        return None
    idx = rng.choice(candidates)
    sp = doc["spans"][idx]
    old_val = doc["text"][sp["start"]:sp["end"]]
    if old_val.startswith("Dr "):
        new_val = rng.choice(_HONORIFICS) + old_val[3:]
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
# Email header hard negative -- nationally distributed, so both Flemish
# (az*/uz*) and Walloon (chu*/chr*) hospital-domain conventions are kept.
# --------------------------------------------------------------------------- #
_EMAIL_LOCALS = ["dr.smith", "dr.dubois", "secretariat", "dr.patel",
                 "referring.physician", "dr.janssens", "reception", "dr.okafor"]
_EMAIL_DOMAINS = ["chuliege.be", "chrcitadelle.be", "cliniquesaintluc.be",
                   "azalma.be", "uzbrussel.be", "znamiddelheim.be"]


def xf_email_header(doc, rng):
    a, b = rng.sample(_EMAIL_LOCALS, 2)
    da, db = rng.choice(_EMAIL_DOMAINS), rng.choice(_EMAIL_DOMAINS)
    email_a, email_b = f"{a}@{da}", f"{b}@{db}"
    prefix = f"From: {email_a}\nTo: {email_b}\nSubject: patient file\n\n"
    email_spans = [
        {"start": prefix.index(email_a), "end": prefix.index(email_a) + len(email_a), "label": "EMAIL"},
        {"start": prefix.index(email_b), "end": prefix.index(email_b) + len(email_b), "label": "EMAIL"},
    ]
    shifted = [{"start": s["start"] + len(prefix), "end": s["end"] + len(prefix), "label": s["label"]}
               for s in doc["spans"]]
    return {"text": prefix + doc["text"], "spans": email_spans + shifted}


# --------------------------------------------------------------------------- #
# Org/address context -- structure unchanged. English sign-offs and
# department names.
# --------------------------------------------------------------------------- #
def build_value_pool(originals, label):
    vals = set()
    for d in originals:
        for s in d["spans"]:
            if s["label"] == label:
                vals.add(d["text"][s["start"]:s["end"]])
    return sorted(vals)


_SIGNOFFS = ["Kind regards,", "Yours sincerely,", "Best regards,"]
_DEPTS = ["Radiology Department", "Cardiology Department", "Orthopaedics Department",
          "Emergency Department", "Internal Medicine Department"]


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
# PyMuPDF recursive-XY-cut extraction noise -- the confirmed failure shapes
# from the real extraction script run against the 5 real (Dutch-language)
# HealthOne Nova PDFs. There is no real ENGLISH reference PDF, but the
# underlying bugs are PDF-layout-geometry-driven (page.find_tables()
# misdetecting a 3-column letterhead; _line_fragments()'s naive "".join()
# with no gap check), not language-specific -- so the same shapes are reused
# here, stated explicitly as an inferred-from-mechanism assumption rather
# than a real-document-confirmed one for English specifically.
#
# The garbled header's own cell labels are kept as terse, plausible
# abbreviations of the actual English header text ("Reg. No." / "NIHDI") --
# NOT reverted to the Dutch "INSZ"/"RIZIV" literal artifact text, since that
# would reintroduce the wrong-language label into an English document.
# --------------------------------------------------------------------------- #

def xf_header_table_garble(doc, rng):
    text = doc["text"]
    marker = "Report contents"
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

    parts = []
    new_spans = []

    def emit(literal):
        parts.append(literal)

    def emit_value(value, label):
        pos = sum(len(p) for p in parts)
        new_spans.append({"start": pos, "end": pos + len(value), "label": label})
        parts.append(value)

    emit("PATIENT : RESPONSIBLE : DATE :\n")
    emit_value(date_val, "DATE")
    emit("\n|PATIENT :|Col2|Col3|\n|---|---|---|\n|")
    emit_value(patient, "NAME")
    emit("|")
    emit_value(patient, "NAME")
    emit("|")
    emit_value(patient, "NAME")
    emit("|\n|Reg. No.|")
    emit_value(insz_val, "INSZ")
    emit("||\n|")
    emit_value(responsible, "NAME")
    emit("|Col2|\n|---|---|\n|NIHDI<br>|")
    emit_value(riziv_val, "RIZIV")
    emit("|\nSENT BY\n:\n")
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

    covered = [(s["start"], s["end"]) for s in doc["spans"]]
    candidates = []
    for m in re.finditer(r"[A-Za-zÀ-ÿ]{6,}", text):
        if not any(a < m.end() and m.start() < b for a, b in covered):
            candidates.append(m)
    if not candidates:
        return None
    word = rng.choice(candidates)
    cut = rng.randint(1, min(3, len(word.group()) - 2))
    insert_at = word.start() + cut

    edits = [(insert_at, addr_val)]
    new_text, new_spans = remap_spans_through_edits(text, doc["spans"], edits)
    new_spans.append({"start": insert_at, "end": insert_at + len(addr_val), "label": "ADDRESS"})
    return {"text": new_text, "spans": new_spans}

# National-Register/NIHDI label-phrasing diversity used to be patched in
# HERE (an xf_id_label_variant augmentation transform, built from round 1
# after validate_diversity_en.py caught INSZ at 100% top-context share on
# the untouched first draft). Removed: augmentation can only ADD transformed
# copies on top of unmodified originals, so the achievable floor was
# mathematically bounded by the augmentation rate no matter how high it was
# pushed (INSZ only reached 63.9%, still far off French's 28.4%). Fixed at
# the ROOT instead -- pii_table_en.py now samples INSZ_LABEL/RIZIV_LABEL
# per-case from LABEL_POOL_INSZ/LABEL_POOL_RIZIV and every one of the 56
# templates renders {INSZ_LABEL}{INSZ}/{RIZIV_LABEL}{RIZIV} instead of a
# hardcoded literal, so label-context variety now applies to 100% of the
# corpus from generation, not a fraction of augmented copies.


def sanity_check(tag, doc):
    for sp in doc["spans"]:
        assert 0 <= sp["start"] < sp["end"] <= len(doc["text"]), \
            f"{tag}: bad span {sp} text={doc['text'][max(0,sp['start']-5):sp['end']+5]!r}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=os.path.join("tamerbert_data_en", "train_filtered.jsonl"))
    ap.add_argument("--out", default="train_augmented_en.jsonl")
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

    total = originals + augmented
    rng.shuffle(total)
    with open(args.out, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
