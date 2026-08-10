"""Stage 3 (regex-ownership ablation), run entirely GPU-free against a cached
raw_predictions.json dumped by kaggle_stage1_trial/train_and_eval.py.

For each hybrid label that has BOTH a model prediction and a regex recognizer
(AGE, DATE, PHONE, ZIP_CODE, STREET), measures the full-pipeline F1 impact of
letting the model own it outright (regex candidate spans for that label
dropped before merge) vs the current keep-both-then-merge behaviour -- both
the label's own delta and the delta on every OTHER label (a regex FP removed
for label X can unblock a previously-shadowed span for label Y in the greedy
priority merge, so the two are not independent).

Also compares the current "skip candidate only if FULLY covered" merge dedup
against a stricter "skip on ANY overlap" variant, since the existing
merge_full_pipeline lets a regex span that partially (not fully) overlaps an
already-kept higher-priority span survive -- a likely second source of the
observed regex-vs-model collisions, independent of label ownership.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class LabelScore:
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def precision(self):
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self):
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self):
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def support(self):
        return self.tp + self.fn


def _overlaps(a, b):
    return a[2] == b[2] and not (a[1] <= b[0] or a[0] >= b[1])


def score_corpus(all_gold, all_pred, mode):
    per_label = defaultdict(lambda: LabelScore(label=""))
    for gold, pred in zip(all_gold, all_pred):
        matched_gold, matched_pred = set(), set()
        for pi, p in enumerate(pred):
            for gi, g in enumerate(gold):
                if gi in matched_gold:
                    continue
                hit = (tuple(p) == tuple(g)) if mode == "strict" else _overlaps(g, p)
                if hit:
                    matched_gold.add(gi)
                    matched_pred.add(pi)
                    per_label[p[2]].tp += 1
                    break
        for pi, p in enumerate(pred):
            if pi not in matched_pred:
                per_label[p[2]].fp += 1
        for gi, g in enumerate(gold):
            if gi not in matched_gold:
                per_label[g[2]].fn += 1
    for lab, sc in per_label.items():
        sc.label = lab
    return dict(per_label)


def overall_f1(per_label):
    tp = sum(s.tp for s in per_label.values())
    fp = sum(s.fp for s in per_label.values())
    fn = sum(s.fn for s in per_label.values())
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1


def merge(model_spans, regex_spans, priority, strict_overlap):
    combined = [tuple(s) for s in model_spans] + [tuple(s) for s in regex_spans]

    def rank(sp):
        return (priority.get(sp[2], 1), sp[1] - sp[0])

    covered, kept = set(), []
    for sp in sorted(combined, key=rank, reverse=True):
        span_range = range(sp[0], sp[1])
        if strict_overlap:
            blocked = any(i in covered for i in span_range)
        else:
            blocked = all(i in covered for i in span_range)
        if blocked:
            continue
        kept.append(sp)
        covered.update(span_range)
    return sorted(kept, key=lambda s: s[0])


def run_variant(gold, model_preds, regex_preds, priority, drop_labels, strict_overlap):
    filtered_regex = [[s for s in doc if s[2] not in drop_labels] for doc in regex_preds]
    full_preds = [merge(model_preds[i], filtered_regex[i], priority, strict_overlap) for i in range(len(gold))]
    out = {}
    for mode in ("strict", "relaxed"):
        per_label = score_corpus(gold, full_preds, mode)
        out[mode] = per_label
    return out


def merge_model_priority_fallback(model_spans, regex_spans, fallback_labels):
    """Model always wins where it fires. Regex only fills genuine gaps for
    fallback_labels (the hybrid labels) -- never competes with an existing
    model span there. Permanent regex-only labels behave as before (no model
    candidate exists for them anyway, so this is a no-op distinction for them)."""
    kept = [tuple(s) for s in model_spans]
    covered = set()
    for sp in kept:
        covered.update(range(sp[0], sp[1]))
    for sp in regex_spans:
        sp = tuple(sp)
        span_range = range(sp[0], sp[1])
        if sp[2] in fallback_labels:
            if any(i in covered for i in span_range):
                continue  # model already said something here; don't second-guess it
        kept.append(sp)
        covered.update(span_range)
    return sorted(kept, key=lambda s: s[0])


def run_variant_fallback(gold, model_preds, regex_preds, fallback_labels):
    full_preds = [merge_model_priority_fallback(model_preds[i], regex_preds[i], fallback_labels)
                  for i in range(len(gold))]
    out = {}
    for mode in ("strict", "relaxed"):
        out[mode] = score_corpus(gold, full_preds, mode)
    return out


def fmt_delta(base_f1, new_f1):
    d = new_f1 - base_f1
    sign = "+" if d >= 0 else ""
    return f"{new_f1:.3f} ({sign}{d:.3f})"


def main(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    gold = [[tuple(s) for s in doc] for doc in data["gold"]]
    model_preds = [[tuple(s) for s in doc] for doc in data["model_preds"]]
    regex_preds = [[tuple(s) for s in doc] for doc in data["regex_preds"]]
    priority = data["label_priority"]

    regex_labels_present = sorted({s[2] for doc in regex_preds for s in doc})
    model_labels_present = sorted({s[2] for doc in model_preds for s in doc})
    ablation_candidates = sorted(set(regex_labels_present) & set(model_labels_present))
    print(f"n_docs={len(gold)}")
    print(f"regex_labels_present={regex_labels_present}")
    print(f"model_labels_present={model_labels_present}")
    print(f"ablation candidates (regex fires AND model owns): {ablation_candidates}")
    print()

    def report(name, variant):
        strict_p, strict_r, strict_f1 = overall_f1(variant["strict"])
        relaxed_p, relaxed_r, relaxed_f1 = overall_f1(variant["relaxed"])
        print(f"[{name}] overall strict F1={strict_f1:.3f} (P={strict_p:.3f} R={strict_r:.3f})  "
              f"relaxed F1={relaxed_f1:.3f} (P={relaxed_p:.3f} R={relaxed_r:.3f})")
        return strict_f1, relaxed_f1

    print("=== baseline (current merge, all regex kept) ===")
    baseline = run_variant(gold, model_preds, regex_preds, priority, drop_labels=set(), strict_overlap=False)
    base_strict_f1, base_relaxed_f1 = report("baseline", baseline)
    base_strict_per_label = {lab: sc.f1 for lab, sc in baseline["strict"].items()}
    print()

    print("=== strict-overlap merge variant (skip candidate on ANY overlap, not just full coverage) ===")
    strict_merge = run_variant(gold, model_preds, regex_preds, priority, drop_labels=set(), strict_overlap=True)
    report("strict-overlap merge, regex kept", strict_merge)
    for lab in ablation_candidates:
        b = baseline["strict"].get(lab, LabelScore(lab)).f1
        s = strict_merge["strict"].get(lab, LabelScore(lab)).f1
        print(f"    {lab:16s} strict F1 {fmt_delta(b, s)}")
    print()

    print("=== per-label regex-ownership ablation (drop regex candidates for ONE label, current merge) ===")
    for drop_lab in ablation_candidates:
        variant = run_variant(gold, model_preds, regex_preds, priority, drop_labels={drop_lab}, strict_overlap=False)
        strict_f1, relaxed_f1 = report(f"drop regex:{drop_lab}", variant)
        own_f1 = variant["strict"].get(drop_lab, LabelScore(drop_lab)).f1
        print(f"    {drop_lab:16s} own strict F1 {fmt_delta(base_strict_per_label.get(drop_lab, 0.0), own_f1)}")
        other_deltas = []
        for lab, sc in variant["strict"].items():
            if lab == drop_lab:
                continue
            b = base_strict_per_label.get(lab, 0.0)
            if abs(sc.f1 - b) > 0.005:
                other_deltas.append(f"{lab}:{fmt_delta(b, sc.f1)}")
        if other_deltas:
            print(f"    side effects on other labels: {', '.join(other_deltas)}")
        print()

    print("=== drop regex for ALL ablation candidates at once (model owns everything hybrid) ===")
    all_drop = run_variant(gold, model_preds, regex_preds, priority, drop_labels=set(ablation_candidates), strict_overlap=False)
    report("drop-all hybrid regex", all_drop)
    for lab in ablation_candidates:
        b = base_strict_per_label.get(lab, 0.0)
        s = all_drop["strict"].get(lab, LabelScore(lab)).f1
        print(f"    {lab:16s} strict F1 {fmt_delta(b, s)}")
    print()

    print("=== drop-all hybrid regex + strict-overlap merge (combined fix) ===")
    combined = run_variant(gold, model_preds, regex_preds, priority, drop_labels=set(ablation_candidates), strict_overlap=True)
    report("drop-all + strict-overlap", combined)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "raw_predictions.json")
