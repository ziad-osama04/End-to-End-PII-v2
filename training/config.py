"""Central configuration for the End-to-End PII Pipeline."""

import os

# Models
SPACY_MODEL = "nl_core_news_lg"
BERTJE_MODEL = "GroNLP/bert-base-dutch-cased"
OLLAMA_MODEL = "qwen3:8b"

# OpenRouter API (cloud fallback when Ollama is not available).
# Keys are read from the environment — NEVER hard-code them. Set OPENROUTER_API_KEYS
# to a comma-separated list (or OPENROUTER_API_KEY for a single key), e.g. in a
# git-ignored training/.env loaded by your shell.
OPENROUTER_API_KEYS = [k.strip() for k in os.environ.get("OPENROUTER_API_KEYS", "").split(",") if k.strip()]
OPENROUTER_API_KEY = OPENROUTER_API_KEYS[0] if OPENROUTER_API_KEYS else os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "qwen/qwen3-8b"

# Generation
NUM_SYNTHETIC_REPORTS = 5000
BATCH_SIZE = 10
MAX_REPORT_LENGTH = 500  # words

# PII Detection
PII_CONFIDENCE_THRESHOLD = 0.7
MAX_VALIDATION_RETRIES = 3

# Known leaked PII (from table2 analysis)
HOSPITAL_BLOCKLIST = ["AZORG"]
FAKER_LOCALE = "nl_BE"  # Belgian context (primary)
FAKER_LOCALE_FALLBACK = "nl_NL"

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = BASE_DIR
RAW_TEXT_DIR = os.path.join(BASE_DIR, "data", "raw_text")
DETECTION_DIR = os.path.join(BASE_DIR, "data", "detection")
PSEUDONYMIZED_DIR = os.path.join(BASE_DIR, "data", "pseudonymized")
SCHEMAS_DIR = os.path.join(BASE_DIR, "data", "schemas")
RECOMBINED_DIR = os.path.join(BASE_DIR, "data", "recombined")
SYNTHETIC_DIR = os.path.join(BASE_DIR, "data", "synthetic_reports")
FINAL_DIR = os.path.join(BASE_DIR, "data", "final")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# Ensure directories exist (useful when imported)
def ensure_directories():
    directories = [
        RAW_TEXT_DIR, DETECTION_DIR, PSEUDONYMIZED_DIR,
        SCHEMAS_DIR, RECOMBINED_DIR, SYNTHETIC_DIR,
        FINAL_DIR, DOCS_DIR, LOGS_DIR
    ]
    for d in directories:
        os.makedirs(d, exist_ok=True)
