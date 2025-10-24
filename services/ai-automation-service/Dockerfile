# Multi-stage Docker build for AI Automation Service
# Using Debian-slim instead of Alpine for pre-built numpy/scikit-learn wheels
# (Alpine requires building from source which is complex and time-consuming)

FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements from service directory
COPY services/ai-automation-service/requirements.txt .

# Install Python dependencies (pre-built wheels available for Debian)
RUN pip install --no-cache-dir --user -r requirements.txt

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

# Download spaCy English model for NER fallback
RUN python -m spacy download en_core_web_sm || echo "spaCy model download failed, will retry on startup"

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code from service directory
COPY services/ai-automation-service/src/ ./src/
COPY services/ai-automation-service/alembic/ ./alembic/
COPY services/ai-automation-service/alembic.ini ./
COPY services/ai-automation-service/tests/ ./tests/

# Copy shared logging (for imports)
COPY shared/ ./shared/

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Create data and models directories
RUN mkdir -p /app/data /app/models

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

