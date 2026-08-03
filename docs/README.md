# Documentation

| Document | What it covers |
|---|---|
| [PII_Masking_API_Contract_v1.2.md](PII_Masking_API_Contract_v1.2.md) | The integration contract this service implements: endpoints, headers, error codes, versioning, and the NiFi ⇄ API flow. |
| [architecture.md](architecture.md) | How this repository is laid out and how a request moves through the service. |

## Quick links

- API app: [`backend/masking_service/app.py`](../backend/masking_service/app.py)
- Masking core: [`backend/masking_service/masking_core.py`](../backend/masking_service/masking_core.py)
- Runtime settings & release identity: [`backend/masking_service/config.py`](../backend/masking_service/config.py)
- Contract tests: [`backend/masking_service/tests/`](../backend/masking_service/tests/)
- Postman collection: [`postman/masking-api-v1.postman_collection.json`](../postman/masking-api-v1.postman_collection.json)
