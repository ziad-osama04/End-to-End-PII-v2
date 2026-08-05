import json
import os

notebook = {
 'cells': [],
 'metadata': {
  'kernelspec': {
   'display_name': 'Python 3',
   'language': 'python',
   'name': 'python3'
  },
  'language_info': {
   'name': 'python'
  }
 },
 'nbformat': 4,
 'nbformat_minor': 4
}

def add_md(text):
    notebook['cells'].append({
        'cell_type': 'markdown',
        'metadata': {},
        'source': [line + '\n' for line in text.split('\n')]
    })

def add_code(text):
    notebook['cells'].append({
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': [line + '\n' for line in text.split('\n')]
    })

# ---------------------------------------------------------------------------
add_md('''# Fine-tune MedRoBERTa.nl for PII Detection (Kaggle **or** Colab)

Token-classification (NER) fine-tune over **all four synthetic-data sources**, unified onto a single coarse PII label scheme. The notebook **auto-detects** whether it is running on Kaggle, Colab, or locally and sets the data/checkpoint paths for you (next cell).

## The dataset archive (`pii-dataset.zip`)

Its top-level layout is:

```
batch_final/                       <- NEW method (highest quality, pre-computed spans)
    reports/         (synth_*.txt)
    ground_truth/    (synth_*.json)
synthetic_reports_labeled.jsonl    <- labeled jsonl (1,764 docs)
hf_ner_dataset.jsonl               <- hf jsonl (267 docs)
recombined/          (variant_*.json)        <- legacy string-matched
synthetic_reports/   (variant_*_report.txt)  <- legacy report texts
```

**On Kaggle:** right sidebar -> **Add Data** -> **Upload** -> upload `pii-dataset.zip` -> name it exactly **`pii-dataset`** (mounts at `/kaggle/input/pii-dataset/`). Accelerator: **GPU T4 x2 / P100**.

**On Colab:** upload `pii-dataset.zip` to the **root of your Google Drive** (`MyDrive/pii-dataset.zip`). The env cell mounts Drive and unzips it to `/content/pii-dataset`. Runtime -> Change runtime type -> **T4 GPU**.

## Internet on Kaggle: ON vs OFF

Kaggle notebooks have **internet OFF by default**. You have two options:

- **Internet ON (simplest):** Notebook options -> **Internet -> On**. Requires a **phone-verified** account (kaggle.com -> Settings -> Phone Verification). With this, nothing else is needed - the base model downloads from Hugging Face automatically. `transformers`/`datasets`/`accelerate` are already preinstalled, so no pip is required either.
- **Internet OFF (offline):** add the base model as a Kaggle input and skip the download:
  1. Right sidebar -> **Add Data** -> search Kaggle for a **`MedRoBERTa.nl`** model/dataset (or upload the HF `CLTL/MedRoBERTa.nl` folder yourself).
  2. Make sure it mounts at one of the paths in `MODEL_DIR_CANDIDATES` (e.g. `/kaggle/input/medroberta-nl`), or edit that list.
  3. The env cell auto-detects the local model and switches transformers to offline mode - no internet needed at all.

## Checkpointing / surviving interrupts (READ THIS)

Both platforms drop long/idle sessions, so checkpoints must land on **persistent** storage:

- **Kaggle:** Notebook options -> **Persistence -> "Files only"** keeps `/kaggle/working/` across sessions. Checkpoints go there.
- **Colab:** `/content/` is **erased on disconnect**, so checkpoints are written to **Google Drive** (`MyDrive/pii-work/`). This is set automatically.

Either way: checkpoints are saved **every epoch**; if the session dies, just **re-run all cells** and training **auto-resumes from the last checkpoint** (`save_total_limit=2`, best model protected). For an unattended Kaggle run use **Save Version -> Save & Run All (Commit)**.''')

# ---------------------------------------------------------------------------
add_code('''# transformers, datasets and accelerate are ALREADY preinstalled on both Kaggle and Colab,
# so this cell is OPTIONAL. It is written to NEVER break the run:
#  - if Internet is OFF (Kaggle default), the install quietly fails and we use what's installed.
#  - we deliberately do NOT install seqeval/evaluate (seqeval ships only a source tarball and its
#    setup.py build fails with "metadata-generation-failed"); entity-level P/R/F1 is computed
#    inline below. The notebook also handles whichever transformers version is already present.
!pip install -q datasets accelerate 2>/dev/null || echo "No internet / already installed - using preinstalled packages."''')

# ---------------------------------------------------------------------------
add_code('''import os
import json
import re
import glob
import hashlib
import inspect
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, TrainingArguments, Trainer
from datasets import Dataset

# ---- Detect environment (Colab / Kaggle / local) and set DATA_ROOT + WORK_ROOT ----
# NOTE: Kaggle's image ALSO ships the `google.colab` package, so importing it is NOT a valid
# Colab test. Check Kaggle first, and require a real Colab signal (/var/colab/hostname).
def _detect_env():
    if (os.environ.get("KAGGLE_KERNEL_RUN_TYPE")
            or os.path.isdir("/kaggle/input") or os.path.isdir("/kaggle/working")):
        return "kaggle"
    if os.path.exists("/var/colab/hostname") or os.environ.get("COLAB_RELEASE_TAG"):
        try:
            import google.colab  # noqa: F401
            return "colab"
        except Exception:
            pass
    return "local"

ENV = _detect_env()
print("Environment:", ENV)

# The uploaded zip can end up nested (Kaggle) or the dataset slug may differ, so locate the
# real data folder by searching for known markers instead of hardcoding the path.
DATA_MARKERS = ["hf_ner_dataset.jsonl", "synthetic_reports_labeled.jsonl", "batch_final"]

def find_data_root(base):
    if not os.path.isdir(base):
        return None
    for root, dirs, files in os.walk(base):
        names = set(dirs) | set(files)
        if any(m in names for m in DATA_MARKERS):
            return root
    return None

if ENV == "kaggle":
    DATA_ROOT = find_data_root("/kaggle/input")       # dataset name/nesting no longer matters
    WORK_ROOT = "/kaggle/working"                     # enable Persistence: Files
elif ENV == "colab":
    from google.colab import drive
    drive.mount("/content/drive")
    DRIVE_DIR = "/content/drive/MyDrive"
    ZIP_PATH  = os.path.join(DRIVE_DIR, "pii-dataset.zip")
    if not os.path.isdir("/content/pii-dataset"):
        import zipfile
        assert os.path.exists(ZIP_PATH), f"Upload pii-dataset.zip to {DRIVE_DIR}"
        print("Unzipping dataset to /content/pii-dataset")
        with zipfile.ZipFile(ZIP_PATH) as z:
            z.extractall("/content/pii-dataset")
    DATA_ROOT = find_data_root("/content/pii-dataset")
    WORK_ROOT = os.path.join(DRIVE_DIR, "pii-work")   # checkpoints survive disconnects
    os.makedirs(WORK_ROOT, exist_ok=True)
else:  # local
    DATA_ROOT = find_data_root("synthetic_reports") or "synthetic_reports"
    WORK_ROOT = "./work"
    os.makedirs(WORK_ROOT, exist_ok=True)

if not DATA_ROOT:
    print("\\n!!! Could not find the dataset. Contents of /kaggle/input:")
    for root, dirs, files in os.walk("/kaggle/input"):
        if root.count("/") - 2 <= 2:
            print(" ", root, "->", sorted(dirs)[:8], [f for f in files][:6])
    raise FileNotFoundError(
        "None of " + str(DATA_MARKERS) + " found. Check that pii-dataset.zip was added as a "
        "dataset and fully extracted.")
print("DATA_ROOT ->", DATA_ROOT)

# ---- Derived paths (same layout on every platform) ----
BATCH_FINAL_DIR  = os.path.join(DATA_ROOT, "batch_final")
BF_REPORTS_DIR   = os.path.join(BATCH_FINAL_DIR, "reports")
BF_GT_DIR        = os.path.join(BATCH_FINAL_DIR, "ground_truth")
SYNTHETIC_DIR    = os.path.join(DATA_ROOT, "synthetic_reports")   # legacy report texts
RECOMBINED_DIR   = os.path.join(DATA_ROOT, "recombined")          # legacy pii json
HF_DATASET_PATH  = os.path.join(DATA_ROOT, "hf_ner_dataset.jsonl")
LABELED_PATH     = os.path.join(DATA_ROOT, "synthetic_reports_labeled.jsonl")

OUTPUT_DIR = os.path.join(WORK_ROOT, "pii-medroberta-finetuned")
FINAL_DIR  = os.path.join(WORK_ROOT, "final-pii-model")

# ---- Base model resolution: prefer a LOCAL copy so Kaggle works with Internet OFF ----
# If you added MedRoBERTa.nl as a Kaggle input (Add Data -> Models or Datasets), point one of
# these at it. Otherwise the Hugging Face id is used, which needs Internet -> On (phone-verified).
MODEL_HF_ID = "CLTL/MedRoBERTa.nl"
MODEL_DIR_CANDIDATES = [
    "/kaggle/input/medroberta-nl",
    "/kaggle/input/medrobertanl",
    "/kaggle/input/medroberta/medroberta.nl",
    os.path.join(DATA_ROOT, "medroberta-nl"),
]
MODEL_NAME = next((d for d in MODEL_DIR_CANDIDATES if os.path.isdir(d)), MODEL_HF_ID)
if os.path.isdir(MODEL_NAME):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    print("Base model: LOCAL ->", MODEL_NAME, "(offline, no internet needed)")
else:
    print("Base model: HF Hub ->", MODEL_NAME, "(requires Internet -> On)")
MAX_LEN    = 512
STRIDE     = 128     # sliding-window overlap so end-of-report PII is not truncated away

# ---- Which sources to include (all on per your choice) ----
USE_BATCH_FINAL     = True
USE_LABELED_JSONL   = True
USE_HF_JSONL        = True
USE_LEGACY          = True
INCLUDE_SPECIAL_CAT = False  # clinical content is NOT PII in the new taxonomy

# Dedup priority when the same document appears in multiple sources (higher wins)
SOURCE_PRIORITY = {"batch_final": 3, "labeled": 2, "hf": 1, "legacy": 0}

print("CUDA available:", torch.cuda.is_available())''')

