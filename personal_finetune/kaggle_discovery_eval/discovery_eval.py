"""TamerBERT generalization-maximizing trial.

Trains on the filtered (leak-free) TamerBERT train.jsonl template pool, then
evaluates on THREE separate surfaces to actually measure generalization
rather than assume it:

  1. eval_indist              -- unseen docs, but templates WERE seen in training
  2. eval_heldout_templates   -- unseen docs from templates NEVER in training
                                  (same generator family, novel structure)
  3. eval_real                -- the 5 real HealthOne Nova documents
                                  (org_data_filled_labeled.jsonl -- the only
                                  actual real-structure ground truth we have)

Regex layer is patterns.py (checksum-validated INSZ/RIZIV, telecom-plan-aware
PHONE validation, hard-negative rejection) inlined in full -- not the simpler
dutch_regex-style patterns used in earlier trials, since this run's whole
point is testing our best available approach.

Two merge strategies are scored for full_pipeline (both are cheap post-hoc
recomputations from the same raw predictions, no extra GPU cost):
  - drop_all:  regex excluded entirely for AGE/DATE/PHONE (model owns them).
               Best peak in-distribution accuracy, proven fragile OOD.
  - fallback:  model wins wherever it fires; regex only fills genuine model
               silence. Proven far more robust OOD in the batch_final holdout
               (0.660 vs 0.476 strict F1) at a real but smaller in-distribution
               cost. Primary strategy for this trial since the explicit goal
               is maximizing generalization.

Self-contained: Kaggle script kernels don't reliably put sibling .py files on
sys.path, so patterns.py is inlined below rather than imported.
"""
from __future__ import annotations

import glob
import inspect
import json
import os
import random
import re
import shutil
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field

os.environ.setdefault(
    "PII_DATA_ROOT",
    "/kaggle/input/datasets/farahelmashad/personal-pii-tamerbert-generalization-data",
)

TRIAL_ID = os.environ.get("TRIAL_ID", "tamerbert-discovery-v1")
SEED = int(os.environ.get("SEED", "42"))
MODEL_HF_ID = "CLTL/MedRoBERTa.nl"
MAX_LEN = 512
STRIDE = 128
MAX_STEPS = int(os.environ.get("MAX_STEPS", "1500"))
# Dry-run guard: cap corpus size for a fast end-to-end pipeline check before
# spending real quota. 0 (falsy) = full corpus.
DOC_LIMIT = int(os.environ.get("DOC_LIMIT", "0"))

OUTPUT_DIR = "/kaggle/working/checkpoints"
REPORT_DIR = "/kaggle/working/reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# Final model is saved OUTSIDE OUTPUT_DIR (which gets wiped at the end -- it
# only ever holds intermediate step-checkpoints for the overfitting curve).
# This becomes part of the kernel's own version output, so a LATER kernel
# version can mount it read-only via kernel-metadata.json's "kernel_sources"
# (Kaggle mounts a prior version's output at /kaggle/input/<kernel-slug>/)
# and run pure inference on a new eval surface without retraining -- no
# checkpoint ever needs to touch the laptop or leave Kaggle's own storage.
FINAL_MODEL_DIR = "/kaggle/working/final_model"
SKIP_TRAINING = os.environ.get("SKIP_TRAINING", "1") == "1"


def find_one(name, is_dir=False, root="/kaggle/input"):
    for r, dirs, files in os.walk(root):
        if is_dir and name in dirs:
            return os.path.join(r, name)
        if not is_dir and name in files:
            return os.path.join(r, name)
    raise FileNotFoundError(f"{name!r} not found anywhere under {root}")


PRETRAINED_MODEL_DIR = os.environ.get("PRETRAINED_MODEL_DIR", "") or (
    find_one("final_model", is_dir=True) if SKIP_TRAINING else "")

print(f"=== TRIAL {TRIAL_ID}  seed={SEED} ===")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForTokenClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)
from transformers.trainer_utils import get_last_checkpoint  # noqa: E402

print("CUDA available:", torch.cuda.is_available(), "device_count:", torch.cuda.device_count())


# =========================================================================== #
# --- patterns.py (inlined in full -- checksum-validated regex layer) ------- #
# =========================================================================== #

RING = "°º˚⁰ᵒ∘⚬"
DASHES = "-‐‑‒–—−﹣"
SPACES = "     　"
INVISIBLE = "­​‌‍﻿"
QUOTES = "‘’ʼ´`"

_FOLD = {}
for c in RING[1:]:
    _FOLD[c] = "°"
for c in DASHES[1:]:
    _FOLD[c] = "-"
