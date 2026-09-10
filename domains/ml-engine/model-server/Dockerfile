# Multi-stage build for model-server
# Merged from openvino-service, ml-service, rag-service (TAP-7276): one
# process, one model load. ner-service is dropped, not folded here.
# Libraries: sentence-transformers/torch (embeddings/rerank/classify),
# scikit-learn (clustering/anomaly detection), SQLAlchemy/asyncpg (RAG).

FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip==25.2

# Build dependencies for scikit-learn / scipy native extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

COPY domains/ml-engine/model-server/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

RUN apt-get update && apt-get install -y --no-install-recommends --only-upgrade openssl libssl3t64 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

# Copy Python dependencies from builder to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY domains/ml-engine/model-server/src/ ./src/

# Model cache directory (former openvino-service: LOW-9, persists across
# restarts when a volume is mounted) and RAG's data directory.
RUN mkdir -p /app/models /app/data && \
    chown -R appuser:appgroup /app /home/appuser/.local

VOLUME ["/app/models"]

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/src
ENV MODELS_DIR=/app/models
ENV HF_HOME=/app/models
ENV MODEL_CACHE_DIR=/app/models

USER appuser

EXPOSE 8019

# start_period=300s: inherited from openvino-service for first-model-load latency.
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8019/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8019"]
