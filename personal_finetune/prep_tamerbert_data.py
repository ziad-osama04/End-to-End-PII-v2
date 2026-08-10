"""Prepare the TamerBERT train.jsonl for the generalization-maximizing trial:
filter out the 19 templates with the confirmed DD-MM-YYYY/MM/YYYY literal-
placeholder-leak bug, then split by TEMPLATE (not just by document) so we get
a genuine three-surface generalization test:

  1. train_filtered.jsonl        -- 90% of docs from the TRAIN template pool
  2. eval_indist.jsonl            -- 10% of docs from the SAME template pool
                                     (in-distribution: seen structures, unseen docs)
  3. eval_heldout_templates.jsonl -- ALL docs from templates NEVER in training
                                     (structural generalization: same generator,
                                     unseen template)
  4. eval_real.jsonl              -- the 5 real HealthOne Nova documents
                                     (org_data_filled_labeled.jsonl, copied as-is;
                                     real-world generalization, the decisive test)

Split is by template_hash for (2) vs (3) so no template leaks across that
boundary; (1)/(2) split is a plain seeded per-document split within the
train-template pool.
"""
from __future__ import annotations

import json
import os
import random
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAMER_DIR = os.path.join(ROOT, "TamerBERT", "TamerBERT")
OUT_DIR = os.path.join(ROOT, "personal_finetune", "tamerbert_data")
os.makedirs(OUT_DIR, exist_ok=True)

SEED = 42
HOLDOUT_TEMPLATE_FRACTION = 0.2  # ~10 of 50 clean templates held out entirely
EVAL_INDIST_FRACTION = 0.1

LEAK_RE = re.compile(r"DD-MM-YYYY|MM/YYYY")


def main():
    records = []
    with open(os.path.join(TAMER_DIR, "train.jsonl"), encoding="utf-8") as f:
        for line in f:
            records.append(json.loads(line))

    by_template = {}
    for r in records:
        by_template.setdefault(r["meta"]["template_hash"], []).append(r)

    bad_templates = {h for h, recs in by_template.items() if any(LEAK_RE.search(r["text"]) for r in recs)}
    clean_templates = sorted(set(by_template) - bad_templates)
    print(f"templates: {len(by_template)} total, {len(bad_templates)} bad (leak), {len(clean_templates)} clean")

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

    write_jsonl(os.path.join(OUT_DIR, "train_filtered.jsonl"), train_docs)
    write_jsonl(os.path.join(OUT_DIR, "eval_indist.jsonl"), eval_indist_docs)
    write_jsonl(os.path.join(OUT_DIR, "eval_heldout_templates.jsonl"), heldout_docs)

    with open(os.path.join(TAMER_DIR, "org_data_filled_labeled.jsonl"), encoding="utf-8") as f:
        real_docs = [json.loads(line) for line in f]
    write_jsonl(os.path.join(OUT_DIR, "eval_real.jsonl"), real_docs)
    print(f"eval_real: {len(real_docs)} docs (the actual HealthOne Nova documents)")

    label_counts = {}
    for d in train_docs:
        for s in d["spans"]:
            label_counts[s["label"]] = label_counts.get(s["label"], 0) + 1
    print("train_filtered label counts:", label_counts)


if __name__ == "__main__":
    main()
