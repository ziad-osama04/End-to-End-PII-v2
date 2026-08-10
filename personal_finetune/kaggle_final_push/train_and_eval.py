"""Stage 1 trial: address-granularity ablation (single ADDRESS vs decomposed).

Personal exploratory track. Uses ONLY new_data (mounted as a private Kaggle
dataset). Never touches Google Drive, the team's shared MLflow experiment, or
the team's backend/ package.

Self-contained on purpose: Kaggle script kernels don't reliably put sibling
.py files on sys.path (learned the hard way -- see dry-run v1), so everything
that would otherwise be data_pipeline.py / eval_metrics.py / dutch_regex.py is
inlined below instead of imported.
"""
from __future__ import annotations

import glob
import hashlib
import inspect
import json
import os
import random
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Literal

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "presidio-analyzer"], check=True)

os.environ.setdefault(
    "PII_DATA_ROOT",
    "/kaggle/input/datasets/farahelmashad/personal-pii-synthetic-training-data",
)

TRIAL_ID = os.environ.get("TRIAL_ID", "final-push-decomposed-seed7")
ADDRESS_MODE = os.environ.get("ADDRESS_MODE", "decomposed")  # "single" or "decomposed"
SEED = int(os.environ.get("SEED", "7"))
MODEL_HF_ID = "CLTL/MedRoBERTa.nl"
MAX_LEN = 512
STRIDE = 128
MAX_STEPS = int(os.environ.get("MAX_STEPS", "1500"))
EVAL_FRACTION = 0.1
# Dry-run guard: cap corpus size so this pass just proves the code path works
# end-to-end (tokenize -> train -> decode -> 3-surface eval) in a couple
# minutes, before spending real quota on the full trial. 0 (falsy) = full corpus.
DOC_LIMIT = int(os.environ.get("DOC_LIMIT", "0"))

OUTPUT_DIR = "/kaggle/working/checkpoints"
REPORT_DIR = "/kaggle/working/reports"
os.makedirs(REPORT_DIR, exist_ok=True)

print(f"=== TRIAL {TRIAL_ID}  address_mode={ADDRESS_MODE}  seed={SEED} ===")

from presidio_analyzer import Pattern, PatternRecognizer  # noqa: E402

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
# --- dutch_regex.py (inlined, unmodified from backend/src/detection/) ------ #
# =========================================================================== #
_MONTHS_NL = (
    "januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|"
    "november|december"
)


def get_dutch_regex_recognizers():
    recognizers = []

    date_patterns = [
        Pattern(name="date_numeric", regex=r"(?<![\d./-])(?:0?[1-9]|[12]\d|3[01])[-/.](?:0?[1-9]|1[0-2])[-/.]\d{2,4}(?!\d)", score=0.6),
        Pattern(name="month_year", regex=r"\b(?:0?[1-9]|1[0-2])[-/]\d{4}\b", score=0.6),
        Pattern(name="date_written", regex=r"\b\d{1,2}\s+(?:" + _MONTHS_NL + r")(?:\s+\d{4})?\b", score=0.75),
        Pattern(name="clock_time", regex=r"\b[0-2]?\d:[0-5]\d\b", score=0.5),
    ]
    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="DATE", patterns=date_patterns,
        context=["datum", "geboren", "geboortedatum", "validatie"]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="AGE",
        patterns=[Pattern(name="age", regex=r"\b\d{1,3}\s*(?:jaar|jr|j\.|-?jarige?)\b", score=0.6)],
        context=["leeftijd", "oud"]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="PHONE",
        patterns=[Pattern(name="phone", regex=r"(?:\+32|\+31|0)[\s./-]?\d(?:[\s./-]?\d){7,8}\b", score=0.7)]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="INSZ",
        patterns=[Pattern(name="insz", regex=r"(?<![\d+])\d{2}[.\-]?\d{2}[.\-]?\d{2}[.\-]?\d{3}[.\-]?\d{2}(?!\d)", score=0.85)],
        context=["insz", "niss", "rijksregister"]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="RIZIV",
        patterns=[
            Pattern(name="riziv_formatted", regex=r"\b\d[.\-]\d{5}[.\-]\d{2}[.\-]\d{3}\b", score=0.85),
            Pattern(name="riziv_bare8", regex=r"(?<![\d.\-])\d{8}(?![\d.\-])", score=0.6),
        ],
        context=["riziv", "inami"]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="BTW_EENHEID",
        patterns=[Pattern(name="btw", regex=r"\bBE\s?0\d{3}[.\s]?\d{3}[.\s]?\d{3}\b", score=0.9)],
        context=["btw", "ondernemingsnummer", "eenheid"]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="EMAIL",
        patterns=[Pattern(name="email", regex=r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", score=0.9)]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="URL",
        patterns=[Pattern(name="url", regex=r"\b(?:https?://|www\.)\S+", score=0.85)]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="IBAN",
        patterns=[Pattern(name="iban", regex=r"\b(?:NL|BE)\d{2}\s?(?:[A-Z0-9]{4}\s?){2,}[A-Z0-9]{1,4}\b", score=0.9)]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="ZIP_CODE",
        patterns=[Pattern(name="zip_city", regex=r"\b[1-9]\d{3}(?=\s+[A-ZÀ-Ý])", score=0.5)]))

    recognizers.append(PatternRecognizer(
        supported_language="nl", supported_entity="STREET",
        patterns=[Pattern(name="street", regex=r"\b[A-ZÀ-Ý][a-zà-ÿ]+(?:\s+[a-zà-ÿ]+)*(?:straat|laan|weg|plein|dreef|steenweg|baan|lei|kaai|markt)\b", score=0.6)]))

    return recognizers


