# OpenVINO Service - Optimized Model Inference
# Phase 1: Containerized AI Models
# Models: all-MiniLM-L6-v2, bge-reranker-base, flan-t5-small (INT8)

FROM python:3.11-slim AS builder

WORKDIR /app

# Copy requirements first for better caching
COPY services/openvino-service/requirements.txt .

# Install Python dependencies with CPU-only torch wheels
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies for OpenVINO
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY services/openvino-service/src/ ./src/

# Set environment variables
ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    MODELS_DIR=/app/models \
    HF_HOME=/app/models

# Create models directory and prune pip caches
RUN mkdir -p /app/models \
 && rm -rf /root/.cache/pip

# Expose port
EXPOSE 8019

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8019/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8019"]
