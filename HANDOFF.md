# PII Masking Service — MLOps Handoff

Everything the MLOps/NiFi team needs to deploy and integrate this masking
service. Implements **PII Masking API Contract v1.2**
([docs/PII_Masking_API_Contract_v1.2.md](docs/PII_Masking_API_Contract_v1.2.md)).

> Fill in the two blanks marked **`<FILL IN>`** before sending this to MLOps.

---

## 1. The endpoint (the one NiFi calls)

```
POST  https://<FILL IN: VPS host or IP>/v1/mask
```

- Send the **raw file bytes** as the request body (not JSON, not multipart).
- The service returns the **masked file** (same format and, for PDFs, the same
  structure) with the version headers listed in section 5.

## 2. Authentication

Every request must include:

```
Authorization: Bearer <FILL IN: SERVICE_TOKEN>
```

The token is sent **separately and privately** (e.g. secrets manager / password
manager) — never in Git, chat, or this file once filled in.

## 3. Status endpoints (no auth — for probes and monitoring)

| Method | Path | Meaning |
|---|---|---|
| `GET` | `/health` | Service process is alive → `{"status":"UP"}` |
| `GET` | `/ready` | Model is loaded and ready → `200`, else `503` |
| `GET` | `/version` | Exact deployed release + model identity |

NiFi should wait for `/ready` = `200` before sending files.

## 4. What it accepts

| Item | Value |
|---|---|
| Supported `Content-Type` | `application/pdf`, `text/plain`, `text/csv`, `application/json` |
| Max file size | 10 MiB (`10485760` bytes) → `413` if larger |
| Timeout target | within 120 s for a file up to 10 MiB |

**Request headers NiFi should send:**

```
Authorization: Bearer <token>
Content-Type: application/pdf          # the file's actual MIME type
Accept: application/pdf                # usually the same as input
X-Request-ID: <uuid>                   # echoed back on the response
Idempotency-Key: <same value on retries of the same file>
X-Team-ID: <team id>
```

## 5. Successful response

`200 OK` with the masked file bytes and these headers (they always match
`/version`):

```
X-Request-ID, X-API-Version, X-Service-Release, X-Git-SHA,
X-Image-Digest, X-Model-Name, X-Model-Version, X-Model-Digest
```

## 6. Errors

Non-2xx with a small JSON body:
`{"error":{"code":"...","message":"...","retryable":true|false,"request_id":"..."}}`

| Status | Meaning | NiFi action |
|---|---|---|
| `400` | Bad/missing request metadata | do not retry |
| `401` | Missing/invalid token | do not retry, alert |
| `413` | File too large | do not retry |
| `415` | Unsupported file type | do not retry |
| `422` | Corrupt / password-protected / unreadable | do not retry |
| `429`, `503` | Temporarily busy / not ready (has `Retry-After`) | retry up to 3× |
| `500`, `502`, `504` | Transient server error | retry up to 3× |

## 7. Deployment (Docker)

The service ships as a Docker image — deploy the image, don't run the code by
hand. Production uses the `model` image (includes the MedRoBERTa stack + OCR).

```bash
# Build (production image with the model + OCR):
docker build --target model -t pii-masking-api:1.0.0-model .

# Run (uses .env for the token and release identity):
docker compose up -d
```

- App listens on **port 8000** inside the container.
- `.env` holds `SERVICE_TOKEN` and the release identity (`SERVICE_RELEASE`,
  `GIT_SHA`, `IMAGE_DIGEST`, `MODEL_VERSION`, `MODEL_DIGEST`) — see
  [.env.example](.env.example).
- Pin the deployed image by **digest**, never `latest`. `/version` reports the
  exact digest that is running.
- **HTTPS:** the contract requires HTTPS for non-local traffic. If NiFi is on a
  different machine, put a reverse proxy (Caddy/nginx) with TLS in front of port
  8000 so the public URL is `https://.../v1/mask`. If NiFi runs on the same
  Docker network, it can reach the service directly at
  `http://masking-api:8000/v1/mask`.

## 8. Quick check (contract smoke test)

```bash
curl --fail-with-body -X POST \
  -H "Authorization: Bearer $SERVICE_TOKEN" \
  -H "Content-Type: application/pdf" \
  -H "X-Request-ID: 041ce3f5-6a98-5272-b8c3-f5e3864b2b71" \
  -H "X-Team-ID: team-1" \
  --data-binary @input.pdf \
  --dump-header headers.txt --output masked.pdf \
  https://<FILL IN: host>/v1/mask
```

Expect `200`, a valid `masked.pdf`, and the version headers in `headers.txt`.

## 9. References

- Full contract: [docs/PII_Masking_API_Contract_v1.2.md](docs/PII_Masking_API_Contract_v1.2.md)
- Ready-to-run requests: [postman/masking-api-v1.postman_collection.json](postman/masking-api-v1.postman_collection.json)
- Architecture: [docs/architecture.md](docs/architecture.md)
- Acceptance status: 39 contract tests passing (`pytest`).

---

### TL;DR — what MLOps receives

1. **URL:** `https://<host>/v1/mask`
2. **Token:** `SERVICE_TOKEN` (sent privately)
3. **Docker image:** `pii-masking-api:1.0.0-model` (pinned by digest)
