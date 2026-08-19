#!/usr/bin/env python3
"""
validate_all_en.py -- master validation pass across every dataset file
produced by the English pipeline. Direct fork of
personal_finetune/french/validate_all_fr.py (language-agnostic mechanics).
Run this after any regeneration.

Checks, per file:
  - every span is in-bounds, non-empty, and (where the schema carries `text`)
    text[start:end] == span text
  - label set is exactly the expected production scheme labels
  - no duplicate ids within a file

Cross-file checks:
  - no id collisions between files built with distinct case-id ranges.
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

EXPECTED_LABELS = {"NAME", "INSZ", "RIZIV", "DATE", "ORGANIZATION", "AGE",
                    "ADDRESS", "PHONE", "URL", "EMAIL"}

FILES_WITH_IDS = [
    "train_en.jsonl",
    "eval_real_en.jsonl",
    "eval_hard_extraction_en.jsonl",
]

FILES_TO_CHECK = FILES_WITH_IDS + [
    "train_augmented_en.jsonl",
    "tamerbert_data_en/train_filtered.jsonl",
    "tamerbert_data_en/eval_indist.jsonl",
    "tamerbert_data_en/eval_heldout_templates.jsonl",
]


def check_file(path):
    n = 0
    bad_span = 0
    bad_text = 0
    bad_label = 0
    ids = set()
    dup_ids = 0
    label_counts = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            n += 1
            text = r["text"]
            if "id" in r:
                if r["id"] in ids:
                    dup_ids += 1
                ids.add(r["id"])
            for s in r["spans"]:
                if not (0 <= s["start"] < s["end"] <= len(text)):
                    bad_span += 1
                    continue
                if "text" in s and text[s["start"]:s["end"]] != s["text"]:
                    bad_text += 1
                if s["label"] not in EXPECTED_LABELS:
                    bad_label += 1
                label_counts[s["label"]] = label_counts.get(s["label"], 0) + 1
    return {
        "n": n, "bad_span": bad_span, "bad_text": bad_text, "bad_label": bad_label,
        "dup_ids": dup_ids, "ids": ids, "label_counts": label_counts,
    }


def main():
    print("=" * 90)
    print("PER-FILE VALIDATION")
    print("=" * 90)
    all_ids_by_file = {}
    total_errors = 0
    for path in FILES_TO_CHECK:
        try:
            result = check_file(path)
        except FileNotFoundError:
            print(f"[SKIP] {path} not found")
            continue
        errors = result["bad_span"] + result["bad_text"] + result["bad_label"] + result["dup_ids"]
        total_errors += errors
        status = "PASS" if errors == 0 else "FAIL"
        print(f"[{status}] {path}: {result['n']} docs, "
              f"{result['bad_span']} bad-span, {result['bad_text']} text-mismatch, "
              f"{result['bad_label']} bad-label, {result['dup_ids']} dup-ids-within-file")
        print(f"       labels: {result['label_counts']}")
        if path in FILES_WITH_IDS:
            all_ids_by_file[path] = result["ids"]

    print()
    print("=" * 90)
    print("CROSS-FILE ID COLLISION CHECK")
    print("=" * 90)
    files = list(all_ids_by_file.keys())
    collision_found = False
    for i in range(len(files)):
        for j in range(i + 1, len(files)):
            overlap = all_ids_by_file[files[i]] & all_ids_by_file[files[j]]
            if overlap:
                collision_found = True
                print(f"[FAIL] {files[i]} <-> {files[j]}: {len(overlap)} colliding ids")
    if not collision_found:
        print(f"[PASS] no id collisions across {', '.join(files)}")

    print()
    print("=" * 90)
    print(f"TOTAL ERRORS: {total_errors}")
    print("=" * 90)


if __name__ == "__main__":
    main()
