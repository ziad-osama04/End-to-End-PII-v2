"""Data loading + label-taxonomy pipeline for the personal MedRoBERTa fine-tune track.

Separate from the team's shared masking_service code and MLflow experiment.
Reads ONLY from ../new_data (the four synthetic sources); never touches
Google Drive or any external dataset.

Finalized taxonomy (confirmed with Eng. Khaled):
  Regex-only, permanent (always mapped to None / never trained as a model span):
    INSZ, RIZIV, URL, EMAIL, BTW_EENHEID
  Model-owned / hybrid (trained; DATE/AGE/PHONE are ablated regex-vs-hybrid later):
    NAME, ORGANIZATION, ADDRESS (or its 4 components), AGE, DATE, PHONE
  GENDER is never a tagged span -- derived post-hoc from INSZ parity, out of scope here.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from typing import Literal

DATA_ROOT = os.environ.get("PII_DATA_ROOT") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "new_data"
)

BATCH_FINAL_DIR = os.path.join(DATA_ROOT, "batch_final")
BF_REPORTS_DIR = os.path.join(BATCH_FINAL_DIR, "reports")
BF_GT_DIR = os.path.join(BATCH_FINAL_DIR, "ground_truth")
SYNTHETIC_DIR = os.path.join(DATA_ROOT, "synthetic_reports")
RECOMBINED_DIR = os.path.join(DATA_ROOT, "recombined")
HF_DATASET_PATH = os.path.join(DATA_ROOT, "hf_ner_dataset.jsonl")
LABELED_PATH = os.path.join(DATA_ROOT, "synthetic_reports_labeled.jsonl")

SOURCE_PRIORITY = {"batch_final": 3, "labeled": 2, "hf": 1, "legacy": 0}

AddressMode = Literal["decomposed", "single"]

# --------------------------------------------------------------------------- #
# Label maps -- regex-permanent labels map to None: they must NEVER enter the
# model's tagset, in every trial, not just the DATE/AGE/PHONE ablation.
# --------------------------------------------------------------------------- #
MAP_BATCH_FINAL = {
    "patient_full_name": "NAME",
    "patient_first_name": "NAME",
    "patient_last_name": "NAME",
    "patient_national_register_number": "INSZ",
    "patient_secondary_record_id": None,       # dossier id, not in taxonomy
    "referring_doctor_name": "NAME",
    "sending_doctor_last_name": "NAME",
    "validating_doctor_last_name": "NAME",
    "cosigning_doctor_name": "NAME",
    "sending_practice_legal_name": "ORGANIZATION",
    "cosigning_practice_legal_name": "ORGANIZATION",
    "hospital_name": "ORGANIZATION",
    "specialty_department": None,              # clinical, not PII
    "institution_street_address": None,        # composite; components used instead
    "institution_street_name": "STREET",
    "institution_house_number": "BUILDING_NUMBER",
    "institution_postal_code": "ZIP_CODE",
    "institution_city": "CITY",
    "institution_phone": "PHONE",
    "institution_direct_dial_phone": "PHONE",
    "institution_website": "URL",
    "report_date": "DATE",
    "validation_date": "DATE",
    "validation_time": "DATE",
    "patient_age": "AGE",
    "patient_dob": "DATE",
}
_ADDRESS_COMPONENT_CATS = {
    "institution_street_name": "STREET",
    "institution_house_number": "BUILDING_NUMBER",
    "institution_postal_code": "ZIP_CODE",
    "institution_city": "CITY",
}

MAP_LABELED = {
    "PATIENT_NAME": "NAME",
    "DOCTOR_NAME": "NAME",
    "RESPONSIBLE_NAME": "NAME",
    "HOSPITAL": "ORGANIZATION",
    "NATIONAL_ID": "INSZ",
    "PROVIDER_ID": "RIZIV",
    "ADDRESS": "ADDRESS_COARSE",
    "PHONE": "PHONE",
    "EMAIL": "EMAIL",
    "DOSSIER_NUMBER": None,
    "DATE": "DATE",
    "SPECIALTY": None,
    "AGE": "AGE",
    "MEDICATION": None,
    "CLINICAL_NOTE": None,
}

MAP_HF = {
    "PATIENT_NAME": "NAME",
    "DOCTOR_NAME": "NAME",
    "BELGIAN_INSZ": "INSZ",
    "BELGIAN_RIZIV": "RIZIV",
    "HOSPITAL": "ORGANIZATION",
}

MAP_LEGACY = {
    "patient_naam": "NAME",
    "insz": "INSZ",
    "riziv_behandelaar": "RIZIV",
    "arts_naam": "NAME",
    "arts_verwijzer": "NAME",
    "ziekenhuis": "ORGANIZATION",
    "adres": "ADDRESS_COARSE",
    "telefoon": "PHONE",
    "email": "EMAIL",
}

# Permanent per the finalized taxonomy: the MODEL must never be trained to
# predict these (they're regex-only in production), but they must stay in the
# ground truth returned by build_dataset() -- the regex-only and full-pipeline
# eval surfaces need real support counts for them. Only strip_for_training()
# removes them, and only for the token-classifier's training labels.
REGEX_PERMANENT_LABELS = ("INSZ", "RIZIV", "URL", "EMAIL", "BTW_EENHEID")
MODEL_LABELS_DECOMPOSED = ("NAME", "ORGANIZATION", "CITY", "ZIP_CODE", "STREET", "BUILDING_NUMBER", "AGE", "DATE", "PHONE")
MODEL_LABELS_SINGLE = ("NAME", "ORGANIZATION", "ADDRESS", "AGE", "DATE", "PHONE")


def strip_for_training(records: list[dict]) -> list[dict]:
    """Return a copy of *records* with regex-permanent labels removed from
    entities -- what the token classifier actually trains on. Use build_dataset()
    directly (unstripped) for regex-only / full-pipeline evaluation ground truth.
    """
    out = []
    for r in records:
        kept = [e for e in r["entities"] if e["label"] not in REGEX_PERMANENT_LABELS]
        out.append({**r, "entities": kept})
    return out


def find_all_occurrences(text: str, query: str) -> list[tuple[int, int]]:
    out, start = [], 0
    while True:
        idx = text.find(query, start)
        if idx == -1:
            break
        out.append((idx, idx + len(query)))
        start = idx + len(query)
    return out


def variant_id_from_name(name: str) -> str:
    m = re.search(r"(variant_\d+)", name)
    return m.group(1) if m else name


# --------------------------------------------------------------------------- #
# Address handling: split a coarse span into 4 components, or merge batch_final's
# 4 native component spans back into one ADDRESS span.
# --------------------------------------------------------------------------- #
ADDRESS_RE = re.compile(
    r"(?P<street>[A-Za-zÀ-ÿ.'\-]+(?:\s+[A-Za-zÀ-ÿ.'\-]+)*?)"
    r"\s+(?P<num>\d+\s?[A-Za-z]?)"
    r"\s*,?\s*"
    r"(?P<zip>\d{4})"
    r"\s*,?\s*(?P<city>[A-Za-zÀ-ÿ.'\-]+(?:[\s-]+[A-Za-zÀ-ÿ.'\-]+)*)"
)


def split_address(text: str, start: int, end: int) -> list[dict]:
    """Regex-split one coarse address span into 4 component spans (decomposed mode)."""
    m = ADDRESS_RE.search(text[start:end])
    if not m:
        return []
    out = []
    for grp, lab in (("street", "STREET"), ("num", "BUILDING_NUMBER"), ("zip", "ZIP_CODE"), ("city", "CITY")):
        a, b = m.span(grp)
        if a >= 0:
            out.append({"start": start + a, "end": start + b, "label": lab})
    return out


_ADDRESS_MERGE_GAP = 60  # max char gap between component spans to treat as one address block


def merge_address_components(entities: list[dict]) -> list[dict]:
    """Cluster nearby STREET/BUILDING_NUMBER/ZIP_CODE/CITY spans into single ADDRESS
    spans (single mode). Components further apart than _ADDRESS_MERGE_GAP are treated
    as separate address occurrences and merged independently.
    """
    comp_labels = {"STREET", "BUILDING_NUMBER", "ZIP_CODE", "CITY"}
    comps = sorted((e for e in entities if e["label"] in comp_labels), key=lambda e: e["start"])
    others = [e for e in entities if e["label"] not in comp_labels]

    merged = []
    cluster: list[dict] = []
    for e in comps:
        if cluster and e["start"] - cluster[-1]["end"] > _ADDRESS_MERGE_GAP:
            merged.append(cluster)
            cluster = []
        cluster.append(e)
    if cluster:
        merged.append(cluster)

    out = list(others)
    for cluster in merged:
        out.append({
            "start": min(c["start"] for c in cluster),
            "end": max(c["end"] for c in cluster),
            "label": "ADDRESS",
        })
    return out


# --------------------------------------------------------------------------- #
# Load every source
# --------------------------------------------------------------------------- #
def load_records(address_mode: AddressMode = "decomposed") -> list[dict]:
    records = []

    # (A) batch_final -- precise pre-computed multi-spans
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

    # (B) synthetic_reports_labeled.jsonl
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

    # (C) hf_ner_dataset.jsonl
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

    # (D) legacy recombined + synthetic_reports
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


def resolve_overlaps(entities: list[dict]) -> list[dict]:
    ents = sorted(entities, key=lambda x: (-(x["end"] - x["start"]), x["start"]))
    kept = []
    for e in ents:
        if any(not (e["end"] <= k["start"] or e["start"] >= k["end"]) for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda x: x["start"])


def dedup_and_clean(records: list[dict]) -> list[dict]:
    for r in records:
        r["entities"] = resolve_overlaps(r["entities"])

    best: dict[str, dict] = {}
    for r in records:
        g = r["group_key"]
        if g not in best or SOURCE_PRIORITY[r["source"]] > SOURCE_PRIORITY[best[g]["source"]]:
            best[g] = r
    records = list(best.values())
    return [r for r in records if r["text"].strip()]


def build_dataset(address_mode: AddressMode = "decomposed") -> list[dict]:
    records = load_records(address_mode)
    return dedup_and_clean(records)


# --------------------------------------------------------------------------- #
# Near-duplicate / template-leakage detection (run ONCE on the corpus, not per
# trial -- if synthetic generation reuses sentence skeletons across "different"
# documents, eval numbers can be inflated by memorized templates rather than
# genuine detection, even though group_key dedup already prevents identical
# doc-id leakage).
# --------------------------------------------------------------------------- #
def text_skeleton(text: str, entities: list[dict]) -> str:
    """Strip entity spans from text, collapse whitespace/digits -- what's left is
    the sentence "template" a synthetic generator would have reused verbatim.
    """
    out = []
    last = 0
    for e in sorted(entities, key=lambda x: x["start"]):
        out.append(text[last:e["start"]])
        last = e["end"]
    out.append(text[last:])
    skeleton = "".join(out)
    skeleton = re.sub(r"\d+", "#", skeleton)
    skeleton = re.sub(r"\s+", " ", skeleton).strip().lower()
    return skeleton


def find_template_clusters(records: list[dict]) -> dict[str, list[str]]:
    """Group record ids by identical skeleton. Any cluster with >1 doc_id is a
    near-duplicate template shared across records -- if those records end up split
    across train/eval, the eval score is partly memorization, not detection.
    """
    by_skeleton: dict[str, list[str]] = defaultdict(list)
    for r in records:
        sk = text_skeleton(r["text"], r["entities"])
        if sk:  # ignore empty skeletons (fully-masked-out text, rare/degenerate)
            by_skeleton[sk].append(r["id"])
    return {sk: ids for sk, ids in by_skeleton.items() if len(ids) > 1}
