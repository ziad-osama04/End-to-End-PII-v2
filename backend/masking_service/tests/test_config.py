"""Unit tests for config.py -- release identity and settings loading.

Contract v1.2 sections 2 and 7 require /version and every masked response to
report immutable identifiers, refusing moving labels like "latest".
"""
from __future__ import annotations

import pytest

from masking_service import config as cfg


def _clear_release_env(monkeypatch):
    for name in (
        "SERVICE_RELEASE", "GIT_SHA", "IMAGE_DIGEST", "MODEL_VERSION", "MODEL_DIGEST",
        "MODEL_URI", "MASKING_MODEL_URI", "MODEL_VERSION_TAG", "MASKING_MODEL_VERSION",
        "SERVICE_TOKEN", "MASKING_API_TOKEN", "MAX_UPLOAD_SIZE_BYTES", "MAX_CONCURRENT_MASKS",
        "SERVICE_NAME", "MODEL_NAME", "APP_NAME", "APP_VERSION", "LOG_LEVEL",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def clean_env(monkeypatch):
    _clear_release_env(monkeypatch)
    return monkeypatch


# --------------------------------------------------------------------------- #
# load_settings defaults
# --------------------------------------------------------------------------- #
def test_defaults_report_unknown_when_unset(clean_env):
    settings = cfg.load_settings()
    assert settings.service_release == cfg.UNKNOWN_IDENTIFIER
    assert settings.git_sha == cfg.UNKNOWN_IDENTIFIER
    assert settings.image_digest == cfg.UNKNOWN_IDENTIFIER
    assert settings.model_digest == cfg.UNKNOWN_IDENTIFIER
    assert settings.masking_model_version == "regex-poc-1"
    assert settings.api_contract_version == "v1"


def test_legacy_env_names_are_honored_as_fallbacks(clean_env):
    clean_env.setenv("MASKING_API_TOKEN", "legacy-token")
    clean_env.setenv("MASKING_MODEL_VERSION", "medroberta-nl-1")
    clean_env.setenv("MASKING_MODEL_URI", "runs:/abc123/model")
    settings = cfg.load_settings()
    assert settings.service_token == "legacy-token"
    assert settings.masking_model_version == "medroberta-nl-1"
    assert settings.model_uri == "runs:/abc123/model"


def test_new_env_names_take_priority_over_legacy(clean_env):
    clean_env.setenv("SERVICE_TOKEN", "new-token")
    clean_env.setenv("MASKING_API_TOKEN", "legacy-token")
    settings = cfg.load_settings()
    assert settings.service_token == "new-token"


@pytest.mark.parametrize("bad_value", ["0", "-1"])
def test_max_upload_size_must_be_positive(clean_env, bad_value):
    clean_env.setenv("MAX_UPLOAD_SIZE_BYTES", bad_value)
    with pytest.raises(ValueError):
        cfg.load_settings()


@pytest.mark.parametrize("bad_value", ["0", "-3"])
def test_max_concurrent_masks_must_be_positive(clean_env, bad_value):
    clean_env.setenv("MAX_CONCURRENT_MASKS", bad_value)
    with pytest.raises(ValueError):
        cfg.load_settings()


# --------------------------------------------------------------------------- #
# Immutable identifiers -- contract v1.2 section 2: no moving labels.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "label", ["latest", "LATEST", "final", "champion", "production", "stable", "fused-xlmr-final"]
)
def test_mutable_labels_are_rejected(clean_env, label):
    clean_env.setenv("SERVICE_RELEASE", label)
    with pytest.raises(ValueError):
        cfg.load_settings()


def test_immutable_value_is_accepted(clean_env):
    clean_env.setenv("SERVICE_RELEASE", "1.3.0")
    clean_env.setenv("GIT_SHA", "71ac34f7b57b49fa89c98a1580c141ce0cbedc8d")
    settings = cfg.load_settings()
    assert settings.service_release == "1.3.0"
    assert settings.git_sha == "71ac34f7b57b49fa89c98a1580c141ce0cbedc8d"


