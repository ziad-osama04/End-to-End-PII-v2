"""MLflow ``pyfunc`` packaging for the masking core.

Why MLflow sits *behind* the HTTP contract, not in front of it:

    The frozen contract (`/v1/mask`) returns the *raw masked file bytes* with
    custom `X-Masking-*` headers. MLflow's built-in scoring server only speaks
    JSON at `/invocations` and cannot emit that response shape. So MLflow is used
    for what it is good at -- immutable model **versioning**, the **registry**,
    reproducible **loading**, and **evaluation/testing** -- while the FastAPI
    layer (``app.py``) provides the exact byte-for-byte contract by loading this
    same pyfunc model.

The pyfunc signature (JSON-friendly, so ``mlflow models serve`` also works):

    input  : pandas.DataFrame with columns
                 content    (str)  -- the raw file text (UTF-8)
                 media_type (str)  -- one of text/plain, text/csv, application/json
    output : pandas.DataFrame with columns
                 masked_content (str)
                 entity_count   (int)
                 model_version  (str)
                 sha256         (str)
                 error          (str, "" when ok)

One row per file; a row that fails validation is returned with ``error`` set and
empty ``masked_content`` -- it never leaks the original input.
"""
from __future__ import annotations

import os
from typing import List

import mlflow.pyfunc
import pandas as pd

# Model version this artifact represents. Immutable once logged; the HTTP layer
# rejects any request whose X-Model-Version differs (contract: HTTP 409).
DEFAULT_MODEL_VERSION = os.environ.get("MASKING_MODEL_VERSION", "regex-poc-1")

ARTIFACT_KEY = "masking_service"


class MaskingModel(mlflow.pyfunc.PythonModel):
    """pyfunc wrapper. Loads the dependency-free masking core at serve time."""

    def load_context(self, context):  # noqa: D401 - MLflow hook
        # Importing here keeps the logged model self-describing via code paths
        # in ``artifacts`` (see log_masking_model). The core has no heavy deps.
        import importlib.util
        import sys

        core_path = context.artifacts[ARTIFACT_KEY]
        spec = importlib.util.spec_from_file_location("masking_core_loaded", core_path)
        module = importlib.util.module_from_spec(spec)
        # Register BEFORE exec so @dataclass can resolve cls.__module__ via
        # sys.modules (otherwise dataclass creation raises AttributeError).
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        self._core = module
        self._masker = module.get_masker(_model_version_from_env(module))

    def predict(self, context, model_input: "pd.DataFrame") -> "pd.DataFrame":
        if isinstance(model_input, dict):
            model_input = pd.DataFrame(model_input)
        rows: List[dict] = []
        for _, row in model_input.iterrows():
            content = "" if pd.isna(row.get("content")) else str(row.get("content"))
            media_type = str(row.get("media_type") or self._core.TXT)
            rows.append(self._mask_one(content, media_type))
        return pd.DataFrame(rows)

    def _mask_one(self, content: str, media_type: str) -> dict:
        ok = {
            "masked_content": "",
            "entity_count": 0,
            "model_version": self._masker.model_version,
            "sha256": "",
            "error": "",
        }
        try:
            result = self._masker.mask_bytes(content.encode("utf-8"), media_type)
        except self._core.UnsupportedMediaType as exc:
            ok["error"] = f"unsupported_media_type:{exc}"
            return ok
        except self._core.MaskingError as exc:
            ok["error"] = f"masking_error:{exc}"
            return ok
        ok.update(
            masked_content=result.content.decode("utf-8"),
            entity_count=result.entity_count,
            model_version=result.model_version,
            sha256=result.sha256,
        )
        return ok


def _model_version_from_env(core_module) -> str:
    version = os.environ.get("MASKING_MODEL_VERSION", DEFAULT_MODEL_VERSION)
    if version not in core_module.available_versions():
        # Fall back to the guaranteed POC masker rather than fail to load.
        return "regex-poc-1"
    return version


# --------------------------------------------------------------------------- #
# Logging / registering helper
# --------------------------------------------------------------------------- #
def _core_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "masking_core.py")


def log_masking_model(
    registered_model_name: str | None = "pii-masking-service",
    model_version_tag: str = DEFAULT_MODEL_VERSION,
):
    """Log the pyfunc model to the active MLflow run and (optionally) register it.

    Returns the ``ModelInfo`` from ``mlflow.pyfunc.log_model``.
    """
    from mlflow.models.signature import ModelSignature
    from mlflow.types.schema import ColSpec, Schema

    input_schema = Schema([ColSpec("string", "content"), ColSpec("string", "media_type")])
    output_schema = Schema([
        ColSpec("string", "masked_content"),
        ColSpec("long", "entity_count"),
        ColSpec("string", "model_version"),
        ColSpec("string", "sha256"),
        ColSpec("string", "error"),
    ])
    signature = ModelSignature(inputs=input_schema, outputs=output_schema)

    input_example = pd.DataFrame(
        {
            "content": ["Bel 0475123456 of mail jan@example.com"],
            "media_type": ["text/plain"],
        }
    )

    kwargs = dict(
        python_model=MaskingModel(),
        artifacts={ARTIFACT_KEY: _core_path()},
        signature=signature,
        input_example=input_example,
        pip_requirements=["mlflow", "pandas"],
        metadata={"model_version": model_version_tag},
    )
    # MLflow renamed the positional arg across versions; support both.
    try:
        info = mlflow.pyfunc.log_model(name="masking_model", **kwargs)
    except TypeError:
        info = mlflow.pyfunc.log_model(artifact_path="masking_model", **kwargs)

    mlflow.set_tag("model_version", model_version_tag)

    if registered_model_name:
        try:
            mlflow.register_model(info.model_uri, registered_model_name)
        except Exception as exc:  # registry may be unavailable (no backend store)
            print(f"[log_masking_model] registry step skipped: {exc}")
    return info
