#!/usr/bin/env bash
# End-to-end contract check against a running service (contract v1.2 section 12).
#
# Usage:
#   BASE_URL=http://localhost:8000 SERVICE_TOKEN=<token> bash shell/contract_test.sh
#
# Confirms /health, /ready, /version, and a successful /v1/mask with the
# mandatory version headers echoed back. Uses synthetic PII only.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
SERVICE_TOKEN="${SERVICE_TOKEN:-replace-with-a-long-random-secret}"
REQUEST_ID="041ce3f5-6a98-5272-b8c3-f5e3864b2b71"

echo "== GET /health =="
curl --fail-with-body -s "${BASE_URL}/health"; echo

echo "== GET /ready =="
curl --fail-with-body -s "${BASE_URL}/ready"; echo

echo "== GET /version =="
curl --fail-with-body -s "${BASE_URL}/version"; echo

echo "== POST /v1/mask (synthetic text) =="
printf 'Patient jan.jansen@example.com IBAN BE68539007547034 tel +32470123456' \
  | curl --fail-with-body -s \
      --request POST \
      --header "Authorization: Bearer ${SERVICE_TOKEN}" \
      --header "Content-Type: text/plain" \
      --header "Accept: text/plain" \
      --header "X-Request-ID: ${REQUEST_ID}" \
      --header "Idempotency-Key: ${REQUEST_ID}" \
      --header "X-Team-ID: team-1" \
      --header "X-Source-ETag: 635ac6adc4cbca869a3f7af32fdb5175" \
      --data-binary @- \
      --dump-header /tmp/mask-headers.txt \
      --output /tmp/mask-body.txt \
      "${BASE_URL}/v1/mask"

echo "--- response headers ---"
grep -iE '^(x-request-id|x-api-version|x-service-release|x-git-sha|x-image-digest|x-model-name|x-model-version|x-model-digest):' /tmp/mask-headers.txt
echo "--- masked body ---"
cat /tmp/mask-body.txt; echo
echo "OK"
