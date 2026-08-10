"""Regex-only eval surface: score the team's real dutch_regex.py recognizers
against new_data's ground truth, with no model involved at all.

This is the one surface fully testable right now, with no GPU/Colab needed --
imports the real production regex module so numbers reflect actual deployed
behavior, not a re-implementation that could drift from it.
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from src.detection.dutch_regex import get_dutch_regex_recognizers  # noqa: E402

import data_pipeline as dp  # noqa: E402
import eval_metrics as em  # noqa: E402

# Only the labels dutch_regex.py can ever produce -- the other model-owned
# labels (NAME, ORGANIZATION, ...) have no regex recognizer, so a regex-only
# surface is expected (not a bug) to score 0 recall on them; they're excluded
# from this report rather than reported as a misleading 0.
REGEX_COVERABLE_LABELS = {"DATE", "AGE", "PHONE"} | set(dp.REGEX_PERMANENT_LABELS)


# ZIP_CODE and STREET rely on [A-ZÀ-Ý] to require a capital letter -- the
# mechanism distinguishing a proper noun (city/street name) from ordinary
# lowercase text. Real Presidio AnalyzerEngine usage (pii_detector.py) doesn't
# force IGNORECASE, so blanket-applying it here would silently defeat that
# check and make this surface report numbers the real pipeline wouldn't
# produce -- confirmed via personal_finetune/regex_edge_cases.py.
_CASE_SENSITIVE_ENTITIES = {"ZIP_CODE", "STREET"}


def _regex_predict(text: str, recognizers) -> list[em.Span]:
    """Raw regex hits, deliberately UNresolved.

    Overlap resolution across labels is a full-pipeline concern (it's what
    src.detection.pii_detector.resolve_overlaps does against the real merged
    model+regex output) -- scoring this surface in isolation, unresolved, is
    what actually answers "how good is the regex layer on its own."
    """
    spans: list[em.Span] = []
    for rec in recognizers:
        entity = rec.supported_entities[0]
        flags = 0 if entity in _CASE_SENSITIVE_ENTITIES else re.IGNORECASE
        for pat in rec.patterns:
            for m in re.finditer(pat.regex, text, flags):
                spans.append((m.start(), m.end(), entity))
    return spans


def run(address_mode: str = "decomposed"):
    records = dp.build_dataset(address_mode)
    recognizers = get_dutch_regex_recognizers()

    golds: list[list[em.Span]] = []
    preds: list[list[em.Span]] = []
    for r in records:
        gold = [(e["start"], e["end"], e["label"]) for e in r["entities"]
                if e["label"] in REGEX_COVERABLE_LABELS]
        if not gold:
            continue  # this surface has nothing to say about a doc with none of its labels
        golds.append(gold)
        pred = [s for s in _regex_predict(r["text"], recognizers) if s[2] in REGEX_COVERABLE_LABELS]
        preds.append(pred)

    print(f"Docs scored (>=1 regex-coverable gold label): {len(golds)} / {len(records)}")
    for mode in ("strict", "relaxed"):
        report = em.run_eval(golds, preds, surface="regex_only", mode=mode)
        em.print_report(report)
        print()

    baseline = em.baseline_empty_scores(golds)
    print("Baseline sanity (always-empty predictor):")
    for lab, sc in baseline.items():
        assert sc.precision == 0.0 and sc.recall == 0.0, "baseline should score zero everywhere"
    print("  OK -- empty predictor scores 0 P/R on every label, as expected.")


if __name__ == "__main__":
    run()
