# Multi-stage Docker build for AI Automation Service
# Using Debian-slim instead of Alpine for pre-built numpy/scikit-learn wheels
# (Alpine requires building from source which is complex and time-consuming)

FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements from service directory
COPY services/ai-automation-service/requirements.txt .

# Install Python dependencies with cache mount for faster rebuilds
# Cache mount speeds up pip install significantly on subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Final stage
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
# Added: libgomp1 for OpenVINO threading, spaCy model download
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Hugging Face stack so community pattern features work out of the box
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    torch==2.2.2+cpu \
 && pip install --no-cache-dir \
    transformers==4.45.2 \
    sentence-transformers==3.3.1 \
    openvino==2024.5.0 \
    optimum-intel==1.20.0

# Download spaCy English model for NER fallback
RUN python -m spacy download en_core_web_sm || echo "spaCy model download failed, will retry on startup"

# Pre-populate Hugging Face cache with NER model (dslim/bert-base-NER)
RUN python - <<'PY' || echo "Transformers NER model download skipped"
from pathlib import Path
from transformers import pipeline

cache_dir = Path("/app/models")
cache_dir.mkdir(parents=True, exist_ok=True)
pipeline("ner", model="dslim/bert-base-NER", cache_dir=str(cache_dir))
PY

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code from service directory
COPY services/ai-automation-service/src/ ./src/
COPY services/ai-automation-service/alembic/ ./alembic/
COPY services/ai-automation-service/alembic.ini ./

# Copy shared logging (for imports)
COPY shared/ ./shared/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH \
    HF_HOME=/app/models

# Create data and models directories
RUN mkdir -p /app/data /app/models \
 && rm -rf /root/.cache/huggingface

# Pre-download Phase 1 models (optional - can also lazy-load on first use)
# Uncomment to pre-download during build (increases build time but faster first run)
# COPY services/ai-automation-service/scripts/download-models.py ./scripts/
# RUN python scripts/download-models.py || echo "Model download failed, will retry on startup"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8018/health || exit 1

# Expose port
EXPOSE 8018

# Run migrations and start service
CMD ["sh", "-c", "alembic upgrade head || echo 'Migration skipped' && python -m uvicorn src.main:app --host 0.0.0.0 --port 8018"]

