# NER Model Service Container
# Pre-built container with dslim/bert-base-NER model

FROM python:3.11-slim AS builder

WORKDIR /app

# Install minimal dependencies (CPU-only)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --user \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.3.1+cpu \
 && pip install --no-cache-dir --user \
    transformers==4.45.2 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.38.0

# Pre-download and cache the NER model to a dedicated directory
RUN python - <<'PY' \
    || echo "NER model download skipped during build"
from pathlib import Path
from transformers import pipeline

cache_dir = Path("/app/model-cache")
cache_dir.mkdir(parents=True, exist_ok=True)
pipeline("ner", model="dslim/bert-base-NER", cache_dir=str(cache_dir))
PY

# Final stage keeps runtime lean
FROM python:3.11-slim

WORKDIR /app

# Copy Python dependencies and model cache from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/model-cache /app/model-cache

# Create model service
COPY services/ai-automation-service/src/model_services/ner_service.py ./ner_service.py

# Ensure model cache directory exists even if build download skipped
RUN mkdir -p /app/model-cache

# Ensure PATH includes user-installed binaries and set model cache directory
ENV PATH=/root/.local/bin:$PATH \
    HF_HOME=/app/model-cache

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8031/health || exit 1

EXPOSE 8031

CMD ["python", "-m", "uvicorn", "ner_service:app", "--host", "0.0.0.0", "--port", "8031"]
