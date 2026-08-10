"""
Round-2 augmentation, built on the round-1 discovery findings validated
against the fresh v3 battery, plus a NEW round-2 discovery pass
(personal_finetune/ood_stress_test_v4_discovery/) run cheaply against the
round-1 model (farahelmashad/pii-tamerbert-v2) before writing any of this.

Regenerated from train_filtered.jsonl from scratch (not layered on top of
round-1's train_augmented.jsonl) to avoid compounding random-sampling
overlap between rounds -- cleaner to reason about.

Carried over from round 1, unchanged (already fully solved, confirmed on
the independent v3 battery -- zero errors on casing/non-medical/inline
instances that had zero overlap with training examples):
  1. casing        -- ~20% of pool
  2. non_medical    -- 180 generated docs
  3. inline_mention -- ~12% of pool

Strengthened (round 1 improved-but-did-not-solve these; the fresh-battery
error trace showed residual fragmentation under BOTH, at 8% and 2.6% of
pool respectively -- clearly under-covered):
  4. ocr_noise      -- 12% -> 22% of pool, noise rate 0.05 -> 0.08
  5. diacritic_honorific -- 4% -> 10% of pool, expanded name/honorific pools

New (round-2 discovery findings):
  6. mojibake       -- whole-document UTF-8-as-Latin-1 corruption; round-2
                        discovery found this breaks NAME recognition
                        specifically (digit fields are immune, since
                        corruption only touches non-ASCII characters)
  7. email_header   -- prepend a plausible "Van:/Aan:/Onderwerp:" email
                        header block with unlabeled name-shaped email
                        local-parts; round-2 discovery found the model tags
                        "dr.claes" (from "dr.claes@domain.be") as NAME

Deliberately NOT touched (reviewed in round-2 discovery, no action needed):
  - foreign phone formats: the MODEL already generalizes reasonably (caught
    a French mobile number correctly); regex has a blind spot there but the
    chosen drop_all merge strategy doesn't route PHONE through regex anyway,
    so it doesn't affect the actual pipeline output.
  - homoglyphs: single test case came back clean, no evidence of a problem
    worth spending training capacity on.
"""
import json
import os
import random

# train_filtered_org.jsonl = train_filtered.jsonl with ORGANIZATION split out
# of NAME (add_organization_label.py) -- augmenting from the org-aware base
# so casing/OCR-noise/etc. all apply correctly to the new label too.
IN_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_filtered_org.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_augmented_v3.jsonl")


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
    """For deterministic, prefix-preserving character-level transforms
    (mojibake) -- remap by re-applying the transform to each span
    boundary's prefix and measuring its new length. Simpler and more
    robust than edit-list tracking for whole-string transforms."""
    text = doc["text"]
    new_text = transform_fn(text)
    new_spans = []
    for sp in doc["spans"]:
        new_start = len(transform_fn(text[:sp["start"]]))
        new_end = len(transform_fn(text[:sp["end"]]))
        new_spans.append({"start": new_start, "end": new_end, "label": sp["label"]})
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# 1-3. Carried over unchanged from round 1
# --------------------------------------------------------------------------- #
def xf_casing(doc, rng):
    fn = rng.choice([str.upper, str.lower, str.title])
    return {"text": fn(doc["text"]), "spans": [dict(s) for s in doc["spans"]]}


_COMPANIES = ["Bpost", "Colruyt Group", "Proximus", "Delhaize", "Telenet",
              "De Lijn", "Bol.com", "Torfs", "JBC", "Decathlon Belgie"]
_PRODUCTS = ["uw pakket", "uw bestelling", "uw abonnement", "uw reservatie", "uw ticket"]
_TEMPLATES = [
    "Geachte klant,\n\nWij danken u voor {product} bij {company}. Dit wordt "
    "momenteel verwerkt en zal binnen enkele werkdagen worden afgehandeld.\n\n"
    "Voor vragen kan u terecht bij onze klantendienst tijdens kantooruren.\n\n"
    "Met vriendelijke groeten,\nKlantendienst {company}\n",

    "Beste,\n\nUw abonnement bij {company} wordt binnenkort automatisch verlengd. "
    "Indien u dit niet wenst, kan u dit tot 14 dagen voor de vervaldatum "
    "stopzetten via uw online account.\n\nMet vriendelijke groeten,\n"
    "Het team van {company}\n",

    "Beste bezoeker,\n\nHartelijk dank voor uw interesse in ons evenement. "
    "{product} is bevestigd en u ontvangt binnenkort meer informatie per "
    "e-mail. Wij kijken ernaar uit u te mogen verwelkomen.\n\n"
    "Vriendelijke groeten,\nHet organisatiecomite\n",

    "Geachte heer, mevrouw,\n\nNaar aanleiding van uw contactname willen wij u "
    "graag informeren dat {product} momenteel in behandeling is bij onze "
    "dienst. Wij nemen zo snel mogelijk contact met u op.\n\n"
    "Met vriendelijke groeten,\n{company}\n",
]


def gen_non_medical(rng, n):
    out = []
    for _ in range(n):
        tmpl = rng.choice(_TEMPLATES)
        text = tmpl.format(company=rng.choice(_COMPANIES), product=rng.choice(_PRODUCTS))
        out.append({"text": text, "spans": []})
    return out


