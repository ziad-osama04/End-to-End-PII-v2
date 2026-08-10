"""
Training-data augmentation targeting the failure modes confirmed by the
discovery pass (personal_finetune/ood_stress_test_v2/). Every transform adds
NEW documents alongside the untouched originals from train_filtered.jsonl --
nothing is removed or replaced, so in-distribution performance shouldn't
regress even if a transform doesn't help.

Five transforms (institutional-name hard negatives was DROPPED after
discovering the corpus already deliberately labels org/hospital names as
NAME -- confirmed identically in pii_table.py's FLAT9 scheme AND all 5 real
ground-truth documents ("AZORG" tagged NAME everywhere). Adding that
"fix" would have taught the model to contradict an established, correct
convention.):

  1. casing        -- upper/lower/title-case whole documents (span-preserving)
  2. non_medical    -- brand-new zero-span documents, generic Dutch business
                        letters, teaches "not every formal letter has PII"
  3. inline_mention -- append a second, unlabeled-cue prose sentence
                        mentioning an existing ADDRESS/PHONE value, teaching
                        recognition without a "Label:" cue
  4. ocr_noise      -- irregular word-internal whitespace across the whole
                        document (PDF-extraction-style noise)
  5. diacritic_honorific -- swap a NAME span's value for a diacritic name
                        and/or an uncommon honorific ("de heer" etc.)

All offset-tracking reuses the same edit-list + monotonic remap approach
validated in ood_stress_test_v2/perturbation_sweep.py.
"""
import json
import os
import random

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_filtered.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_augmented.jsonl")


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
    """edits: list of (position, inserted_text) in original-text coordinates."""
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


# --------------------------------------------------------------------------- #
# 1. Casing
# --------------------------------------------------------------------------- #
def xf_casing(doc, rng):
    fn = rng.choice([str.upper, str.lower, str.title])
    return {"text": fn(doc["text"]), "spans": [dict(s) for s in doc["spans"]]}


# --------------------------------------------------------------------------- #
# 2. Non-medical negatives -- entirely new, zero-span documents
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# 3. Inline mention -- add a second, unlabeled-cue occurrence of an existing
#    ADDRESS/PHONE value elsewhere in the same document.
# --------------------------------------------------------------------------- #
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
    insert_at = len(doc["text"])  # append at end of document
    new_span_start = insert_at + len(sentence_before_value)
    new_span = {"start": new_span_start, "end": new_span_start + len(value), "label": sp["label"]}
    new_text = doc["text"] + sentence_before_value + value + sentence_after_value
    return {"text": new_text, "spans": [dict(s) for s in doc["spans"]] + [new_span]}


# --------------------------------------------------------------------------- #
# 4. OCR noise -- irregular word-internal whitespace across the whole doc
# --------------------------------------------------------------------------- #
def xf_ocr_noise(doc, rng, rate=0.05):
    text = doc["text"]
    edits = []
    for i, ch in enumerate(text):
        if ch.isalpha() and i > 0 and text[i - 1].isalpha() and rng.random() < rate:
            edits.append((i, " "))
    new_text, new_spans = remap_spans_through_edits(text, doc["spans"], edits)
    return {"text": new_text, "spans": new_spans}


# --------------------------------------------------------------------------- #
# 5. Diacritic / honorific swap on a NAME span
# --------------------------------------------------------------------------- #
_DIACRITIC_NAMES = ["Müller", "Amélie Dupont", "François Léger", "José Fernández",
                     "Ürkan Yildiz", "Renée Vaes", "André Piérard"]
_HONORIFICS = ["de heer ", "mevrouw ", "dhr. ", "mw. "]


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


def sanity_check(tag, doc):
    for sp in doc["spans"]:
        assert 0 <= sp["start"] < sp["end"] <= len(doc["text"]), f"{tag}: bad span {sp}"


def main():
    rng = random.Random(42)
    originals = load_docs(IN_PATH)
    print(f"loaded {len(originals)} original training documents")

    augmented = []

    # 1. casing -- ~20% of the pool, highest priority given severity found
    n_casing = int(len(originals) * 0.20)
    for doc in rng.sample(originals, n_casing):
        new_doc = xf_casing(doc, rng)
        sanity_check("casing", new_doc)
        augmented.append(new_doc)
    print(f"casing: +{n_casing}")

    # 2. non-medical negatives
    n_nonmed = 180
    nonmed_docs = gen_non_medical(rng, n_nonmed)
    for d in nonmed_docs:
        sanity_check("non_medical", d)
    augmented.extend(nonmed_docs)
    print(f"non_medical: +{n_nonmed}")

    # 3. inline mention -- ~12% of the pool
    n_inline = int(len(originals) * 0.12)
    made = 0
    for doc in rng.sample(originals, n_inline):
        new_doc = xf_inline_mention(doc, rng)
        if new_doc is None:
            continue
        sanity_check("inline_mention", new_doc)
        augmented.append(new_doc)
        made += 1
    print(f"inline_mention: +{made}")

    # 4. OCR noise -- ~12% of the pool
    n_ocr = int(len(originals) * 0.12)
    for doc in rng.sample(originals, n_ocr):
        new_doc = xf_ocr_noise(doc, rng)
        sanity_check("ocr_noise", new_doc)
        augmented.append(new_doc)
    print(f"ocr_noise: +{n_ocr}")

    # 5. diacritic/honorific -- ~4% of the pool
    n_diac = int(len(originals) * 0.04)
    made = 0
    for doc in rng.sample(originals, n_diac):
        new_doc = xf_diacritic_honorific(doc, rng)
        if new_doc is None:
            continue
        sanity_check("diacritic_honorific", new_doc)
        augmented.append(new_doc)
        made += 1
    print(f"diacritic_honorific: +{made}")

    total = originals + augmented
    rng.shuffle(total)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
