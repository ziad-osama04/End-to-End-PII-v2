"""Test the masking model DIRECTLY on a JSONL file -- no HTTP API needed.

It loads the masker in-process (same code + same fine-tuned weights the API and
the MLflow model use) and, for each JSONL record:

  * masks the record's text and writes it to an output JSONL, and
  * if the record carries ground-truth PII spans, scores char-level
    precision / recall / F1 AND a per-entity-type recall breakdown.

Tailored to (and auto-detects) this dataset shape:
    {"file": "...", "source_text": "...(raw report)...",
     "privacy_mask": [{"label": "PATIENT_NAME", "start": 48, "end": 60, "value": "..."}, ...]}

Usage (from backend/):
    python -m masking_service.run_jsonl_test --input test.jsonl --version medroberta-nl-1

Options:
    --text-field   default auto (source_text, text, content, input, raw, body, note)
    --span-field   default auto (privacy_mask, spans, entities, labels, annotations)
    --output       masked-output JSONL (default: <input>.masked.jsonl)
    --limit N      only the first N records
    --version      regex-poc-1 | medroberta-nl-1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from typing import List, Optional, Tuple

from masking_service import masking_core as core

_TEXT_FIELDS = ["source_text", "text", "content", "input", "raw", "body", "sentence", "note"]
_SPAN_FIELDS = ["privacy_mask", "spans", "entities", "labels", "ground_truth", "annotations"]

# A ground-truth entity counts as "caught" if at least this fraction of its
# characters were masked by the model.
_CATCH_THRESHOLD = 0.5


def _get_masker(version: str):
    if version == "medroberta-nl-1":
        from masking_service.medroberta_masker import register
        return register()
    return core.get_masker(version)


def _detect_field(record: dict, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in record:
            return c
    return None


def _extract_gt_entities(value) -> List[Tuple[int, int, str]]:
    """Normalize a ground-truth value into a list of (start, end, label)."""
    out = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and "start" in item and "end" in item:
                out.append((int(item["start"]), int(item["end"]),
                            str(item.get("label", "PII"))))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                label = str(item[2]) if len(item) >= 3 else "PII"
                out.append((int(item[0]), int(item[1]), label))
    return out


def _char_mask(entities: List[Tuple[int, int, str]], n: int) -> List[bool]:
    marked = [False] * n
    for start, end, _label in entities:
        for i in range(max(0, start), min(n, end)):
            marked[i] = True
    return marked


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="path to the JSONL test file")
    ap.add_argument("--version", default="medroberta-nl-1",
                    help="regex-poc-1 or medroberta-nl-1")
    ap.add_argument("--text-field", default="auto")
    ap.add_argument("--span-field", default="auto")
    ap.add_argument("--output", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--exclude-labels", default="",
                    help="comma-separated GT labels to drop from scoring "
                         "(e.g. CLINICAL_NOTE,MEDICATION -- content kept visible by design)")
    args = ap.parse_args()

    exclude = {s.strip() for s in args.exclude_labels.split(",") if s.strip()}
    if exclude:
        print(f"excluding from scoring: {sorted(exclude)}")

    if not os.path.isfile(args.input):
        sys.exit(f"input not found: {args.input}")
    out_path = args.output or (os.path.splitext(args.input)[0] + ".masked.jsonl")

    print(f"Loading masker '{args.version}' (first MedRoBERTa load may take ~15s)...")
    masker = _get_masker(args.version)

    text_field = None if args.text_field == "auto" else args.text_field
    span_field = None if args.span_field == "auto" else args.span_field

    TP = FP = FN = 0
    n_records = n_scored = total_entities = 0
    label_total = defaultdict(int)
    label_caught = defaultdict(int)
    miss_examples = defaultdict(list)

    with open(args.input, "r", encoding="utf-8") as fin, \
         open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)

            if text_field is None:
                text_field = _detect_field(record, _TEXT_FIELDS)
                if text_field is None:
                    sys.exit(f"No text field found. Keys: {list(record)}. "
                             f"Pass --text-field <name>.")
                print(f"text field         : '{text_field}'")
            if span_field is None:
                span_field = _detect_field(record, _SPAN_FIELDS) or ""
                print(f"ground-truth field : "
                      f"{span_field or '(none -> scoring skipped)'}")

            text = str(record.get(text_field, ""))
            result = masker.mask_bytes(text.encode("utf-8"), core.TXT)
            masked = result.content.decode("utf-8")
            total_entities += result.entity_count

            row = {"file": record.get("file"), "masked": masked,
                   "entity_count": result.entity_count,
                   "model_version": result.model_version}

            if span_field and span_field in record:
                gt = _extract_gt_entities(record[span_field])
                if exclude:
                    gt = [(s, e, lab) for (s, e, lab) in gt if lab not in exclude]
                pred = masker.detect_spans(text)
                gt_chars = _char_mask(gt, len(text))
                pred_chars = _char_mask(pred, len(text))
                TP += sum(1 for a, b in zip(gt_chars, pred_chars) if a and b)
                FP += sum(1 for a, b in zip(gt_chars, pred_chars) if b and not a)
                FN += sum(1 for a, b in zip(gt_chars, pred_chars) if a and not b)
                n_scored += 1

                # per-entity-type recall
                for start, end, label in gt:
                    label_total[label] += 1
                    seg = pred_chars[max(0, start):min(len(text), end)]
                    covered = sum(seg) / (end - start) if end > start else 0
                    if covered >= _CATCH_THRESHOLD:
                        label_caught[label] += 1
                    elif len(miss_examples[label]) < 3:
                        miss_examples[label].append(text[start:end])
                row["gt_span_count"] = len(gt)
                row["pred_span_count"] = len(pred)

            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_records += 1
            if args.limit and n_records >= args.limit:
                break
            if n_records % 25 == 0:
                print(f"  processed {n_records} records...")

    # ---- report ---------------------------------------------------------- #
    print("=" * 60)
    print(f"model             : {args.version}")
    print(f"records processed : {n_records}")
    print(f"entities masked   : {total_entities}")
    print(f"masked output ->  : {out_path}")
    if n_scored:
        precision = TP / (TP + FP) if (TP + FP) else 0.0
        recall = TP / (TP + FN) if (TP + FN) else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        print("-" * 60)
        print(f"CHAR-LEVEL over {n_scored} records:")
        print(f"  precision : {precision:.4f} ({precision*100:.1f}%)")
        print(f"  recall    : {recall:.4f} ({recall*100:.1f}%)")
        print(f"  f1        : {f1:.4f} ({f1*100:.1f}%)")
        print("-" * 60)
        print(f"PER-ENTITY-TYPE recall (caught = >={int(_CATCH_THRESHOLD*100)}% chars masked):")
        print(f"  {'label':<18}{'caught':>8}{'total':>8}{'recall':>9}")
        for label in sorted(label_total, key=lambda l: -label_total[l]):
            c, t = label_caught[label], label_total[label]
            print(f"  {label:<18}{c:>8}{t:>8}{(c/t*100 if t else 0):>8.1f}%")
        weak = [l for l in label_total if label_caught[l] / label_total[l] < 0.8]
        if weak:
            print("-" * 60)
            print("weakest labels (examples missed):")
            for l in sorted(weak, key=lambda l: label_caught[l] / label_total[l])[:6]:
                ex = ", ".join(repr(x) for x in miss_examples.get(l, [])) or "-"
                print(f"  {l:<18} e.g. {ex}")
    print("=" * 60)


if __name__ == "__main__":
    main()
