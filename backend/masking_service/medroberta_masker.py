"""MedRoBERTa masker (model version ``medroberta-nl-1``).

Wraps the project's fine-tuned Dutch clinical PII detector
(``backend/src/detection``: Presidio + the ``ziadosama/final-pii-model-v2``
MedRoBERTa token-classifier + Dutch regex) as a :class:`masking_core.Masker`.

It only overrides ``mask_string`` -- the TXT/CSV/JSON structure preservation,
output validation, SHA256, and byte handling are inherited from the base
``Masker`` unchanged, so behaviour matches the contract for every media type.

Heavy deps (torch/transformers/presidio/spaCy) are imported lazily on first use,
so importing this module is cheap and never breaks the dependency-free core.

Model source resolution (handled by ``src.detection.transformers_recognizer``):
    * ``PII_MODEL_DIR`` env var -> load weights from that local directory
      (this is how the MLflow-bundled model loads its own artifacts offline);
    * otherwise the Hugging Face Hub repo ``ziadosama/final-pii-model-v2``.
"""
from __future__ import annotations

import os
import sys
from typing import Tuple

from masking_service import masking_core as core

MODEL_VERSION = "final-pii-model-v2"


def _add_backend_to_path() -> None:
    """Ensure ``backend/`` is importable so ``import src.detection...`` works."""
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)


class MedRobertaMasker(core.Masker):
    model_version = MODEL_VERSION

    def __init__(self) -> None:
        self._detector = None
        self._keep_visible = None
        self._operator_config = None

    def _ensure(self):
        if self._detector is None:
            _add_backend_to_path()
            from src.detection.pii_detector import get_detector, KEEP_VISIBLE
            from presidio_anonymizer.entities import OperatorConfig

            self._detector = get_detector()
            self._keep_visible = KEEP_VISIBLE
            self._operator_config = OperatorConfig
        return self._detector

    def mask_string(self, text: str) -> Tuple[str, int]:
        if not text or not text.strip():
            return text, 0
        detector = self._ensure()

        from src.detection.pii_detector import resolve_overlaps

        results = detector.analyzer.analyze(text=text, language="nl")
        # Keep clinical content visible; redact only identifying entities
        # (identical policy to PIIDetector.redact_text).
        results = [r for r in results if r.entity_type not in self._keep_visible]
        results = resolve_overlaps(results)
        if not results:
            return text, 0

        entity_types = {r.entity_type for r in results}
        operators = {
            et: self._operator_config("replace", {"new_value": f"<{et}>"})
            for et in entity_types
        }
        operators["DEFAULT"] = self._operator_config(
            "replace", {"new_value": "<REDACTED>"}
        )
        anonymized = detector.anonymizer.anonymize(
            text=text, analyzer_results=results, operators=operators
        )
        return anonymized.text, len(results)

    def detect_spans(self, text):
        if not text or not text.strip():
            return []
        from src.detection.pii_detector import resolve_overlaps

        detector = self._ensure()
        results = detector.analyzer.analyze(text=text, language="nl")
        results = [r for r in results if r.entity_type not in self._keep_visible]
        results = resolve_overlaps(results)
        return [(r.start, r.end, r.entity_type) for r in results]


def register() -> MedRobertaMasker:
    """Register the MedRoBERTa masker into the core registry and return it."""
    masker = MedRobertaMasker()
    core.register(masker)
    return masker
