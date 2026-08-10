"""
Round-4 (FINAL) augmentation. Built under a hard deadline directly from
tamerbert-org-boundary-v1's (kernel v11) own results -- three concrete,
observed regressions/gaps, not speculation:

1. `ood` doc 9 is still broken, but for a different reason than round 3
   targeted: the org name there is followed by the INSTITUTION'S OWN
   address, which is deliberately left UNLABELED in gold (only the
   patient's separate address later in the doc is scored). Round 3's
   letterhead transform only ever trained "org + a GOLD-LABELED address"
   -- never "org + an address-shaped line that ISN'T actually PII". The
   model has no signal that the immediately-following line can be a hard
   negative, so it still fragments the org name's own characters.
2. `ood_v5`'s v5_06 SIGNATURE mention (second occurrence, later in the doc)
   regressed to a total miss. Round 3's letterhead transform only ever
   put ORGANIZATION at position 0 -- it never explicitly re-trained the
   *second*, signature-style mention pattern.
3. NAME F1 dropped on `ood`/`ood_v2`/`ood_v3` (three independent OOD
   surfaces with ZERO organization content), with the model hallucinating
   stray 1-character ORGANIZATION fragments inside plain NAME text. Round
   3's letterhead transform was too concentrated: one rigid template
   ("ORG\nADDRESS\n\n", always doc-initial, always the same shape) at 15%
   of the pool, drawn from only 90 org names -- likely overfit that exact
   shape at some cost to general boundary stability elsewhere.

Fix, all inside a single redesigned `xf_org_context` (replaces round 3's
`xf_letterhead`) with FOUR sub-variants instead of one rigid template,
at a REDUCED 10% pool fraction (was 15%) to lessen concentration risk:
  A. plain letterhead: org \\n address \\n\\n                  (round 3's case, kept)
  B. hard negative:    org \\n <unlabeled address-shaped line> \\n\\n
  C. same-line:        org, address                            (the v6_03 case)
  D. org alone:        org \\n\\n                               (no address at all,
                        breaks the "org always paired with address" assumption)
Every variant has a 50% chance of ALSO appending a signature-style second
mention of the SAME org at the end of the document ("Met vriendelijke
groeten,\\n{org}") to directly re-train the dual-mention recall pattern
that regressed.

Carried over unchanged from round 3 (no evidence of a problem, don't
touch what isn't broken under a deadline): casing, non_medical,
inline_mention, ocr_noise, diacritic_honorific, mojibake, email_header.
"""
import json
import os
import random

IN_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_filtered_org.jsonl")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data", "train_augmented_v5.jsonl")


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
# 8. REDESIGNED (round 4): org_context -- 4 structural variants + optional
#    signature mention. See module docstring for the root-cause evidence.
# --------------------------------------------------------------------------- #
def build_value_pool(originals, label):
    vals = set()
    for d in originals:
        for s in d["spans"]:
            if s["label"] == label:
                vals.add(d["text"][s["start"]:s["end"]])
    return sorted(vals)


_SIGNOFFS = ["Met vriendelijke groeten,", "Met vriendelijke groet,", "Hoogachtend,"]
_DEPTS = ["Dienst Radiologie", "Dienst Cardiologie", "Dienst Orthopedie",
          "Dienst Spoedgevallen", "Dienst Interne Geneeskunde"]


def xf_org_context(doc, rng, org_pool, addr_pool):
    org_val = rng.choice(org_pool)
    addr_val = rng.choice(addr_pool)
    variant = rng.choice(["plain", "hard_negative", "same_line", "org_alone"])

    if variant == "plain":
        prefix = f"{org_val}\n{addr_val}\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"},
                         {"start": len(org_val) + 1, "end": len(org_val) + 1 + len(addr_val), "label": "ADDRESS"}]
    elif variant == "hard_negative":
        # The address-shaped line is present in the TEXT but deliberately
        # NOT gold-labeled -- teaches the model the org span shouldn't
        # bleed into (or fragment because of) a following line that merely
        # LOOKS like an address. Mirrors `ood` doc 9's actual structure
        # (institution's own address, left unlabeled in that battery).
        prefix = f"{org_val}\n{addr_val}\nwww.{org_val.split()[0].lower()}.be\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"}]
    elif variant == "same_line":
        prefix = f"{org_val}, {addr_val}\n\n"
        prefix_spans = [{"start": 0, "end": len(org_val), "label": "ORGANIZATION"},
                         {"start": len(org_val) + 2, "end": len(org_val) + 2 + len(addr_val), "label": "ADDRESS"}]
    else:  # org_alone -- breaks the "org always paired with address" assumption
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


def sanity_check(tag, doc):
    for sp in doc["spans"]:
        assert 0 <= sp["start"] < sp["end"] <= len(doc["text"]), \
            f"{tag}: bad span {sp} text={doc['text'][max(0,sp['start']-5):sp['end']+5]!r}"


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
    print(f"org_context value pools: {len(org_pool)} distinct org names, {len(addr_pool)} distinct addresses")
    n_org_ctx = int(len(originals) * 0.10)
    for doc in rng.sample(originals, n_org_ctx):
        d = xf_org_context(doc, rng, org_pool, addr_pool)
        sanity_check("org_context", d)
        augmented.append(d)
    print(f"org_context: +{n_org_ctx}")

    total = originals + augmented
    rng.shuffle(total)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for d in total:
            f.write(json.dumps({"text": d["text"], "spans": d["spans"]}, ensure_ascii=False) + "\n")

    print(f"\nTOTAL: {len(originals)} original + {len(augmented)} augmented = {len(total)} documents")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
