"""
Sliding-window boundary-crossing stress doc.

MAX_LEN=512, STRIDE=128 means window1=tokens[0:512], window2=tokens[384:896],
window3=tokens[768:1280], etc. (each window starts 384 tokens after the
previous one starts). A short PII span whose tokens straddle exactly at a
window-END boundary (512, 896, 1280, ...) risks being truncated/garbled in
the window that cuts through it -- decode_model_preds's resolve_overlaps
should recover via the next window's full (untruncated) version of the same
span, but that's a real-code-path claim worth testing empirically rather
than trusting by inspection.

Strategy: build a long, repetitive multi-day admission log (the same
patient's name/INSZ/phone/address repeated every ~400-600 characters), then
use the ACTUAL tokenizer to find precisely which characters sit at each
window-end token boundary, and confirm at least one PII occurrence's char
span straddles one of those exact boundaries. If none do naturally, this
script reports the boundary positions so a targeted insertion can be added.
"""
import json
import os
import re

from transformers import AutoTokenizer

MARKER = re.compile(r"\[\[([A-Z_]+)\|(.*?)\]\]", re.S)


def build_marked(raw_text):
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
    return "".join(out), spans


NAME = "Willem Van Overloop"
INSZ = "58110310137"
PHONE = "0470 55 66 77"
ADDRESS = "Kwadeplasstraat 9, 3290 Diest"

DAY_TEMPLATE = """Dag {n} - Verpleegkundige rapportage

Patient [[NAME|{name}]] (INSZ [[INSZ|{insz}]]) blijft opgenomen op de afdeling
cardiologie. Bloeddruk stabiel, hartslag regelmatig. Medicatie ongewijzigd
voortgezet volgens schema. Contactpersoon bereikbaar op [[PHONE|{phone}]].
Woonadres blijft [[ADDRESS|{address}]] voor ontslagbrief-correspondentie.
Geen bijzonderheden te melden voor deze dienst. Volgende evaluatie gepland
voor morgenvroeg tijdens de artsenronde. Patient rust comfortabel en toont
geen tekenen van complicaties op dit moment in het opnametraject.

"""

raw_base = "ONTSLAGVERSLAG - LANGDURIGE OPNAME\n\n"
for day in range(1, 14):
    raw_base += DAY_TEMPLATE.format(n=day, name=NAME, insz=INSZ, phone=PHONE, address=ADDRESS)

tok = AutoTokenizer.from_pretrained("CLTL/MedRoBERTa.nl", add_prefix_space=True)
MAX_LEN, STRIDE = 512, 128


def analyze(raw_text):
    text, spans = build_marked(raw_text)
    enc = tok(text, return_offsets_mapping=True, truncation=False)
    offsets = enc["offset_mapping"]
    n_tokens = len(offsets)
    window_starts = list(range(0, max(1, n_tokens - MAX_LEN + STRIDE), MAX_LEN - STRIDE))
    window_ends = [min(n_tokens, s + MAX_LEN) for s in window_starts]
    boundary_chars = sorted(set(offsets[min(e, n_tokens - 1)][0] for e in window_ends if e < n_tokens))
    straddling = [(sp, b) for sp in spans for b in boundary_chars if sp["start"] < b < sp["end"]]
    return text, spans, n_tokens, boundary_chars, straddling


text, spans, n_tokens, boundary_chars, straddling = analyze(raw_base)
print(f"base doc: {len(text)} chars, {n_tokens} tokens, boundaries={boundary_chars}, straddling={len(straddling)}")

# Insert a short probe phone-number sentence near the first boundary, nudging
# its exact insertion offset until its span genuinely straddles a boundary
# (insertion shifts subsequent token/char alignment, so this can't be solved
# in closed form -- a short search is simpler and just as rigorous).
PROBE_VALUE = "0499 12 34 56"
PROBE_TEMPLATE = "Extra notitie: bereikbaar op [[PHONE|{v}]] indien nodig.\n"
target = boundary_chars[0] if boundary_chars else len(raw_base) // 2

found = False
for offset_nudge in range(-40, 41, 4):
    insert_at = max(0, target + offset_nudge)
    # insert_at is a position in raw_base (pre-marker-stripped) -- find the
    # nearest safe insertion point (not mid-marker) by snapping to a newline
    safe_pos = raw_base.rfind("\n", 0, insert_at)
    if safe_pos == -1:
        continue
    candidate_raw = raw_base[:safe_pos + 1] + PROBE_TEMPLATE.format(v=PROBE_VALUE) + raw_base[safe_pos + 1:]
    text, spans, n_tokens, boundary_chars, straddling = analyze(candidate_raw)
    probe_straddles = [s for s in straddling if text[s[0]["start"]:s[0]["end"]] == PROBE_VALUE]
    if probe_straddles:
        found = True
        print(f"probe straddles with insertion nudge={offset_nudge}")
        break

if not found:
    print("WARNING: probe never straddled a boundary across the search range; "
          "keeping the last candidate anyway (still a useful long-document test).")

print(f"\nfinal doc: {len(text)} chars, {n_tokens} tokens")
print(f"window-end char boundaries: {boundary_chars}")
print(f"\nspans straddling a window boundary: {len(straddling)}")
for sp, b in straddling:
    print(f"  {sp['label']:8s} {text[sp['start']:sp['end']]!r}  boundary_char={b} "
          f"(span {sp['start']}-{sp['end']})")

OUT_PATH = os.path.join(os.path.dirname(__file__), "boundary_doc.jsonl")
with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(json.dumps({"id": "boundary01", "category": "window_boundary",
                         "note": f"{len(straddling)} PII spans straddle a stride-window boundary",
                         "text": text, "spans": spans}, ensure_ascii=False) + "\n")
print(f"\nwrote {OUT_PATH}")
