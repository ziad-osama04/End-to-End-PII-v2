"""
Round-2 discovery battery -- probes dimensions untouched by v1/v2/v3/the
perturbation sweep, run cheaply (inference-only) against the current
farahelmashad/pii-tamerbert-v2 model before deciding what round-2
augmentation needs to cover.

  1. mojibake        -- UTF-8-as-Latin-1 double-encoding corruption, a very
                         real PDF-extraction failure mode, applied to the
                         WHOLE document (realistic: a real encoding bug
                         doesn't selectively spare the PII)
  2. quoted_email     -- forwarded/reply email with ">" quote-prefixed lines,
                         PII appearing both in a new message and a quoted one
  3. foreign_id_phone -- non-Belgian phone/ID formats a hospital might still
                         plausibly encounter (out-of-scope-format probe, not
                         necessarily a "bug" -- informs a scope decision)
  4. minimal_doc      -- a single short sentence, robustness floor check
  5. homoglyph        -- a Cyrillic look-alike character substituted into a
                         Latin name (lower priority, cheap to check)
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


def mojibake(s):
    return s.encode("utf-8").decode("latin-1")


def apply_transform(doc, transform_fn):
    """Generic remap: works for any deterministic, prefix-preserving
    character-level transform (mojibake, casing, ...) by re-applying the
    transform to each span boundary's prefix and measuring its new length."""
    text = doc["text"]
    new_text = transform_fn(text)
    new_spans = []
    for sp in doc["spans"]:
        new_start = len(transform_fn(text[:sp["start"]]))
        new_end = len(transform_fn(text[:sp["end"]]))
        new_spans.append({"start": new_start, "end": new_end, "label": sp["label"]})
    return {"id": doc["id"], "category": doc["category"], "note": doc["note"],
            "text": new_text, "spans": new_spans}


DOCS = []

# 1. Mojibake -- whole-document UTF-8-as-Latin-1 corruption.
_base_mojibake = build(
    "v4d_01", "mojibake",
    "Whole-document double-encoding corruption (a real PDF-extraction bug).",
    """Patiente: [[NAME|Amélie Müller]]
Geboortedatum: [[DATE|14/03/1991]]
Adres: [[ADDRESS|Ürkerstraat 8, 2000 Antwerpen]]
Telefoon: [[PHONE|03 456 78 90]]

Patiente werd geïnformeerd over de diagnose en toont begrip voor het traject.
"""
)
DOCS.append(apply_transform(_base_mojibake, mojibake))

# 2. Quoted/forwarded email -- ">" prefixed reply chain.
DOCS.append(build(
    "v4d_02", "quoted_email",
    "Forwarded email with '>' quoted lower message, PII in both layers.",
    """Van: dr.claes@azstlucas.be
Aan: verwijzer@huisartsenpraktijk.be
Onderwerp: Fwd: dossier patient

Beste collega,

Zie hieronder het oorspronkelijke bericht met de gegevens van de patient.
Graag uw verdere opvolging.

Met vriendelijke groeten,
[[NAME|dr. Claes]]

> Van: secretariaat@azstlucas.be
> Aan: dr.claes@azstlucas.be
> Onderwerp: dossier patient
>
> Patient: [[NAME|Wouter Van Damme]]
> INSZ: [[INSZ|75052210173]]
> Contact: [[PHONE|09 234 56 78]]
> Adres: [[ADDRESS|Sint-Pietersplein 3, 9000 Gent]]
"""
))

# 3. Foreign ID/phone formats -- a French mobile number and a generic
#    international-format contact, alongside a normal Belgian INSZ.
DOCS.append(build(
    "v4d_03", "foreign_id_phone",
    "Non-Belgian phone format -- scope probe, not necessarily a bug to fix.",
    """Patient: [[NAME|Marie Lefebvre]]
Geboortedatum: [[DATE|08/06/1979]]
INSZ: [[INSZ|79060810003]]
Frans mobiel nummer (familie): [[PHONE|+33 6 12 34 56 78]]
Adres in Belgie: [[ADDRESS|Stationsstraat 5, 7500 Doornik]]
"""
))

# 4. Minimal document -- a single short sentence.
DOCS.append(build(
    "v4d_04", "minimal_doc",
    "Single-sentence document, robustness floor check.",
    """Contact: [[NAME|Jan Peeters]], [[PHONE|0470 11 22 33]]."""
))

# 5. Homoglyph -- Cyrillic 'а' (U+0430) substituted for Latin 'a' in a name.
DOCS.append(build(
    "v4d_05", "homoglyph",
    "Cyrillic look-alike character substituted into a Latin name.",
    """Patient: [[NAME|Kаrel Peeters]]
Geboortedatum: [[DATE|11/02/1972]]
Telefoon: [[PHONE|03 221 44 55]]
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "v4_discovery.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} round-2 discovery documents to {OUT_PATH}")
