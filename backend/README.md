# backend/

The Python side of the project. It hosts **two FastAPI apps** and the shared
**detection core**. Both apps import the same detector, so they mask identically.

| Path | What it is |
|---|---|
| [`masking_service/`](masking_service) | **Contract v1.2 masking API** — the production service NiFi/MLOps integrates with. Raw bytes in, masked bytes out, immutable version headers. See [masking_service/README.md](masking_service/README.md). |
| [`main.py`](main.py) | **Redaction demo API** (`MedRoBERTa PII Redaction API`) — small app the React UI calls: `POST /api/chat` (mask text) and `POST /api/upload` (mask a file; returns a masked **PDF** for PDF input). |
| [`src/detection/`](src/detection) | **Detection core** shared by both apps. |
| [`src/ingestion/`](src/ingestion) | Demo API router (file parsing + dispatch). |
| [`scripts/`](scripts) | Data prep + `augment_clinical_negatives.py` (clinical-table training negatives). |

> Both apps listen on **port 8000** — run one at a time.

## Detection core (`src/detection/`)

| File | Role |
|---|---|
| `pii_detector.py` | Builds the Presidio `AnalyzerEngine` (model + regex recognizers), `resolve_overlaps` (coverage-preserving), and `redact_text`. |
| `transformers_recognizer.py` | Wraps the fine-tuned `ziadosama/final-pii-model-v2`; reads its labels from the model config (no hard-coded label list). |
| `dutch_regex.py` | Structured Belgian/Dutch identifiers (INSZ w/ checksum + gender, RIZIV, BTW, EMAIL, URL, IBAN, PHONE, ZIP/STREET, DATE, AGE) + `derive_gender`. |

The model source is `PII_MODEL_DIR` (a local folder) if set, else the Hugging Face
Hub repo. Set `HF_TOKEN` for a private repo.

## Run

```bash
# Contract masking API
cp ../.env.example ../.env            # set SERVICE_TOKEN
pip install -r ../requirements-api.txt         # API runtime
pip install -r requirements.txt                # model/detector stack (torch, transformers, presidio…)
python -m spacy download nl_core_news_sm
uvicorn masking_service.app:app --port 8000

# Demo API (for the React UI) — from repo root, or:
python main.py
```

## Test & evaluate

```bash
pytest masking_service/tests                    # contract acceptance tests
python -m masking_service.evaluate_precise \    # real per-label P/R/F1
    --docs ../training/data/pseudonymized \
    --report ../training/docs/phase_4_pseudonymization_report.md
```

See the repo [README](../README.md) for the full picture and
[docs/architecture.md](../docs/architecture.md) for internals.
