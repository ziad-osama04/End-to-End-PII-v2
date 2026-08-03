"""Unit tests for mlflow_medroberta.py.

load_context() downloads real fine-tuned weights from the Hub, so predict()
is tested with self._masker stubbed directly (bypassing load_context) --
covering the row-building/error-handling logic that's this module's own
responsibility, not MedRoBERTa's detection accuracy (covered separately in
test_medroberta_masker.py) or a real network call.

_materialize_weights' local-directory branch is tested for real (no network);
its Hub-download branch is not, deliberately, to keep this suite offline.
"""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from masking_service import masking_core as core
from masking_service.mlflow_medroberta import (
    MODEL_VERSION,
    MedRobertaMLflowModel,
    _materialize_weights,
)


class _FakeMasker:
    """Stands in for MedRobertaMasker without touching torch/transformers."""

    def __init__(self, fail_with: Exception | None = None):
        self.fail_with = fail_with
        self.calls: list[tuple[bytes, str]] = []

    def mask_bytes(self, raw: bytes, media_type: str) -> core.MaskResult:
        self.calls.append((raw, media_type))
        if self.fail_with is not None:
            raise self.fail_with
        text = raw.decode("utf-8")
        masked = text.replace("secret", "<REDACTED>")
        content = masked.encode("utf-8")
        return core.MaskResult(
            content=content,
            entity_count=1 if masked != text else 0,
            model_version=MODEL_VERSION,
            sha256=hashlib.sha256(content).hexdigest(),
        )


@pytest.fixture
def model():
    m = MedRobertaMLflowModel()
    m._masker = _FakeMasker()
    return m


def test_predict_masks_and_reports_metadata(model):
    df = pd.DataFrame({"content": ["contains secret data"], "media_type": ["text/plain"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["masked_content"] == "contains <REDACTED> data"
    assert row["entity_count"] == 1
    assert row["model_version"] == MODEL_VERSION
    assert row["error"] == ""
    assert len(row["sha256"]) == 64


def test_predict_no_pii_reports_zero_entities(model):
    df = pd.DataFrame({"content": ["nothing sensitive here"], "media_type": ["text/plain"]})
    out = model.predict(None, df)
    row = out.iloc[0]
    assert row["masked_content"] == "nothing sensitive here"
    assert row["entity_count"] == 0


def test_predict_masker_exception_reports_error_not_crash():
    m = MedRobertaMLflowModel()
    m._masker = _FakeMasker(fail_with=core.MaskingError("boom"))
    df = pd.DataFrame({"content": ["secret data"], "media_type": ["text/plain"]})
    out = m.predict(None, df)
    row = out.iloc[0]
    assert row["error"] == "MaskingError"
    assert row["masked_content"] == ""  # never leaks the input on failure


def test_predict_handles_multiple_rows_independently(model):
    df = pd.DataFrame(
        {
            "content": ["secret one", "public two"],
            "media_type": ["text/plain", "text/plain"],
        }
    )
    out = model.predict(None, df)
    assert "<REDACTED>" in out.iloc[0]["masked_content"]
    assert out.iloc[1]["masked_content"] == "public two"


def test_predict_accepts_plain_dict_input(model):
    out = model.predict(None, {"content": ["secret x"], "media_type": ["text/plain"]})
    assert out.iloc[0]["masked_content"] == "<REDACTED> x"


def test_predict_missing_content_treated_as_empty_string(model):
    df = pd.DataFrame({"content": [None], "media_type": ["text/plain"]})
    model.predict(None, df)  # must not raise
    assert model._masker.calls[0][0] == b""


def test_predict_missing_media_type_defaults_to_text_plain(model):
    df = pd.DataFrame({"content": ["secret"], "media_type": [None]})
    model.predict(None, df)
    assert model._masker.calls[0][1] == "text/plain"


# --------------------------------------------------------------------------- #
# _materialize_weights -- local-directory branch (no network)
# --------------------------------------------------------------------------- #
def test_materialize_weights_uses_local_dir_when_set(tmp_path, monkeypatch):
    local_dir = tmp_path / "weights"
    local_dir.mkdir()
    monkeypatch.setenv("PII_MODEL_DIR", str(local_dir))

    result = _materialize_weights(str(tmp_path / "unused_dest"))
    assert result == str(local_dir)


def test_materialize_weights_falls_through_to_hub_when_local_dir_missing(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("PII_MODEL_DIR", str(tmp_path / "does_not_exist"))
    calls = []
    monkeypatch.setattr(
        "huggingface_hub.snapshot_download",
        lambda **kwargs: calls.append(kwargs) or str(tmp_path / "hub_download"),
    )

    result = _materialize_weights(str(tmp_path))
    assert result == str(tmp_path / "hub_download")
    assert calls[0]["repo_id"] == "ziadosama/pii-medroberta-nl"
