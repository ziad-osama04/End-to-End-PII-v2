"""Shared pytest bootstrap.

The masking service is a package under ``backend/`` (imported as
``masking_service``), so ``backend/`` goes on ``sys.path``. A test token and the
default deterministic model version are seeded here so importing the app never
depends on a developer's shell environment.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"

if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("SERVICE_TOKEN", "test-token")
os.environ.setdefault("MASKING_MODEL_VERSION", "regex-poc-1")
os.environ.pop("MODEL_URI", None)
os.environ.pop("MASKING_MODEL_URI", None)
