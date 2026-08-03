# PII Masking Service — contract API + MLflow

Implements the frozen **NiFi ⇄ masking-API** boundary from `api-contract.md` and
packages the masker as an **MLflow model** so it can be versioned, registered,
served, and evaluated.

```
masking_service/
├── masking_core.py     # deterministic, dependency-free masker (model version: regex-poc-1)
├── mlflow_model.py     # mlflow.pyfunc wrapper + log/register helper
├── log_model.py        # CLI: log + register the model to MLflow
├── app.py              # FastAPI service: GET /healthz, POST /v1/mask (the contract)
├── requirements.txt
└── tests/test_contract.py   # acceptance-evidence tests
```

## Why MLflow sits *behind* the HTTP contract

The contract's `POST /v1/mask` returns the **raw masked file bytes** with custom
`X-Masking-*` headers. MLflow's built-in scoring server only speaks JSON at
`/invocations` and can't emit that shape. So we use MLflow for what it's good at
— **immutable model versioning, the registry, reproducible loading, and
evaluation** — and put a thin FastAPI layer in front that loads the same MLflow
model and produces the exact byte-for-byte contract response.

Two ways to run inference:
- **Contract API** (`app.py`) — what NiFi calls. Bytes in, bytes out.
- **MLflow native** (`mlflow models serve`) — JSON `/invocations`, handy for
  quick testing and for `mlflow.evaluate`.

Both use the identical `masking_core`, so results match.

---

## Endpoints (contract)

### `GET /healthz`
Returns `200` **only** after the requested immutable model is loaded:
```json
{"status":"ok","model_version":"regex-poc-1"}
```

### `POST /v1/mask`
Request headers: `Authorization: Bearer <token>`, `Content-Type`
(`text/plain|text/csv|application/json`), `X-Request-ID`, `X-Source-Key`,
`X-Source-ETag`, `X-Model-Version`. Body = raw UTF-8 file bytes (≤ 10 MiB).

Response = masked file bytes + headers `X-Request-ID`, `X-Masking-Model-Version`,
`X-Masking-Entity-Count`, `X-Masked-Content-SHA256`.

Status codes: `200 / 400 / 401 / 409 / 413 / 415 / 422 / 503` exactly as the
contract's table. Never `429`; transient failures are `503`.

---

## Exact MLflow steps

All commands run from the `backend/` directory.

```bash
cd backend
pip install -r masking_service/requirements.txt
```

### 1. Start an MLflow tracking server (terminal 1)
MLflow 3.x requires a database backend (the old `./mlruns` file store is
deprecated), so point it at a local SQLite DB:
```bash
mlflow server --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///mlflow.db \
  --artifacts-destination ./mlartifacts
```
This serves the MLflow UI at http://127.0.0.1:5000 and a registry backend.

> No server? You can skip terminal 1 and log straight to the SQLite DB by
> setting `MLFLOW_TRACKING_URI=sqlite:///mlflow.db` in the next step.

### 2. Log + register the model (terminal 2)
```bash
# Against the server:
export MLFLOW_TRACKING_URI=http://127.0.0.1:5000
# ...or serverless, straight to SQLite:
# export MLFLOW_TRACKING_URI=sqlite:///mlflow.db
# Windows PowerShell: $env:MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
export MASKING_MODEL_VERSION=regex-poc-1
python -m masking_service.log_model
```
This creates experiment **pii-masking-service**, logs the pyfunc model, registers
it as **pii-masking-service** in the Model Registry, and prints a `model_uri`
like `runs:/<run_id>/masking_model`. Open the UI → *Models* to see version 1.

### 3. Inference with MLflow (native JSON)
Load and predict in Python:
```python
import mlflow.pyfunc, pandas as pd
m = mlflow.pyfunc.load_model("models:/pii-masking-service/1")   # or the runs:/... uri
print(m.predict(pd.DataFrame({
    "content": ["bel 0475123456 of mail jan@example.com"],
    "media_type": ["text/plain"],
})))
# -> masked_content, entity_count, model_version, sha256, error
```
Or serve it as a REST endpoint:
```bash
mlflow models serve -m "models:/pii-masking-service/1" -p 5001 --env-manager local
curl -s http://127.0.0.1:5001/invocations \
  -H 'Content-Type: application/json' \
  -d '{"dataframe_split":{"columns":["content","media_type"],
        "data":[["bel 0475123456","text/plain"]]}}'
```

