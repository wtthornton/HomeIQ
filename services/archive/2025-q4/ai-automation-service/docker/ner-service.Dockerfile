# NER Model Service Container
# Pre-built container with dslim/bert-base-NER model

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install minimal dependencies (CPU-only)
# Epic 41 Story 41.1: Updated to PyTorch 2.4.0+cpu, FastAPI 0.123.x, Uvicorn 0.32.x
RUN pip install --no-cache-dir --user \
    --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.4.0,<3.0.0" \
 && pip install --no-cache-dir --user \
    "transformers>=4.46.1,<5.0.0" \
    "fastapi>=0.123.0,<0.124.0" \
    "uvicorn[standard]>=0.32.0,<0.33.0"

# Note: NER model download removed from build-time to reduce image size
# Model will be downloaded at startup by the service (first request will be slower)
# This reduces image size by ~400MB+ (model weights)

# Final stage keeps runtime lean
FROM python:3.12-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Create model service
COPY src/model_services/ner_service.py ./ner_service.py

# Create model cache directory (will be populated at startup)
RUN mkdir -p /app/model-cache

# Ensure PATH includes user-installed binaries and set model cache directory
ENV PATH=/root/.local/bin:$PATH \
    HF_HOME=/app/model-cache

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8031/health || exit 1

EXPOSE 8031

CMD ["python", "-m", "uvicorn", "ner_service:app", "--host", "0.0.0.0", "--port", "8031"]
