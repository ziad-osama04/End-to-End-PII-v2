"""
FIFTH genuinely fresh validation battery (v6). Built to give an honest
verdict on round 3's fix specifically: ORGANIZATION as the literal first
token of a document, immediately (no blank-line separator) followed by an
ADDRESS -- the exact structural blind spot found in tamerbert-taxonomy-v1's
OOD results (ood doc 9's letterhead, ood_v5's v5_06). Every org name,
address, and patient name below is new -- zero overlap with the
augmentation's letterhead value pools or any prior OOD battery.
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

# 1. Direct letterhead adjacency -- org name at position 0, single newline,
#    then a full street+zip+city address. This is the exact pattern that
#    fragmented in ood doc 9.
DOCS.append(build(
    "v6_01", "letterhead_adjacency",
    "ORGANIZATION at doc-initial position 0, immediately followed by ADDRESS on the next line -- new names, zero overlap with training pools.",
    """[[ORGANIZATION|Jan Palfijnziekenhuis]]
[[ADDRESS|Watersportlaan 5, 2170 Merksem]]

Betreft: opvolgconsult

Patient: [[NAME|Karel Van Acker]]
Geboortedatum: [[DATE|11/03/1971]]

De patient werd gezien op de raadpleging orthopedie en toont goede vooruitgang.

Met vriendelijke groeten,
[[NAME|dr. Lievens]]
[[ORGANIZATION|Jan Palfijnziekenhuis]] - Dienst Orthopedie
"""
))

# 2. Abbreviated org name at position 0 -- checks whether the short "XX
#    Name" abbreviation prefix survives (v5_06 truncated exactly this).
DOCS.append(build(
    "v6_02", "letterhead_abbreviation",
    "Abbreviated ORGANIZATION ('UZ ...') at doc-initial position 0, immediately followed by ADDRESS -- targets the abbreviation-prefix truncation seen in v5_06.",
    """[[ORGANIZATION|UZ Antwerpen]]
[[ADDRESS|Drie Eikenstraat 655, 2650 Edegem]]

Verslag spoedopname

Patiente: [[NAME|Yasmine El Amrani]]
Leeftijd: [[AGE|29 jaar]]
Telefoon: [[PHONE|03 821 30 00]]

Patiente werd opgenomen na een val met lichte hoofdwonde, verder ongeval.
"""
))

# 3. Same-line comma adjacency -- a different concrete formatting of the
#    same underlying blind spot (org immediately followed by address, but
#    on one line with a comma instead of a newline).
DOCS.append(build(
    "v6_03", "letterhead_sameline",
    "ORGANIZATION immediately followed by ADDRESS on the SAME line via a comma separator -- a different concrete formatting of the same adjacency blind spot.",
    """[[ORGANIZATION|AZ Klina]], [[ADDRESS|Augustijnslei 100, 2930 Brasschaat]]

Patient: [[NAME|Robert Maes]]
Geboortedatum: [[DATE|05/09/1948]]

Patient wordt doorverwezen naar de dienst cardiologie voor verder nazicht.
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_v6.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} v6 fresh validation documents to {OUT_PATH}")
