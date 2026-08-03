"""FastAPI service implementing PII Masking API contract v1.2.

Endpoints (contract v1.2 section 2):
    GET  /health   -> 200 once the web process is alive.
    GET  /ready    -> 200 when the model is loaded, 503 otherwise.
    GET  /version  -> exact deployed API, code, image, and model identity.
    POST /v1/mask  -> masked file bytes + the mandatory version headers.
    GET  /healthz  -> retained for deployments that already poll it.

Design notes tying back to the contract:
  * The masking model is loaded once at startup. If ``MODEL_URI`` (or the legacy
    ``MASKING_MODEL_URI``) is set the model is loaded from MLflow; otherwise the
    dependency-free in-process masker is used. Either way the loaded model
    version is fixed for the process lifetime -- the service never silently
    switches models.
  * The service never receives or touches R2/S3 credentials (NiFi owns object
    movement).
  * Stateless: nothing is persisted between requests; no temp files are written.
  * Logging is metadata-only. Request/response bodies, extracted entities, and
    raw PII are NEVER logged. Errors carry no input echo and no stack traces to
    the client (contract v1.2 section 5).
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import os
import time

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from masking_service import config as cfg
from masking_service import masking_core as core

# --------------------------------------------------------------------------- #
# Settings (validated once at import; a bad deployment fails fast).
# --------------------------------------------------------------------------- #
settings = cfg.load_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("masking_service")

# Contract v1.2 section 4: the same release identity feeds /version and every
# masked response header, from one source, so the two cannot drift apart.
_VERSION_HEADERS = {
    "api_contract_version": "X-API-Version",
    "service_release": "X-Service-Release",
    "git_sha": "X-Git-SHA",
    "image_digest": "X-Image-Digest",
    "model_name": "X-Model-Name",
    "model_version": "X-Model-Version",
    "model_digest": "X-Model-Digest",
}

# Contract v1.2 section 5: the code a caller matches on, and which statuses
# NiFi may retry.
_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "UNPROCESSABLE_DOCUMENT",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}
_RETRYABLE = frozenset({429, 500, 502, 503, 504})
RETRY_AFTER_SECONDS = 5
_MAX_ECHOED_HEADER_CHARS = 256


class _State:
    masker = None            # in-process core masker (default / fallback)
    mlflow_model = None      # loaded MLflow pyfunc, if MODEL_URI is set
    ready = False
    model_version = settings.masking_model_version


state = _State()


def _load_model() -> None:
    """Load the requested immutable model. /ready stays 503 until done."""
    if settings.model_uri:
        try:
            import mlflow.pyfunc
            import pandas as pd

            state.mlflow_model = mlflow.pyfunc.load_model(settings.model_uri)
            probe = state.mlflow_model.predict(
                pd.DataFrame({"content": ["ok"], "media_type": [core.TXT]})
            )
            state.model_version = str(probe.iloc[0]["model_version"])
            state.ready = True
            log.info("model_loaded source=mlflow version=%s", state.model_version)
            return
        except Exception:
            # Fail closed; never leak internals. /ready reports not-ready.
            log.exception("model_load_failed source=mlflow")
            state.ready = False
            return

    try:
        if settings.masking_model_version == "medroberta-nl-1":
            from masking_service.medroberta_masker import register as _register

            _register()
        state.masker = core.get_masker(settings.masking_model_version)
        state.model_version = state.masker.model_version
        state.ready = True
        log.info("model_loaded source=inprocess version=%s", state.model_version)
    except KeyError:
        log.error(
            "model_load_failed source=inprocess version=%s",
            settings.masking_model_version,
        )
        state.ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mask_slots = asyncio.Semaphore(settings.max_concurrent_masks)
    unknown = cfg.unknown_release_fields(settings)
    if unknown:
        # Contract v1.2 section 2 requires /version to identify the exact
        # release. Warn loudly rather than claim an identity we cannot prove.
        log.warning("release_identity_incomplete fields=%s", ",".join(unknown))
    _load_model()
    yield
    state.masker = None
    state.mlflow_model = None


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
# Tests build a TestClient without lifespan in some paths, so seed state here.
app.state.mask_slots = asyncio.Semaphore(settings.max_concurrent_masks)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _safe_header(value: str | None) -> str:
    """Return *value* fit to echo back in a response header.

    A carriage return in a caller-supplied header would split the response, so
    non-printable characters are dropped and the length is capped.
    """
    if not value:
        return ""
    return "".join(ch for ch in value if ch.isprintable())[:_MAX_ECHOED_HEADER_CHARS]


def _identity() -> dict[str, str]:
    return cfg.release_identity(settings, state.model_version)


def _error(status: int, message: str, request_id: str | None) -> Response:
    """Return the contract v1.2 section 5 error body. No input echo, no trace."""
    request_id = _safe_header(request_id)
    body = {
        "error": {
            "code": _ERROR_CODES.get(status, "ERROR"),
            "message": message,
            "retryable": status in _RETRYABLE,
            "request_id": request_id,
        }
    }
    headers = {"X-Request-ID": request_id}
    if status in (429, 503):
        headers["Retry-After"] = str(RETRY_AFTER_SECONDS)
    return JSONResponse(body, status_code=status, headers=headers)


def _token_ok(authorization: str | None) -> bool:
    expected = settings.service_token
    if not expected:
        # Misconfiguration: refuse everything rather than run open.
        return False
    if not authorization or not authorization.startswith("Bearer "):
        return False
    presented = authorization[len("Bearer ") :].strip()
    return hmac.compare_digest(presented, expected)


def _mask_with_model(raw: bytes, media_type: str) -> core.MaskResult:
    """Route to the MLflow model if loaded, else the in-process masker.

    Both paths raise the same core exceptions so the HTTP layer maps status
    codes in one place.
    """
    # PDF is masked outside the dependency-free core, using the in-process
    # masker's span detector. It needs per-span geometry, which the MLflow
    # pyfunc model does not expose, so PDF is only offered with an in-process
    # masker (config advertises it accordingly).
    if media_type == core.PDF:
        if state.masker is None:
            raise core.UnsupportedMediaType(media_type)
        from masking_service import pdf_masking

        content, count = pdf_masking.mask_pdf(raw, state.masker.detect_spans)
        return core.MaskResult(
            content=content,
            entity_count=count,
            model_version=state.masker.model_version,
            sha256=hashlib.sha256(content).hexdigest(),
        )

    if state.mlflow_model is None:
        return state.masker.mask_bytes(raw, media_type)

    mt = core.normalize_media_type(media_type)
    if mt not in core.SUPPORTED_MEDIA_TYPES:
        raise core.UnsupportedMediaType(mt)
    if not raw:
        raise core.MaskingError("empty body")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise core.MaskingError("input is not valid UTF-8") from exc

    import pandas as pd

    out = state.mlflow_model.predict(
        pd.DataFrame({"content": [text], "media_type": [mt]})
    )
    row = out.iloc[0]
    err = str(row.get("error") or "")
    if err.startswith("unsupported_media_type"):
        raise core.UnsupportedMediaType(mt)
    if err:
        raise core.MaskingError(err)
    content = str(row["masked_content"]).encode("utf-8")
    return core.MaskResult(
        content=content,
        entity_count=int(row["entity_count"]),
        model_version=str(row["model_version"]),
        sha256=hashlib.sha256(content).hexdigest(),
    )


# --------------------------------------------------------------------------- #
# Status endpoints (no authentication -- they report no PII and no secret).
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    """Liveness: the web service process answers requests."""
    return {"status": "UP"}


@app.get("/ready")
def ready():
    """Readiness: the model and required runtime resources are loaded."""
    if not state.ready:
        return JSONResponse(
            {"status": "NOT_READY", "model_loaded": False}, status_code=503
        )
    return {"status": "READY", "model_loaded": True}


@app.get("/version")
def version():
    """Report the exact API, code, image, and model identity now loaded."""
    return {
        "service": settings.service_name,
        **_identity(),
        "supported_mime_types": sorted(settings.supported_media_types),
        "max_file_bytes": settings.max_upload_size_bytes,
    }


@app.get("/healthz")
def healthz():
    """Retained for deployments that already poll /healthz."""
    if not state.ready:
        return JSONResponse({"status": "loading"}, status_code=503)
    return {"status": "ok", "model_version": state.model_version}


# --------------------------------------------------------------------------- #
# Mask
# --------------------------------------------------------------------------- #
@app.post("/v1/mask")
async def mask(request: Request):
    started = time.monotonic()
    request_id = request.headers.get("X-Request-ID")
    team_id = _safe_header(request.headers.get("X-Team-ID"))

    # 401 -- authenticate first; never process an unauthenticated request.
    if not _token_ok(request.headers.get("Authorization")):
        return _error(401, "Missing or invalid service credential.", request_id)

    # 415 -- unsupported media type.
    media_type = core.normalize_media_type(request.headers.get("Content-Type", ""))
    if media_type not in settings.supported_media_types:
        return _error(415, "The supplied media type is not supported.", request_id)

    # 400 -- the request must carry a correlation id.
    if not request_id:
        return _error(400, "X-Request-ID header is required.", request_id)

    # 413 -- reject oversize early via Content-Length when advertised.
    content_length = request.headers.get("Content-Length")
    if content_length and content_length.isdigit():
        if int(content_length) > settings.max_upload_size_bytes:
            return _error(413, "Payload exceeds the contracted limit.", request_id)

    # 503 -- model must be loaded and ready before masking.
    if not state.ready:
        return _error(503, "The model is warming up.", request_id)

    slots: asyncio.Semaphore = request.app.state.mask_slots
    if slots.locked():
        # Every slot is busy. A queued request would age past the caller's
        # socket-read timeout, so tell the caller to send it again.
        return _error(429, "The service is at its concurrency limit.", request_id)

    async with slots:
        body = await request.body()

        # 400 -- empty body.
        if not body:
            return _error(400, "The request body is empty.", request_id)

        # 413 -- enforce again on the actual bytes (chunked / missing header).
        if len(body) > settings.max_upload_size_bytes:
            return _error(413, "Payload exceeds the contracted limit.", request_id)

        # Mask. Map failures to contract statuses; never return the input.
        try:
            result = await asyncio.to_thread(_mask_with_model, body, media_type)
        except core.UnsupportedMediaType:
            return _error(415, "The supplied media type is not supported.", request_id)
        except core.MaskingError:
            return _error(422, "The document could not be masked safely.", request_id)
        except Exception:
            log.exception("mask_failed request_id_present=%s", bool(request_id))
            return _error(500, "Masking failed.", request_id)

    duration_ms = int((time.monotonic() - started) * 1000)
    # Metadata-only success log: no body, no entities, no PII, no filenames.
    log.info(
        "mask_ok request_id=%s team=%s status=200 media=%s bytes_in=%d "
        "bytes_out=%d entities=%d duration_ms=%d release=%s model_version=%s",
        _safe_header(request_id),
        team_id,
        media_type,
        len(body),
        len(result.content),
        result.entity_count,
        duration_ms,
        settings.service_release,
        result.model_version,
    )

    identity = _identity()
    # The masked response reports the model version actually used by the masker.
    identity["model_version"] = result.model_version
    headers = {
        "X-Request-ID": _safe_header(request_id),
        "X-Masking-Duration-Ms": str(duration_ms),
        "X-Masked-Content-SHA256": result.sha256,
    }
    headers.update({header: identity[fld] for fld, header in _VERSION_HEADERS.items()})
    return Response(content=result.content, media_type=media_type, headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "masking_service.app:app",
        host="0.0.0.0",  # noqa: S104
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )
