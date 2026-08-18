#!/usr/bin/env python3
"""
build_eval_real_fr.py -- dedicated evaluation set grounded in the 5 real
HealthOne Nova seed letters (TamerBERT/TamerBERT/org_data_filled/*.txt).

These 5 documents are the ONLY genuine ground truth this project has: the
actual real letters the whole template bank was originally derived from
(confirmed by direct text comparison -- each maps exactly to one of the 5
templates with near-zero "extra field" counts: c144ae81adf7f4e6,
a733c617b8ae2b93, 87a289529c8aaff9, ba143439c76c2175, 7fed825dd1a65d86).

All 5 of these templates unfortunately landed in the TRAIN pool (not the
20% held-out split -- confirmed by checking tamerbert_data_fr/*.jsonl), so
this is not a template-holdout eval. What it DOES give: a document set
whose narrative structure is grounded in real clinical writing rather than
purely synthetic template variety, rendered with a case-ID range (900000+)
that was never touched by the main train_fr.jsonl generation (seed=42,
doc_id 0-6499), so the specific PII VALUES are guaranteed unseen even
though the template itself was trained on.

Usage:
    python3 build_eval_real_fr.py --out eval_real_fr.jsonl
"""
import argparse
import json
import random

import pii_table_fr as m

REAL_LETTER_TEMPLATES = [
    ("c144ae81adf7f4e6", "HealthOne NOVA1_filled.txt"),
    ("a733c617b8ae2b93", "HealthOne NOVA2_filled.txt"),
    ("87a289529c8aaff9", "HealthOne NOVA3_filled.txt"),
    ("ba143439c76c2175", "HealthOne NOVA4_filled.txt"),
    ("7fed825dd1a65d86", "HealthOne NOVA_filled.txt"),
]


def load_templates(path):
    templates = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            templates[t["template_hash"]] = t
    return templates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--templates", default="translated_templates_fr.jsonl")
    ap.add_argument("--out", default="eval_real_fr.jsonl")
    ap.add_argument("--seed", type=int, default=987654)
    ap.add_argument("--docs-per-letter", type=int, default=10,
                     help="render N distinct synthetic instances per real letter "
                          "(varies demographics/PII while keeping the real narrative structure)")
    args = ap.parse_args()

    templates = load_templates(args.templates)
    rng = random.Random(args.seed)
    scheme = dict(m.FLAT9, ORGANIZATION="ORGANIZATION")

    records = []
    doc_id = 900000
    for template_hash, source_file in REAL_LETTER_TEMPLATES:
        tmpl = templates[template_hash]
        for _ in range(args.docs_per_letter):
            case = m.build_case(doc_id, rng, None)
            text, spans = m.render(tmpl["masked_text_fr"], case, scheme)
            records.append({
                "id": f"REAL{doc_id:06d}_{case.case_id}",
                "text": text,
                "spans": spans,
                "meta": {
                    "template_hash": template_hash,
                    "letter_type": tmpl["letter_type"],
                    "specialty": tmpl["specialty"],
                    "sex": case.sex,
                    "age_band": case.age_band,
                    "name_origin": case.name_origin,
                    "region": case.region,
                    "urbanicity": case.urbanicity,
                    "source": "real_letter_grounded",
                    "source_file": source_file,
                },
            })
            doc_id += 1

    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} documents -> {args.out} "
          f"({len(REAL_LETTER_TEMPLATES)} real letters x {args.docs_per_letter} instances)")


if __name__ == "__main__":
    main()