### 4. Testing / evaluation logged to MLflow
Run the contract acceptance tests and log a pass/fail metric + the model's
precision/recall to an MLflow run:
```bash
python -m masking_service.evaluate            # writes metrics to the active experiment
python -m pytest masking_service/tests -v     # 28 acceptance-evidence tests
```
`evaluate.py` logs `precision`, `recall`, `f1`, and `acceptance_tests_passed`
to a run under experiment **pii-masking-service** so results show up in the UI.

### 5. Run the contract API backed by the MLflow model
Point the FastAPI service at the registered model and start it:
```bash
export MASKING_API_TOKEN=change-me-internal-token
export MASKING_MODEL_URI="models:/pii-masking-service/1"    # omit to use in-process masker
uvicorn masking_service.app:app --host 0.0.0.0 --port 9000
```
Smoke test:
```bash
curl -i http://127.0.0.1:9000/healthz
curl -i http://127.0.0.1:9000/v1/mask \
  -H "Authorization: Bearer change-me-internal-token" \
  -H "Content-Type: text/plain" \
  -H "X-Request-ID: req-1" -H "X-Source-Key: k" \
  -H "X-Source-ETag: e" -H "X-Model-Version: regex-poc-1" \
  --data-binary "bel 0475123456"
```

---

## Configuration (environment variables)

| Var | Used by | Default | Meaning |
|---|---|---|---|
| `MASKING_API_TOKEN` | `app.py` | *(empty → all requests 401)* | internal bearer token |
| `MASKING_MODEL_VERSION` | all | `regex-poc-1` | immutable model version to load |
| `MASKING_MODEL_URI` | `app.py` | *(unset → in-process masker)* | MLflow model uri to load |
| `MLFLOW_TRACKING_URI` | `log_model.py`, `evaluate.py` | *(unset)* | `http://127.0.0.1:5000` or `sqlite:///mlflow.db` (file store is deprecated in MLflow 3.x) |

## Model versions

- **`regex-poc-1`** — deterministic, dependency-free regex masker. Always
  available; matches the `model_version` named in the contract. Masks:
  `EMAIL, IBAN, NATIONAL_ID (INSZ), PROVIDER_ID (RIZIV), PHONE, ADDRESS,
  HOSPITAL, BMI, DATE, AGE, HEIGHT, WEIGHT`.
- **`medroberta-nl-1`** — the fine-tuned **MedRoBERTa** detector
  (`ziadosama/pii-medroberta-nl` + Presidio + Dutch regex, from
  `backend/src/detection`). Adds free-text entities regex can't catch, notably
  `PATIENT_NAME`, `DOCTOR_NAME`, `DOSSIER_NUMBER`, `SPECIALTY`, `ORG`, `WEBSITE`.
  Wrapped by [medroberta_masker.py](medroberta_masker.py); it reuses the exact
  same TXT/CSV/JSON structure preservation and validation as the base masker.

### Uploading the fine-tuned MedRoBERTa model to MLflow

[mlflow_medroberta.py](mlflow_medroberta.py) logs a **self-contained** pyfunc:
the fine-tuned weights are downloaded once from the Hub and **bundled as MLflow
artifacts**, so the model is genuinely uploaded to the server and needs no Hub
access at serve time.

```bash
# from backend/, with MLFLOW_TRACKING_URI (+ auth) set as above:
$env:MASKING_MODEL_VERSION="medroberta-nl-1"
python -m masking_service.mlflow_medroberta          # uploads weights + code
```
Then load / serve it exactly like the POC model:
```python
import mlflow.pyfunc, pandas as pd
m = mlflow.pyfunc.load_model("models:/pii-masking-service/<version>")
m.predict(pd.DataFrame({"content":["patient Dirk Willaert"], "media_type":["text/plain"]}))
# -> "<PATIENT_NAME>"
```
Run the contract API on it: set `MASKING_MODEL_VERSION=medroberta-nl-1` (in-process)
or `MASKING_MODEL_URI=models:/pii-masking-service/<version>` (from MLflow).

> The `upload_to_mlflow.ps1` helper defaults to `medroberta-nl-1`. Pass
> `-ModelVersion regex-poc-1` to upload the lightweight POC instead.
