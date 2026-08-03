"""Masking service: contract-compliant PII masking boundary + MLflow packaging.

Public surface:
    masking_core   -- deterministic, dependency-free maskers + structure-preserving apply
    mlflow_model   -- mlflow.pyfunc wrapper around a masker (immutable model versions)
    app            -- FastAPI service implementing the frozen NiFi <-> AI-team contract
"""
