"""Runtime settings and release identity for the masking service.

PII Masking API contract v1.2 sections 2 and 7 require ``/version`` and every
masked response to report the *exact* release that is running now: the API
contract version, the service release, the source commit, the image digest,
and the model name/version/digest. Each value must be immutable and describe
what is actually loaded -- a moving label such as ``latest`` or ``champion`` is
not sufficient.

A build or a deployment injects these identifiers as environment variables.
Any value left unset is reported as ``unknown`` rather than a guessed identity.

Legacy environment names from the earlier proof-of-concept
(``MASKING_API_TOKEN``, ``MASKING_MODEL_VERSION``, ``MASKING_MODEL_URI``) are
still honored as fall-backs so existing deployments keep working.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from masking_service import masking_core as core

# A value the service cannot prove is reported unchanged rather than faked.
UNKNOWN_IDENTIFIER = "unknown"

# Contract v1.2 section 2: a moving label does not identify a release.
_MUTABLE_LABELS = frozenset(
    {"latest", "final", "champion", "production", "stable", "fused-xlmr-final"}
)


def _env(name: str, *fallbacks: str, default: str = "") -> str:
    """Return the first environment value set among ``name`` and *fallbacks*."""
    for key in (name, *fallbacks):
        value = os.environ.get(key)
        if value:
            return value
    return default


def _immutable(name: str, default: str = UNKNOWN_IDENTIFIER) -> str:
    """Return an identifier that must name one exact release, not a label."""
    value = os.environ.get(name, "").strip() or default
    if value.lower() in _MUTABLE_LABELS:
        raise ValueError(f"{name} must be an immutable identifier, not a moving label.")
    return value


def _digest(name: str) -> str:
    """Return a ``sha256:<64 hex>`` digest, or ``unknown`` when unset."""
    value = _immutable(name).lower()
    if value == UNKNOWN_IDENTIFIER:
        return value
    if re.fullmatch(r"sha256:[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be sha256 followed by 64 hexadecimal digits.")
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = "PII Masking Service"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    # Release identity reported on /version and on every masked response.
    api_contract_version: str = "v1"
    service_name: str = "pii-medroberta-masker"
    service_release: str = UNKNOWN_IDENTIFIER
    git_sha: str = UNKNOWN_IDENTIFIER
    image_digest: str = UNKNOWN_IDENTIFIER
    # The production core is the fine-tuned MedRoBERTa + Dutch regex detector.
    model_name: str = "pii-medroberta-nl"
    model_version: str = UNKNOWN_IDENTIFIER
    model_digest: str = UNKNOWN_IDENTIFIER

    # Shared bearer credential. Never logged or committed.
    service_token: str = ""

    # Which in-process masker version to load, or an MLflow model URI. The code
    # default is the dependency-free "regex-poc-1" masker so a bare install and
    # CI stay light; production sets MASKING_MODEL_VERSION=medroberta-nl-1 (or a
    # MODEL_URI) in .env to load the fine-tuned MedRoBERTa + regex core.
    masking_model_version: str = core.Masker.model_version
    model_uri: str = ""

    # Transport limits and concurrency bound.
    max_upload_size_bytes: int = core.MAX_BYTES
    max_concurrent_masks: int = 2

    supported_media_types: tuple[str, ...] = field(
        default_factory=lambda: core.SUPPORTED_MEDIA_TYPES
    )


def load_settings() -> Settings:
    """Return validated runtime settings, raising on the first invalid value."""
    masking_model_version = _env(
        "MODEL_VERSION_TAG",
        "MASKING_MODEL_VERSION",
        default=core.Masker.model_version,
    )
    max_upload = int(
        os.environ.get("MAX_UPLOAD_SIZE_BYTES", str(core.MAX_BYTES))
    )
    if max_upload < 1:
        raise ValueError("MAX_UPLOAD_SIZE_BYTES must be positive.")
    max_concurrent = int(os.environ.get("MAX_CONCURRENT_MASKS", "2"))
    if max_concurrent < 1:
        raise ValueError("MAX_CONCURRENT_MASKS must be positive.")

    return Settings(
        app_name=os.environ.get("APP_NAME", Settings.app_name),
        app_version=os.environ.get("APP_VERSION", Settings.app_version),
        log_level=os.environ.get("LOG_LEVEL", Settings.log_level),
        service_name=os.environ.get("SERVICE_NAME", Settings.service_name),
        service_release=_immutable("SERVICE_RELEASE"),
        git_sha=_immutable("GIT_SHA"),
        image_digest=_digest("IMAGE_DIGEST"),
        model_name=os.environ.get("MODEL_NAME", Settings.model_name),
        # The reported model version defaults to the loaded masker version but a
        # deployment can pin it to an immutable MLflow numeric version.
        model_version=_immutable("MODEL_VERSION", masking_model_version),
        model_digest=_digest("MODEL_DIGEST"),
        service_token=_env("SERVICE_TOKEN", "MASKING_API_TOKEN"),
        masking_model_version=masking_model_version,
        model_uri=_env("MODEL_URI", "MASKING_MODEL_URI"),
        max_upload_size_bytes=max_upload,
        max_concurrent_masks=max_concurrent,
    )


def release_identity(settings: Settings, loaded_model_version: str) -> dict[str, str]:
    """Return the identity of the running release for /version and headers.

    ``loaded_model_version`` is the version of the model actually loaded at
    startup; it overrides the configured default so the reported value can never
    claim a model the process did not load.
    """
    model_version = settings.model_version
    if model_version == UNKNOWN_IDENTIFIER:
        model_version = loaded_model_version
    return {
        "api_contract_version": settings.api_contract_version,
        "service_release": settings.service_release,
        "git_sha": settings.git_sha,
        "image_digest": settings.image_digest,
        "model_name": settings.model_name,
        "model_version": model_version,
        "model_digest": settings.model_digest,
    }


def unknown_release_fields(settings: Settings) -> list[str]:
    """Return the release identifiers this deployment cannot prove."""
    identity = {
        "service_release": settings.service_release,
        "git_sha": settings.git_sha,
        "image_digest": settings.image_digest,
        "model_digest": settings.model_digest,
    }
    return sorted(name for name, value in identity.items() if value == UNKNOWN_IDENTIFIER)
