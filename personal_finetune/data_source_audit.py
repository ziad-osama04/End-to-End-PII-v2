"""Cross-source data-quality audit: format diversity, checksum validity, and
hard-negative surface presence, for every PII data source we have access to.

Sources audited:
  - new_data/{batch_final, labeled, hf, legacy}   (our current training corpus)
  - TamerBERT/dataset_500.jsonl, train.jsonl        (newer sibling generator)
  - TamerBERT/org_data_filled_labeled.jsonl         (the only REAL-structure
    ground truth we have -- 5 docs, used as the reference to score against,
    not as a training source)

Reuses patterns.py's real mod-97 checksum validators rather than re-deriving
them, since those are already tested (70/70 self-test) against real surfaces.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "TamerBERT", "TamerBERT"))
sys.path.insert(0, os.path.join(ROOT, "personal_finetune"))

from patterns import valid_insz, valid_riziv  # noqa: E402
import data_pipeline as dp  # noqa: E402


def classify_insz(s):
    digits = re.sub(r"\D", "", s)
    if "." in s and "-" in s:
        return "dotted-dashed"
    if "." in s:
        return "dotted"
    if " " in s:
        return "spaced"
    if s == digits:
        return "bare"
    return "other"


def classify_riziv(s):
    digits = re.sub(r"\D", "", s)
    if "-" in s:
        return "dashed"
    if " " in s:
        return "spaced"
    if s == digits:
        return "bare"
    return "other"


def classify_phone(s):
    has_intl = bool(re.match(r"\s*\+3[12]", s))
    has_trunk_marker = "(0)" in s
    sep = "space" if " " in s else ("slash" if "/" in s else ("dot" if "." in s else ("dash" if "-" in s else "none")))
    return f"{'intl' if has_intl else 'national'}{'+trunk' if has_trunk_marker else ''}/{sep}"


def classify_date(s):
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{2,4}", s):
        return "dd/mm/yyyy"
    if re.fullmatch(r"\d{1,2}-\d{1,2}-\d{2,4}", s):
        return "dd-mm-yyyy"
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", s):
        return "yyyy-mm-dd (iso)"
    if re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{2,4}", s):
        return "dd.mm.yyyy"
    if re.fullmatch(r"\d{1,2}/\d{4}", s) or re.fullmatch(r"\d{1,2}-\d{4}", s):
        return "mm/yyyy"
    if re.search(r"[A-Za-zÀ-ÿ]", s):
        return "written (month name)"
    return "other"


def classify_address(s):
    has_bus = bool(re.search(r"\bbus\b", s, re.I))
    has_floor = bool(re.search(r"verdieping", s, re.I))
    is_pobox = bool(re.search(r"\bpostbus\b", s, re.I))
    if is_pobox:
        return "postbus (PO box)"
    if has_bus:
        return "street+busnr"
    if has_floor:
        return "street+floor"
    return "street+number, plain"


CLASSIFIERS = {
    "INSZ": classify_insz, "RIZIV": classify_riziv, "PHONE": classify_phone,
    "DATE": classify_date, "ADDRESS": classify_address,
}


def audit_records(name, records, text_key="text", spans_key="spans", label_key="label",
                   start_key="start", end_key="end"):
    n_docs = len(records)
    label_counts = Counter()
    format_variants = defaultdict(Counter)
    insz_valid = insz_total = 0
    riziv_valid = riziv_total = 0
    total_chars = 0
    for r in records:
        text = r[text_key]
        total_chars += len(text)
        spans = r[spans_key]
        for sp in spans:
            lab = sp[label_key]
            s, e = sp[start_key], sp[end_key]
            surface = text[s:e]
            label_counts[lab] += 1
            if lab in CLASSIFIERS:
                format_variants[lab][CLASSIFIERS[lab](surface)] += 1
            if lab == "INSZ":
                insz_total += 1
                ok, _, _ = valid_insz(re.sub(r"\D", "", surface))
                insz_valid += ok
            elif lab == "RIZIV":
                riziv_total += 1
                digits = re.sub(r"\D", "", surface)
                if len(digits) == 11:
                    riziv_valid += valid_riziv(digits)

    print(f"\n{'=' * 90}\n{name}  ({n_docs} docs, avg {total_chars // max(1, n_docs)} chars/doc)")
    print(f"labels: {dict(label_counts)}")
    if insz_total:
        print(f"INSZ checksum-valid: {insz_valid}/{insz_total} ({insz_valid/insz_total:.1%})")
    if riziv_total:
        print(f"RIZIV checksum-valid (of 11-digit forms): {riziv_valid}/{riziv_total} ({riziv_valid/max(1,riziv_total):.1%})")
    for lab, counter in format_variants.items():
        total = sum(counter.values())
        variants = sorted(counter.items(), key=lambda x: -x[1])
        print(f"  {lab:10s} {len(counter)} format variant(s): "
              + ", ".join(f"{v}={c}/{total}({c/total:.0%})" for v, c in variants))
    return {
        "n_docs": n_docs, "label_counts": label_counts, "format_variants": format_variants,
        "insz_valid_rate": insz_valid / insz_total if insz_total else None,
        "riziv_valid_rate": riziv_valid / riziv_total if riziv_total else None,
    }


def load_new_data_source(source_name, address_mode="decomposed"):
    records = dp.build_dataset(address_mode)
    out = []
    for r in records:
        if r["source"] != source_name:
            continue
        spans = [{"label": e["label"], "start": e["start"], "end": e["end"]} for e in r["entities"]]
        out.append({"text": r["text"], "spans": spans})
    return out


def load_jsonl(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            out.append({"text": d["text"], "spans": d["spans"]})
    return out


def main():
    results = {}
    for src in ("batch_final", "labeled", "hf", "legacy"):
        recs = load_new_data_source(src)
        if recs:
            results[f"new_data/{src}"] = audit_records(f"new_data/{src}", recs)

    tamer_dir = os.path.join(ROOT, "TamerBERT", "TamerBERT")
    results["TamerBERT/dataset_500"] = audit_records(
        "TamerBERT/dataset_500.jsonl", load_jsonl(os.path.join(tamer_dir, "dataset_500.jsonl")))
    results["TamerBERT/train"] = audit_records(
        "TamerBERT/train.jsonl", load_jsonl(os.path.join(tamer_dir, "train.jsonl")))
    results["REAL ground truth (org_data_filled)"] = audit_records(
        "REAL ground truth: org_data_filled_labeled.jsonl (5 docs)",
        load_jsonl(os.path.join(tamer_dir, "org_data_filled_labeled.jsonl")))

    print(f"\n{'=' * 90}\nSUMMARY: format-diversity comparison vs REAL ground truth")
    real = results["REAL ground truth (org_data_filled)"]["format_variants"]
    for name, res in results.items():
        if name.startswith("REAL"):
            continue
        fv = res["format_variants"]
        overlaps = []
        for lab, real_counter in real.items():
            real_variants = set(real_counter.keys())
            src_variants = set(fv.get(lab, {}).keys())
            missing = real_variants - src_variants
            if missing:
                overlaps.append(f"{lab}: missing real variant(s) {sorted(missing)}")
        print(f"\n{name}:")
        if overlaps:
            for o in overlaps:
                print(f"    {o}")
        else:
            print("    covers all real-document format variants seen")


if __name__ == "__main__":
    main()
