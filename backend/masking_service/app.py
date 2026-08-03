"""FastAPI service implementing the frozen NiFi <-> masking-API contract.

Endpoints:
    GET  /healthz     -> 200 only after the requested immutable model is loaded
    POST /v1/mask     -> masked file bytes + X-Masking-* headers

Design notes tying back to the contract:
  * The masking model is loaded once at startup. If MASKING_MODEL_URI is set the
    model is loaded from MLflow (registry or run artifact); otherwise the
    dependency-free in-process masker is used. Either way the *loaded* model
    version is fixed for the process lifetime -- we "never silently switch".
  * The service never receives or touches S3 credentials (NiFi owns S3).
  * Stateless: nothing is persisted between requests; no temp files are written.
  * Logging is metadata-only. Request/response bodies, extracted entities, and
    raw PII are NEVER logged. Errors carry no input echo and no stack traces to
    the client.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from masking_service import masking_core as core

# --------------------------------------------------------------------------- #
# Configuration (all via env so NiFi/ops controls it; no secrets in code)
# --------------------------------------------------------------------------- #
INTERNAL_TOKEN = os.environ.get("MASKING_API_TOKEN", "")
LOADED_MODEL_VERSION = os.environ.get("MASKING_MODEL_VERSION", "regex-poc-1")
MODEL_URI = os.environ.get("MASKING_MODEL_URI")  # optional MLflow model uri
MAX_BYTES = core.MAX_BYTES

# Metadata-only logger. We deliberately never interpolate bodies/PII into logs.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("masking_service")

class _State:
    masker = None            # in-process core masker (fallback / default)
    mlflow_model = None      # loaded MLflow pyfunc, if MODEL_URI set
    ready = False
    model_version = LOADED_MODEL_VERSION


state = _State()


def _load_model() -> None:
    """Load the requested immutable model. /healthz stays non-200 until done."""
    if MODEL_URI:
        try:
            import mlflow.pyfunc

            state.mlflow_model = mlflow.pyfunc.load_model(MODEL_URI)
            # Probe the loaded version deterministically via a no-PII sample.
            import pandas as pd

            probe = state.mlflow_model.predict(
                pd.DataFrame({"content": ["ok"], "media_type": [core.TXT]})
            )
            state.model_version = str(probe.iloc[0]["model_version"])
            state.ready = True
            log.info("model_loaded source=mlflow version=%s", state.model_version)
            return
        except Exception:
            # Do not leak internals; fail closed so /healthz reports not-ready.
            log.exception("model_load_failed source=mlflow")
            state.ready = False
            return

    try:
        # The MedRoBERTa masker registers itself lazily (heavy deps) only when
        # explicitly requested, so the default regex path stays dependency-free.
        if LOADED_MODEL_VERSION == "medroberta-nl-1":
            from masking_service.medroberta_masker import register as _register_medroberta

            _register_medroberta()
        state.masker = core.get_masker(LOADED_MODEL_VERSION)
        state.model_version = state.masker.model_version
        state.ready = True
        log.info("model_loaded source=inprocess version=%s", state.model_version)
    except KeyError:
        log.error("model_load_failed source=inprocess version=%s", LOADED_MODEL_VERSION)
        state.ready = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _load_model()
    yield


app = FastAPI(title="PII Masking Service", version=LOADED_MODEL_VERSION, lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Health
# --------------------------------------------------------------------------- #
@app.get("/healthz")
def healthz():
    if not state.ready:
        return JSONResponse({"status": "loading"}, status_code=503)
    return {"status": "ok", "model_version": state.model_version}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _error(status: int, code: str, request_id: str | None) -> Response:
    """Metadata-only error response: no input echo, no stack trace."""
    headers = {}
    if request_id:
        headers["X-Request-ID"] = request_id
    return JSONResponse({"error": code}, status_code=status, headers=headers)


def _token_ok(authorization: str | None) -> bool:
    if not INTERNAL_TOKEN:
        # Misconfiguration: refuse everything rather than run open.
        return False
    if not authorization or not authorization.startswith("Bearer "):
        return False
    presented = authorization[len("Bearer ") :].strip()
    return hmac.compare_digest(presented, INTERNAL_TOKEN)


def _mask_with_model(raw: bytes, media_type: str) -> core.MaskResult:
    """Route to the MLflow model if loaded, else the in-process masker.

    Raises the same core exceptions (UnsupportedMediaType / MaskingError) so the
    HTTP layer maps status codes in one place.
    """
    if state.mlflow_model is None:
        return state.masker.mask_bytes(raw, media_type)

    # MLflow path: enforce the same guards the core would, then delegate.
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
# Mask
# --------------------------------------------------------------------------- #
@app.post("/v1/mask")
async def mask(request: Request):
    request_id = request.headers.get("X-Request-ID")

    # 401 -- authenticate first; never process an unauthenticated request.
    if not _token_ok(request.headers.get("Authorization")):
        return _error(401, "invalid_token", request_id)

    # 415 -- unsupported media type.
    media_type = core.normalize_media_type(request.headers.get("Content-Type", ""))
    if media_type not in core.SUPPORTED_MEDIA_TYPES:
        return _error(415, "unsupported_media_type", request_id)

    # 400 -- required request metadata must be present.
    required = ("X-Request-ID", "X-Source-Key", "X-Source-ETag", "X-Model-Version")
    if any(not request.headers.get(h) for h in required):
        return _error(400, "missing_metadata", request_id)

    # 413 -- reject oversize early via Content-Length when advertised.
    content_length = request.headers.get("Content-Length")
    if content_length and content_length.isdigit() and int(content_length) > MAX_BYTES:
        return _error(413, "payload_too_large", request_id)

    body = await request.body()

    # 400 -- empty body.
    if not body:
        return _error(400, "empty_body", request_id)

    # 413 -- enforce again on the actual bytes (chunked / missing header).
    if len(body) > MAX_BYTES:
        return _error(413, "payload_too_large", request_id)

    # 409 -- requested model version must match the loaded, ready model.
    if not state.ready:
        return _error(503, "model_not_ready", request_id)
    requested_version = request.headers.get("X-Model-Version")
    if requested_version != state.model_version:
        return _error(409, "model_version_not_loaded", request_id)

    # Mask. Map failures to 422 (validation) / 503 (transient) -- never return input.
    try:
        result = _mask_with_model(body, media_type)
    except core.UnsupportedMediaType:
        return _error(415, "unsupported_media_type", request_id)
    except core.MaskingError:
        # Malformed input or output-validation failure. No input echo.
        return _error(422, "masking_validation_failed", request_id)
    except Exception:
        # Temporary/internal failure. Contract: return 503 (never 429), no trace.
        log.exception("mask_failed request_id_present=%s", bool(request_id))
        return _error(503, "temporary_failure", request_id)

    # Metadata-only success log: no body, no entities, no PII.
    log.info(
        "mask_ok bytes_in=%d bytes_out=%d entities=%d version=%s",
        len(body),
        len(result.content),
        result.entity_count,
        result.model_version,
    )

    headers = {
        "X-Request-ID": request_id,
        "X-Masking-Model-Version": result.model_version,
        "X-Masking-Entity-Count": str(result.entity_count),
        "X-Masked-Content-SHA256": result.sha256,
    }
    return Response(content=result.content, media_type=media_type, headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("masking_service.app:app", host="0.0.0.0", port=9000, reload=False)
