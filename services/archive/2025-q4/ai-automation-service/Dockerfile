# Multi-stage Docker build for AI Automation Service
# Using Debian-slim instead of Alpine for pre-built numpy/scikit-learn wheels
# (Alpine requires building from source which is complex and time-consuming)

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Copy requirements from service directory
COPY requirements.txt .

# Install Python dependencies with cache mount for faster rebuilds
# Cache mount speeds up pip install significantly on subsequent builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Final stage
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
# Added: libgomp1 for OpenVINO threading, spaCy model download
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Hugging Face stack so community pattern features work out of the box
# Epic 41 Story 41.1: Updated to PyTorch 2.4.0+cpu and latest stable versions
RUN pip install --no-cache-dir \
    --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.4.0,<3.0.0" \
 && pip install --no-cache-dir \
    "transformers>=4.46.1,<5.0.0" \
    "sentence-transformers>=3.3.1,<4.0.0" \
    "openvino>=2024.5.0,<2025.0.0" \
    "optimum-intel>=1.21.0,<2.0.0"

# Note: Model downloads removed from build-time to reduce image size
# Models will be downloaded at startup via ensure_model_cache.py or service initialization
# This includes: spaCy models, NER models, and training models (flan-t5-small)
# Models are stored in /app/models which is mounted as a volume (ai_automation_models)

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code from service directory
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Copy shared logging (for imports)
COPY ../shared/ ./shared/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH \
    HF_HOME=/app/models

# Create data and models directories
# Models directory will be populated at startup via ensure_model_cache.py
RUN mkdir -p /app/data /app/models \
 && rm -rf /root/.cache/huggingface

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8018/health || exit 1

# Expose port
EXPOSE 8018

# Run migrations, ensure model cache, and start service
CMD ["sh", "-c", "alembic upgrade heads || echo 'Migration skipped' && python scripts/ensure_model_cache.py && python -m uvicorn src.main:app --host 0.0.0.0 --port 8018"]

