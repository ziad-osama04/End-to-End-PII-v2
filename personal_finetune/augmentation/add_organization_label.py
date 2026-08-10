"""
Splits ORGANIZATION out of the merged NAME label, per the team's finalized
taxonomy (Eng. Khaled, 2026-08). Confirmed via direct inspection that every
one of the 3348 train_filtered.jsonl documents (and every eval_indist/
eval_heldout_templates document) carries exactly 2 organization-slotted
spans, cleanly distinguished from person names via the existing "slot"
metadata field (ORGANIZATION vs NAME_PATIENT/NAME_DOCTOR/etc.) with zero
merging artifacts -- so this is a pure metadata relabel, no per-document
text parsing needed.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "tamerbert_data")


def relabel_file(in_fname, out_fname):
    n_docs = n_relabeled = 0
    with open(os.path.join(ROOT, in_fname), encoding="utf-8") as fin, \
         open(os.path.join(ROOT, out_fname), "w", encoding="utf-8") as fout:
        for line in fin:
            d = json.loads(line)
            for s in d["spans"]:
                if s["label"] == "NAME" and s.get("slot") == "ORGANIZATION":
                    s["label"] = "ORGANIZATION"
                    n_relabeled += 1
            fout.write(json.dumps(d, ensure_ascii=False) + "\n")
            n_docs += 1
    print(f"{in_fname} -> {out_fname}: {n_docs} docs, {n_relabeled} spans relabeled NAME->ORGANIZATION")


if __name__ == "__main__":
    relabel_file("train_filtered.jsonl", "train_filtered_org.jsonl")
    relabel_file("eval_indist.jsonl", "eval_indist_org.jsonl")
    relabel_file("eval_heldout_templates.jsonl", "eval_heldout_templates_org.jsonl")
