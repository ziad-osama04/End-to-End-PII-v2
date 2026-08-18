#!/usr/bin/env python3
"""
derender_templates_v2.py -- improved template recovery.

v1 (derender_templates.py) only masked SCORED spans back to {slot}, which
silently froze every UNSCORED-but-genuinely-variable Case field (SPECIALTY,
DIAGNOSIS, RELATIVE_RELATION, all DX_* distractor fields) as fixed literal
text -- confirmed by direct evidence: diffing two documents sharing the
same template_hash shows these exact fields varying between them (e.g.
"Moeder"<->"Zus", both real RELATIONS words; "8u"<->"3x/week", both in
DISTRACTORS['numeric_lookalike']). This script detects and re-parametrizes
those fields too, using pii_table.py's own pools as the reference
dictionary, not just the labeled spans.

Method: for one representative document per template_hash, build a combined
list of (value, placeholder_name) pairs from every relevant pool, sort by
value length descending (longest match first, to avoid partial-match
corruption), then substring-replace each occurrence -- alongside the
existing scored-span masking. Fields with real collision risk (short common
words: HONORIFIC "de heer"/"mevrouw", PRONOUN_SUBJ "hij"/"zij") are handled
separately with word-boundary regex and flagged for manual review rather
than blindly trusted, since a pronoun referring to a DOCTOR or RELATIVE
elsewhere in the same document must not be mistaken for the PATIENT's own
{PRONOUN_SUBJ}.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "TamerBERT", "TamerBERT"))
import pii_table as dutch

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAMER_DIR = os.path.join(ROOT, "TamerBERT", "TamerBERT")
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovered_templates_nl_v2.jsonl")

LEAK_RE = re.compile(r"DD-MM-YYYY|MM/YYYY")

# High-confidence pools: long/distinctive strings, safe for blind substring
# replacement. Order matters -- sort by length descending across ALL pools
# combined so the longest, most specific match always wins first.
HIGH_CONFIDENCE_POOLS = [
    (dutch.SPECIALTIES, "SPECIALTY"),
    ([d[0] for d in dutch.DIAGNOSES], "DIAGNOSIS"),
    (dutch.DISTRACTORS["eponym_disease"], "DX_EPONYM"),
    (dutch.DISTRACTORS["eponym_test"], "DX_TEST"),
    (dutch.DISTRACTORS["anatomy_latin"], "DX_ANATOMY"),
    (dutch.DISTRACTORS["municipality_homograph"], "DX_HOMOGRAPH"),
    (dutch.DISTRACTORS["numeric_lookalike"], "DX_NUMERIC"),
    (dutch.DISTRACTORS["abbreviation"], "DX_ABBREV"),
    (dutch.DISTRACTORS["code_switch"], "DX_CODESWITCH"),
]
# drug_brand feeds BOTH DX_DRUG and DX_DRUG_2 (two independently-sampled
# Case fields from the same pool) -- can't tell which from the value alone,
# so first occurrence in the doc -> DX_DRUG, second -> DX_DRUG_2 (heuristic).
DRUG_POOL = dutch.DISTRACTORS["drug_brand"]

RELATION_WORDS = ["Moeder", "Vader", "Zus", "Broer", "Dochter", "Zoon",
                  "Tante", "Oom", "Grootmoeder", "Grootvader", "Nicht", "Neef"]


def mask_scored_spans(text, spans):
    out = text
    for s in sorted(spans, key=lambda s: s["start"], reverse=True):
        out = out[:s["start"]] + "{" + s["slot"] + "}" + out[s["end"]:]
    return out


def mask_known_values(text):
    """Re-parametrize any substring matching a known Case-field pool value.
    Returns (masked_text, list of (field, value) recovered) for review."""
    recovered = []

    # Build one flat (value, field) list across all high-confidence pools,
    # longest value first so e.g. a long DIAGNOSIS string is matched before
    # a short substring of it could accidentally match something else.
    flat = []
    for pool, field in HIGH_CONFIDENCE_POOLS:
        for v in pool:
            flat.append((v, field))
    for v in RELATION_WORDS:
        flat.append((v, "RELATIVE_RELATION"))
    flat.sort(key=lambda vf: -len(vf[0]))

    for value, field in flat:
        while value in text:
            idx = text.index(value)
            text = text[:idx] + "{" + field + "}" + text[idx + len(value):]
            recovered.append((field, value))

    # drug_brand: first occurrence -> DX_DRUG, second -> DX_DRUG_2
    drug_sorted = sorted(DRUG_POOL, key=lambda v: -len(v))
    drug_slot_order = ["DX_DRUG", "DX_DRUG_2"]
    slot_i = 0
    changed = True
    while changed and slot_i < len(drug_slot_order):
        changed = False
        for value in drug_sorted:
            if value in text:
                idx = text.index(value)
                field = drug_slot_order[slot_i]
                text = text[:idx] + "{" + field + "}" + text[idx + len(value):]
                recovered.append((field, value))
                slot_i += 1
                changed = True
                break

    return text, recovered


def mask_risky_words(text):
    """HONORIFIC and PRONOUN_SUBJ: word-boundary regex, flagged for manual
    review rather than blindly trusted (a pronoun could refer to someone
    other than the patient elsewhere in the same document)."""
    flags_for_review = []

    for value, field in [("de heer", "HONORIFIC"), ("mevrouw", "HONORIFIC")]:
        pattern = re.compile(re.escape(value))
        if pattern.search(text):
            flags_for_review.append((field, value, len(pattern.findall(text))))

    for value, field in [(r"\bhij\b", "PRONOUN_SUBJ"), (r"\bzij\b", "PRONOUN_SUBJ")]:
        pattern = re.compile(value, re.IGNORECASE)
        matches = pattern.findall(text)
        if matches:
            flags_for_review.append((field, value, len(matches)))

    return flags_for_review


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
    print(f"templates: {len(by_template)} total, {len(bad_templates)} bad (leak), {len(clean_hashes)} clean")

    recovered_records = []
    total_extra_slots = 0
    for h in clean_hashes:
        rep = by_template[h][0]
        masked_scored = mask_scored_spans(rep["text"], rep["spans"])
        masked_full, recovered_fields = mask_known_values(masked_scored)
        risky = mask_risky_words(masked_full)
        total_extra_slots += len(recovered_fields)

        recovered_records.append({
            "template_hash": h,
            "letter_type": rep["meta"].get("letter_type", ""),
            "specialty": rep["meta"].get("specialty", ""),
            "n_docs": len(by_template[h]),
            "masked_text_v1": masked_scored,   # old approach, for comparison
            "masked_text_v2": masked_full,     # new approach with extra fields recovered
            "extra_fields_recovered": [{"field": f, "value": v} for f, v in recovered_fields],
            "risky_words_needing_manual_review": [
                {"field": f, "pattern": v, "count": c} for f, v, c in risky],
        })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for rec in recovered_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"wrote {len(recovered_records)} v2-recovered templates -> {OUT_PATH}")
    print(f"total extra fields recovered across all templates: {total_extra_slots} "
          f"(avg {total_extra_slots/len(recovered_records):.1f} per template)")
    n_with_risky = sum(1 for r in recovered_records if r["risky_words_needing_manual_review"])
    print(f"templates with HONORIFIC/PRONOUN_SUBJ words needing manual review: {n_with_risky}/{len(recovered_records)}")


if __name__ == "__main__":
    main()