for c in SPACES:
    _FOLD[c] = " "
for c in INVISIBLE:
    _FOLD[c] = ""
for c in QUOTES:
    _FOLD[c] = "'"
_FOLD_TABLE = str.maketrans(_FOLD)


def fold(text):
    return unicodedata.normalize("NFC", text).translate(_FOLD_TABLE)


P = {}
# Trailing lookahead is (?!\d) only, not (?![\d.\-/]) -- the wider set
# rejected a match whenever a sentence-final "." immediately followed the
# number (e.g. "...INSZ 58092710179." at end of sentence), which is the
# single most common way a number ends in real prose. Only a following
# DIGIT should be rejected (it means this was a truncated prefix of a
# longer run); trailing punctuation is not part of the number.
P["INSZ"] = re.compile(r"(?<![\d.\-/])(\d{2})[.\-/ ]?(\d{2})[.\-/ ]?(\d{2})"
                       r"[-.\s]?(\d{3})[.\-/ ]?(\d{2})(?!\d)")
P["RIZIV"] = re.compile(r"(?<![\d.\-/])(\d)[-.\s]?(\d{5})[-.\s]?(\d{2})"
                        r"[-.\s]?(\d{3})(?!\d)")
P["EMAIL"] = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
P["URL"] = re.compile(
    r"\bhttps?://[^\s<>\"'\])]+|\bwww\.[\w-]+(?:\.[\w-]+)+(?:/[^\s<>\"'\])]*)?"
    r"|(?<![@\w.])\b[\w-]{2,}\.(?:be|nl|com|org|net|eu)(?:/[^\s<>\"'\])]*)?")
P["TELEFOON"] = re.compile(
    r"(?<!\d)(?:(?:\+32|0032|32)[\s./-]?(?:\(0\)[\s./-]?)?)?"
    r"(?:0?(?:4[5-9]\d(?:[\s./-]?\d){6}"
    r"|[2349](?:[\s./-]?\d){7}"
    r"|(?:1\d|5\d|6\d|7\d|8\d)(?:[\s./-]?\d){6}"
    r"|800(?:[\s./-]?\d){5}"
    r"|(?:70|78|900)(?:[\s./-]?\d){6}))"
    r"(?!\d)",
    re.IGNORECASE)
_MONTHS = (r"jan(?:uari)?|feb(?:ruari)?|m(?:rt|aa|aart)|apr(?:il)?|mei|jun(?:i)?"
           r"|jul(?:i)?|aug(?:ustus)?|sep(?:t|tember)?|okt(?:ober)?"
           r"|nov(?:ember)?|dec(?:ember)?")
_DATE_ANCHOR = r"\b(?:op|d\.d\.|datum:?)\s+"
P["DOB"] = re.compile(
    rf"[{RING}]\s?(\d{{1,2}})[-/.](\d{{1,2}})[-/.]((?:19|20)?\d{{2}})"
    rf"|[{RING}]\s?((?:19|20)\d{{2}})-(\d{{1,2}})-(\d{{1,2}})(?!\d)"
    rf"|[{RING}]\s?((?:19|20)\d{{2}})\b"
    rf"|[{RING}]\s?(\d{{1,2}})\s+({_MONTHS})\s+((?:19|20)\d{{2}})", re.I)
P["DATE_DMY"] = re.compile(
    r"(?<![\d/.\-])(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])\2((?:19|20)\d{2})(?![\d])")
P["DATE_DMY_2YR"] = re.compile(
    r"(?<![\d/.\-])(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])\2(\d{2})(?![\d])")
P["DATE_ISO"] = re.compile(r"(?<![\d\-])((?:19|20)\d{2})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])(?![\d\-])")
# Same YYYY-MM-DD structure but slash-separated (e.g. "1962/07/30") -- never
# covered by any prior pattern; confirmed missing on the OOD stress set.
P["DATE_ISO_SLASH"] = re.compile(r"(?<![\d/])((?:19|20)\d{2})/(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])(?![\d/])")
P["DATE_YM_REV"] = re.compile(
    r"(?<![\d/.\-])((?:19|20)\d{2})([/.\-])(0?[1-9]|1[0-2])(?!\d)(?![/.\-]\d)")
P["DATE_MY"] = re.compile(r"(?<![\d/.\-])(0?[1-9]|1[0-2])[/.\-]((?:19|20)\d{2})(?![\d])")
P["DATE_TEXT"] = re.compile(
    rf"\b(?:(0?[1-9]|[12]\d|3[01])\s+)?({_MONTHS})\s+'?((?:19|20)?\d{{2}})\b", re.I)