# ---------------------------------------------------------------------------
add_md('''## 1. Unified label scheme (v2 taxonomy)

Every source is mapped onto one PII taxonomy. Anything that maps to `None` is dropped.

**Model (NER) labels:** `NAME` (patient + doctor merged), `DATE` (all formats, incl. DOB),
`ORGANIZATION` (hospital + practice), `CITY`, `ZIP_CODE`, `STREET`, `BUILDING_NUMBER`,
`AGE`, `PHONE`, plus `INSZ`, `RIZIV`, `URL`, `EMAIL` where a source labels them.

**Split address:** `batch_final` already provides the four address components as separate
spans; coarse whole-address spans from the other sources are regex-split into the same four
labels in step 2b.

**Dropped (not PII):** medical `SPECIALTY`, `MEDICATION`, `CLINICAL_NOTE`, height/weight/BMI,
and the secondary record / dossier id. These are clinical context, not identifiers.

**Derived downstream (not trained here):** `GENDER` is computed from the INSZ checksum by the
regex/inference layer, not string-matched, so it never mislabels a stray "M"/"V".
`BTW_EENHEID` is regex-only (`BE0…`).''')

add_code('''# Each dict maps a SOURCE's raw label to the canonical PII label (or None to drop).
# v2 taxonomy: names -> NAME; address -> CITY/ZIP_CODE/STREET/BUILDING_NUMBER;
# hospital + practice -> ORGANIZATION; ids -> INSZ/RIZIV; website -> URL;
# DOB folded into DATE; clinical content dropped. "ADDRESS_COARSE" is a marker
# that step 2b regex-splits into the four address components.

MAP_BATCH_FINAL = {
    "patient_full_name": "NAME",
    "patient_first_name": "NAME",
    "patient_last_name": "NAME",
    "patient_national_register_number": "INSZ",
    "patient_secondary_record_id": None,          # dossier id, not in taxonomy
    "referring_doctor_name": "NAME",
    "sending_doctor_last_name": "NAME",
    "validating_doctor_last_name": "NAME",
    "cosigning_doctor_name": "NAME",
    "sending_practice_legal_name": "ORGANIZATION",
    "cosigning_practice_legal_name": "ORGANIZATION",
    "hospital_name": "ORGANIZATION",
    "specialty_department": None,                 # clinical, not PII
    "institution_street_address": None,           # composite dropped; keep components
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
    "patient_dob": "DATE",                        # DOB folded into DATE
}

MAP_LABELED = {
    "PATIENT_NAME": "NAME",
    "DOCTOR_NAME": "NAME",
    "RESPONSIBLE_NAME": "NAME",
    "HOSPITAL": "ORGANIZATION",
    "NATIONAL_ID": "INSZ",
    "PROVIDER_ID": "RIZIV",
    "ADDRESS": "ADDRESS_COARSE",                  # regex-split in step 2b
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

# legacy pii keys -> canonical. "geslacht" (M/V) is dropped: GENDER is derived
# from the INSZ downstream, not string-matched (it would tag every stray "M").
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
}''')

