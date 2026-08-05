"""Dataset-agnostic precise-de-identification evaluation.

Runs the full masking pipeline (final-pii-model-v2 + Dutch regex +
coverage-preserving resolver -- the exact production path) over a folder of
documents and reports real per-label precision / recall / F1.

Ground truth is derived automatically from the pseudonymizer's replacement
report (no hand-labelling), applying the PRECISE de-identification policy:

  * real-identifier entity types  -> counted as PII (mapped to the v2 taxonomy);
  * clinical / free-text spaCy types (PERSON / ORGANIZATION / LOCATION and the
    non-identifier LEAKED_* types) -> put on an IGNORE list. A prediction that
    only overlaps an ignored span is neither a true nor a false positive, so the
    score is not distorted by fake PII the pseudonymizer injected into clinical
    text (disease eponyms, medications, lab units).

Because the gold comes from the report + policy (not per-file labels), this works
for ANY dataset the pipeline produces, and gives the same clean result before or
after the pseudonymizer is switched to precise mode.

Usage:
    python -m masking_service.evaluate_precise \
        --docs   "C:/.../end to end pii/data/pseudonymized" \
        --report "C:/.../end to end pii/docs/phase_4_pseudonymization_report.md"
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
from src.detection.pii_detector import (  # noqa: E402
    KEEP_VISIBLE,
    get_detector,
    resolve_overlaps,
)

# Pseudonymizer entity type -> v2 PII label (real identifiers only).
TYPE_TO_LABEL = {
    "TAGGED_PATIENT": "NAME", "TAGGED_RESPONSIBLE": "NAME", "TAGGED_DOCTOR": "NAME",
    "TAGGED_NAME_ID": "NAME",
    "TAGGED_NATIONAL_ID": "INSZ", "BELGIAN_INSZ": "INSZ",
    "TAGGED_PROVIDER_ID": "RIZIV",
    "TAGGED_PHONE": "PHONE", "PHONE_NUMBER_NL_BE": "PHONE",
    "TAGGED_URL": "URL",
    "TAGGED_HOSPITAL": "ORGANIZATION", "LEAKED_HOSPITAL": "ORGANIZATION",
    "LEAKED_DOB": "DATE",
    "LEAKED_AGE": "AGE",
    "IBAN_NL_BE": "IBAN",
    "TAGGED_ADDRESS": "ADDRESS",  # split into components below
}
# Clinical / free-text types: not identifiers under the precise policy.
IGNORE_TYPES = {
    "PERSON", "ORGANIZATION", "LOCATION",
    "LEAKED_RACE", "LEAKED_HEIGHT", "LEAKED_WEIGHT", "LEAKED_BMI", "LEAKED_DEPT",
}
LABELS = ["NAME", "DATE", "ORGANIZATION", "CITY", "ZIP_CODE", "STREET",
          "BUILDING_NUMBER", "AGE", "PHONE", "INSZ", "RIZIV", "URL", "EMAIL", "IBAN"]

_ADDR = re.compile(r"^(?P<STREET>.+?)\s+(?P<BUILDING_NUMBER>\d+[A-Za-z]?),\s*(?P<ZIP_CODE>\d{4})\s+(?P<CITY>.+)$")
# Dates are left unchanged by the pseudonymizer (not in the report), so find them
# structurally. Same day/month bounds as the production DATE recogniser.
_DATE_RE = re.compile(
    r"(?<![\d./-])(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]\d{2,4}(?!\d)"
    r"|\b[0-2]?\d:[0-5]\d\b"
)
_REPORT_ROW = re.compile(r"^\|\s*(?P<doc>[^|]+?)\s*\|\s*(?P<type>[A-Z_]+)\s*\|\s*`(?P<orig>.*?)`\s*\|\s*`(?P<repl>.*?)`\s*\|")


def find_all(text, s):
    out, i = [], 0
    while s and True:
        j = text.find(s, i)
        if j == -1:
            break
        out.append((j, j + len(s)))
        i = j + len(s)
    return out


def parse_report(path):
    """Return {doc_basename: [(entity_type, replacement_value), ...]}."""
    per_doc = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = _REPORT_ROW.match(line)
            if not m or m.group("type") in ("Entity Type",):
                continue
            doc = os.path.splitext(m.group("doc").strip())[0]
            per_doc[doc].append((m.group("type"), m.group("repl")))
    return per_doc


def address_spans(text, full_addr):
    m = _ADDR.match(full_addr)
    spans = defaultdict(list)
    if not m:
        return spans
    for s, e in find_all(text, full_addr):
        for lab in ("STREET", "BUILDING_NUMBER", "ZIP_CODE", "CITY"):
            a, b = m.span(lab)
            spans[lab].append((s + a, s + b))
    return spans


def overlaps(a, b):
    return not (a[1] <= b[0] or a[0] >= b[1])


def build_gold(text, rows):
    """Return (gold_spans_by_label, ignore_spans) for one document."""
    gold = defaultdict(list)
    ignore = []
    for etype, value in rows:
        if etype in IGNORE_TYPES:
            ignore.extend(find_all(text, value))
            continue
        label = TYPE_TO_LABEL.get(etype)
        if not label:
            continue
        if label == "ADDRESS":
            for lab, sp in address_spans(text, value).items():
                gold[lab].extend(sp)
        else:
            gold[label].extend(find_all(text, value))
    # Dates: not in the report (left unchanged), so detect structurally.
    for m in _DATE_RE.finditer(text):
        gold["DATE"].append((m.start(), m.end()))
    return gold, ignore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True, help="folder of pseudonymized .txt docs")
    ap.add_argument("--report", required=True, help="phase_4_pseudonymization_report.md")
    args = ap.parse_args()

    report = parse_report(args.report)
    detector = get_detector()

    tp = defaultdict(int); fp = defaultdict(int); fn = defaultdict(int)
    ignored_preds = 0
    files = sorted(glob.glob(os.path.join(args.docs, "*.txt")))
    for path in files:
        base = os.path.splitext(os.path.basename(path))[0]
        rows = report.get(base)
        if not rows:
            print(f"  (no report rows for {base}, skipping)")
            continue
        text = open(path, encoding="utf-8", errors="ignore").read()
        gold, ignore = build_gold(text, rows)

        results = resolve_overlaps([r for r in detector.analyzer.analyze(text=text, language="nl")
                                    if r.entity_type not in KEEP_VISIBLE])
        pred = defaultdict(list)
        for r in results:
            pred[r.entity_type].append((r.start, r.end))

        for lab in set(gold) | set(pred):
            g, p = gold.get(lab, []), pred.get(lab, [])
            for gs in g:
                (tp if any(overlaps(gs, ps) for ps in p) else fn)[lab] += 1
            for ps in p:
                if any(overlaps(ps, gs) for gs in g):
                    continue
                if any(overlaps(ps, ig) for ig in ignore):
                    ignored_preds += 1   # masked an injected clinical fake -> ignore
                    continue
                fp[lab] += 1

    print(f"\nEvaluated {len(files)} docs.  (ignored {ignored_preds} predictions on injected clinical fakes)\n")
    print(f"{'LABEL':16}{'gold':>5}{'pred':>6}{'TP':>5}{'FP':>4}{'FN':>4}{'P':>7}{'R':>7}{'F1':>7}")
    TP = FP = FN = 0
    for lab in LABELS:
        t, f_, n = tp[lab], fp[lab], fn[lab]
        if t + f_ + n == 0:
            continue
        P = t / (t + f_) if t + f_ else 0.0
        R = t / (t + n) if t + n else 0.0
        F = 2 * P * R / (P + R) if P + R else 0.0
        TP += t; FP += f_; FN += n
        print(f"{lab:16}{t + n:5}{t + f_:6}{t:5}{f_:4}{n:4}{P:7.3f}{R:7.3f}{F:7.3f}")
    P = TP / (TP + FP) if TP + FP else 0
    R = TP / (TP + FN) if TP + FN else 0
    F = 2 * P * R / (P + R) if P + R else 0
    print(f"\n{'OVERALL':16}{'':11}{TP:5}{FP:4}{FN:4}{P:7.3f}{R:7.3f}{F:7.3f}")


if __name__ == "__main__":
    main()
