#!/usr/bin/env python3
"""
emit_dataset_fr.py -- cross-produce Cases x translated French templates into
a train.jsonl-equivalent dataset, matching the schema prep_tamerbert_data.py
(and its French fork, prep_data_fr.py) expects to read.

Reads: translated_templates_fr_pilot.jsonl (or any file matching the same
schema: template_hash, letter_type, specialty, masked_text_fr).
Writes: train_fr.jsonl, one record per rendered document:
    {"id": ..., "text": ..., "spans": [...], "meta": {
        "template_hash": ..., "letter_type": ..., "specialty": ...,
        "sex": ..., "age_band": ..., "name_origin": ..., "region": ...,
        "urbanicity": ..., "source": ""
    }}

This mirrors the Dutch train.jsonl's meta shape (see derender_templates.py's
docstring) so prep_data_fr.py's template_hash-based splitting logic and
LEAK_RE filter work unchanged.

Usage:
    python3 emit_dataset_fr.py --templates translated_templates_fr_pilot.jsonl \
        --docs-per-template 20 --out train_fr.jsonl --seed 42
"""

import argparse
import json
import random

import pii_table_fr as m


def load_templates(path):
    templates = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            templates.append(json.loads(line))
    return templates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", default="translated_templates_fr_pilot.jsonl")
    ap.add_argument("--docs-per-template", type=int, default=20,
                     help="how many documents to render per template "
                          "(Dutch original used ~93 per template)")
    ap.add_argument("--out", default="train_fr.jsonl")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--label-scheme", choices=["merged", "split", "flat9", "production"],
                     default="production",
                     help="'production' matches the actual shipped Dutch taxonomy "
                          "(README: NAME/DATE/PHONE/ADDRESS/ORGANIZATION/AGE) -- "
                          "FLAT9 with ORGANIZATION split back out instead of merged "
                          "into NAME, since add_organization_label.py did the same "
                          "un-merge for the Dutch pipeline")
    args = ap.parse_args()

    templates = load_templates(args.templates)
    print(f"loaded {len(templates)} templates from {args.templates}")

    production_scheme = dict(m.FLAT9, ORGANIZATION="ORGANIZATION")
    scheme = {"merged": m.MERGED, "split": m.SPLIT, "flat9": m.FLAT9,
              "production": production_scheme}[args.label_scheme]
    rng = random.Random(args.seed)

    records = []
    doc_id = 0
    for tmpl in templates:
        for _ in range(args.docs_per_template):
            case = m.build_case(doc_id, rng, None)
            text, spans = m.render(tmpl["masked_text_fr"], case, scheme)
            records.append({
                "id": f"FR{doc_id:06d}_{case.case_id}",
                "text": text,
                "spans": spans,
                "meta": {
                    "template_hash": tmpl["template_hash"],
                    "letter_type": tmpl["letter_type"],
                    "specialty": tmpl["specialty"],
                    "sex": case.sex,
                    "age_band": case.age_band,
                    "name_origin": case.name_origin,
                    "region": case.region,
                    "urbanicity": case.urbanicity,
                    "source": "",
                },
            })
            doc_id += 1

    rng.shuffle(records)
    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} documents -> {args.out} "
          f"({len(templates)} templates x {args.docs_per_template} docs/template)")


if __name__ == "__main__":
    main()