P["DATE_NOYEAR"] = re.compile(
    _DATE_ANCHOR + r"(0?[1-9]|[12]\d|3[01])([/.\-])(0?[1-9]|1[0-2])(?!\d)(?![/.\-]\d)",
    re.I)
P["DATE_COMPACT"] = re.compile(
    _DATE_ANCHOR + r"((?:19|20)\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)"
    r"|" + _DATE_ANCHOR + r"(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)",
    re.I)
P["AGE"] = re.compile(
    r"\b(\d{1,3})\s*(?:jaar|jr\.?|j\.)(?!\w)"
    r"|\b(\d{1,3})\s?-?\s?jarig[e]?\b"
    r"|(?<=leeftijd:)\s?(\d{1,3})\b"
    r"|(?<=leeftijd)\s(\d{1,3})\b", re.I)


def valid_insz(digits):
    if len(digits) != 11:
        return False, None, False
    body, chk = digits[:9], int(digits[9:])
    century = None
    if 97 - (int(body) % 97) == chk:
        century = 1900
    elif 97 - (int("2" + body) % 97) == chk:
        century = 2000
    if century is None:
        return False, None, False
    month = int(digits[2:4])
    is_bis = month > 12
    if is_bis and not (21 <= month <= 32 or 41 <= month <= 52):
        return False, None, False
    if not is_bis and not (1 <= month <= 12):
        return False, None, False
    if not (1 <= int(digits[6:9]) <= 997):
        return False, None, False
    return True, century, is_bis


def valid_riziv(digits):
    if len(digits) != 11:
        return False
    return 97 - (int(digits[:6]) % 97) == int(digits[6:8])


def valid_phone(s):
    s = re.sub(r"\(\s*0\s*\)", "", s)
    d = re.sub(r"\D", "", s)
    if d.startswith("0032"):
        d = "0" + d[4:]
    elif d.startswith("32") and len(d) in (10, 11):
        d = "0" + d[2:]
    if not d.startswith("0"):
        return False, None
    if re.match(r"^04(5[56]|[6-9]\d)", d):
        if len(d) == 10:
            return True, "mobile"
        if len(d) == 9:
            return True, "landline"
        return False, "mobile"
    if re.match(r"^0(70|77|78)", d):
        return (len(d) == 9), "service"
    if re.match(r"^0(800|900)", d):
        return (8 <= len(d) <= 10), "service"
    if re.match(r"^0[2349]", d):
        return (len(d) == 9), "landline"
    if re.match(r"^0(1[0-9]|5[0-9]|6[0-9]|7[1-8]|8[0-9])", d):
        return (len(d) == 9), "landline"
    return False, None