# ---------------------------------------------------------------------------
add_md('''## 2. Load every source into a common record format

Each record: `{"id", "source", "group_key", "text", "entities": [{"start","end","label"}]}` with labels already mapped to the canonical scheme.''')

add_code('''def find_all_occurrences(text, query):
    out, start = [], 0
    while True:
        idx = text.find(query, start)
        if idx == -1:
            break
        out.append((idx, idx + len(query)))
        start = idx + len(query)
    return out

def variant_id_from_name(name):
    m = re.search(r"(variant_\\d+)", name)
    return m.group(1) if m else name

records = []

# ---- (A) batch_final : precise pre-computed multi-spans ----
if USE_BATCH_FINAL and os.path.isdir(BF_REPORTS_DIR) and os.path.isdir(BF_GT_DIR):
    print("Loading batch_final ...")
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
        records.append({"id": doc_id, "source": "batch_final",
                        "group_key": "bf::" + doc_id, "text": text, "entities": ents})

# ---- (B) synthetic_reports_labeled.jsonl : spans + values ----
if USE_LABELED_JSONL and os.path.exists(LABELED_PATH):
    print("Loading synthetic_reports_labeled.jsonl ...")
    with open(LABELED_PATH, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            text = d["source_text"]
            ents = []
            for e in d.get("privacy_mask", []):
                canon = MAP_LABELED.get(e["label"])
                if not canon:
                    continue
                ents.append({"start": e["start"], "end": e["end"], "label": canon})
            gid = "variant::" + variant_id_from_name(d.get("file", ""))
            records.append({"id": d.get("file", ""), "source": "labeled",
                            "group_key": gid, "text": text, "entities": ents})

# ---- (C) hf_ner_dataset.jsonl : coarse spans (no doc id) ----
if USE_HF_JSONL and os.path.exists(HF_DATASET_PATH):
    print("Loading hf_ner_dataset.jsonl ...")
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
            sig = hashlib.md5(re.sub(r"\\W+", "", text).lower().encode()).hexdigest()[:12]
            records.append({"id": f"hf_{i}", "source": "hf",
                            "group_key": "hf::" + sig, "text": text, "entities": ents})

# ---- (D) legacy recombined + synthetic_reports : string-matched ----
if USE_LEGACY and os.path.isdir(SYNTHETIC_DIR) and os.path.isdir(RECOMBINED_DIR):
    print("Loading legacy string-matched reports ...")
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
            for s, e in find_all_occurrences(text, value):
                ents.append({"start": s, "end": e, "label": canon})
        records.append({"id": base, "source": "legacy",
                        "group_key": "variant::" + base, "text": text, "entities": ents})

print(f"\\nRaw records loaded: {len(records)}")
from collections import Counter
print("By source:", dict(Counter(r["source"] for r in records)))''')

# ---------------------------------------------------------------------------
add_md('''## 2b. Split coarse ADDRESS spans into components

`batch_final` already provides `CITY / ZIP_CODE / STREET / BUILDING_NUMBER` as separate
spans. The other sources only mark a whole-address span (`ADDRESS_COARSE`); this step
regex-splits those into the same four component labels so every source supervises the
fine-grained address taxonomy. An address that does not parse is dropped rather than
mislabelled.''')

