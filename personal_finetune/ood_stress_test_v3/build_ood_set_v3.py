"""
THIRD, genuinely fresh validation battery -- built AFTER the augmentation
plan was designed, using different specific instances (different names,
different phrasings, different scenarios) than anything in v1, v2, the
perturbation sweep, or the augmentation templates themselves. This is the
one that gets to render an honest verdict: if the retrained model does well
here, that's real generalization, not memorization of the exact examples
used to build the fix.
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

# 1. ALL CAPS -- different patient, different letter type than v2_03.
DOCS.append(build(
    "v3_01", "all_caps",
    "Fresh all-caps document, different fields than v2_03.",
    """VERSLAG SPOEDGEVAL
PATIENT: [[NAME|NADIA EL AMRANI]]
GEBOORTEDATUM: [[DATE|23/11/1982]]
INSZ: [[INSZ|82112310039]]
ADRES: [[ADDRESS|BROUWERSSTRAAT 12, 8000 BRUGGE]]
TELEFOON: [[PHONE|050 33 44 55]]
KLACHT: HOOFDPIJN EN DUIZELIGHEID SINDS TWEE DAGEN.
"""
))

# 2. lowercase -- fresh.
DOCS.append(build(
    "v3_02", "lowercase",
    "Fresh lowercase document.",
    """patientenbrief

naam: [[NAME|bart van hoof]]
geboortedatum: [[DATE|05-08-1990]]
adres: [[ADDRESS|kastanjelaan 9, 3800 sint-truiden]]
telefoon: [[PHONE|011 67 88 99]]

patient werd gezien voor een routineonderzoek, geen bijzonderheden.
"""
))

# 3. Title case -- fresh.
DOCS.append(build(
    "v3_03", "title_case",
    "Fresh title-case document.",
    """Verwijsbrief Cardiologie

Naam: [[NAME|Dominique Lambert]]
Geboortedatum: [[DATE|30 September 1977]]
Adres: [[ADDRESS|Vlasstraat 22, 8500 Kortrijk]]
Telefoon: [[PHONE|056 12 34 56]]

De Patient Wordt Doorverwezen Voor Verder Cardiologisch Onderzoek Wegens
Aanhoudende Klachten Van Kortademigheid.
"""
))

# 4. Non-medical, zero PII -- a municipal/utility scenario, distinct from
#    the shipping/subscription/event templates used in augmentation.
DOCS.append(build(
    "v3_04", "non_medical_no_pii",
    "Municipal tax notice, zero real PII -- different scenario than augmentation templates.",
    """Gemeentebestuur - Dienst Belastingen

Geachte inwoner,

Wij informeren u dat het aanslagbiljet voor de gemeentebelasting van dit jaar
binnenkort wordt verstuurd. Betaling dient te gebeuren binnen de twee maanden
na ontvangst van het aanslagbiljet.

Voor vragen kan u terecht bij de dienst belastingen tijdens de openingsuren
van het gemeentehuis.

Met vriendelijke groeten,
Dienst Belastingen
"""
))

# 5. Inline mention -- different phrasing/value than the augmentation
#    templates and different from the original ood11.
DOCS.append(build(
    "v3_05", "inline_mention",
    "Fresh inline PII mention, different phrasing than augmentation templates.",
    """Beste collega,

Ik verwijs u onze gemeenschappelijke patiente door, die momenteel verblijft
op [[ADDRESS|Heidebaan 41, 3600 Genk]] samen met haar familie. Mocht u haar
willen contacteren, dat kan het best via [[PHONE|089 22 11 00]] in de
voormiddag.

Met vriendelijke groeten,
"""
))

# 6. OCR noise -- different corruption instance/rate than ood08.
DOCS.append(build(
    "v3_06", "ocr_noise",
    "Fresh OCR-artifact text, different corruption pattern than ood08.",
    """PATIE NTGEGEVENS

Naa m:  [[NAME|Robrecht  Van Loo]]
Gebo ort edatum:  [[DATE|19-09-1965]]
Adr  es:  [[ADDRESS|Papen straat  14 ,  9300  Aalst]]
Tel:   [[PHONE|053- 21 44 09]]

Kli nis che notitie: pat ient stabi el, geen bij zonderh eden op dit moment.
"""
))

# 7. Diacritic/honorific -- different names than the curated augmentation
#    list and than v2_01/v2_02.
DOCS.append(build(
    "v3_07", "name_diacritics_honorific",
    "Fresh diacritic names/honorifics, not in the augmentation's curated list.",
    """Patiente: [[NAME|Björn Andersson]]
Behandelend arts: [[NAME|mevrouw Céline Wéry]]
Contactpersoon: [[NAME|dhr. Łukasz Kowalski]]
Geboortedatum: [[DATE|17/02/1988]]
Telefoon: [[PHONE|02 987 65 43]]
"""
))

OUT_PATH = os.path.join(os.path.dirname(__file__), "ood_docs_v3.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    for d in DOCS:
        f.write(json.dumps(d, ensure_ascii=False) + "\n")

print(f"wrote {len(DOCS)} v3 fresh validation documents to {OUT_PATH}")
