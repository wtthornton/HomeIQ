# Model Preparation Container

**Purpose:** Pre-download and cache ML models for deterministic builds and faster service startup.

## Overview

The model-prep container downloads all ML models used by HomeIQ AI services into a shared Docker volume. This ensures:

- ✅ **Deterministic caching** - Models are downloaded once and cached
- ✅ **Faster startup** - Services don't wait for model downloads
- ✅ **Offline capability** - Models available after initial download
- ✅ **Consistent versions** - All services use the same cached models
- ✅ **CI/CD friendly** - Models can be pre-cached in build pipelines

## Models Downloaded

| Model | Size (INT8) | Used By | Purpose |
|-------|-------------|---------|---------|
| `all-MiniLM-L6-v2` | ~20MB | ai-automation-service | Embeddings |
| `bge-reranker-base` | ~280MB | ai-automation-service | Re-ranking |
| `flan-t5-small` | ~80MB | ai-automation-service, ai-training-service | Classification/Training |

**Total:** ~380MB (INT8) or ~1.5GB (FP32)

## Usage

### Option 1: Standalone Container (Recommended)

Pre-download models before starting services:

```bash
# Build the model-prep container
docker build -t homeiq-model-prep -f services/model-prep/Dockerfile services/model-prep

# Run to download models into shared volume
docker run --rm \
  -v homeiq_models:/app/models \
  homeiq-model-prep

# Then start services (models already cached)
docker-compose up ai-automation-service
```

### Option 2: Docker Compose Integration

Add to `docker-compose.yml`:

```yaml
services:
  model-prep:
    build:
      context: ./services/model-prep
      dockerfile: Dockerfile
    volumes:
      - homeiq_models:/app/models
    environment:
      - HF_HOME=/app/models
    profiles:
      - setup  # Only run when explicitly requested

volumes:
  homeiq_models:
    # Shared volume for all AI services
```

Run once:

```bash
docker-compose --profile setup up model-prep
```

### Option 3: CI/CD Pipeline

Pre-cache models in CI/CD:

```yaml
# Example GitHub Actions
- name: Cache ML Models
  run: |
    docker build -t homeiq-model-prep -f services/model-prep/Dockerfile services/model-prep
    docker run --rm \
      -v homeiq_models:/app/models \
      homeiq-model-prep
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_HOME` | `/app/models` | HuggingFace cache directory |
| `TRANSFORMERS_CACHE` | `/app/models` | Transformers cache directory |
| `MODELS_TO_DOWNLOAD` | (all) | Comma-separated list of model keys to download |

### Selective Model Download

Download only specific models:

```bash
docker run --rm \
  -v homeiq_models:/app/models \
  -e MODELS_TO_DOWNLOAD="all-MiniLM-L6-v2,flan-t5-small" \
  homeiq-model-prep
```

## Integration with Services

Services should use the shared volume:

```yaml
# docker-compose.yml
services:
  ai-automation-service:
    volumes:
      - homeiq_models:/app/models  # Shared model cache
    environment:
      - HF_HOME=/app/models
```

Services will automatically use cached models if available, or download them if missing.

## Verification

Check if models are cached:

```bash
# List cached models
docker run --rm \
  -v homeiq_models:/app/models \
  python:3.12-slim \
  ls -lh /app/models

# Expected output:
# models--sentence-transformers--all-MiniLM-L6-v2/
# models--BAAI--bge-reranker-base/
# models--google--flan-t5-small/
```

## Troubleshooting

### Models Not Found

If services still download models:

1. **Check volume mount:**
   ```bash
   docker volume inspect homeiq_models
   ```

2. **Verify models exist:**
   ```bash
   docker run --rm -v homeiq_models:/app/models python:3.12-slim ls -R /app/models
   ```

3. **Check environment variables:**
   ```bash
   docker exec <service-container> env | grep HF_HOME
   ```

### OpenVINO Models Not Available

If OpenVINO is not available, standard models will be downloaded (larger size):

```bash
# Check OpenVINO installation
docker run --rm homeiq-model-prep python -c "import openvino; print(openvino.__version__)"
```

### Network Issues

If downloads fail due to network:

1. **Retry with longer timeout:**
   ```bash
   docker run --rm \
     -v homeiq_models:/app/models \
     -e HF_HUB_DOWNLOAD_TIMEOUT=600 \
     homeiq-model-prep
   ```

2. **Use proxy (if needed):**
   ```bash
   docker run --rm \
     -v homeiq_models:/app/models \
     -e HTTP_PROXY=http://proxy:port \
     -e HTTPS_PROXY=http://proxy:port \
     homeiq-model-prep
   ```

## Benefits

### Before Model-Prep

- ❌ Services download models on first use (5-10 min delay)
- ❌ Inconsistent model versions across services
- ❌ Requires internet connection on first run
- ❌ Slower CI/CD pipelines

### After Model-Prep

- ✅ Models pre-cached, services start immediately
- ✅ Consistent model versions across all services
- ✅ Works offline after initial download
- ✅ Faster CI/CD (models cached in build stage)

## Related Documentation

- [AI Automation Service Model Management](../../services/ai-automation-service/README-PHASE1-MODELS.md)
- [Docker Optimization Plan](../../docs/DOCKER_OPTIMIZATION_PLAN.md)
- [Model Manager Implementation](../../services/ai-automation-service/src/models/model_manager.py)