add_code('''# Belgian/Dutch address: "<street words> <number>, <4-digit zip> <city>"
ADDRESS_RE = re.compile(
    r"(?P<street>[A-Za-zÀ-ÿ.'\\-]+(?:\\s+[A-Za-zÀ-ÿ.'\\-]+)*?)"
    r"\\s+(?P<num>\\d+\\s?[A-Za-z]?)"
    r"\\s*,?\\s*"
    r"(?P<zip>\\d{4})"
    r"\\s*,?\\s*(?P<city>[A-Za-zÀ-ÿ.'\\-]+(?:[\\s-]+[A-Za-zÀ-ÿ.'\\-]+)*)"
)

def split_address(text, start, end):
    """Regex-split a whole-address span into the four component labels."""
    m = ADDRESS_RE.search(text[start:end])
    if not m:
        return []
    out = []
    for grp, lab in (("street", "STREET"), ("num", "BUILDING_NUMBER"),
                     ("zip", "ZIP_CODE"), ("city", "CITY")):
        a, b = m.span(grp)
        if a >= 0:
            out.append({"start": start + a, "end": start + b, "label": lab})
    return out

split_n = kept_coarse = 0
for r in records:
    new_ents = []
    for e in r["entities"]:
        if e["label"] == "ADDRESS_COARSE":
            comp = split_address(r["text"], e["start"], e["end"])
            if comp:
                new_ents.extend(comp); split_n += 1
            else:
                kept_coarse += 1     # dropped (unparseable)
        else:
            new_ents.append(e)
    r["entities"] = new_ents
print(f"Coarse addresses split into components: {split_n}  (dropped unparseable: {kept_coarse})")''')

# ---------------------------------------------------------------------------
add_md('''## 3. Overlap resolution + dedup

- **Overlap resolution (within a doc):** sort spans, keep the longest; drop any span that overlaps one already kept. This absorbs sub-spans (`patient_first_name` into `patient_full_name`, `institution_postal_code` into `ADDRESS`).
- **Dedup (across sources):** the labeled/hf/legacy sets are different labelings of the *same* `variant_*` reports. Records sharing a `group_key` are collapsed to the single highest-priority source, so no document leaks across the train/test split and no conflicting labels are trained on.''')

add_code('''def resolve_overlaps(entities):
    # keep longest spans first; drop anything overlapping an already-kept span
    ents = sorted(entities, key=lambda x: (-(x["end"] - x["start"]), x["start"]))
    kept = []
    for e in ents:
        if any(not (e["end"] <= k["start"] or e["start"] >= k["end"]) for k in kept):
            continue
        kept.append(e)
    return sorted(kept, key=lambda x: x["start"])

before = sum(len(r["entities"]) for r in records)
for r in records:
    r["entities"] = resolve_overlaps(r["entities"])
after = sum(len(r["entities"]) for r in records)
print(f"Entities after overlap resolution: {after} (dropped {before - after} overlapping)")

# Dedup by group_key, keeping highest-priority source
best = {}
for r in records:
    g = r["group_key"]
    if g not in best or SOURCE_PRIORITY[r["source"]] > SOURCE_PRIORITY[best[g]["source"]]:
        best[g] = r
records = list(best.values())
print(f"Records after dedup: {len(records)}")
print("By source after dedup:", dict(Counter(r["source"] for r in records)))

# drop empty-text / keep all (docs with zero entities still teach 'O')
records = [r for r in records if r["text"].strip()]
print(f"Final records: {len(records)}")''')

# ---------------------------------------------------------------------------
add_md('''## 4. Data QA''')

add_code('''from collections import Counter, defaultdict

label_counts = Counter()
per_source_labels = defaultdict(Counter)
docs_with_entities = 0
for r in records:
    if r["entities"]:
        docs_with_entities += 1
    for e in r["entities"]:
        label_counts[e["label"]] += 1
        per_source_labels[r["source"]][e["label"]] += 1

print(f"Docs with >=1 entity: {docs_with_entities}/{len(records)}")
print("\\nEntity count per canonical label:")
for lab, c in label_counts.most_common():
    print(f"  {lab:16s} {c}")

print("\\nLabel coverage per source (which types each source contributes):")
for src, cc in per_source_labels.items():
    print(f"  {src:11s} -> {sorted(cc.keys())}")

# sanity: a few spans should slice out sensible text
r0 = next(r for r in records if r["entities"])
print("\\nSample spans from", r0["id"], "(", r0["source"], "):")
for e in r0["entities"][:6]:
    print(f"  [{e['label']}] {r0['text'][e['start']:e['end']]!r}")''')

# ---------------------------------------------------------------------------
add_md('''## 5. Build label list, tokenize with sliding windows, align BIO tags

Long reports are split into overlapping 512-token windows (`stride=128`) so PII near the end of a report (institution address, phone, website, validation block) is not lost to truncation.''')

