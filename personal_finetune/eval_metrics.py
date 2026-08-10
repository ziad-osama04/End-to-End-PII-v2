"""Entity-level evaluation metrics shared by all three eval surfaces
(model-only, regex-only, full-pipeline). No GPU/torch dependency here.

Design choices driven by "100% sure we're choosing correctly":
  * Both STRICT (exact span+type match) and RELAXED (any char overlap, same
    type) scoring -- for a masking product, a boundary that's off by a word
    still masks the PII; strict-only scoring over-punishes that.
  * Bootstrap confidence intervals on F1, not just a point estimate -- per-label
    support can be small enough that a single run's ranking is noise.
  * A label x label confusion matrix -- a same-span-wrong-type error (e.g. NAME
    predicted where ORGANIZATION was gold) is a different failure mode than a
    total miss and should not be silently folded into "false negative."
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field


Span = tuple[int, int, str]  # (start, end, label)


@dataclass
class LabelScore:
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def support(self) -> int:
        return self.tp + self.fn

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _overlaps(a: Span, b: Span) -> bool:
    return a[2] == b[2] and not (a[1] <= b[0] or a[0] >= b[1])


def score_document(gold: list[Span], pred: list[Span], mode: str) -> dict[str, LabelScore]:
    """Score one document. mode: 'strict' (exact span+type) or 'relaxed' (overlap+type)."""
    per_label: dict[str, LabelScore] = defaultdict(lambda: LabelScore(label=""))
    matched_gold: set[int] = set()
    matched_pred: set[int] = set()

    for pi, p in enumerate(pred):
        for gi, g in enumerate(gold):
            if gi in matched_gold:
                continue
            hit = (p == g) if mode == "strict" else _overlaps(g, p)
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


def aggregate(doc_scores: list[dict[str, LabelScore]]) -> dict[str, LabelScore]:
    totals: dict[str, LabelScore] = {}
    for doc in doc_scores:
        for lab, sc in doc.items():
            t = totals.setdefault(lab, LabelScore(label=lab))
            t.tp += sc.tp
            t.fp += sc.fp
            t.fn += sc.fn
    return totals


def overall(totals: dict[str, LabelScore]) -> LabelScore:
    o = LabelScore(label="__overall__")
    for sc in totals.values():
        o.tp += sc.tp
        o.fp += sc.fp
        o.fn += sc.fn
    return o


MIN_RELIABLE_SUPPORT = 10


def flag_unreliable(totals: dict[str, LabelScore]) -> list[str]:
    return [lab for lab, sc in totals.items() if sc.support < MIN_RELIABLE_SUPPORT]


# --------------------------------------------------------------------------- #
# Bootstrap confidence intervals (resample documents, not individual spans, so
# resampling respects within-document correlation).
# --------------------------------------------------------------------------- #
def bootstrap_ci(
    doc_scores: list[dict[str, LabelScore]],
    label: str,
    n_resamples: int = 1000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Return (point_f1, ci_low, ci_high) at 95% for one label."""
    rng = random.Random(seed)
    n = len(doc_scores)
    if n == 0:
        return (0.0, 0.0, 0.0)
    point = aggregate(doc_scores).get(label, LabelScore(label=label)).f1

    samples = []
    for _ in range(n_resamples):
        resampled = [doc_scores[rng.randrange(n)] for _ in range(n)]
        agg = aggregate(resampled).get(label, LabelScore(label=label))
        samples.append(agg.f1)
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[int(0.975 * n_resamples) - 1]
    return (point, lo, hi)


# --------------------------------------------------------------------------- #
# Confusion matrix: for each gold span, what label (if any) did a prediction
# that overlaps it carry? Answers "is NAME being confused with ORGANIZATION",
# not just "was it a hit or a miss."
# --------------------------------------------------------------------------- #
def confusion_matrix(gold: list[Span], pred: list[Span]) -> Counter:
    """Counter keyed by (gold_label, pred_label_or_None) across one document.
    pred_label is None when no prediction overlaps that gold span at all.
    """
    cm = Counter()
    for g in gold:
        overlapping = [p for p in pred if not (g[1] <= p[0] or g[0] >= p[1])]
        if not overlapping:
            cm[(g[2], None)] += 1
        else:
            for p in overlapping:
                cm[(g[2], p[2])] += 1
    return cm


def aggregate_confusion(matrices: list[Counter]) -> Counter:
    total = Counter()
    for m in matrices:
        total.update(m)
    return total


# --------------------------------------------------------------------------- #
# Trivial baseline: an always-empty predictor. Its recall is always 0 and
# precision undefined-as-0, so it's a floor every real F1 must clear -- a
# sanity check on the harness itself, not on any model.
# --------------------------------------------------------------------------- #
def baseline_empty_scores(golds: list[list[Span]]) -> dict[str, LabelScore]:
    doc_scores = [score_document(g, [], "strict") for g in golds]
    return aggregate(doc_scores)


@dataclass
class EvalReport:
    surface: str
    mode: str
    per_label: dict[str, LabelScore]
    overall_score: LabelScore
    unreliable_labels: list[str]
    confusion: Counter
    cis: dict[str, tuple[float, float, float]] = field(default_factory=dict)


def run_eval(
    golds: list[list[Span]],
    preds: list[list[Span]],
    surface: str,
    mode: str = "strict",
    compute_ci: bool = True,
) -> EvalReport:
    assert len(golds) == len(preds)
    doc_scores = [score_document(g, p, mode) for g, p in zip(golds, preds)]
    totals = aggregate(doc_scores)
    cis = {}
    if compute_ci:
        for lab in totals:
            cis[lab] = bootstrap_ci(doc_scores, lab)
    matrices = [confusion_matrix(g, p) for g, p in zip(golds, preds)]
    return EvalReport(
        surface=surface,
        mode=mode,
        per_label=totals,
        overall_score=overall(totals),
        unreliable_labels=flag_unreliable(totals),
        confusion=aggregate_confusion(matrices),
        cis=cis,
    )


def print_report(report: EvalReport) -> None:
    o = report.overall_score
    print(f"=== {report.surface} ({report.mode}) ===")
    print(f"overall  P={o.precision:.3f}  R={o.recall:.3f}  F1={o.f1:.3f}  (tp={o.tp} fp={o.fp} fn={o.fn})")
    if report.unreliable_labels:
        print(f"UNRELIABLE (support<{MIN_RELIABLE_SUPPORT}): {report.unreliable_labels}")
    print("per-label:")
    for lab, sc in sorted(report.per_label.items(), key=lambda kv: -kv[1].support):
        ci = report.cis.get(lab)
        ci_str = f"  95% CI=[{ci[1]:.3f},{ci[2]:.3f}]" if ci else ""
        print(f"  {lab:16s} P={sc.precision:.3f} R={sc.recall:.3f} F1={sc.f1:.3f} n={sc.support}{ci_str}")
    if report.confusion:
        print("confusion (gold -> pred, top 10 non-diagonal):")
        non_diag = [(k, v) for k, v in report.confusion.items() if k[0] != k[1]]
        for (gold_lab, pred_lab), n in sorted(non_diag, key=lambda kv: -kv[1])[:10]:
            print(f"  {gold_lab:16s} -> {pred_lab or 'MISS':16s} x{n}")
