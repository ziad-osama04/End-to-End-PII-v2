"""Quantize pii-tamerbert-v5 to ONNX INT8 and validate size/latency/accuracy.

Pulls the final checkpoint directly from HF Hub (never touches the laptop),
exports to ONNX, applies dynamic INT8 weight quantization, then re-runs the
SAME eval methodology used throughout the fine-tuning track (sliding-window
tokenization, patterns.py regex layer, merge_drop_all) against both the fp32
and int8 ONNX models on identical eval sets, so size/latency numbers are
never reported without an accuracy number sitting next to them.

The quantized model is pushed to a new private HF repo at the end, again
without any weights touching local disk -- only the small JSON report
leaves this kernel via reports/.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import subprocess
import sys
import time
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "optimum[onnxruntime]", "onnxruntime"],
    check=True,
)

os.environ.setdefault(
    "PII_DATA_ROOT",
    "/kaggle/input/datasets/farahelmashad/personal-pii-tamerbert-generalization-data",
)

REPO_ID = "farahelmashad/pii-medroberta-nl-v2"
QUANTIZED_REPO_ID = "farahelmashad/pii-medroberta-nl-v2-int8-onnx"
MAX_LEN = 512
STRIDE = 128
LATENCY_TRIALS = 50

WORK = "/kaggle/working"
FP32_DIR = os.path.join(WORK, "onnx_fp32")
INT8_DIR = os.path.join(WORK, "onnx_int8")
REPORT_DIR = os.path.join(WORK, "reports")
for d in (FP32_DIR, INT8_DIR, REPORT_DIR):
    os.makedirs(d, exist_ok=True)


def find_one(name, is_dir=False):
    for root, dirs, files in os.walk("/kaggle/input"):
        if is_dir and name in dirs:
            return os.path.join(root, name)
        if not is_dir and name in files:
            return os.path.join(root, name)
    raise FileNotFoundError(f"{name!r} not found anywhere under /kaggle/input")


TOKEN_PATH = find_one("token.txt")
with open(TOKEN_PATH, encoding="utf-8") as f:
    HF_TOKEN = f.read().strip()

import numpy as np  # noqa: E402
from huggingface_hub import login  # noqa: E402
from transformers import AutoTokenizer  # noqa: E402
import onnxruntime as ort  # noqa: E402
from onnxruntime.quantization import quantize_dynamic, QuantType  # noqa: E402
from optimum.onnxruntime import ORTModelForTokenClassification  # noqa: E402

login(token=HF_TOKEN)

# =========================================================================== #
# --- Export + quantize ------------------------------------------------------ #
# =========================================================================== #
print(f"=== Exporting {REPO_ID} to ONNX (fp32) ===")
t0 = time.time()
ort_model = ORTModelForTokenClassification.from_pretrained(REPO_ID, export=True, token=HF_TOKEN)
ort_model.save_pretrained(FP32_DIR)
tokenizer = AutoTokenizer.from_pretrained(REPO_ID, token=HF_TOKEN, add_prefix_space=True)
tokenizer.save_pretrained(FP32_DIR)
id2label = {int(k): v for k, v in ort_model.config.id2label.items()}
label2id = {v: k for k, v in id2label.items()}
model_labels = sorted({v[2:] for v in id2label.values() if v != "O"})
print(f"export took {time.time() - t0:.1f}s  model_labels={model_labels}")

import glob  # noqa: E402
fp32_onnx_path = glob.glob(os.path.join(FP32_DIR, "*.onnx"))[0]
fp32_size = os.path.getsize(fp32_onnx_path)

print("=== Quantizing to dynamic INT8 ===")
t0 = time.time()
int8_onnx_path = os.path.join(INT8_DIR, "model.onnx")
quantize_dynamic(fp32_onnx_path, int8_onnx_path, weight_type=QuantType.QInt8)
tokenizer.save_pretrained(INT8_DIR)
ort_model.config.save_pretrained(INT8_DIR)
int8_size = os.path.getsize(int8_onnx_path)
print(f"quantize took {time.time() - t0:.1f}s")
print(f"fp32 size: {fp32_size / 1e6:.1f} MB   int8 size: {int8_size / 1e6:.1f} MB   "
      f"reduction: {(1 - int8_size / fp32_size) * 100:.1f}%")

sess_fp32 = ort.InferenceSession(fp32_onnx_path, providers=["CPUExecutionProvider"])
sess_int8 = ort.InferenceSession(int8_onnx_path, providers=["CPUExecutionProvider"])
onnx_input_names = {i.name for i in sess_fp32.get_inputs()}


# =========================================================================== #
# --- patterns.py (inlined, same as train_and_eval.py) ----------------------- #
# =========================================================================== #
RING = "°º˚⁰ᵒ∘⚬"
DASHES = "-‐‑‒–—−﹣"
SPACES = "     　"
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
P["INSZ"] = re.compile(r"(?<![\d.\-/])(\d{2})[.\-/ ]?(\d{2})[.\-/ ]?(\d{2})"
                       r"[-.\s]?(\d{3})[.\-/ ]?(\d{2})(?!\d)")
P["RIZIV"] = re.compile(r"(?<![\d.\-/])(\d)[-.\s]?(\d{5})[-.\s]?(\d{2})"
                        r"[-.\s]?(\d{3})(?!\d)")
P["BTW_EENHEID"] = re.compile(
    r"\bBE\s?([01])[.\s]?(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})(?!\d)", re.I)
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


def valid_btw(digits):
    if len(digits) != 10 or digits[0] not in "01":
        return False
    return 97 - (int(digits[:8]) % 97) == int(digits[8:])


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


ORDER = [
    ("INSZ", "INSZ"), ("RIZIV", "RIZIV"), ("BTW_EENHEID", "BTW_EENHEID"),
    ("EMAIL", "EMAIL"), ("URL", "URL"),
    ("TELEFOON", "PHONE"),
    ("DOB", "DATE"),
    ("DATE_ISO", "DATE"), ("DATE_ISO_SLASH", "DATE"), ("DATE_DMY", "DATE"), ("DATE_DMY_2YR", "DATE"),
    ("DATE_TEXT", "DATE"), ("DATE_YM_REV", "DATE"), ("DATE_MY", "DATE"),
    ("DATE_COMPACT", "DATE"), ("DATE_NOYEAR", "DATE"),
    ("AGE", "AGE"),
]


def patterns_detect(text):
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
            elif label == "BTW_EENHEID":
                digits = re.sub(r"\D", "", surface)[-10:]
                ok = len(digits) == 10 and valid_btw(digits)
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


REGEX_PERMANENT_LABELS = ("INSZ", "RIZIV", "URL", "EMAIL", "BTW_EENHEID")
HYBRID_LABELS = {"AGE", "DATE", "PHONE"}
_LABEL_PRIORITY = {"INSZ": 9, "RIZIV": 9, "URL": 10, "EMAIL": 10, "BTW_EENHEID": 9,
                    "DATE": 8, "PHONE": 7, "AGE": 5, "NAME": 4, "ORGANIZATION": 4, "ADDRESS": 6}


def merge_drop_all(model_spans, regex_spans):
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


# =========================================================================== #
# --- minimal eval_metrics ---------------------------------------------------- #
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


def score_document(gold, pred):
    per_label = defaultdict(lambda: LabelScore(label=""))
    matched_gold, matched_pred = set(), set()
    for pi, p in enumerate(pred):
        for gi, g in enumerate(gold):
            if gi in matched_gold:
                continue
            if p == g:
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


def run_eval(golds, preds):
    doc_scores = [score_document(g, p) for g, p in zip(golds, preds)]
    totals = em_aggregate(doc_scores)
    return totals, em_overall(totals)


# =========================================================================== #
# --- Data loading + tokenization -------------------------------------------- #
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


eval_sets = {
    "indist": load_split("eval_indist_org.jsonl"),
    "real": load_split("eval_real_org.jsonl"),
    "ood": load_split("ood_docs.jsonl"),
    "ood_v2": load_split("ood_docs_v2.jsonl"),
    "ood_v3": load_split("ood_docs_v3.jsonl"),
    "ood_v5": load_split("ood_docs_v5.jsonl"),
    "ood_v6": load_split("ood_docs_v6.jsonl"),
}
print("eval sizes:", {k: len(v) for k, v in eval_sets.items()})


def tokenize_split(recs):
    texts = [r["text"] for r in recs]
    tok = tokenizer(texts, truncation=True, max_length=MAX_LEN, stride=STRIDE,
                     return_overflowing_tokens=True, return_offsets_mapping=True, padding="max_length")
    sample_map = tok.pop("overflow_to_sample_mapping")
    offset_batch = tok.pop("offset_mapping")
    window_meta = [(sample_map[i], offset_batch[i]) for i in range(len(sample_map))]
    return tok, window_meta


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


def run_onnx(session, enc, batch_size=16):
    n = len(enc["input_ids"])
    all_logits = []
    for start in range(0, n, batch_size):
        batch = {k: np.array(v[start:start + batch_size], dtype=np.int64)
                  for k, v in enc.items() if k in onnx_input_names}
        logits = session.run(None, batch)[0]
        all_logits.append(logits)
    return np.concatenate(all_logits, axis=0)


def eval_model(session, name):
    print(f"\n########## {name} ##########")
    all_reports = {}
    for surface, recs in eval_sets.items():
        enc, window_meta = tokenize_split(recs)
        logits = run_onnx(session, enc)
        pred_ids = np.argmax(logits, axis=2)
        model_preds = decode_model_preds(pred_ids, window_meta, len(recs))
        regex_preds = [patterns_detect(r["text"]) for r in recs]
        full_preds = [merge_drop_all(model_preds[i], regex_preds[i]) for i in range(len(recs))]

        all_gold = [[(e["start"], e["end"], e["label"]) for e in r["entities"]] for r in recs]
        totals, overall = run_eval(all_gold, full_preds)
        all_reports[surface] = {
            "overall": {"precision": overall.precision, "recall": overall.recall,
                        "f1": overall.f1, "tp": overall.tp, "fp": overall.fp, "fn": overall.fn},
            "per_label": {lab: {"precision": sc.precision, "recall": sc.recall,
                                 "f1": sc.f1, "support": sc.support} for lab, sc in totals.items()},
        }
        o = all_reports[surface]["overall"]
        print(f"  {surface:10s} full_pipeline_dropall_strict  "
              f"P={o['precision']:.3f} R={o['recall']:.3f} F1={o['f1']:.3f}")
    return all_reports


# =========================================================================== #
# --- Latency benchmark ------------------------------------------------------- #
# =========================================================================== #
def benchmark_latency(session, name):
    sample_text = eval_sets["real"][0]["text"]
    enc = tokenizer([sample_text], truncation=True, max_length=MAX_LEN,
                     padding="max_length", return_tensors="np")
    batch = {k: v.astype(np.int64) for k, v in enc.items() if k in onnx_input_names}
    for _ in range(3):  # warmup
        session.run(None, batch)
    times = []
    for _ in range(LATENCY_TRIALS):
        t0 = time.perf_counter()
        session.run(None, batch)
        times.append((time.perf_counter() - t0) * 1000)
    mean_ms = statistics.mean(times)
    p95_ms = sorted(times)[int(0.95 * len(times)) - 1]
    print(f"  {name}: mean={mean_ms:.2f}ms  p95={p95_ms:.2f}ms  (single 512-token window, batch=1, CPU)")
    return {"mean_ms": mean_ms, "p95_ms": p95_ms}


print("\n=== Latency benchmark (single-window, batch=1, CPU) ===")
latency_fp32 = benchmark_latency(sess_fp32, "fp32 onnx")
latency_int8 = benchmark_latency(sess_int8, "int8 onnx")

print("\n=== Accuracy: fp32 ONNX ===")
reports_fp32 = eval_model(sess_fp32, "fp32 onnx")
print("\n=== Accuracy: int8 ONNX ===")
reports_int8 = eval_model(sess_int8, "int8 onnx")

summary = {
    "repo_id": REPO_ID,
    "size": {"fp32_bytes": fp32_size, "int8_bytes": int8_size,
              "reduction_pct": (1 - int8_size / fp32_size) * 100},
    "latency": {"fp32": latency_fp32, "int8": latency_int8,
                "speedup_x": latency_fp32["mean_ms"] / latency_int8["mean_ms"]},
    "accuracy": {"fp32": reports_fp32, "int8": reports_int8},
}
with open(os.path.join(REPORT_DIR, "quantization_report.json"), "w") as f:
    json.dump(summary, f, indent=2)

print("\n=== SUMMARY ===")
print(f"size: {fp32_size/1e6:.1f}MB -> {int8_size/1e6:.1f}MB "
      f"({summary['size']['reduction_pct']:.1f}% smaller)")
print(f"latency: {latency_fp32['mean_ms']:.2f}ms -> {latency_int8['mean_ms']:.2f}ms "
      f"({summary['latency']['speedup_x']:.2f}x)")

# =========================================================================== #
# --- Push quantized model to HF Hub ------------------------------------------ #
# =========================================================================== #
print(f"\n=== Pushing quantized model to {QUANTIZED_REPO_ID} ===")
from huggingface_hub import HfApi  # noqa: E402
api = HfApi()
api.create_repo(QUANTIZED_REPO_ID, private=True, exist_ok=True, token=HF_TOKEN)
api.upload_folder(folder_path=INT8_DIR, repo_id=QUANTIZED_REPO_ID, token=HF_TOKEN)
print(f"DONE: pushed to https://huggingface.co/{QUANTIZED_REPO_ID} (private)")
