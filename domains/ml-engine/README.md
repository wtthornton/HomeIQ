# ml-engine

All ML model inference and embedding generation. Heaviest compute requirements (GPU/high memory). Changes driven by model updates, not feature work.

## Services

| Service | Port | Role |
|---------|------|------|
| openvino-service | 8026 | Transformer embeddings, semantic search, reranking |
| ml-service | 8025 | Classical ML — clustering, anomaly detection |
| rag-service | 8027 | Retrieval-Augmented Generation + vector search |
| device-intelligence-service | 8028 | 6,000+ device capability mapping (ML models) |
| model-prep | — | HuggingFace model download/cache (one-shot) |
| nlp-fine-tuning | — | NLP model fine-tuning pipeline (one-shot) |

## Depends On

core-platform (data-api for entity/device metadata)

## Depended On By

automation-core, blueprints, device-management

## Compose

```bash
docker compose -f domains/ml-engine/compose.yml up -d
```