# =========================================================================== #
# --- data_pipeline.py (inlined) --------------------------------------------- #
# =========================================================================== #
DATA_ROOT = os.environ["PII_DATA_ROOT"]
BATCH_FINAL_DIR = os.path.join(DATA_ROOT, "batch_final")
BF_REPORTS_DIR = os.path.join(BATCH_FINAL_DIR, "reports")
BF_GT_DIR = os.path.join(BATCH_FINAL_DIR, "ground_truth")
SYNTHETIC_DIR = os.path.join(DATA_ROOT, "synthetic_reports")
RECOMBINED_DIR = os.path.join(DATA_ROOT, "recombined")
HF_DATASET_PATH = os.path.join(DATA_ROOT, "hf_ner_dataset.jsonl")
LABELED_PATH = os.path.join(DATA_ROOT, "synthetic_reports_labeled.jsonl")
SOURCE_PRIORITY = {"batch_final": 3, "labeled": 2, "hf": 1, "legacy": 0}
AddressMode = Literal["decomposed", "single"]

MAP_BATCH_FINAL = {
    "patient_full_name": "NAME", "patient_first_name": "NAME", "patient_last_name": "NAME",
    "patient_national_register_number": "INSZ", "patient_secondary_record_id": None,
    "referring_doctor_name": "NAME", "sending_doctor_last_name": "NAME",
    "validating_doctor_last_name": "NAME", "cosigning_doctor_name": "NAME",
    "sending_practice_legal_name": "ORGANIZATION", "cosigning_practice_legal_name": "ORGANIZATION",
    "hospital_name": "ORGANIZATION", "specialty_department": None,
    "institution_street_address": None, "institution_street_name": "STREET",
    "institution_house_number": "BUILDING_NUMBER", "institution_postal_code": "ZIP_CODE",
    "institution_city": "CITY", "institution_phone": "PHONE",
    "institution_direct_dial_phone": "PHONE", "institution_website": "URL",
    "report_date": "DATE", "validation_date": "DATE", "validation_time": "DATE",
    "patient_age": "AGE", "patient_dob": "DATE",
}
MAP_LABELED = {
    "PATIENT_NAME": "NAME", "DOCTOR_NAME": "NAME", "RESPONSIBLE_NAME": "NAME",
    "HOSPITAL": "ORGANIZATION", "NATIONAL_ID": "INSZ", "PROVIDER_ID": "RIZIV",
    "ADDRESS": "ADDRESS_COARSE", "PHONE": "PHONE", "EMAIL": "EMAIL",
    "DOSSIER_NUMBER": None, "DATE": "DATE", "SPECIALTY": None, "AGE": "AGE",
    "MEDICATION": None, "CLINICAL_NOTE": None,
}
MAP_HF = {
    "PATIENT_NAME": "NAME", "DOCTOR_NAME": "NAME",
    "BELGIAN_INSZ": "INSZ", "BELGIAN_RIZIV": "RIZIV", "HOSPITAL": "ORGANIZATION",
}
MAP_LEGACY = {
    "patient_naam": "NAME", "insz": "INSZ", "riziv_behandelaar": "RIZIV",
    "arts_naam": "NAME", "arts_verwijzer": "NAME", "ziekenhuis": "ORGANIZATION",
    "adres": "ADDRESS_COARSE", "telefoon": "PHONE", "email": "EMAIL",
}