add_code('''tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, add_prefix_space=True)
assert tokenizer.is_fast, "A fast tokenizer is required for offset mapping."

# Build label list deterministically from the canonical labels present
canonical = sorted({e["label"] for r in records for e in r["entities"]})
label_list = ["O"] + [f"{p}-{c}" for c in canonical for p in ("B", "I")]
label2id = {l: i for i, l in enumerate(label_list)}
id2label = {i: l for i, l in enumerate(label_list)}
print(f"{len(label_list)} BIO labels over {len(canonical)} entity types:")
print(canonical)

def char_bio(text, entities):
    ch = ["O"] * len(text)
    for e in entities:
        s, en, lab = e["start"], e["end"], e["label"]
        s = max(0, s); en = min(len(text), en)
        for i in range(s, en):
            ch[i] = ("B-" if i == s else "I-") + lab
    return ch

def tokenize_and_align(examples):
    tok = tokenizer(
        examples["text"], truncation=True, max_length=MAX_LEN, stride=STRIDE,
        return_overflowing_tokens=True, return_offsets_mapping=True, padding="max_length",
    )
    sample_map = tok.pop("overflow_to_sample_mapping")
    offset_batch = tok.pop("offset_mapping")

    char_cache = {}
    all_labels = []
    for chunk_idx, offsets in enumerate(offset_batch):
        si = sample_map[chunk_idx]
        if si not in char_cache:
            char_cache[si] = char_bio(examples["text"][si], examples["entities"][si])
        ch = char_cache[si]
        lab_ids = []
        for (a, b) in offsets:
            if a == 0 and b == 0:            # special tokens + padding
                lab_ids.append(-100)
            else:
                lab_ids.append(label2id[ch[a]])
        all_labels.append(lab_ids)

    tok["labels"] = all_labels
    return tok

ds = Dataset.from_list([{"text": r["text"], "entities": r["entities"]} for r in records])
ds = ds.train_test_split(test_size=0.1, seed=42)

print("Tokenizing + aligning (with sliding windows)...")
tokenized = ds.map(tokenize_and_align, batched=True, remove_columns=ds["train"].column_names)
print(tokenized)''')

# ---------------------------------------------------------------------------
add_md('''## 6. Metrics + model''')

add_code('''# ---- Inline entity-level scorer (seqeval-equivalent, IOB2), no external deps ----
from collections import defaultdict

def extract_entities(tags):
    """List of BIO tag strings -> set of (type, start, end) spans."""
    ents, cur = [], None
    for i, tag in enumerate(tags):
        if tag == "O":
            if cur:
                ents.append(cur); cur = None
            continue
        prefix, _, etype = tag.partition("-")
        if prefix == "B" or cur is None or cur[0] != etype:
            if cur:
                ents.append(cur)
            cur = [etype, i, i + 1]
        else:  # I- continuing same type
            cur[2] = i + 1
    if cur:
        ents.append(cur)
    return {tuple(e) for e in ents}

def entity_scores(true_seqs, pred_seqs):
    tp, fp, fn = defaultdict(int), defaultdict(int), defaultdict(int)
    tok_correct = tok_total = 0
    for t, p in zip(true_seqs, pred_seqs):
        for a, b in zip(t, p):
            tok_total += 1
            tok_correct += (a == b)
        T, P = extract_entities(t), extract_entities(p)
        for e in P:
            (tp if e in T else fp)[e[0]] += 1
        for e in T:
            if e not in P:
                fn[e[0]] += 1
    per = {}
    for ty in set(list(tp) + list(fp) + list(fn)):
        pr = tp[ty] / (tp[ty] + fp[ty]) if (tp[ty] + fp[ty]) else 0.0
        rc = tp[ty] / (tp[ty] + fn[ty]) if (tp[ty] + fn[ty]) else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) else 0.0
        per[ty] = {"precision": pr, "recall": rc, "f1": f1, "number": tp[ty] + fn[ty]}
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    P_ = TP / (TP + FP) if (TP + FP) else 0.0
    R_ = TP / (TP + FN) if (TP + FN) else 0.0
    F_ = 2 * P_ * R_ / (P_ + R_) if (P_ + R_) else 0.0
    return {"overall_precision": P_, "overall_recall": R_, "overall_f1": F_,
            "overall_accuracy": tok_correct / tok_total if tok_total else 0.0,
            "per_entity": per}

def decode(preds, labels):
    preds = np.argmax(preds, axis=2)
    tp = [[label_list[pp] for pp, ll in zip(pr, la) if ll != -100]
          for pr, la in zip(preds, labels)]
    tl = [[label_list[ll] for pp, ll in zip(pr, la) if ll != -100]
          for pr, la in zip(preds, labels)]
    return tp, tl

def compute_metrics(p):
    tp, tl = decode(p[0], p[1])
    r = entity_scores(tl, tp)
    return {"precision": r["overall_precision"], "recall": r["overall_recall"],
            "f1": r["overall_f1"], "accuracy": r["overall_accuracy"]}

model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME, num_labels=len(label_list), id2label=id2label, label2id=label2id
)''')

