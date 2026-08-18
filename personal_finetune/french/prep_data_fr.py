#!/usr/bin/env python3
"""
prep_data_fr.py -- French fork of personal_finetune/prep_tamerbert_data.py.

Splitting logic (template_hash grouping, 20% held-out templates, 10%
in-distribution eval split, seed 42) is language-agnostic, copied as-is.
Adds a French leak-regex check (JJ-MM-AAAA / MM/AAAA) alongside the
original Dutch one, since the underlying bug (a literal date-format hint
typed into template prose instead of a real placeholder) is a generic
authoring mistake that could recur in French templates too.

Usage:
    python3 prep_data_fr.py --input train_fr.jsonl --out-dir tamerbert_data_fr
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re

SEED = 42
HOLDOUT_TEMPLATE_FRACTION = 0.2
EVAL_INDIST_FRACTION = 0.1

LEAK_RE = re.compile(r"DD-MM-YYYY|MM/YYYY|JJ-MM-AAAA|MM/AAAA")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="train_fr.jsonl")
    ap.add_argument("--out-dir", default="tamerbert_data_fr")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    records = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))
    print(f"loaded {len(records)} records from {args.input}")

    by_template = {}
    for r in records:
        by_template.setdefault(r["meta"]["template_hash"], []).append(r)

    bad_templates = {h for h, recs in by_template.items() if any(LEAK_RE.search(r["text"]) for r in recs)}
    clean_templates = sorted(set(by_template) - bad_templates)
    print(f"templates: {len(by_template)} total, {len(bad_templates)} bad (leak), {len(clean_templates)} clean")
    if bad_templates:
        print(f"LEAKY TEMPLATES (fix before using): {sorted(bad_templates)}")

    rng = random.Random(SEED)
    rng.shuffle(clean_templates)
    n_holdout = max(1, int(len(clean_templates) * HOLDOUT_TEMPLATE_FRACTION))
    heldout_templates = set(clean_templates[:n_holdout])
    train_pool_templates = set(clean_templates[n_holdout:])
    print(f"train-pool templates: {len(train_pool_templates)}  held-out templates: {len(heldout_templates)}")

    train_pool_docs = [r for h in train_pool_templates for r in by_template[h]]
    heldout_docs = [r for h in heldout_templates for r in by_template[h]]

    rng.shuffle(train_pool_docs)
    n_eval_indist = max(1, int(len(train_pool_docs) * EVAL_INDIST_FRACTION))
    eval_indist_docs = train_pool_docs[:n_eval_indist]
    train_docs = train_pool_docs[n_eval_indist:]

    print(f"train_filtered: {len(train_docs)} docs")
    print(f"eval_indist: {len(eval_indist_docs)} docs (unseen docs, seen templates)")
    print(f"eval_heldout_templates: {len(heldout_docs)} docs (unseen templates, same generator)")

    def write_jsonl(path, docs):
        with open(path, "w", encoding="utf-8") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")

    write_jsonl(os.path.join(args.out_dir, "train_filtered.jsonl"), train_docs)
    write_jsonl(os.path.join(args.out_dir, "eval_indist.jsonl"), eval_indist_docs)
    write_jsonl(os.path.join(args.out_dir, "eval_heldout_templates.jsonl"), heldout_docs)

    label_counts = {}
    for d in train_docs:
        for s in d["spans"]:
            label_counts[s["label"]] = label_counts.get(s["label"], 0) + 1
    print("train_filtered label counts:", label_counts)


if __name__ == "__main__":
    main()
