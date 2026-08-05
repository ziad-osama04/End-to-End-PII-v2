# Phase 8 — PII Validation Report
Generated: 2026-07-26T12:09:09.831006

## Summary
- **Documents validated**: 267
- **Passed**: 267
- **Failed**: 0
- **Pass rate**: 100.0%

## Validation Strategy
The validator checks synthetic reports for:
1. **Blocklist matches** — Original leaked PII values from source documents (e.g., "AZORG")
2. **Original redaction tag leaks** — Template placeholders from source PDFs (PATIENT A, dr. ARTS_X, [ADRES], etc.)
3. **Real Belgian identifier patterns** — INSZ, RIZIV, IBAN, phone numbers, emails

> **Note**: Synthetic reports intentionally contain Faker-generated fake names, dates,
> and hospital names. These are NOT flagged as they are expected synthetic content.


---
## Final Certificate
**267/267 reports passed all PII validation checks.**
Validated reports saved to: `data/final/`

In our current repository, we are actually using a **multi-layer approach** for PII detection, but it relies primarily on **spaCy** rather than a Transformer model like MedRoBERTa or RobBERT. 

Here is exactly what is actively running in our `pii_detector.py` code right now:

### 1. spaCy (`nl_core_news_lg`)
This is our core NLP engine for Named Entity Recognition (NER). It is a statistical model (not a Transformer) that looks for generic entity types like `PERSON`, `ORGANIZATION`, and `LOCATION`.
* **Cost:** Zero GPU required. It runs extremely fast on a standard CPU.
* **Why we used it:** It serves as a fast baseline to catch things like hospital names ("AZORG") or unexpected names.

### 2. Custom Regex & Logic (`dutch_regex.py`)
Because spaCy isn't perfect at catching highly specific medical or Belgian identifiers, we built custom regex recognizers that run alongside it in Microsoft Presidio. This layer actively catches:
* Dates of birth, Age, Height, Weight, BMI
* Belgian Identifiers (INSZ, RIZIV, Phone numbers, IBANs)

### 3. Redaction Tag Parsers (`tag_parser.py`)
This layer specifically looks for the existing template placeholders in the HealthOne NOVA documents (e.g., `PATIENT A`, `dr. ARTS_C`, `[ADRES]`).

---

### What about MedRoBERTa.nl?
You might notice that `MEDROBERTA_MODEL = "CLTL/MedRoBERTa.nl"` is defined in our `config.py` file, and it was mentioned in the original implementation plan. However, **it is not actually hooked up or running** in the current `pii_detector.py` script. The detection is currently handled 100% by spaCy and Regex. 

**Summary:** 
Currently, the pipeline is extremely lightweight and cheap to run because it only uses **spaCy + Regex** for detection. If you want to increase the recall (accuracy) for complex, unstructured text, we could easily update `pii_detector.py` to use a Transformer like **RobBERT** or **MedRoBERTa.nl** as the backend engine for Presidi