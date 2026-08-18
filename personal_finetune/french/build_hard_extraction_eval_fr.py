#!/usr/bin/env python3
"""
build_hard_extraction_eval_fr.py -- dedicated hard-eval set applying real,
empirically-confirmed PyMuPDF recursive-XY-cut extraction noise to documents
rendered from the 5 real-letter-derived templates.

Each of the 5 real HealthOne Nova PDFs was run through the team's actual
extraction script (extract_pdf_text.py) and diffed against clean reference
text. The noise applied to each template here matches what THAT SPECIFIC
letter's own PDF actually exhibited, not a generic corruption:

  a733c617b8ae2b93 (NOVA2) -> header_table_garble (confirmed: 3-column
      PATIENT/RESPONSABLE/DATE header misdetected as a ruled table)
  87a289529c8aaff9 (NOVA3) -> header_table_garble (same failure, plus this
      letter's own spirometry-table row-splitting is already baked into the
      template's literal text, inherited from the recovered Dutch source)
  ba143439c76c2175 (NOVA4) -> header_table_garble (same failure, plus a
      literal "<br>" tag leaking into the RIZIV cell in the real extraction)
  c144ae81adf7f4e6 (NOVA1) -> midword_splice (confirmed: an address spliced
      zero-separator into the middle of a body word, "p[ADRES] nd")
  7fed825dd1a65d86 (NOVA)  -> left clean; this letter's own real PDF extracted
      without header or mid-word corruption, so a clean-control instance here
      is itself a real, useful data point (not every input is corrupted)

Usage:
    python3 build_hard_extraction_eval_fr.py --out eval_hard_extraction_fr.jsonl
"""
import argparse
import json
import random

import pii_table_fr as m
from augment_fr import xf_header_table_garble, xf_midword_splice, sanity_check

REAL_LETTER_NOISE = [
    ("a733c617b8ae2b93", "header_table_garble", "HealthOne NOVA2.pdf"),
    ("87a289529c8aaff9", "header_table_garble", "HealthOne NOVA3.pdf"),
    ("ba143439c76c2175", "header_table_garble", "HealthOne NOVA4.pdf"),
    ("c144ae81adf7f4e6", "midword_splice", "HealthOne NOVA1.pdf"),
    ("7fed825dd1a65d86", "clean", "HealthOne NOVA.pdf"),
]

TRANSFORMS = {
    "header_table_garble": xf_header_table_garble,
    "midword_splice": xf_midword_splice,
}


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
    ap.add_argument("--out", default="eval_hard_extraction_fr.jsonl")
    ap.add_argument("--seed", type=int, default=13579)
    ap.add_argument("--docs-per-letter", type=int, default=15)
    args = ap.parse_args()

    templates = load_templates(args.templates)
    rng = random.Random(args.seed)
    scheme = dict(m.FLAT9, ORGANIZATION="ORGANIZATION")

    records = []
    skipped = 0
    doc_id = 950000
    for template_hash, noise, source_file in REAL_LETTER_NOISE:
        tmpl = templates[template_hash]
        made = 0
        attempts = 0
        while made < args.docs_per_letter and attempts < args.docs_per_letter * 4:
            attempts += 1
            case = m.build_case(doc_id, rng, None)
            text, spans = m.render(tmpl["masked_text_fr"], case, scheme)
            doc_id += 1
            doc = {"text": text, "spans": [{"start": s["start"], "end": s["end"], "label": s["label"]}
                                            for s in spans]}
            if noise != "clean":
                noisy = TRANSFORMS[noise](doc, rng)
                if noisy is None:
                    skipped += 1
                    continue
                sanity_check(noise, noisy)
                doc = noisy
            records.append({
                "id": f"HARDX{doc_id:06d}_{case.case_id}",
                "text": doc["text"],
                "spans": doc["spans"],
                "meta": {
                    "template_hash": template_hash,
                    "letter_type": tmpl["letter_type"],
                    "specialty": tmpl["specialty"],
                    "sex": case.sex,
                    "source": "real_letter_extraction_noise",
                    "source_file": source_file,
                    "noise_type": noise,
                },
            })
            made += 1

    with open(args.out, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} documents -> {args.out} "
          f"({len(REAL_LETTER_NOISE)} real letters x up to {args.docs_per_letter} instances, "
          f"{skipped} skipped where the transform found nothing to corrupt)")


if __name__ == "__main__":
    main()
