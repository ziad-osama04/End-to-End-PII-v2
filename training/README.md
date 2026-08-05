# training/ — data pipeline & model fine-tuning

Everything needed to **generate the data and (re)train the PII model**. This is
separate from the deployable service in `backend/` — nothing here is required to
*run* the masking API (the service loads the model from Hugging Face). It's here
so the repo is self-contained for reproducing the dataset and the model.

> This folder is excluded from the Docker image and its heavy data/secrets are
> git-ignored (see the repo `.gitignore` / `.dockerignore`).

## Layout

```
training/
├── src/
│   ├── extraction/         PDF → raw text
│   ├── detection/          PII detection (spaCy, MedRoBERTa, regex, tag parser)
│   ├── pseudonymization/   pseudonymizer.py — replaces real PII with fake PII
│   ├── synthesis/          report_generator.py, recombiner.py (synthetic data)
│   ├── schema/             schema_extractor.py
│   └── validation/         pii_validator.py
├── data/
│   ├── raw_text/           extracted source text
│   ├── detection/          *_pii_map.json (detected PII per doc)
│   ├── pseudonymized/      de-identified output (the eval set)
│   ├── schemas/  real/  final/  recombined/
│   └── synthetic_reports/  (also top-level below)
├── synthetic_reports/      training dataset (batch_final + jsonl + legacy) incl.
│                           the 150 spirometry negatives
├── generate_notebook.py    builds the fine-tune notebook
├── kaggle_finetune_medroberta.ipynb   the Kaggle/Colab fine-tune notebook
├── config.py               central config (paths, models, API keys via env)
├── main.py                 pipeline entry point
└── requirements.txt        pipeline dependencies
```

## Configuration & secrets

`config.py` reads API keys from the **environment** — never hard-code them:

```bash
# training/.env (git-ignored) or your shell
export OPENROUTER_API_KEYS="key1,key2"     # comma-separated
# or a single key:
export OPENROUTER_API_KEY="key"
```

> ⚠️ Earlier versions of `config.py` had keys hard-coded. Those keys are
> considered compromised — **rotate them** in the OpenRouter dashboard.

## De-identification policy (important)

`pseudonymizer.py` uses **precise de-identification** (`PSEUDONYMIZE_FREETEXT = False`):
it replaces only real identifiers (patient/doctor names, INSZ, RIZIV, address,
phone, URL, hospital) and **leaves clinical terms untouched** (disease eponyms
like *Von Willebrand*, medications, lab units). This keeps the output medically
useful and avoids training the model to mask clinical text. Set
`PSEUDONYMIZE_FREETEXT = True` only for an aggressive "mask anything name-shaped"
policy.

## Common tasks

```bash
cd training
pip install -r requirements.txt
python -m spacy download nl_core_news_lg      # detection model

# Regenerate the de-identified data with the current (precise) policy:
python src/pseudonymization/pseudonymizer.py

# Rebuild the fine-tune notebook after editing the label taxonomy:
python generate_notebook.py

# Add clinical-table negatives before a retrain (writes into synthetic_reports/):
python ../backend/scripts/augment_clinical_negatives.py --n 150
```

Then zip `synthetic_reports/` as `pii-dataset.zip` and run
`kaggle_finetune_medroberta.ipynb` on Kaggle (Internet On, GPU). The output
`final-pii-model/` is what the service loads (published as
`ziadosama/final-pii-model-v2`).

## Evaluating the trained model

Use the dataset-agnostic evaluator in the service:

```bash
cd ../backend
python -m masking_service.evaluate_precise \
    --docs   ../training/data/pseudonymized \
    --report ../training/docs/phase_4_pseudonymization_report.md
```
