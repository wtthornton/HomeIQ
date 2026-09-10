# model-server

Merged ML inference service (TAP-7276): one process, one model load.

Folds three former `ml-engine` services into a single FastAPI app, each
mounted at its **exact existing route paths** so consumers only change the
host:

| Former service    | Routes                                                             |
|--------------------|---------------------------------------------------------------------|
| openvino-service   | `/embeddings`, `/rerank`, `/classify`, `/models/status`, `/models/warmup` |
| ml-service         | `/cluster`, `/anomaly`, `/batch/process`, `/algorithms/status`      |
| rag-service        | `/api/v1/rag/*`, `/api/v1/metrics*`                                  |

`ner-service` is **dropped outright** — no caller, no tests, its sole
documented consumer (`ai-core-service`) does not exist in the repo. See
`docs/architecture/collapse-map.md` section C3.

## One model, one load

The OpenVINO embedding/rerank/classify model is owned by a single
`OpenVINOManager` instance (`src/openvino/models/openvino_manager.py`).
RAG's retrieval path used to call that model over HTTP to a separate
`openvino-service` container; it now goes through `LocalOpenVINOBridge`
(`src/rag/clients/openvino_client.py`), an in-process adapter around the
same manager instance — see `tests/test_shared_model_load.py`.

## Layout

```
src/
  main.py       # merged FastAPI app, lifespan, unified health check
  openvino/     # former openvino-service/src (model manager, request/response models)
  ml/           # former ml-service/src (clustering, anomaly detection, batch)
  rag/          # former rag-service/src (retrieval, database, api routers)
tests/          # merged test suites from all three former services
```

## Running

```
uvicorn src.main:app --host 0.0.0.0 --port 8019
```

Requires `POSTGRES_URL` (RAG's `rag` schema) and the standard HomeIQ
`.env` block; see `compose.yml`.