REGEX_PERMANENT_LABELS = ("INSZ", "RIZIV", "URL", "EMAIL", "BTW_EENHEID")


def strip_for_training(records):
    out = []
    for r in records:
        kept = [e for e in r["entities"] if e["label"] not in REGEX_PERMANENT_LABELS]
        out.append({**r, "entities": kept})
    return out


def find_all_occurrences(text, query):
    out, start = [], 0
    while True:
        idx = text.find(query, start)
        if idx == -1:
            break
        out.append((idx, idx + len(query)))
        start = idx + len(query)
    return out


def variant_id_from_name(name):
    m = re.search(r"(variant_\d+)", name)
    return m.group(1) if m else name


ADDRESS_RE = re.compile(
    r"(?P<street>[A-Za-zÀ-ÿ.'\-]+(?:\s+[A-Za-zÀ-ÿ.'\-]+)*?)"
    r"\s+(?P<num>\d+\s?[A-Za-z]?)"
    r"\s*,?\s*"
    r"(?P<zip>\d{4})"
    r"\s*,?\s*(?P<city>[A-Za-zÀ-ÿ.'\-]+(?:[\s-]+[A-Za-zÀ-ÿ.'\-]+)*)"
)


def split_address(text, start, end):
    m = ADDRESS_RE.search(text[start:end])
    if not m:
        return []
    out = []
    for grp, lab in (("street", "STREET"), ("num", "BUILDING_NUMBER"), ("zip", "ZIP_CODE"), ("city", "CITY")):
        a, b = m.span(grp)
        if a >= 0:
            out.append({"start": start + a, "end": start + b, "label": lab})
    return out


_ADDRESS_MERGE_GAP = 60


def merge_address_components(entities):
    comp_labels = {"STREET", "BUILDING_NUMBER", "ZIP_CODE", "CITY"}
    comps = sorted((e for e in entities if e["label"] in comp_labels), key=lambda e: e["start"])
    others = [e for e in entities if e["label"] not in comp_labels]
    merged, cluster = [], []
    for e in comps:
        if cluster and e["start"] - cluster[-1]["end"] > _ADDRESS_MERGE_GAP:
            merged.append(cluster)
            cluster = []
        cluster.append(e)
    if cluster:
        merged.append(cluster)
    out = list(others)
    for cluster in merged:
        out.append({"start": min(c["start"] for c in cluster), "end": max(c["end"] for c in cluster), "label": "ADDRESS"})
    return out