# --------------------------------------------------------------------------- #
# Digest validation
# --------------------------------------------------------------------------- #
def test_digest_accepts_well_formed_sha256(clean_env):
    digest = "sha256:" + "1" * 64
    clean_env.setenv("IMAGE_DIGEST", digest)
    settings = cfg.load_settings()
    assert settings.image_digest == digest


@pytest.mark.parametrize(
    "bad_digest",
    ["sha256:tooshort", "not-a-digest", "sha256:" + "g" * 64, "md5:" + "1" * 32],
)
def test_digest_rejects_malformed_values(clean_env, bad_digest):
    clean_env.setenv("IMAGE_DIGEST", bad_digest)
    with pytest.raises(ValueError):
        cfg.load_settings()


def test_digest_unset_reports_unknown(clean_env):
    settings = cfg.load_settings()
    assert settings.image_digest == cfg.UNKNOWN_IDENTIFIER
    assert settings.model_digest == cfg.UNKNOWN_IDENTIFIER


# --------------------------------------------------------------------------- #
# supported_media_types -- PDF advertised only when genuinely maskable
# --------------------------------------------------------------------------- #
def test_pdf_advertised_when_fitz_available_and_no_model_uri(clean_env, monkeypatch):
    monkeypatch.setattr(cfg.importlib.util, "find_spec", lambda name: object())
    settings = cfg.load_settings()
    assert cfg.core.PDF in settings.supported_media_types


def test_pdf_not_advertised_when_fitz_missing(clean_env, monkeypatch):
    monkeypatch.setattr(cfg.importlib.util, "find_spec", lambda name: None)
    settings = cfg.load_settings()
    assert cfg.core.PDF not in settings.supported_media_types


def test_pdf_not_advertised_when_model_uri_set(clean_env, monkeypatch):
    monkeypatch.setattr(cfg.importlib.util, "find_spec", lambda name: object())
    clean_env.setenv("MODEL_URI", "models:/pii-masking-service/2")
    settings = cfg.load_settings()
    assert cfg.core.PDF not in settings.supported_media_types


# --------------------------------------------------------------------------- #
# release_identity -- the single source /version and headers both read from.
# --------------------------------------------------------------------------- #
def test_release_identity_falls_back_to_loaded_model_version_when_unset(clean_env):
    settings = cfg.load_settings()
    identity = cfg.release_identity(settings, loaded_model_version="regex-poc-1")
    assert identity["model_version"] == "regex-poc-1"


def test_release_identity_prefers_pinned_model_version_over_loaded(clean_env):
    clean_env.setenv("MODEL_VERSION", "17")
    settings = cfg.load_settings()
    identity = cfg.release_identity(settings, loaded_model_version="medroberta-nl-1")
    assert identity["model_version"] == "17"


def test_release_identity_matches_settings_for_other_fields(clean_env):
    clean_env.setenv("SERVICE_RELEASE", "1.3.0")
    clean_env.setenv("GIT_SHA", "a" * 40)
    settings = cfg.load_settings()
    identity = cfg.release_identity(settings, loaded_model_version="regex-poc-1")
    assert identity["service_release"] == "1.3.0"
    assert identity["git_sha"] == "a" * 40
    assert identity["api_contract_version"] == "v1"


# --------------------------------------------------------------------------- #
# unknown_release_fields
# --------------------------------------------------------------------------- #
def test_unknown_release_fields_lists_everything_unset(clean_env):
    settings = cfg.load_settings()
    unknown = cfg.unknown_release_fields(settings)
    assert set(unknown) == {"service_release", "git_sha", "image_digest", "model_digest"}


def test_unknown_release_fields_shrinks_as_values_are_set(clean_env):
    clean_env.setenv("SERVICE_RELEASE", "1.3.0")
    clean_env.setenv("GIT_SHA", "a" * 40)
    settings = cfg.load_settings()
    unknown = cfg.unknown_release_fields(settings)
    assert unknown == ["image_digest", "model_digest"]
