"""
Round-3 augmentation, built on round-2's taxonomy-update retrain
(tamerbert-taxonomy-v1 / pii-tamerbert-v3) results.

Regenerated from train_filtered_org.jsonl from scratch (same discipline as
round 2: avoid compounding random-sampling overlap between rounds).

Carried over from round 2, unchanged (validated clean on round-2's fresh
v5 battery, no residual issues found):
  1. casing
  2. non_medical
  3. inline_mention
  4. ocr_noise
  5. diacritic_honorific
  6. mojibake
  7. email_header

New (round-3 finding, from analyzing tamerbert-taxonomy-v1's OOD results):
  8. letterhead -- ORGANIZATION as the literal first token of a document,
     immediately followed (single newline, no blank-line separator) by an
     ADDRESS. Root-caused by a direct query over train_augmented_v3.jsonl:
     across all 6135 training docs, ORGANIZATION NEVER once starts at
     position 0, and NEVER once sits within 3 characters of a following
     ADDRESS span. Both fresh OOD failures this round (ood doc 9's
     org_ambiguity letterhead, and ood_v5's v5_06 org_and_btw doc) hit
     exactly this blind spot -- the model fragmented/truncated ORGANIZATION
     specifically in this configuration, while nailing the exact same org
     name's *signature* mention elsewhere in the same document. Draws org
     and address values from pools already present in the corpus (not a
     new hardcoded list) so it stays as diverse as the template pool itself.

Also fixed this round (not a training change): ood_stress_test_v5's v5_04
"email_header" doc had two real email addresses in its raw text that were
never wrapped in an EMAIL gold-label marker -- an oversight from before
EMAIL became a real scored label. Fixed directly in
ood_stress_test_v5/build_ood_set_v5.py (content unchanged, gold labels
corrected) since every one of our 7 standing eval surfaces had exactly
zero EMAIL gold spans -- the regex+checksum logic was never actually
validated end-to-end against real ground truth until now.
"""
import json
import os
import random

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_filtered_org.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_augmented_v4.jsonl")


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
# 4. OCR noise
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
# 5. Diacritic / honorific
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
# 6. Mojibake
# --------------------------------------------------------------------------- #
def mojibake(s):
    return s.encode("utf-8").decode("latin-1")


def xf_mojibake(doc, rng):
    with_diacritic = xf_diacritic_honorific(doc, rng)
    if with_diacritic is None or not any(ord(c) > 127 for c in with_diacritic["text"]):
        return None
    return remap_via_transform(with_diacritic, mojibake)


# --------------------------------------------------------------------------- #
# 7. Email header hard negative
# --------------------------------------------------------------------------- #
_EMAIL_LOCALS = ["dr.peeters", "dr.claes", "secretariaat", "dr.vandenberghe",
                 "verwijzer", "dr.aerts", "onthaal", "dr.demeyer"]
_EMAIL_DOMAINS = ["azstlucas.be", "uzgent.be", "huisartsenpraktijk.be", "azgroeninge.be"]


def xf_email_header(doc, rng):
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


# --------------------------------------------------------------------------- #
# 8. NEW: letterhead -- ORGANIZATION at position 0, immediately (single
#    newline) followed by ADDRESS. See module docstring for the root-cause
#    evidence. Values drawn from pools built from the corpus itself.
# --------------------------------------------------------------------------- #
def build_value_pool(originals, label):
    vals = set()
    for d in originals:
        for s in d["spans"]:
            if s["label"] == label:
                vals.add(d["text"][s["start"]:s["end"]])
    return sorted(vals)


def xf_letterhead(doc, rng, org_pool, addr_pool):
    org_val = rng.choice(org_pool)
    addr_val = rng.choice(addr_pool)
    prefix = f"{org_val}\n{addr_val}\n\n"
    new_org_span = {"start": 0, "end": len(org_val), "label": "ORGANIZATION"}
    new_addr_span = {"start": len(org_val) + 1, "end": len(org_val) + 1 + len(addr_val), "label": "ADDRESS"}
    shifted = [{"start": s["start"] + len(prefix), "end": s["end"] + len(prefix), "label": s["label"]}
               for s in doc["spans"]]
    return {"text": prefix + doc["text"], "spans": [new_org_span, new_addr_span] + shifted}


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

    org_pool = build_value_pool(originals, "ORGANIZATION")
    addr_pool = build_value_pool(originals, "ADDRESS")
    print(f"letterhead value pools: {len(org_pool)} distinct org names, {len(addr_pool)} distinct addresses")
    n_letterhead = int(len(originals) * 0.15)
    for doc in rng.sample(originals, n_letterhead):
        d = xf_letterhead(doc, rng, org_pool, addr_pool)
        sanity_check("letterhead", d)
        augmented.append(d)
    print(f"letterhead: +{n_letterhead}")

    total = originals + augmented
    rng.shuffle(total)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