def load_records(address_mode="decomposed"):
    records = []

    if os.path.isdir(BF_REPORTS_DIR) and os.path.isdir(BF_GT_DIR):
        for gt_path in sorted(glob.glob(os.path.join(BF_GT_DIR, "*.json"))):
            doc_id = os.path.splitext(os.path.basename(gt_path))[0]
            rpt_path = os.path.join(BF_REPORTS_DIR, doc_id + ".txt")
            if not os.path.exists(rpt_path):
                continue
            with open(rpt_path, encoding="utf-8") as f:
                text = f.read()
            with open(gt_path, encoding="utf-8") as f:
                gt = json.load(f)
            ents = []
            for e in gt.get("pii_entities", []):
                canon = MAP_BATCH_FINAL.get(e["category"])
                if not canon:
                    continue
                for span in e.get("spans", []):
                    ents.append({"start": span[0], "end": span[1], "label": canon})
            if address_mode == "single":
                ents = merge_address_components(ents)
            records.append({"id": doc_id, "source": "batch_final", "group_key": "bf::" + doc_id,
                             "text": text, "entities": ents})

    if os.path.exists(LABELED_PATH):
        with open(LABELED_PATH, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                text = d["source_text"]
                ents = []
                for e in d.get("privacy_mask", []):
                    canon = MAP_LABELED.get(e["label"])
                    if not canon:
                        continue
                    if canon == "ADDRESS_COARSE":
                        if address_mode == "decomposed":
                            ents.extend(split_address(text, e["start"], e["end"]))
                        else:
                            ents.append({"start": e["start"], "end": e["end"], "label": "ADDRESS"})
                        continue
                    ents.append({"start": e["start"], "end": e["end"], "label": canon})
                gid = "variant::" + variant_id_from_name(d.get("file", ""))
                records.append({"id": d.get("file", ""), "source": "labeled", "group_key": gid,
                                 "text": text, "entities": ents})

    if os.path.exists(HF_DATASET_PATH):
        with open(HF_DATASET_PATH, encoding="utf-8") as f:
            for i, line in enumerate(f):
                d = json.loads(line)
                text = d["text"]
                ents = []
                for e in d.get("spans", []):
                    canon = MAP_HF.get(e["label"])
                    if not canon:
                        continue
                    ents.append({"start": e["start"], "end": e["end"], "label": canon})
                sig = hashlib.md5(re.sub(r"\W+", "", text).lower().encode()).hexdigest()[:12]
                records.append({"id": f"hf_{i}", "source": "hf", "group_key": "hf::" + sig,
                                 "text": text, "entities": ents})

    if os.path.isdir(SYNTHETIC_DIR) and os.path.isdir(RECOMBINED_DIR):
        for rpt in sorted(f for f in os.listdir(SYNTHETIC_DIR) if f.endswith("_report.txt")):
            base = rpt.replace("_report.txt", "")
            jpath = os.path.join(RECOMBINED_DIR, base + ".json")
            if not os.path.exists(jpath):
                continue
            with open(os.path.join(SYNTHETIC_DIR, rpt), encoding="utf-8") as f:
                text = f.read()
            with open(jpath, encoding="utf-8") as f:
                pii = json.load(f).get("pii", {})
            ents = []
            for key, value in pii.items():
                canon = MAP_LEGACY.get(key)
                if not canon or not isinstance(value, str) or len(value.strip()) < 4:
                    continue
                if canon == "ADDRESS_COARSE":
                    for s, e_ in find_all_occurrences(text, value):
                        if address_mode == "decomposed":
                            ents.extend(split_address(text, s, e_))
                        else:
                            ents.append({"start": s, "end": e_, "label": "ADDRESS"})
                    continue
                for s, e_ in find_all_occurrences(text, value):
                    ents.append({"start": s, "end": e_, "label": canon})
            records.append({"id": base, "source": "legacy", "group_key": "variant::" + base,
                             "text": text, "entities": ents})

    return records


def resolve_overlaps(entities):
    ents = sorted(entities, key=lambda x: (-(x["end"] - x["start"]), x["start"]))
    kept = []
    for e in ents:
        if any(not (e["end"] <= k["start"] or e["start"] >= k["end"]) for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda x: x["start"])


def dedup_and_clean(records):
    for r in records:
        r["entities"] = resolve_overlaps(r["entities"])
    best = {}
    for r in records:
        g = r["group_key"]
        if g not in best or SOURCE_PRIORITY[r["source"]] > SOURCE_PRIORITY[best[g]["source"]]:
            best[g] = r
    records = list(best.values())
    return [r for r in records if r["text"].strip()]


def build_dataset(address_mode="decomposed"):
    return dedup_and_clean(load_records(address_mode))


# =========================================================================== #
# --- eval_metrics.py (inlined) ---------------------------------------------- #
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


def baseline_empty_scores(golds):
    doc_scores = [score_document(g, [], "strict") for g in golds]
    return em_aggregate(doc_scores)


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
# --- Main: load, split, train, decode, 3-surface eval ---------------------- #
# =========================================================================== #
records = build_dataset(ADDRESS_MODE)
rng = random.Random(SEED)
shuffled = records[:]
rng.shuffle(shuffled)
if DOC_LIMIT:
    shuffled = shuffled[:DOC_LIMIT]
    print(f"DRY RUN: capped corpus to {DOC_LIMIT} docs")
n_eval = max(1, int(len(shuffled) * EVAL_FRACTION))
eval_recs = shuffled[:n_eval]
train_recs_full = shuffled[n_eval:]
train_recs = strip_for_training(train_recs_full)

print(f"records total={len(records)}  train={len(train_recs)}  eval={len(eval_recs)}")

model_labels = sorted({e["label"] for r in train_recs for e in r["entities"]})
label_list = ["O"] + [f"{p}-{c}" for c in model_labels for p in ("B", "I")]
label2id = {l: i for i, l in enumerate(label_list)}
id2label = {i: l for i, l in enumerate(label_list)}
print(f"model_labels ({len(model_labels)}): {model_labels}")

with open(os.path.join(REPORT_DIR, "trial_config.json"), "w") as f:
    json.dump({"trial_id": TRIAL_ID, "address_mode": ADDRESS_MODE, "seed": SEED,
               "model_labels": model_labels, "max_steps": MAX_STEPS,
               "n_train": len(train_recs), "n_eval": len(eval_recs)}, f, indent=2)

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
                lab_ids.append(-100 if (a == 0 and b == 0) else label2id.get(ch[a], label2id["O"]))
            all_labels.append(lab_ids)
        tok["labels"] = all_labels
    return tok, window_meta


print("Tokenizing train split...")
train_enc, _ = tokenize_split(train_recs, for_training=True)
print("Tokenizing eval split...")
eval_enc, eval_window_meta = tokenize_split(eval_recs, for_training=False)


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


train_dataset = WindowDataset(train_enc, has_labels=True)
eval_dataset_for_predict = WindowDataset(eval_enc, has_labels=False)

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_HF_ID, num_labels=len(label_list), id2label=id2label, label2id=label2id
)

