# Setup Guide — Clone & Run the Full Project

Step-by-step instructions to clone this repository and run everything: the
**chatbot demo** (React UI + redaction API) and the **contract masking API**.

The repo has three runnable parts:

| Part | What it is | Port |
|---|---|---|
| **Chatbot backend** (`backend/main.py`) | Redaction API for the UI | 8000 |
| **Frontend** (`frontend/`) | React chatbot UI | 5173 |
| **Contract masking API** (`backend/masking_service/`) | NiFi/MLOps integration service | 8000 |

> The chatbot backend and the contract API both use port 8000 — run **one at a
> time**, not both together.

---

## 0. Prerequisites

Install these first:

- **Python 3.12** — <https://www.python.org/downloads/>
- **Node.js 20+** — <https://nodejs.org/> (for the frontend)
- **Git** — <https://git-scm.com/>
- **Tesseract OCR** *(optional — only for scanned PDFs/images)*:
  - Windows: <https://github.com/UB-Mannheim/tesseract/wiki> (install the Dutch
    language pack `nld` during setup)
  - Docker users don't need this; the `model` image installs it.
- **Docker** *(optional — only if you want the container path)*

Check they work:

```bash
python --version   # 3.12.x
node --version     # v20+ (v24 is fine)
git --version
```

---

## 1. Clone the repository

```bash
git clone <your-repo-url> End-to-End-PII-v2
cd End-to-End-PII-v2
```

---

## 2. Files you must provide (not included in Git)

These are intentionally **not** committed (secrets and large model files). You
supply them once:

### a) Environment file `.env`

```bash
cp .env.example .env      # Windows PowerShell: copy .env.example .env
```

Open `.env` and set at minimum:
- `SERVICE_TOKEN` — any long random string (needed by the contract API).
- If the model repo is **private**, also set `HF_TOKEN` (see below).

### b) The fine-tuned model weights

The MedRoBERTa PII model loads automatically from the Hugging Face Hub repo
**`ziadosama/pii-medroberta-nl`** on first run — no manual download needed if the
repo is public.

- **Private repo?** Authenticate once so it can download:
  ```bash
  huggingface-cli login          # or set HF_TOKEN in .env
  ```
- **Have a local copy of the weights?** Point to the folder instead of the Hub:
  ```
  PII_MODEL_DIR=C:/path/to/final-pii-model     # set this in .env
  ```

### c) The Dutch spaCy tokenizer

```bash
python -m spacy download nl_core_news_sm
```

*(Run this after installing the backend requirements in step 3.)*

---

## 3. Backend setup (Python)

Create a virtual environment and install the dependencies.

```bash
cd backend
python -m venv venv

# Activate it:
#   Windows (PowerShell):  venv\Scripts\Activate.ps1
#   Windows (cmd/bat):     venv\Scripts\activate
#   macOS/Linux:           source venv/bin/activate

pip install -r requirements.txt        # full model + detector stack
python -m spacy download nl_core_news_sm
cd ..
```

> First install is large (PyTorch, Transformers, etc.) and can take several
> minutes.

---

## 4. Run the project

Pick the part you want to run.

### Option A — Chatbot demo (easiest, Windows)

From the project root, just run the launcher:

```bash
start_chatbot.bat
```

It opens two windows (backend + frontend). When the frontend says
`ready in … ms`, open:

```
http://localhost:5173
```

Upload a PDF → you get a **downloadable masked PDF** back; type text → you get
masked text.

### Option A (manual, any OS)

Two terminals:

```bash
# Terminal 1 — backend
cd backend
venv\Scripts\activate            # or: source venv/bin/activate
python main.py                   # serves on http://localhost:8000
```

```bash
# Terminal 2 — frontend
cd frontend
npm install                      # first time only
npm run dev                      # serves on http://localhost:5173
```

### Option B — Contract masking API (locally)

```bash
# from the project root, with .env set (SERVICE_TOKEN)
pip install -r requirements-api.txt      # API runtime
# (the model stack from backend/requirements.txt is already installed in step 3)
cd backend
uvicorn masking_service.app:app --port 8000
```

Verify it:

```bash
curl http://localhost:8000/health     # {"status":"UP"}
curl http://localhost:8000/ready      # {"status":"READY",...}
```

### Option C — Contract masking API (Docker)

```bash
# production image (includes MedRoBERTa + OCR)
docker build --target model -t pii-masking-api:1.0.0-model .
docker compose up
```

See [HANDOFF.md](HANDOFF.md) for the MLOps deployment details.

---

## 5. Run the tests

```bash
pip install -r requirements-api.txt -r requirements-dev.txt
pytest        # 39 contract tests (uses the light regex masker; no GPU needed)
```

---

## 6. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: masking_service` | Run backend commands from the `backend/` folder, or `pytest` from the project root (a `conftest.py` sets the path). |
| Model download fails / 401 | The Hub repo is private — run `huggingface-cli login` or set `HF_TOKEN` in `.env`. |
| `OSError: [E050] Can't find model 'nl_core_news_sm'` | Run `python -m spacy download nl_core_news_sm`. |
| Scanned PDF/image gives an OCR error | Install Tesseract + the Dutch pack (`nld`), or use the Docker `model` image. |
| Port 8000 already in use | You're running the chatbot backend and the contract API at once — stop one. |
| `SERVICE_TOKEN must contain a runtime secret` | Set `SERVICE_TOKEN` in `.env` (contract API only). |

---

## Where to go next

- Project overview & architecture: [README.md](README.md), [docs/architecture.md](docs/architecture.md)
- API contract: [docs/PII_Masking_API_Contract_v1.2.md](docs/PII_Masking_API_Contract_v1.2.md)
- MLOps deployment/handoff: [HANDOFF.md](HANDOFF.md)
