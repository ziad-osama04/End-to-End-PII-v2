# PII masking service image (contract v1.2).
#
# Production serves the fine-tuned MedRoBERTa + regex core, so build the `model`
# stage, which adds the detector stack from backend/requirements.txt on top of
# the API runtime. The `api` stage is a light, dependency-free image for the
# "regex-poc-1" fallback masker used in smoke tests and CI.
#
#   Production:  docker build --target model -t pii-masking-api:1.0.0-model .
#   Regex-only:  docker build --target api   -t pii-masking-api:1.0.0 .
#
# Never bake a secret into a build argument -- image layers keep it. SERVICE_TOKEN
# and the immutable IMAGE_DIGEST are injected at runtime (see docker-compose.yml).

FROM python:3.12-slim AS api

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

# Record the release this image was built from. /version reports both values,
# so a running container names its own source. The image digest is only known
# after the push, so the deployment injects IMAGE_DIGEST at runtime.
ARG SERVICE_RELEASE=unknown
ARG GIT_SHA=unknown
ENV SERVICE_RELEASE=${SERVICE_RELEASE} \
    GIT_SHA=${GIT_SHA}

WORKDIR /app

COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt \
    && groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app \
    && chown -R app:app /app

COPY --chown=app:app backend/masking_service ./masking_service

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=3)"]

CMD ["uvicorn", "masking_service.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]


# Full detector/model stack for the "medroberta-nl-1" or MLflow-packaged model.
FROM api AS model

USER root
COPY backend/requirements.txt ./requirements-model.txt
RUN pip install --no-cache-dir -r requirements-model.txt
USER app
