"""Evaluate the masking model and log metrics to MLflow.

Run (from backend/):
    python -m masking_service.evaluate

What it logs to experiment "pii-masking-service":
    params : model_version, n_docs
    metrics: latency_ms_avg, latency_ms_p95, throughput_docs_per_s,
             residual_structured_pii_total, leakage_rate, files_with_leak,
             deterministic, acceptance_tests_passed

"Residual structured PII" re-scans the MASKED output for the high-precision
structured classes (email / phone / IBAN / INSZ / RIZIV). Those must be gone
after masking; any hit is a leak. This is the contract's "known-PII leakage
test" for the classes regex-poc-1 targets.

If MLflow isn't installed/reachable, metrics are printed and the run is skipped.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import time
from statistics import mean

from masking_service import masking_core as core

# High-precision structured classes that must never survive masking.
_LEAK_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "IBAN": re.compile(r"\b(?:NL|BE)\d{2}\s?(?:[A-Z0-9]{4}\s?){2,}[A-Z0-9]{1,4}\b"),
    "NATIONAL_ID": re.compile(r"\b\d{2}[.-]?\d{2}[.-]?\d{2}[- ]?\d{3}[.-]?\d{2}\b"),
    "PROVIDER_ID": re.compile(r"\b\d{1}[-]?\d{5}[-]?\d{2}[-]?\d{3}\b"),
    "PHONE": re.compile(r"(?<!\d)(?:\+(?:32|31)|0)[\s-]?\d[\s-]?\d{6,8}(?!\d)"),
}


def _load_docs(limit: int = 120) -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    pattern = os.path.join(here, "..", "..", "data", "final", "*.txt")
    docs = []
    for path in sorted(glob.glob(pattern))[:limit]:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            docs.append(f.read())
    return docs


def _run_acceptance_tests() -> tuple[int, int]:
    """Return (passed, ok) where ok=1 if the pytest suite fully passed."""
    here = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", os.path.join(here, "tests"), "-q"],
        capture_output=True,
        text=True,
        cwd=os.path.join(here, ".."),
    )
    m = re.search(r"(\d+) passed", proc.stdout + proc.stderr)
    passed = int(m.group(1)) if m else 0
    return passed, int(proc.returncode == 0)


def evaluate() -> dict:
    version = os.environ.get("MASKING_MODEL_VERSION", "regex-poc-1")
    # The MedRoBERTa masker self-registers on demand (heavy deps).
    if version == "medroberta-nl-1":
        from masking_service.medroberta_masker import register as _reg
        _reg()
    masker = core.get_masker(version)

    # MedRoBERTa is ~1000x slower per doc than regex; sample fewer unless the
    # caller overrides EVAL_DOC_LIMIT.
    default_limit = 15 if version == "medroberta-nl-1" else 120
    limit = int(os.environ.get("EVAL_DOC_LIMIT", str(default_limit)))
    docs = _load_docs(limit=limit)
    if not docs:
        docs = [
            "Patient Jan Jansen, tel 0475123456, mail jan@example.com, "
            "INSZ 85.07.30-033.61, IBAN BE68539007547034, op 12-03-2024."
        ]

    latencies: list[float] = []
    residual_total = 0
    files_with_leak = 0
    deterministic = 1

    for text in docs:
        raw = text.encode("utf-8")
        t0 = time.perf_counter()
        result = masker.mask_bytes(raw, core.TXT)
        latencies.append((time.perf_counter() - t0) * 1000.0)

        # Determinism: same input -> same sha256.
        if masker.mask_bytes(raw, core.TXT).sha256 != result.sha256:
            deterministic = 0

        masked = result.content.decode("utf-8")
        doc_leaks = sum(len(p.findall(masked)) for p in _LEAK_PATTERNS.values())
        residual_total += doc_leaks
        if doc_leaks:
            files_with_leak += 1

    latencies.sort()
    p95 = latencies[int(len(latencies) * 0.95) - 1] if latencies else 0.0
    total_s = sum(latencies) / 1000.0
    metrics = {
        "latency_ms_avg": round(mean(latencies), 3) if latencies else 0.0,
        "latency_ms_p95": round(p95, 3),
        "throughput_docs_per_s": round(len(docs) / total_s, 2) if total_s else 0.0,
        "residual_structured_pii_total": residual_total,
        "leakage_rate": round(files_with_leak / len(docs), 4),
        "files_with_leak": files_with_leak,
        "deterministic": deterministic,
    }

    passed, tests_ok = _run_acceptance_tests()
    metrics["acceptance_tests_passed"] = passed
    metrics["acceptance_tests_ok"] = tests_ok

    _log_to_mlflow(version, len(docs), metrics)
    return metrics


def _log_to_mlflow(version: str, n_docs: int, metrics: dict) -> None:
    try:
        import mlflow
    except ImportError:
        print("[evaluate] mlflow not installed; printing metrics only.")
        _print(version, n_docs, metrics)
        return

    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("pii-masking-service")
    with mlflow.start_run(run_name=f"evaluate-{version}"):
        mlflow.log_param("model_version", version)
        mlflow.log_param("n_docs", n_docs)
        for k, v in metrics.items():
            mlflow.log_metric(k, float(v))
    _print(version, n_docs, metrics)
    print(f"[evaluate] logged to MLflow tracking_uri={mlflow.get_tracking_uri()}")


def _print(version: str, n_docs: int, metrics: dict) -> None:
    print("=" * 50)
    print(f"model_version : {version}")
    print(f"n_docs        : {n_docs}")
    for k, v in metrics.items():
        print(f"{k:32s}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    evaluate()