ta_params = inspect.signature(TrainingArguments.__init__).parameters
eval_key = "eval_strategy" if "eval_strategy" in ta_params else "evaluation_strategy"
SAVE_STEPS = 250
# Keep every checkpoint (not just the last 2) so the post-training overfitting-curve
# pass below can reload each one and check whether eval F1 plateaus/degrades while
# train loss keeps dropping -- deleted wholesale at the end regardless (never leaves
# this session).
N_CHECKPOINTS = MAX_STEPS // SAVE_STEPS + 2
ta_kwargs = dict(
    output_dir=OUTPUT_DIR, learning_rate=2e-5, per_device_train_batch_size=16,
    max_steps=MAX_STEPS, save_strategy="steps", save_steps=SAVE_STEPS, save_total_limit=N_CHECKPOINTS,
    logging_steps=50, fp16=torch.cuda.is_available(), report_to="none", push_to_hub=False,
)
ta_kwargs[eval_key] = "no"
training_args = TrainingArguments(**ta_kwargs)

tr_params = inspect.signature(Trainer.__init__).parameters
tok_kwarg = {"processing_class": tokenizer} if "processing_class" in tr_params else {"tokenizer": tokenizer}
trainer = Trainer(model=model, args=training_args, train_dataset=train_dataset, **tok_kwarg)

last_checkpoint = get_last_checkpoint(OUTPUT_DIR) if os.path.isdir(OUTPUT_DIR) else None
if last_checkpoint:
    print(f"Resuming from checkpoint: {last_checkpoint}")
trainer.train(resume_from_checkpoint=last_checkpoint)

def decode_model_preds(pred_ids):
    per_doc_spans = {i: [] for i in range(len(eval_recs))}
    for window_idx, (doc_idx, offsets) in enumerate(eval_window_meta):
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
                    per_doc_spans[doc_idx].append({"start": cur_start, "end": cur_end, "label": cur_label})
                    cur_label = None
                continue
            if prefix == "B" or cur_label != lab:
                if cur_label is not None:
                    per_doc_spans[doc_idx].append({"start": cur_start, "end": cur_end, "label": cur_label})
                cur_label, cur_start, cur_end = lab, a, b
            else:
                cur_end = b
        if cur_label is not None:
            per_doc_spans[doc_idx].append({"start": cur_start, "end": cur_end, "label": cur_label})
    return [resolve_overlaps(per_doc_spans[i]) for i in range(len(eval_recs))]


print("Running predictions on eval split...")
raw_preds = trainer.predict(eval_dataset_for_predict).predictions
pred_ids = np.argmax(raw_preds, axis=2)
model_preds = decode_model_preds(pred_ids)

recognizers = get_dutch_regex_recognizers()


