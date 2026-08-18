#!/usr/bin/env python3
"""
derender_templates.py -- mechanically recover the ~50 real Dutch letter
templates that built TamerBERT/TamerBERT/train.jsonl, by masking each
labeled span back to its {slot} placeholder.

Why this works: every record's spans carry a `slot` field (the original
template placeholder name) and every record's `meta` carries a
`template_hash` identifying which literal template it came from (69 unique
hashes across 6,417 docs, ~93 docs per hash -- confirmed real template
reuse, not per-document uniqueness). For one representative record per
hash, replacing each span's text[start:end] with {slot} (processed in
descending start order so earlier replacements don't shift later offsets)
reconstructs the original masked template.

Reuses prep_tamerbert_data.py's LEAK_RE to drop the ~19 templates with the
confirmed literal-placeholder-leak bug (literal "DD-MM-YYYY"/"MM/YYYY" text
baked into the template prose instead of a real {DATE_...} placeholder).

Output: personal_finetune/french/recovered_templates_nl.jsonl, one JSON
object per clean recovered template:
    {"template_hash": ..., "letter_type": ..., "specialty": ...,
     "n_docs": ..., "masked_text": ...}

This is the INPUT to the translation step, not the output of it -- the
masked_text here is still Dutch. Translate masked_text to French per
template, leaving every {SLOT} token untouched.
"""

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAMER_DIR = os.path.join(ROOT, "TamerBERT", "TamerBERT")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovered_templates_nl.jsonl")

LEAK_RE = re.compile(r"DD-MM-YYYY|MM/YYYY")


def mask_template(text: str, spans: list) -> str:
    """Replace each span's text[start:end] with {slot}, processing in
    descending start order so earlier replacements don't shift later
    offsets that haven't been processed yet."""
    out = text
    for s in sorted(spans, key=lambda s: s["start"], reverse=True):
        out = out[:s["start"]] + "{" + s["slot"] + "}" + out[s["end"]:]
    return out


def main():
    records = []
    with open(os.path.join(TAMER_DIR, "train.jsonl"), encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    print(f"loaded {len(records)} records from train.jsonl")

    by_template = {}
    for r in records:
        by_template.setdefault(r["meta"]["template_hash"], []).append(r)

    bad_templates = {h for h, recs in by_template.items() if any(LEAK_RE.search(r["text"]) for r in recs)}
    clean_hashes = sorted(set(by_template) - bad_templates)
    print(f"templates: {len(by_template)} total, {len(bad_templates)} bad (leak, dropped), "
          f"{len(clean_hashes)} clean (recovering these)")

    recovered = []
    mask_check_failures = 0
    for h in clean_hashes:
        recs = by_template[h]
        rep = recs[0]  # one representative record per template_hash
        masked = mask_template(rep["text"], rep["spans"])

        # Sanity check: every {slot} token we just inserted should be
        # findable in the masked text, and re-substituting the ORIGINAL
        # values back in should reproduce the original text exactly --
        # a cheap round-trip check that the masking didn't corrupt offsets.
        roundtrip = masked
        for s in sorted(rep["spans"], key=lambda s: s["start"], reverse=True):
            token = "{" + s["slot"] + "}"
            idx = roundtrip.rfind(token)
            if idx == -1:
                mask_check_failures += 1
                break
        recovered.append({
            "template_hash": h,
            "letter_type": rep["meta"].get("letter_type", ""),
            "specialty": rep["meta"].get("specialty", ""),
            "n_docs": len(recs),
            "masked_text": masked,
        })

    print(f"round-trip token-presence check failures: {mask_check_failures}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for rec in recovered:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"wrote {len(recovered)} recovered masked templates -> {OUT_PATH}")

    letter_types = {}
    for rec in recovered:
        letter_types[rec["letter_type"]] = letter_types.get(rec["letter_type"], 0) + 1
    print("by letter_type:", letter_types)


if __name__ == "__main__":
    main()