def valid_date_parts(d, m, y):
    d, m, y = int(d), int(m), int(y)
    if y < 100:
        y += 1900 if y > 30 else 2000
    if not (1 <= m <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100):
        return False
    dim = [31, 29 if (y % 4 == 0 and (y % 100 or y % 400 == 0)) else 28,
           31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


def valid_date_parts_noyear(d, m):
    d, m = int(d), int(m)
    if not (1 <= m <= 12 and 1 <= d <= 31):
        return False
    dim = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d <= dim[m - 1]


NEGATIVE_CONTEXT = [
    re.compile(r"\b(?:BD|RR|HR|HF|SpO2|spo2|pols|temp|T)\s*[:=]\s*$", re.I),
    re.compile(r"\b\d+\s*(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg)\s*$", re.I),
    re.compile(r"\b(?:as|axis|hoek|flexie|extensie|abductie|rotatie|ROM)\s*$", re.I),
    re.compile(r"\b(?:FEV1|FVC|PEF|FEF|TLC|RV|VC|TGV|Raw|sGaw|TLco|Kco|Va)\b[^\n]{0,20}$"),
    # reference-range disclaimer phrasing ("niet gevalideerd/geëxtrapoleerd
    # boven/onder de N jaar") -- the number is a threshold in a boilerplate
    # sentence, not a patient's age. Confirmed on real docs and OOD stress
    # docs alike (recurred 3x across both).
    re.compile(r"\b(?:boven|onder)\s+de\s*$", re.I),
]
NEGATIVE_SURFACE = re.compile(
    r"^(?:\d{1,2}/\d{1,2}(?:/\d{1,2})?$"
    r"|\d+\s?[xX]$"
    r"|\d+\s?(?:mg|mcg|g|ml|cc|ie|E|IU|kg|cm|mmHg|%)$"
    r")")
FREQ_RE = re.compile(r"^\d{1,2}\s*/\s*[dwmj]$", re.I)
BP_RE = re.compile(r"^\d{2,3}\s*/\s*\d{2,3}$")


def is_hard_negative(text, start, end, label=None):
    surface = text[start:end].strip()
    if label != "DATE":
        if FREQ_RE.match(surface):
            return "dosing frequency"
        if BP_RE.match(surface):
            return "blood pressure"
        if NEGATIVE_SURFACE.match(surface):
            return "dose/count"
    left = text[max(0, start - 24):start]
    if label != "DATE":
        for pat in NEGATIVE_CONTEXT:
            if pat.search(left):
                return f"negative context: {left.strip()[-16:]!r}"
    right = text[end:end + 8]
    if re.match(r"\s*(?:mg|mcg|ml|cc|kg|cm|mmHg|%|ie\b|E\b|graden)", right, re.I):
        return "followed by unit"
    return None


@dataclass
class Hit:
    label: str
    start: int
    end: int
    text: str
    valid: bool = True
    detail: str = ""


# Most specific first; DOB remapped to DATE (our taxonomy has no separate
# DOB label -- gold data tags birth dates as DATE).
ORDER = [
    ("INSZ", "INSZ"), ("RIZIV", "RIZIV"),
    ("EMAIL", "EMAIL"), ("URL", "URL"),
    ("TELEFOON", "PHONE"),
    ("DOB", "DATE"),
    ("DATE_ISO", "DATE"), ("DATE_ISO_SLASH", "DATE"), ("DATE_DMY", "DATE"), ("DATE_DMY_2YR", "DATE"),
    ("DATE_TEXT", "DATE"), ("DATE_YM_REV", "DATE"), ("DATE_MY", "DATE"),
    ("DATE_COMPACT", "DATE"), ("DATE_NOYEAR", "DATE"),
    ("AGE", "AGE"),
]


def patterns_detect(text):
    """Returns a list of (start, end, label) tuples, folded-text offsets."""
    src = fold(text)
    consumed = [False] * len(src)
    hits = []
    for pat_name, label in ORDER:
        for m in P[pat_name].finditer(src):
            s, e = m.start(), m.end()
            if any(consumed[s:e]):
                continue
            neg = is_hard_negative(src, s, e, label)
            if neg:
                continue
            surface = m.group()
            ok = True
            if label == "INSZ":
                ok, _, _ = valid_insz(re.sub(r"\D", "", surface))
            elif label == "RIZIV":
                digits = re.sub(r"\D", "", surface)
                ok = len(digits) == 11 and valid_riziv(digits)
            elif label == "PHONE":
                ok, _ = valid_phone(surface)
            elif label == "DATE":
                g = m.groups()
                if pat_name == "DATE_DMY":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_ISO":
                    ok = valid_date_parts(g[2], g[1], g[0])
                elif pat_name == "DATE_ISO_SLASH":
                    ok = valid_date_parts(g[2], g[1], g[0])
                elif pat_name == "DATE_DMY_2YR":
                    ok = valid_date_parts(g[0], g[2], g[3])
                elif pat_name == "DATE_NOYEAR":
                    ok = valid_date_parts_noyear(g[0], g[2])
                elif pat_name == "DATE_COMPACT":
                    if g[0]:
                        ok = valid_date_parts(g[2], g[1], g[0])
                    else:
                        ok = valid_date_parts(g[5], g[4], g[3])
            elif label == "AGE":
                v = next((x for x in m.groups() if x), None)
                ok = v is not None and 0 <= int(v) <= 120

            if not ok:
                continue
            if label == "AGE":
                gi = next((i for i, g in enumerate(m.groups(), 1) if g), None)
                if gi and m.start(gi) >= 0:
                    gs, ge = m.span(gi)
                    tail = re.match(r"\s*(?:jaar|jr\.?|j\.|-?\s?jarige?)", src[ge:ge + 10], re.I)
                    s, e = gs, (ge + tail.end() if tail else ge)
            elif pat_name in ("DATE_NOYEAR", "DATE_COMPACT"):
                populated = [i for i, g in enumerate(m.groups(), 1) if g]
                s, e = m.start(populated[0]), m.end(populated[-1])
            elif pat_name == "DOB":
                populated = [i for i, g in enumerate(m.groups(), 1) if g]
                s, e = m.start(populated[0]), m.end(populated[-1])

            for i in range(s, e):
                consumed[i] = True
            hits.append((s, e, label))
    return sorted(hits, key=lambda h: h[0])


# =========================================================================== #
# --- eval_metrics (inlined) ------------------------------------------------- #
# =========================================================================== #
@dataclass
class LabelScore:
    label: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    @property
    def support(self):
        return self.tp + self.fn

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


def _overlaps(a, b):
    return a[2] == b[2] and not (a[1] <= b[0] or a[0] >= b[1])


def score_document(gold, pred, mode):
    per_label = defaultdict(lambda: LabelScore(label=""))
    matched_gold, matched_pred = set(), set()
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


def em_aggregate(doc_scores):
    totals = {}
    for doc in doc_scores:
        for lab, sc in doc.items():
            t = totals.setdefault(lab, LabelScore(label=lab))
            t.tp += sc.tp
            t.fp += sc.fp
            t.fn += sc.fn
    return totals


def em_overall(totals):
    o = LabelScore(label="__overall__")
    for sc in totals.values():
        o.tp += sc.tp
        o.fp += sc.fp
        o.fn += sc.fn
    return o


MIN_RELIABLE_SUPPORT = 10


def flag_unreliable(totals):
    return [lab for lab, sc in totals.items() if sc.support < MIN_RELIABLE_SUPPORT]


def bootstrap_ci(doc_scores, label, n_resamples=1000, seed=0):
    rng = random.Random(seed)
    n = len(doc_scores)
    if n == 0:
        return (0.0, 0.0, 0.0)
    point = em_aggregate(doc_scores).get(label, LabelScore(label=label)).f1
    samples = []
    for _ in range(n_resamples):
        resampled = [doc_scores[rng.randrange(n)] for _ in range(n)]
        agg = em_aggregate(resampled).get(label, LabelScore(label=label))
        samples.append(agg.f1)
    samples.sort()
    lo = samples[int(0.025 * n_resamples)]
    hi = samples[int(0.975 * n_resamples) - 1]
    return (point, lo, hi)


def confusion_matrix(gold, pred):
    cm = Counter()
    for g in gold:
        overlapping = [p for p in pred if not (g[1] <= p[0] or g[0] >= p[1])]
        if not overlapping:
            cm[(g[2], None)] += 1
        else:
            for p in overlapping:
                cm[(g[2], p[2])] += 1
    return cm


def aggregate_confusion(matrices):
    total = Counter()
    for m in matrices:
        total.update(m)
    return total


@dataclass
class EvalReport:
    surface: str
    mode: str
    per_label: dict
    overall_score: LabelScore
    unreliable_labels: list
    confusion: Counter
    cis: dict = field(default_factory=dict)


def run_eval(golds, preds, surface, mode="strict", compute_ci=True):
    assert len(golds) == len(preds)
    doc_scores = [score_document(g, p, mode) for g, p in zip(golds, preds)]
    totals = em_aggregate(doc_scores)
    cis = {lab: bootstrap_ci(doc_scores, lab) for lab in totals} if compute_ci else {}
    matrices = [confusion_matrix(g, p) for g, p in zip(golds, preds)]
    return EvalReport(surface=surface, mode=mode, per_label=totals, overall_score=em_overall(totals),
                       unreliable_labels=flag_unreliable(totals), confusion=aggregate_confusion(matrices), cis=cis)


def print_report(report):
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


# =========================================================================== #
# --- Merge strategies -------------------------------------------------------#
# =========================================================================== #
# INSZ/RIZIV/URL are pure regex-owned (never model-trained). NAME/ADDRESS are
# pure model-owned (patterns.py has no competing regex for either). AGE/DATE/
# PHONE are the "BOTH" category -- the only labels where a merge decision
# matters at all.
HYBRID_LABELS = {"AGE", "DATE", "PHONE"}
REGEX_PERMANENT_LABELS = ("INSZ", "RIZIV", "URL")
_LABEL_PRIORITY = {"INSZ": 9, "RIZIV": 9, "URL": 10, "DATE": 8, "PHONE": 7, "AGE": 5, "NAME": 4, "ADDRESS": 6}


def merge_drop_all(model_spans, regex_spans):
    """Regex excluded entirely for AGE/DATE/PHONE -- model owns them outright."""
    filtered_regex = [s for s in regex_spans if s[2] not in HYBRID_LABELS]
    combined = [tuple(s) for s in model_spans] + filtered_regex

    def rank(sp):
        return (_LABEL_PRIORITY.get(sp[2], 1), sp[1] - sp[0])

    covered, kept = set(), []
    for sp in sorted(combined, key=rank, reverse=True):
        span_range = range(sp[0], sp[1])
        if all(i in covered for i in span_range):
            continue
        kept.append(sp)
        covered.update(span_range)
    return sorted(kept, key=lambda s: s[0])


def merge_fallback(model_spans, regex_spans):
    """Model always wins where it fires; regex only fills genuine gaps for
    AGE/DATE/PHONE. Proven far more robust under distribution shift."""
    kept = [tuple(s) for s in model_spans]
    covered = set()
    for sp in kept:
        covered.update(range(sp[0], sp[1]))
    for sp in regex_spans:
        sp = tuple(sp)
        span_range = range(sp[0], sp[1])
        if sp[2] in HYBRID_LABELS:
            if any(i in covered for i in span_range):
                continue
        kept.append(sp)
        covered.update(span_range)
    return sorted(kept, key=lambda s: s[0])


# =========================================================================== #
# --- Main: load, tokenize, train, decode, eval ------------------------------#
# =========================================================================== #
DATA_ROOT = os.environ["PII_DATA_ROOT"]


def load_split(fname):
    path = os.path.join(DATA_ROOT, fname)
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out.append({"text": d["text"], "entities": [
                {"start": s["start"], "end": s["end"], "label": s["label"]} for s in d["spans"]
            ]})
    return out


# Discovery run: no training data needed at all (SKIP_TRAINING is forced on
# for this script). The 4 original surfaces are kept as a regression check
# (confirms the mounted final_model/ scores identically to the trial run's
# own numbers), plus 3 new discovery surfaces: an independent hand-crafted
# battery (ood_v2), a purpose-built sliding-window boundary-crossing doc,
# and a large automated perturbation sweep over existing labeled documents.
DISCOVERY_ROOT = os.path.dirname(find_one("ood_docs_v2.jsonl"))


def load_split_from(root, fname):
    out = []
    with open(os.path.join(root, fname), encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out.append({"text": d["text"], "entities": [
                {"start": s["start"], "end": s["end"], "label": s["label"]} for s in d["spans"]
            ]})
    return out


eval_sets = {
    "indist": load_split("eval_indist.jsonl"),
    "heldout_templates": load_split("eval_heldout_templates.jsonl"),
    "real": load_split("eval_real.jsonl"),
    "ood": load_split("ood_docs.jsonl"),
    "ood_v2": load_split_from(DISCOVERY_ROOT, "ood_docs_v2.jsonl"),
    "boundary": load_split_from(DISCOVERY_ROOT, "boundary_doc.jsonl"),
    "perturbation_sweep": load_split_from(DISCOVERY_ROOT, "perturbation_sweep.jsonl"),
    "v4_discovery": load_split_from(DISCOVERY_ROOT, "v4_discovery.jsonl"),
}

if DOC_LIMIT:
    eval_sets = {k: v[:max(1, DOC_LIMIT // 10)] for k, v in eval_sets.items()}
    print("DRY RUN: capped " + "  ".join(f"{k}={len(v)}" for k, v in eval_sets.items()))

print("Loading pretrained model to derive label set (no training data needed)...")
_tmp_model = AutoModelForTokenClassification.from_pretrained(PRETRAINED_MODEL_DIR)
id2label = {int(k): v for k, v in _tmp_model.config.id2label.items()}
label2id = {v: int(k) for k, v in _tmp_model.config.id2label.items()}
label_list = [id2label[i] for i in sorted(id2label)]
model_labels = sorted({v[2:] for v in id2label.values() if v != "O"})
del _tmp_model
print(f"  " + "  ".join(f"{k}={len(v)}" for k, v in eval_sets.items()))
print(f"model_labels ({len(model_labels)}): {model_labels}")

with open(os.path.join(REPORT_DIR, "trial_config.json"), "w") as f:
    json.dump({"trial_id": TRIAL_ID, "seed": SEED, "model_labels": model_labels,
               "pretrained_model_dir": PRETRAINED_MODEL_DIR,
               "n_eval": {k: len(v) for k, v in eval_sets.items()}}, f, indent=2)

tokenizer = AutoTokenizer.from_pretrained(MODEL_HF_ID, add_prefix_space=True)
assert tokenizer.is_fast


def char_bio(text, entities):
    ch = ["O"] * len(text)
    for e in entities:
        s, en, lab = e["start"], e["end"], e["label"]
        s, en = max(0, s), min(len(text), en)
        for i in range(s, en):
            ch[i] = ("B-" if i == s else "I-") + lab
    return ch


def tokenize_split(recs, for_training):
    texts = [r["text"] for r in recs]
    tok = tokenizer(texts, truncation=True, max_length=MAX_LEN, stride=STRIDE,
                     return_overflowing_tokens=True, return_offsets_mapping=True, padding="max_length")
    sample_map = tok.pop("overflow_to_sample_mapping")
    offset_batch = tok.pop("offset_mapping")
    window_meta = [(sample_map[i], offset_batch[i]) for i in range(len(sample_map))]
    if for_training:
        char_cache, all_labels = {}, []
        for i, (doc_idx, offsets) in enumerate(window_meta):
            if doc_idx not in char_cache:
                char_cache[doc_idx] = char_bio(recs[doc_idx]["text"], recs[doc_idx]["entities"])
            ch = char_cache[doc_idx]
            lab_ids = []
            for (a, b) in offsets:
                # (0,0) is the padding-token marker; a token can ALSO land exactly at
                # end-of-string (trailing whitespace in the source text -- every doc in
                # this corpus has one), giving offset (len(text), len(text)) which is
                # non-(0,0) but still out of bounds for indexing into `ch`.
                if (a == 0 and b == 0) or a >= len(ch):
                    lab_ids.append(-100)
                else:
                    lab_ids.append(label2id.get(ch[a], label2id["O"]))
            all_labels.append(lab_ids)
        tok["labels"] = all_labels
    return tok, window_meta


eval_encs = {}
for name, recs in eval_sets.items():
    print(f"Tokenizing eval split '{name}'...")
    eval_encs[name] = tokenize_split(recs, for_training=False)


class WindowDataset(torch.utils.data.Dataset):
    def __init__(self, enc, has_labels):
        self.enc, self.has_labels, self.n = enc, has_labels, len(enc["input_ids"])

    def __len__(self):
        return self.n

    def __getitem__(self, i):
        item = {k: torch.tensor(v[i]) for k, v in self.enc.items() if k != "labels"}
        if self.has_labels:
            item["labels"] = torch.tensor(self.enc["labels"][i])
        return item


ta_params = inspect.signature(TrainingArguments.__init__).parameters
eval_key = "eval_strategy" if "eval_strategy" in ta_params else "evaluation_strategy"
ta_kwargs = dict(
    output_dir=OUTPUT_DIR, per_device_eval_batch_size=32,
    fp16=torch.cuda.is_available(), report_to="none", push_to_hub=False, seed=SEED,
)
ta_kwargs[eval_key] = "no"
training_args = TrainingArguments(**ta_kwargs)
tr_params = inspect.signature(Trainer.__init__).parameters
tok_kwarg = {"processing_class": tokenizer} if "processing_class" in tr_params else {"tokenizer": tokenizer}

print(f"Loading finished model from {PRETRAINED_MODEL_DIR} -- discovery run, no GPU training.")
model = AutoModelForTokenClassification.from_pretrained(PRETRAINED_MODEL_DIR)
trainer = Trainer(model=model, args=training_args, **tok_kwarg)


def decode_model_preds(pred_ids, window_meta, n_docs):
    per_doc_spans = {i: [] for i in range(n_docs)}
    for window_idx, (doc_idx, offsets) in enumerate(window_meta):
        ids = pred_ids[window_idx]
        cur_label = cur_start = cur_end = None
        for tok_idx, (a, b) in enumerate(offsets):
            if a == 0 and b == 0:
                lab, prefix = None, None
            else:
                tag = id2label[int(ids[tok_idx])]
                lab = None if tag == "O" else tag[2:]
                prefix = tag[:1] if tag != "O" else None
            if lab is None:
                if cur_label is not None:
                    per_doc_spans[doc_idx].append((cur_start, cur_end, cur_label))
                    cur_label = None
                continue
            if prefix == "B" or cur_label != lab:
                if cur_label is not None:
                    per_doc_spans[doc_idx].append((cur_start, cur_end, cur_label))
                cur_label, cur_start, cur_end = lab, a, b
            else:
                cur_end = b
        if cur_label is not None:
            per_doc_spans[doc_idx].append((cur_start, cur_end, cur_label))

    def resolve_overlaps(entities):
        ents = sorted(entities, key=lambda x: (-(x[1] - x[0]), x[0]))
        kept = []
        for e in ents:
            if any(not (e[1] <= k[0] or e[0] >= k[1]) for k in kept):
                continue
            kept.append(e)
        return sorted(kept, key=lambda x: x[0])

    return [resolve_overlaps(per_doc_spans[i]) for i in range(n_docs)]


print("Building per-checkpoint overfitting curve on eval_indist (model_only, strict)...")
model_gold_by_set = {}
for name, recs in eval_sets.items():
    model_gold_by_set[name] = [[(e["start"], e["end"], e["label"]) for e in r["entities"] if e["label"] in model_labels]
                                for r in recs]

checkpoint_curve = []
ckpt_dirs = [] if SKIP_TRAINING else sorted(
    glob.glob(os.path.join(OUTPUT_DIR, "checkpoint-*")), key=lambda p: int(p.rsplit("-", 1)[-1]))
if SKIP_TRAINING:
    print("SKIP_TRAINING: no intermediate checkpoints this run, curve left empty.")
indist_enc, indist_meta = eval_encs["indist"]
indist_dataset = WindowDataset(indist_enc, has_labels=False)
for ckpt_dir in ckpt_dirs:
    step = int(ckpt_dir.rsplit("-", 1)[-1])
    ckpt_model = AutoModelForTokenClassification.from_pretrained(ckpt_dir)
    ckpt_trainer = Trainer(model=ckpt_model, args=training_args, **tok_kwarg)
    ckpt_pred_ids = np.argmax(ckpt_trainer.predict(indist_dataset).predictions, axis=2)
    ckpt_preds = decode_model_preds(ckpt_pred_ids, indist_meta, len(eval_sets["indist"]))
    r = run_eval(model_gold_by_set["indist"], ckpt_preds, "model_only", "strict", compute_ci=False)
    checkpoint_curve.append({"step": step, "f1": r.overall_score.f1,
                              "precision": r.overall_score.precision, "recall": r.overall_score.recall})
    print(f"  step={step}  strict_f1={r.overall_score.f1:.3f}")
    del ckpt_model, ckpt_trainer
with open(os.path.join(REPORT_DIR, "checkpoint_curve.json"), "w") as f:
    json.dump(checkpoint_curve, f, indent=2)

# =========================================================================== #
# --- 3-surface x (model_only/regex_only/full_pipeline x2 merges) eval ------ #
# =========================================================================== #
all_reports = {}
all_raw = {}
for name, recs in eval_sets.items():
    print(f"\n########## EVAL SURFACE: {name} ({len(recs)} docs) ##########")
    enc, window_meta = eval_encs[name]
    ds = WindowDataset(enc, has_labels=False)
    pred_ids = np.argmax(trainer.predict(ds).predictions, axis=2)
    model_preds = decode_model_preds(pred_ids, window_meta, len(recs))
    regex_preds = [patterns_detect(r["text"]) for r in recs]

    all_gold = [[(e["start"], e["end"], e["label"]) for e in r["entities"]] for r in recs]
    model_gold = model_gold_by_set[name]
    regex_gold_labels = set(REGEX_PERMANENT_LABELS) | HYBRID_LABELS
    regex_gold = [[s for s in g if s[2] in regex_gold_labels] for g in all_gold]

    full_preds_dropall = [merge_drop_all(model_preds[i], regex_preds[i]) for i in range(len(recs))]
    full_preds_fallback = [merge_fallback(model_preds[i], regex_preds[i]) for i in range(len(recs))]

    reports = {}
    for mode in ("strict", "relaxed"):
        reports[f"model_only_{mode}"] = run_eval(model_gold, model_preds, "model_only", mode)
        reports[f"regex_only_{mode}"] = run_eval(regex_gold, regex_preds, "regex_only", mode)
        reports[f"full_pipeline_dropall_{mode}"] = run_eval(all_gold, full_preds_dropall, "full_pipeline_dropall", mode)
        reports[f"full_pipeline_fallback_{mode}"] = run_eval(all_gold, full_preds_fallback, "full_pipeline_fallback", mode)
    for r in reports.values():
        print_report(r)
        print()
    all_reports[name] = reports
    all_raw[name] = {
        "doc_count": len(recs),
        "gold": [list(g) for g in all_gold],
        "model_preds": [list(map(list, mp)) for mp in model_preds],
        "regex_preds": [list(map(list, rp)) for rp in regex_preds],
    }


def report_to_json(r):
    return {
        "surface": r.surface, "mode": r.mode,
        "overall": {"precision": r.overall_score.precision, "recall": r.overall_score.recall,
                    "f1": r.overall_score.f1, "tp": r.overall_score.tp, "fp": r.overall_score.fp,
                    "fn": r.overall_score.fn},
        "per_label": {lab: {"precision": sc.precision, "recall": sc.recall, "f1": sc.f1,
                             "support": sc.support} for lab, sc in r.per_label.items()},
        "unreliable_labels": r.unreliable_labels,
        "cis": r.cis,
    }


with open(os.path.join(REPORT_DIR, "eval_report.json"), "w") as f:
    json.dump({name: {k: report_to_json(v) for k, v in reports.items()} for name, reports in all_reports.items()},
               f, indent=2)

with open(os.path.join(REPORT_DIR, "raw_predictions.json"), "w") as f:
    json.dump(all_raw, f)

shutil.rmtree(OUTPUT_DIR, ignore_errors=True)  # intermediate step-checkpoints only; FINAL_MODEL_DIR is untouched
print("\nDONE.")