_INLINE_ADDRESS_TEMPLATES = [
    "De patient woont op {v} en is hiervan op de hoogte gebracht.\n",
    "Correspondentie wordt verstuurd naar {v}.\n",
    "Patient blijft bereikbaar op het adres {v}.\n",
]
_INLINE_PHONE_TEMPLATES = [
    "Voor dringende vragen is de patient bereikbaar via {v}.\n",
    "Contactname kan telefonisch via {v}.\n",
    "De patient gaf {v} op als contactnummer.\n",
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
# 4. OCR noise -- STRENGTHENED (rate 0.05 -> 0.08)
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
# 5. Diacritic / honorific -- STRENGTHENED (expanded pools)
# --------------------------------------------------------------------------- #
_DIACRITIC_NAMES = ["Müller", "Amélie Dupont", "François Léger", "José Fernández",
                     "Ürkan Yildiz", "Renée Vaes", "André Piérard", "Björn Andersson",
                     "Céline Wéry", "Łukasz Kowalski", "Zoë Van der Meulen",
                     "Nuñez Garcia", "Sørensen Vermeulen"]
_HONORIFICS = ["de heer ", "mevrouw ", "dhr. ", "mw. ", "mej. "]


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
# 6. NEW: mojibake -- whole-document UTF-8-as-Latin-1 corruption
# --------------------------------------------------------------------------- #
def mojibake(s):
    return s.encode("utf-8").decode("latin-1")


def xf_mojibake(doc, rng):
    """pii_table.py's NAMES pools are plain ASCII -- a random document has no
    diacritics IN ITS PII SPANS to corrupt (only occasional incidental ones
    in boilerplate, e.g. a stray existing "PATI�NT" artifact). Applying
    mojibake alone would corrupt boilerplate and miss the point entirely, so
    first inject a diacritic name (same pool as xf_diacritic_honorific),
    THEN corrupt -- this guarantees the corruption actually lands on a PII
    value, matching what round-2 discovery showed breaks recognition."""
    with_diacritic = xf_diacritic_honorific(doc, rng)
    if with_diacritic is None or not any(ord(c) > 127 for c in with_diacritic["text"]):
        return None
    return remap_via_transform(with_diacritic, mojibake)


# --------------------------------------------------------------------------- #
# 7. NEW: email header hard negative -- prepend a "Van:/Aan:/Onderwerp:"
#    block with unlabeled name-shaped email local-parts.
# --------------------------------------------------------------------------- #
_EMAIL_LOCALS = ["dr.peeters", "dr.claes", "secretariaat", "dr.vandenberghe",
                 "verwijzer", "dr.aerts", "onthaal", "dr.demeyer"]
_EMAIL_DOMAINS = ["azstlucas.be", "uzgent.be", "huisartsenpraktijk.be", "azgroeninge.be"]
def xf_email_header(doc, rng):
    """Originally left the email addresses entirely unlabeled (teaching only
    "this is not a NAME"). Now that EMAIL is a real scored label (team
    taxonomy update), label them positively instead -- same effect on model
    training (EMAIL is regex-permanent, so strip_for_training() removes it
    before the model ever sees a label either way), but now the eval gold
    actually has an EMAIL entity to score regex_only/full_pipeline against,
    which the old unlabeled version couldn't do."""
    a, b = rng.sample(_EMAIL_LOCALS, 2)
    da, db = rng.choice(_EMAIL_DOMAINS), rng.choice(_EMAIL_DOMAINS)
    email_a, email_b = f"{a}@{da}", f"{b}@{db}"
    prefix = f"Van: {email_a}\nAan: {email_b}\nOnderwerp: dossier patient\n\n"
    email_spans = [
        {"start": prefix.index(email_a), "end": prefix.index(email_a) + len(email_a), "label": "EMAIL"},
        {"start": prefix.index(email_b), "end": prefix.index(email_b) + len(email_b), "label": "EMAIL"},
    ]
    shifted = [{"start": s["start"] + len(prefix), "end": s["end"] + len(prefix), "label": s["label"]}
               for s in doc["spans"]]
    return {"text": prefix + doc["text"], "spans": email_spans + shifted}


def sanity_check(tag, doc):
    for sp in doc["spans"]:
        assert 0 <= sp["start"] < sp["end"] <= len(doc["text"]), f"{tag}: bad span {sp}"


def main():
    rng = random.Random(42)
    originals = load_docs(IN_PATH)
    print(f"loaded {len(originals)} original training documents")

    augmented = []

    n_casing = int(len(originals) * 0.20)
    for doc in rng.sample(originals, n_casing):
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
    for doc in rng.sample(originals, n_inline):
        d = xf_inline_mention(doc, rng)
        if d is None:
            continue
        sanity_check("inline_mention", d)
        augmented.append(d)
        made += 1
    print(f"inline_mention: +{made}")

    n_ocr = int(len(originals) * 0.22)
    for doc in rng.sample(originals, n_ocr):
        d = xf_ocr_noise(doc, rng)
        sanity_check("ocr_noise", d)
        augmented.append(d)
    print(f"ocr_noise: +{n_ocr}")

    n_diac = int(len(originals) * 0.10)
    made = 0
    for doc in rng.sample(originals, n_diac):
        d = xf_diacritic_honorific(doc, rng)
        if d is None:
            continue
        sanity_check("diacritic_honorific", d)
        augmented.append(d)
        made += 1
    print(f"diacritic_honorific: +{made}")

    n_moji = int(len(originals) * 0.06)
    made = 0
    for doc in rng.sample(originals, n_moji):
        d = xf_mojibake(doc, rng)
        if d is None:
            continue
        sanity_check("mojibake", d)
        augmented.append(d)
        made += 1
    print(f"mojibake: +{made}")

    n_email = int(len(originals) * 0.08)
    for doc in rng.sample(originals, n_email):
        d = xf_email_header(doc, rng)
        sanity_check("email_header", d)
        augmented.append(d)
    print(f"email_header: +{n_email}")

    total = originals + augmented
    rng.shuffle(total)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
