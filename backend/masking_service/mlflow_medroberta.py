"""Package + upload the fine-tuned MedRoBERTa masking model to MLflow.

This logs a **self-contained** MLflow ``pyfunc`` model whose artifacts include
the actual fine-tuned weights (downloaded once from the Hugging Face Hub and
bundled), so the model is genuinely *uploaded* to the tracking server -- it does
not depend on Hub access at serve time.

Bundled into the logged model:
    artifacts.hf_model    -> the fine-tuned weights/tokenizer/config
    artifacts.masking_core-> masking_core.py (dependency-free)
    code_paths            -> masking_service/ and src/ (masker + detector code)

At load time the pyfunc points ``PII_MODEL_DIR`` at the bundled weights and
masks exactly like the live service.

CLI:
    python -m masking_service.mlflow_medroberta
Env:
    MLFLOW_TRACKING_URI      e.g. https://mlflow.me
    MLFLOW_TRACKING_USERNAME / MLFLOW_TRACKING_PASSWORD   (if the server needs auth)
    HF_MODEL_REPO            default "ziadosama/pii-medroberta-nl"
    PII_MODEL_DIR            optional: use a local weights dir instead of the Hub
"""
from __future__ import annotations

import os
import tempfile

import mlflow
import pandas as pd

HF_MODEL_REPO = os.environ.get("HF_MODEL_REPO", "ziadosama/pii-medroberta-nl")
MODEL_VERSION = "medroberta-nl-1"
REGISTERED_NAME = "pii-masking-service"


def _here() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _backend_dir() -> str:
    return os.path.dirname(_here())


def _materialize_weights(dest_root: str) -> str:
    """Return a local dir holding the fine-tuned weights.

    Uses PII_MODEL_DIR if it points at a real directory; otherwise downloads a
    full snapshot of the Hub repo into ``dest_root`` so it can be bundled.
    """
    local = os.environ.get("PII_MODEL_DIR")
    if local and os.path.isdir(local):
        print(f"[mlflow_medroberta] using local weights: {local}")
        return local

    from huggingface_hub import snapshot_download

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    print(f"[mlflow_medroberta] downloading weights from Hub: {HF_MODEL_REPO}")
    path = snapshot_download(
        repo_id=HF_MODEL_REPO,
        local_dir=os.path.join(dest_root, "hf_model"),
        token=token,
        # weights + config + tokenizer only; skip the git metadata.
        ignore_patterns=["*.msgpack", "*.h5", ".gitattributes", "README.md"],
    )
    return path


class MedRobertaMLflowModel(mlflow.pyfunc.PythonModel):
    """pyfunc that masks files using the bundled fine-tuned weights."""

    def load_context(self, context):
        import sys

        # Point the detector at the bundled weights (offline, no Hub needed).
        os.environ["PII_MODEL_DIR"] = context.artifacts["hf_model"]

        # code_paths dir is already on sys.path; ensure it also finds `src`.
        for p in sys.path:
            if os.path.isdir(os.path.join(p, "src", "detection")):
                break

        from masking_service.medroberta_masker import MedRobertaMasker

        self._masker = MedRobertaMasker()
        # warm up so the first real request is fast and /healthz-style probes pass
        self._masker.mask_bytes(b"warmup", "text/plain")

    def predict(self, context, model_input):
        import hashlib

        if isinstance(model_input, dict):
            model_input = pd.DataFrame(model_input)
        rows = []
        for _, row in model_input.iterrows():
            content = "" if pd.isna(row.get("content")) else str(row.get("content"))
            media_type = str(row.get("media_type") or "text/plain")
            out = {
                "masked_content": "",
                "entity_count": 0,
                "model_version": MODEL_VERSION,
                "sha256": "",
                "error": "",
            }
            try:
                result = self._masker.mask_bytes(content.encode("utf-8"), media_type)
                out.update(
                    masked_content=result.content.decode("utf-8"),
                    entity_count=result.entity_count,
                    model_version=result.model_version,
                    sha256=result.sha256,
                )
            except Exception as exc:  # never leak input; report as error row
                out["error"] = f"{type(exc).__name__}"
            rows.append(out)
        return pd.DataFrame(rows)


def log_medroberta_model(registered_model_name: str | None = REGISTERED_NAME):
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

    with tempfile.TemporaryDirectory() as tmp:
        weights_dir = _materialize_weights(tmp)

        artifacts = {
            "hf_model": weights_dir,
            "masking_core": os.path.join(_here(), "masking_core.py"),
        }
        code_paths = [
            os.path.join(_backend_dir(), "masking_service"),
            os.path.join(_backend_dir(), "src"),
        ]
        pip_requirements = [
            "mlflow", "pandas", "torch", "transformers",
            "presidio-analyzer", "presidio-anonymizer", "spacy>=3.8,<3.9",
            # Dutch spaCy tokenizer used by the detector:
            "https://github.com/explosion/spacy-models/releases/download/"
            "nl_core_news_sm-3.8.0/nl_core_news_sm-3.8.0-py3-none-any.whl",
        ]

        kwargs = dict(
            python_model=MedRobertaMLflowModel(),
            artifacts=artifacts,
            code_paths=code_paths,
            signature=signature,
            pip_requirements=pip_requirements,
            metadata={"model_version": MODEL_VERSION, "hf_repo": HF_MODEL_REPO},
        )
        try:
            info = mlflow.pyfunc.log_model(name="medroberta_masking_model", **kwargs)
        except TypeError:
            info = mlflow.pyfunc.log_model(artifact_path="medroberta_masking_model", **kwargs)

    mlflow.set_tag("model_version", MODEL_VERSION)
    if registered_model_name:
        try:
            mlflow.register_model(info.model_uri, registered_model_name)
        except Exception as exc:
            print(f"[mlflow_medroberta] registry step skipped: {exc}")
    return info


def main() -> None:
    if os.environ.get("MLFLOW_TRACKING_URI"):
        mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
    mlflow.set_experiment("pii-masking-service")

    with mlflow.start_run(run_name=f"log-{MODEL_VERSION}") as run:
        mlflow.log_param("model_version", MODEL_VERSION)
        mlflow.log_param("hf_repo", HF_MODEL_REPO)
        info = log_medroberta_model()
        print("=" * 60)
        print(f"Uploaded fine-tuned model version : {MODEL_VERSION}")
        print(f"run_id                            : {run.info.run_id}")
        print(f"model_uri                         : {info.model_uri}")
        print(f"tracking_uri                      : {mlflow.get_tracking_uri()}")
        print("=" * 60)


if __name__ == "__main__":
    main()
