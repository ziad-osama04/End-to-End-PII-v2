"""Unit tests for mlflow_model.py's MaskingModel pyfunc wrapper.

load_context() needs a real MLflow PythonModelContext with artifacts, so these
tests bypass it and wire _core/_masker directly -- exactly the state
load_context would have produced -- to test predict()'s row-by-row logic and
error handling without needing an actual MLflow run.
"""
from __future__ import annotations

import pandas as pd
import pytest

from masking_service import masking_core as core
from masking_service.mlflow_model import MaskingModel, _model_version_from_env


@pytest.fixture
def model():
    m = MaskingModel()
    m._core = core
    m._masker = core.get_masker("regex-poc-1")
    return m


def test_predict_masks_pii_and_reports_metadata(model):
    df = pd.DataFrame({"content": ["bel 0475123456"], "media_type": ["text/plain"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["masked_content"] == "bel <PHONE>"
    assert row["entity_count"] == 1
    assert row["model_version"] == "regex-poc-1"
    assert row["error"] == ""
    assert len(row["sha256"]) == 64


def test_predict_handles_multiple_rows_independently(model):
    df = pd.DataFrame(
        {
            "content": ["bel 0475123456", "mail jan@example.com"],
            "media_type": ["text/plain", "text/plain"],
        }
    )
    out = model.predict(None, df)
    assert out.iloc[0]["masked_content"] == "bel <PHONE>"
    assert out.iloc[1]["masked_content"] == "mail <EMAIL>"


def test_predict_unsupported_media_type_reports_error_not_exception(model):
    df = pd.DataFrame({"content": ["<a/>"], "media_type": ["application/xml"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["error"].startswith("unsupported_media_type")
    assert row["masked_content"] == ""


def test_predict_masking_error_reports_error_not_exception(model):
    df = pd.DataFrame({"content": ["{not json"], "media_type": ["application/json"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["error"].startswith("masking_error")
    assert row["masked_content"] == ""


def test_predict_never_leaks_original_content_on_error(model):
    df = pd.DataFrame({"content": ['{"phone": "0475123456"'], "media_type": ["application/json"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert "0475123456" not in row["error"]
    assert row["masked_content"] == ""


def test_predict_accepts_plain_dict_input(model):
    out = model.predict(None, {"content": ["bel 0475123456"], "media_type": ["text/plain"]})
    assert out.iloc[0]["masked_content"] == "bel <PHONE>"


def test_predict_missing_content_treated_as_empty(model):
    df = pd.DataFrame({"content": [None], "media_type": ["text/plain"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["error"] != ""  # empty body is a MaskingError, not a crash


def test_predict_missing_media_type_defaults_to_text_plain(model):
    df = pd.DataFrame({"content": ["bel 0475123456"], "media_type": [None]})
    out = model.predict(None, df)
    assert out.iloc[0]["masked_content"] == "bel <PHONE>"


# --------------------------------------------------------------------------- #
# _model_version_from_env
# --------------------------------------------------------------------------- #
def test_model_version_from_env_uses_registered_version(monkeypatch):
    monkeypatch.setenv("MASKING_MODEL_VERSION", "regex-poc-1")
    assert _model_version_from_env(core) == "regex-poc-1"


def test_model_version_from_env_falls_back_for_unregistered_version(monkeypatch):
    monkeypatch.setenv("MASKING_MODEL_VERSION", "does-not-exist")
    assert _model_version_from_env(core) == "regex-poc-1"