# ZIP_CODE and STREET rely on [A-ZÀ-Ý] to require a capital letter -- that's
# the mechanism distinguishing a proper noun (city/street name) from ordinary
# lowercase text. Running case-insensitively silently defeats that check and
# was confirmed (via personal_finetune/regex_edge_cases.py) to make both
# patterns wildly over-match. Every other recognizer here is digit/symbol
# based, where case carries no meaning, so IGNORECASE is safe there.
_CASE_SENSITIVE_ENTITIES = {"ZIP_CODE", "STREET"}


def regex_predict(text):
    spans = []
    for rec in recognizers:
        entity = rec.supported_entities[0]
        flags = 0 if entity in _CASE_SENSITIVE_ENTITIES else re.IGNORECASE
        for pat in rec.patterns:
            for m in re.finditer(pat.regex, text, flags):
                spans.append((m.start(), m.end(), entity))
    return spans


regex_preds = [regex_predict(r["text"]) for r in eval_recs]

# Stage 3 ablation (run on trials s1-t2/s1-t2b) confirmed regex actively hurts these
# 5 hybrid labels in the full-pipeline merge (model already owns them at ~0.99+ F1
# alone; naive regex+model merge dragged full-pipeline F1 down to 0.87). Keep regex
# predictions for the regex_only surface's own reporting, but never let them compete
# with the model in the merged full-pipeline surface.
REGEX_MERGE_EXCLUDE = {"AGE", "DATE", "PHONE", "STREET", "ZIP_CODE"}
regex_preds_for_merge = [[s for s in doc if s[2] not in REGEX_MERGE_EXCLUDE] for doc in regex_preds]

_LABEL_PRIORITY = {
    "EMAIL": 10, "URL": 10, "IBAN": 9, "INSZ": 9, "RIZIV": 9, "BTW_EENHEID": 9,
    "DATE": 8, "PHONE": 7, "ZIP_CODE": 6, "BUILDING_NUMBER": 6, "STREET": 6,
    "CITY": 6, "ADDRESS": 6, "AGE": 5, "NAME": 4, "ORGANIZATION": 3,
}


def merge_full_pipeline(model_spans, regex_spans):
    combined = [(s["start"], s["end"], s["label"]) for s in model_spans] + regex_spans

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


full_preds = [merge_full_pipeline(model_preds[i], regex_preds_for_merge[i]) for i in range(len(eval_recs))]

REGEX_COVERABLE = {"DATE", "AGE", "PHONE"} | set(REGEX_PERMANENT_LABELS)


def to_spans(entities):
    return [(e["start"], e["end"], e["label"]) for e in entities]


all_gold = [to_spans(r["entities"]) for r in eval_recs]
model_gold = [[s for s in g if s[2] in model_labels] for g in all_gold]
regex_gold = [[s for s in g if s[2] in REGEX_COVERABLE] for g in all_gold]

print("Building per-checkpoint overfitting curve (model_only surface, strict+relaxed)...")
checkpoint_curve = []
ckpt_dirs = sorted(
    glob.glob(os.path.join(OUTPUT_DIR, "checkpoint-*")),
    key=lambda p: int(p.rsplit("-", 1)[-1]),
)
for ckpt_dir in ckpt_dirs:
    step = int(ckpt_dir.rsplit("-", 1)[-1])
    ckpt_model = AutoModelForTokenClassification.from_pretrained(ckpt_dir)
    ckpt_trainer = Trainer(model=ckpt_model, args=training_args, **tok_kwarg)
    ckpt_pred_ids = np.argmax(ckpt_trainer.predict(eval_dataset_for_predict).predictions, axis=2)
    ckpt_model_preds = decode_model_preds(ckpt_pred_ids)
    ckpt_pred_spans = [[(s["start"], s["end"], s["label"]) for s in ds] for ds in ckpt_model_preds]
    row = {"step": step}
    for mode in ("strict", "relaxed"):
        r = run_eval(model_gold, ckpt_pred_spans, "model_only", mode, compute_ci=False)
        row[mode] = {"precision": r.overall_score.precision, "recall": r.overall_score.recall, "f1": r.overall_score.f1}
    checkpoint_curve.append(row)
    print(f"  step={step}  strict_f1={row['strict']['f1']:.3f}  relaxed_f1={row['relaxed']['f1']:.3f}")
    del ckpt_model, ckpt_trainer