# ---------------------------------------------------------------------------
add_md('''## 7. Train (with checkpointing + auto-resume)

Checkpoints are written every epoch to `OUTPUT_DIR`. If the session is interrupted, re-run this cell (with Kaggle **Persistence: Files** enabled) and it resumes from the last checkpoint. `save_total_limit=2` keeps disk usage down while `load_best_model_at_end` protects the best checkpoint.''')

add_code('''# Build TrainingArguments compatibly across transformers versions (eval_strategy vs evaluation_strategy)
ta_params = inspect.signature(TrainingArguments.__init__).parameters
eval_key = "eval_strategy" if "eval_strategy" in ta_params else "evaluation_strategy"

ta_kwargs = dict(
    output_dir=OUTPUT_DIR,
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=5,
    weight_decay=0.01,
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="f1",
    greater_is_better=True,
    logging_steps=50,
    fp16=torch.cuda.is_available(),
    report_to="none",
    push_to_hub=False,
)
ta_kwargs[eval_key] = "epoch"
training_args = TrainingArguments(**ta_kwargs)

# Trainer: tokenizer= renamed to processing_class in newer versions
tr_params = inspect.signature(Trainer.__init__).parameters
tok_kwarg = ({"processing_class": tokenizer} if "processing_class" in tr_params
             else {"tokenizer": tokenizer})

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized["train"],
    eval_dataset=tokenized["test"],
    compute_metrics=compute_metrics,
    **tok_kwarg,
)

from transformers.trainer_utils import get_last_checkpoint
last_checkpoint = None
if os.path.isdir(OUTPUT_DIR):
    last_checkpoint = get_last_checkpoint(OUTPUT_DIR)
    if last_checkpoint:
        print(f"Resuming from checkpoint: {last_checkpoint}")

trainer.train(resume_from_checkpoint=last_checkpoint)''')

# ---------------------------------------------------------------------------
add_md('''## 8. Evaluate + save final model & artifacts''')

add_code('''metrics = trainer.evaluate()
print("Final eval:", metrics)

os.makedirs(FINAL_DIR, exist_ok=True)
trainer.save_model(FINAL_DIR)
tokenizer.save_pretrained(FINAL_DIR)

with open(os.path.join(FINAL_DIR, "label_list.json"), "w", encoding="utf-8") as f:
    json.dump({"label_list": label_list, "id2label": id2label, "label2id": label2id}, f, indent=2)
with open(os.path.join(FINAL_DIR, "eval_metrics.json"), "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

# detailed per-entity report
pred = trainer.predict(tokenized["test"])
tp, tl = decode(pred.predictions, pred.label_ids)
report = entity_scores(tl, tp)
with open(os.path.join(FINAL_DIR, "per_entity_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=float)
print("Overall  P={overall_precision:.3f}  R={overall_recall:.3f}  F1={overall_f1:.3f}".format(**report))
print("Per-entity F1:")
for k, v in sorted(report["per_entity"].items(), key=lambda kv: -kv[1]["number"]):
    print(f"  {k:16s} f1={v['f1']:.3f}  (n={v['number']})")

print(f"\\nSaved to {FINAL_DIR} - download it from the Kaggle output pane.")''')

# ---------------------------------------------------------------------------
add_md('''## 9. Quick inference demo''')

add_code('''from transformers import pipeline
nlp = pipeline("token-classification", model=FINAL_DIR, tokenizer=FINAL_DIR,
               aggregation_strategy="simple", device=0 if torch.cuda.is_available() else -1)

sample = records[0]["text"][:1200]
for ent in nlp(sample):
    print(f"{ent['entity_group']:14s} {ent['score']:.2f}  {ent['word']!r}")''')

# ---------------------------------------------------------------------------
with open("kaggle_finetune_medroberta.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print("Notebook created successfully!")
