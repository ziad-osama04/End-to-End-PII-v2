#!/usr/bin/env python3
"""
derender_templates_v3.py -- correct version of the improved recovery.

v2 (derender_templates_v2.py) tried to recover unscored-but-variable Case
fields (SPECIALTY, DIAGNOSIS, RELATIVE_RELATION, DX_*) by doing SEQUENTIAL
str.replace() calls against a mutating string. This corrupted the output
two ways, confirmed by inspection: (1) short pool values like "co"/"OS"
matched as SUBSTRINGS inside unrelated words ("collega" -> "{DX_ABBREV}llega",
"conditie" -> "{DX_ABBREV}nditie"), and (2) later replacement passes matched
INSIDE placeholder tokens already inserted by earlier passes ("{DIAGNOSIS}"
containing "OS" got corrupted to "{DIAGN{DX_ABBREV}IS}").

v3 fixes both: find every match as a (start, end, field) interval against
the ORIGINAL, unmodified text using word-boundary regex, merge with the
real scored spans, resolve overlaps by preferring scored spans first then
longest-match-wins among the rest, and perform exactly ONE substitution
pass sorted by start position descending -- the same safe, corruption-free
method already proven correct for scored-span-only masking in v1.
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
OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovered_templates_nl_v3.jsonl")

LEAK_RE = re.compile(r"DD-MM-YYYY|MM/YYYY")

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
    (dutch.DISTRACTORS["drug_brand"], "DX_DRUG"),  # DX_DRUG_2 disambiguated after
]
RELATION_WORDS_LIST = ["Moeder", "Vader", "Zus", "Broer", "Dochter", "Zoon",
                       "Tante", "Oom", "Grootmoeder", "Grootvader", "Nicht", "Neef"]
RELATION_POOL = (RELATION_WORDS_LIST, "RELATIVE_RELATION")  # matches the (list, field) shape find_all_matches expects
HONORIFIC_WORDS = [("de heer", "HONORIFIC"), ("mevrouw", "HONORIFIC")]
PRONOUN_WORDS = [("hij", "PRONOUN_SUBJ"), ("zij", "PRONOUN_SUBJ")]


def word_bound_pattern(value):
    """Word-boundary regex for a pool value. \\b works fine even for
    multi-word phrases (boundary only needs to hold at the two ends)."""
    return re.compile(r"(?<![A-Za-zÀ-ÿ])" + re.escape(value) + r"(?![A-Za-zÀ-ÿ])")


def find_all_matches(text, pools):
    """Return list of (start, end, field, value) for every match, against
    the ORIGINAL unmodified text -- no mutation, so no self-corruption."""
    matches = []
    for pool, field in pools:
        for value in pool:
            for m in word_bound_pattern(value).finditer(text):
                matches.append((m.start(), m.end(), field, value))
    return matches


def resolve_overlaps(candidate_matches, scored_spans):
    """scored_spans always win (label, start, end, slot already ground
    truth). Among candidates, prefer longest match; reject anything
    overlapping an already-accepted interval."""
    accepted = [(s["start"], s["end"], s["slot"], text_slice_placeholder(s))
                for s in scored_spans]
    accepted_ranges = [(a[0], a[1]) for a in accepted]

    def overlaps(a, b):
        return not (a[1] <= b[0] or b[1] <= a[0])

    # longest candidate first so a long DIAGNOSIS string wins over a short
    # DX_ABBREV substring that happens to sit inside it
    candidates_sorted = sorted(candidate_matches, key=lambda m: -(m[1] - m[0]))
    for start, end, field, value in candidates_sorted:
        if any(overlaps((start, end), r) for r in accepted_ranges):
            continue
        accepted.append((start, end, field, value))
        accepted_ranges.append((start, end))

    return accepted


def text_slice_placeholder(scored_span):
    return None  # placeholder marker, unused field for scored spans


def disambiguate_drug_slots(accepted):
    """Two DX_DRUG matches (independently-sampled Case fields from the same
    pool) can't be told apart by value alone -- first-in-document -> DX_DRUG,
    second -> DX_DRUG_2, by text position."""
    drug_idxs = [i for i, a in enumerate(accepted) if a[2] == "DX_DRUG"]
    drug_idxs.sort(key=lambda i: accepted[i][0])  # sort by start position
    for rank, i in enumerate(drug_idxs):
        if rank >= 1:
            a = accepted[i]
            accepted[i] = (a[0], a[1], "DX_DRUG_2", a[3])
    return accepted


def mask(text, accepted):
    out = text
    for start, end, field, _value in sorted(accepted, key=lambda a: a[0], reverse=True):
        out = out[:start] + "{" + field + "}" + out[end:]
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
    print(f"templates: {len(by_template)} total, {len(bad_templates)} bad (leak), {len(clean_hashes)} clean")

    recovered_records = []
    total_extra = 0
    for h in clean_hashes:
        rep = by_template[h][0]
        text = rep["text"]

        candidate_matches = find_all_matches(text, HIGH_CONFIDENCE_POOLS + [RELATION_POOL])
        # Defensive sanity check against exactly the class of bug already
        # caught once here: every matched value must be >=2 chars UNLESS it
        # is a genuinely short real pool entry (co/OD/OS/nle exist in
        # DISTRACTORS['abbreviation'] on purpose).
        known_short_ok = {v for v in dutch.DISTRACTORS["abbreviation"]}
        for start, end, field, value in candidate_matches:
            if len(value) < 2 and value not in known_short_ok:
                raise AssertionError(f"suspiciously short match {value!r} for {field} "
                                      f"in template {h} -- likely a pool/data bug, not a real match")
        accepted = resolve_overlaps(candidate_matches, rep["spans"])
        accepted = disambiguate_drug_slots(accepted)
        masked = mask(text, accepted)

        # risky words: report only, don't auto-mask (need manual review --
        # a pronoun/honorific might refer to someone other than the patient)
        risky = []
        for value, field in HONORIFIC_WORDS + PRONOUN_WORDS:
            n = len(word_bound_pattern(value).findall(text))
            if n:
                risky.append({"field": field, "pattern": value, "count": n})

        extra_count = len(accepted) - len(rep["spans"])
        total_extra += extra_count

        recovered_records.append({
            "template_hash": h,
            "letter_type": rep["meta"].get("letter_type", ""),
            "specialty": rep["meta"].get("specialty", ""),
            "n_docs": len(by_template[h]),
            "masked_text_v3": masked,
            "n_scored_spans": len(rep["spans"]),
            "n_extra_fields_recovered": extra_count,
            "risky_words_needing_manual_review": risky,
        })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for rec in recovered_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"wrote {len(recovered_records)} v3-recovered templates -> {OUT_PATH}")
    print(f"total extra fields recovered: {total_extra} (avg {total_extra/len(recovered_records):.1f}/template)")
    n_risky = sum(1 for r in recovered_records if r["risky_words_needing_manual_review"])
    print(f"templates with HONORIFIC/PRONOUN_SUBJ needing manual review: {n_risky}/{len(recovered_records)}")


if __name__ == "__main__":
    main()
