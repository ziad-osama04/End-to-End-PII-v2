"""Log + register the masking pyfunc model to MLflow.

Run:
    python -m masking_service.log_model

Env:
    MLFLOW_TRACKING_URI     e.g. http://127.0.0.1:5000  (defaults to ./mlruns)
    MASKING_MODEL_VERSION   immutable version tag, default "regex-poc-1"

Prints the resulting model_uri and (if a run server is up) the run URL.
"""
from __future__ import annotations

import os

import mlflow

from masking_service.mlflow_model import DEFAULT_MODEL_VERSION, log_masking_model


def main() -> None:
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI")
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("pii-masking-service")

    version = os.environ.get("MASKING_MODEL_VERSION", DEFAULT_MODEL_VERSION)

    with mlflow.start_run(run_name=f"log-{version}") as run:
        mlflow.log_param("model_version", version)
        info = log_masking_model(
            registered_model_name="pii-masking-service",
            model_version_tag=version,
        )
        print("=" * 60)
        print(f"Logged masking model  version : {version}")
        print(f"run_id                        : {run.info.run_id}")
        print(f"model_uri                     : {info.model_uri}")
        print(f"tracking_uri                  : {mlflow.get_tracking_uri()}")
        print("=" * 60)
        print("Load it back with:")
        print(f"  import mlflow.pyfunc")
        print(f"  m = mlflow.pyfunc.load_model('{info.model_uri}')")


if __name__ == "__main__":
    main()
