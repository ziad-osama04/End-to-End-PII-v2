"""
Second, INDEPENDENT hand-crafted stress battery -- covers dimensions the
first 14-doc battery never touched. Deliberately NOT reusing any specific
hospital names / OCR corruption patterns / phrasings from the first battery,
since those directly informed the planned augmentation fixes; testing on
the same instances again would validate memorization of the fix, not real
generalization.

Dimensions covered here:
  - name diversity: diacritics, apostrophes, Belgian tussenvoegsels
  - adversarial casing: ALL CAPS, Title Case Everywhere
  - partial redaction mixing: some fields already [GEREDIGEERD], others real
  - non-medical false-positive probe: no real PII at all
  - new hard-negative numeric ID categories: medical record number, invoice
    number, patient portal ID -- all superficially INSZ/RIZIV/phone-shaped
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

# 1. Diacritics + apostrophe names -- training's NAMES pools are plain-ASCII
#    Dutch/Flemish names; real Belgian populations include immigrant-origin
#    names with diacritics that patients/staff genuinely have.
DOCS.append(build(
    "v2_01", "name_diacritics",
    "Names with diacritics and apostrophes, absent from training NAMES pools.",
    """Patient: [[NAME|Amélie Müller]]
Behandelend arts: [[NAME|dr. O'Brien]]
Geboortedatum: [[DATE|14/03/1991]]
Adres: [[ADDRESS|Ürkerstraat 8, 2000 Antwerpen]]
Telefoon: [[PHONE|03 456 78 90]]

Patiente werd gezien in consultatie, geen bijzonderheden.
"""
))

# 2. Belgian tussenvoegsels -- "van der", "de", multi-word surnames are
#    present in pii_table.py's NAMES pool for SOME entries, but not
#    systematically stress-tested as a dedicated dimension before.
DOCS.append(build(
    "v2_02", "name_tussenvoegsel",
    "Multi-word Belgian surname conventions.",
    """Patiente: [[NAME|Anne-Sophie van der Linden-Maes]]
Contactpersoon: [[NAME|de heer Jean-Pierre du Bois]]
Geboortedatum: [[DATE|02-11-1975]]
Tel: [[PHONE|011 22 33 44]]
"""
))

# 3. ALL CAPS document -- casing is uniform lowercase-title in training
#    templates; scanned intake forms are frequently rendered in all-caps.
DOCS.append(build(
    "v2_03", "all_caps",
    "Entire document in uppercase.",
    """PATIENTENFICHE
NAAM: [[NAME|KAREL PEETERS]]
GEBOORTEDATUM: [[DATE|09/07/1968]]
INSZ: [[INSZ|68070910139]]
ADRES: [[ADDRESS|KERKSTRAAT 4, 9000 GENT]]
TELEFOON: [[PHONE|09 225 66 77]]
REDEN VAN OPNAME: PIJN OP DE BORST, ONDERZOEK LOOPT.
"""
))

# 4. Title Case Everywhere -- another scanned-doc/export convention.
DOCS.append(build(
    "v2_04", "title_case",
    "Every Word Capitalized, including boilerplate prose.",
    """Patienteninformatie

Naam: [[NAME|Rita Van Damme]]
Geboortedatum: [[DATE|21 Mei 1980]]
Adres: [[ADDRESS|Molenweg 17, 8500 Kortrijk]]
Telefoon: [[PHONE|056 33 22 11]]

De Patiente Werd Gezien Voor Een Routine Controle En Toont Geen
Bijzondere Klachten Op Dit Moment.
"""
))

# 5. Partial redaction mixing -- some fields already redacted upstream,
#    others still real PII. Plausible if a document passes through a partial
#    manual redaction step before reaching this pipeline.
DOCS.append(build(
    "v2_05", "partial_redaction",
    "Some fields pre-redacted, others still real PII -- tests whether real PII near redaction markers still gets caught.",
    """Patient: [GEREDIGEERD]
Geboortedatum: [GEREDIGEERD]
INSZ: [GEREDIGEERD]
Adres: [[ADDRESS|Beukenlaan 33, 3500 Hasselt]]
Telefoon: [[PHONE|011 44 55 66]]
Behandelend arts: [[NAME|dr. Van Hecke]]

Patient werd besproken tijdens het multidisciplinair overleg.
"""
))

# 6. Non-medical false-positive probe -- no real PII at all; measures the
#    false-positive floor on genuinely unrelated business correspondence
#    that might accidentally get routed through this pipeline.
DOCS.append(build(
    "v2_06", "non_medical_no_pii",
    "Generic business letter, zero real PII -- pure false-positive probe.",
    """Geachte klant,

Wij danken u voor uw recente bestelling bij onze onderneming. Uw pakket
wordt momenteel verwerkt en zal binnen 3 tot 5 werkdagen worden geleverd.

Voor vragen over uw bestelling kan u terecht op onze klantendienst tijdens
kantooruren. Wij staan steeds klaar om u verder te helpen.

Met vriendelijke groeten,
Klantendienst
"""
))

# 7. New hard-negative numeric ID categories -- medical record number,
#    invoice number, patient portal ID: all superficially resemble
#    INSZ/RIZIV/phone digit shapes but are NOT those identifiers.
DOCS.append(build(
    "v2_07", "numeric_id_hard_negatives",
    "Non-INSZ/RIZIV numeric IDs that could be confused with them.",
    """Patient [[NAME|Sofie Aerts]] (dossiernummer 2024-08812234, factuurnummer
FAC-991823765) werd gezien op de spoedafdeling.
Portaal-ID: PT-556677889. Kamernummer 214B.
INSZ: [[INSZ|85041210191]]
Contact: [[PHONE|02 345 67 89]]
Geboortedatum: [[DATE|12/04/1985]]
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_v2.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} v2 stress documents to {OUT_PATH}")
