"""
FOURTH genuinely fresh validation battery (v5 -- "v4" is reserved for the
round-2 DISCOVERY battery that informed these fixes, kept distinct to avoid
confusion). Built after round-2 augmentation was finalized, using different
specific names/phrasings/scenarios than anything in v4_discovery or the
augmentation's own curated pools. This is round 2's honest verdict.
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


def remap_via_transform(doc, transform_fn):
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

# 1. Fresh OCR noise -- different corruption pattern/density than v3_06.
DOCS.append(build(
    "v5_01", "ocr_noise",
    "Fresh OCR-artifact instance, different pattern than v3_06.",
    """SPOEDVERSLAG

Pati ent:  [[NAME|Els  Coppens]]
Gebo ortedat um:  [[DATE|03/12/1958]]
Ad res :  [[ADDRESS|Meerm  innestraat  6 ,  2018  Antwerpen]]
Telefo on:  [[PHONE|03- 88 12 45]]

Reden van komst: pijn t hv  rechter  onderbeen na  val.
"""
))

# 2. Fresh honorific -- different honorific/name than the augmentation's
#    curated pool (which includes "de heer/mevrouw/dhr./mw./mej.").
DOCS.append(build(
    "v5_02", "honorific",
    "Fresh honorific usage, checking generalization beyond the curated pool.",
    """Patiente: [[NAME|mejuffrouw Sara Van Reeth]]
Contactpersoon: [[NAME|de heer Willy Dumont]]
Geboortedatum: [[DATE|19/09/1995]]
Telefoon: [[PHONE|09 445 67 12]]
"""
))

# 3. Fresh mojibake -- different diacritic name than augmentation's pool.
_base_moji = build(
    "v5_03", "mojibake",
    "Fresh mojibake instance, different name than augmentation's curated pool.",
    """Patient: [[NAME|Björk Håkansson]]
Geboortedatum: [[DATE|22/01/1983]]
Adres: [[ADDRESS|Kroonstraat 19, 2600 Berchem]]
Telefoon: [[PHONE|03 771 22 90]]

Patient werd geïnformeerd en toont begrip voor het vervolgtraject.
"""
)
DOCS.append(remap_via_transform(_base_moji, mojibake))

# 4. Fresh email header -- different names/domains than augmentation's pool.
# EMAIL spans were originally left unlabeled (an oversight from before EMAIL
# became a real scored label) -- fixed round 3 after finding every one of
# our 7 standing eval surfaces had exactly zero EMAIL gold spans, meaning
# the regex+checksum path was never validated end-to-end against real
# ground truth. Content unchanged, only the gold labels are corrected.
DOCS.append(build(
    "v5_04", "email_header",
    "Fresh email-header context, different names/domains than augmentation pool.",
    """Van: [[EMAIL|dr.willems@uzleuven.be]]
Aan: [[EMAIL|onthaal.spoed@uzleuven.be]]
Onderwerp: opvolging patient

Beste,

Gelieve onderstaande patient verder op te volgen na ontslag.

Patient: [[NAME|Tom Sanders]]
INSZ: [[INSZ|71030410130]]
Telefoon: [[PHONE|016 33 22 11]]
Adres: [[ADDRESS|Diestsestraat 88, 3000 Leuven]]

Met vriendelijke groeten,
[[NAME|dr. Willems]]
"""
))

# 5. Casing regression check -- fresh instance, quick reconfirmation.
DOCS.append(build(
    "v5_05", "all_caps",
    "Fresh all-caps regression check.",
    """MEDISCH VERSLAG
PATIENT: [[NAME|GEERT VAN DAMME]]
GEBOORTEDATUM: [[DATE|14/07/1963]]
ADRES: [[ADDRESS|MOLENSTRAAT 22, 3500 HASSELT]]
TELEFOON: [[PHONE|011 22 33 44]]
"""
))

# 6. New labels end-to-end check -- ORGANIZATION (letterhead + signature,
#    same pattern as the corrected ood12) and BTW_EENHEID (brand new regex,
#    no training-data precedent at all since pii_table.py never generates
#    one -- this is the only place it gets exercised before the retrain).
DOCS.append(build(
    "v5_06", "organization_and_btw",
    "Fresh ORGANIZATION + brand-new BTW_EENHEID regex, no training precedent for the latter.",
    """[[ORGANIZATION|AZ Delta Roeselare]]
Ondernemingsnummer: [[BTW_EENHEID|BE0456987190]]

Betreft: [[NAME|Nadia Verstraete]]

Geachte,

Uw patient werd onderzocht op onze dienst radiologie.

Met vriendelijke groet,
[[ORGANIZATION|AZ Delta Roeselare]] - Dienst Radiologie
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_v5.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} v5 fresh validation documents to {OUT_PATH}")