with open(os.path.join(REPORT_DIR, "checkpoint_curve.json"), "w") as f:
    json.dump(checkpoint_curve, f, indent=2)
model_pred_spans = [[(s["start"], s["end"], s["label"]) for s in ds] for ds in model_preds]

reports = {}
for mode in ("strict", "relaxed"):
    reports[f"model_only_{mode}"] = run_eval(model_gold, model_pred_spans, "model_only", mode)
    reports[f"regex_only_{mode}"] = run_eval(regex_gold, regex_preds, "regex_only", mode)
    reports[f"full_pipeline_{mode}"] = run_eval(all_gold, full_preds, "full_pipeline", mode)

for r in reports.values():
    print_report(r)
    print()


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
    json.dump({k: report_to_json(v) for k, v in reports.items()}, f, indent=2)

# Raw per-doc spans (no text, just offsets+labels) so regex-ownership / merge-strategy
# ablation can be re-run post-hoc, locally, against these cached predictions --
# without spending another GPU trial to retrain the model.
with open(os.path.join(REPORT_DIR, "raw_predictions.json"), "w") as f:
    json.dump({
        "doc_ids": [r["id"] for r in eval_recs],
        "model_labels": model_labels,
        "regex_coverable": sorted(REGEX_COVERABLE),
        "label_priority": _LABEL_PRIORITY,
        "gold": [list(g) for g in all_gold],
        "model_preds": [list(map(list, mp)) for mp in model_pred_spans],
        "regex_preds": [list(map(list, rp)) for rp in regex_preds],
    }, f)

# Final winning model -- the ONE persistent artifact this personal track is
# allowed to push anywhere (private HF Hub repo only, never Drive, never the
# team's shared storage/MLflow). Everything else in this session (checkpoints,
# reports) stays ephemeral to this Kaggle run.
#
# Token intentionally NOT hardcoded (an earlier version of this script did,
# and that token had to be revoked after it got caught by GitHub push
# protection) -- read it from a mounted private Kaggle dataset instead, same
# pattern as kaggle_push_to_hf/push_to_hf.py.
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_REPO_ID = "farahelmashad/personal-pii-medroberta-decomposed-v1"
PUSH_TO_HUB = os.environ.get("PUSH_TO_HUB", "true").lower() == "true"

if PUSH_TO_HUB:
    print(f"Pushing final model to private HF Hub repo: {HF_REPO_ID}")
    model.push_to_hub(HF_REPO_ID, token=HF_TOKEN, private=True, commit_message=f"trial={TRIAL_ID}")
    tokenizer.push_to_hub(HF_REPO_ID, token=HF_TOKEN, private=True, commit_message=f"trial={TRIAL_ID}")
    card = (
        f"# {HF_REPO_ID}\n\n"
        "Personal exploratory PII-detection fine-tune of CLTL/MedRoBERTa.nl. "
        "NOT the team's shared pii-masking-service model -- separate personal track.\n\n"
        f"- trial_id: {TRIAL_ID}\n"
        f"- address_mode: {ADDRESS_MODE}\n"
        f"- seed: {SEED}\n"
        f"- max_steps: {MAX_STEPS}\n"
        f"- model_labels: {model_labels}\n\n"
        "Regex-permanent labels (never trained, handled by regex only in the full "
        "pipeline): INSZ, RIZIV, BTW_EENHEID, EMAIL, URL.\n\n"
        "Full-pipeline merge must exclude regex candidates for AGE/DATE/PHONE/STREET/"
        "ZIP_CODE -- letting regex compete with this model for those labels was shown "
        "to drag full-pipeline strict F1 from ~0.99 down to ~0.87 (Stage 3 ablation).\n"
    )
    with open(os.path.join(REPORT_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write(card)
    from huggingface_hub import upload_file
    upload_file(path_or_fileobj=os.path.join(REPORT_DIR, "README.md"), path_in_repo="README.md",
                repo_id=HF_REPO_ID, token=HF_TOKEN, commit_message="Add model card")
    print("Push complete.")

# Never let a full model checkpoint end up in the kernel's Output bundle --
# reports/ (small JSON) is the only thing that should ever leave this session.
shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

print("DONE.")
