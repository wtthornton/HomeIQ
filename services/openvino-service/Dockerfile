# Multi-stage build for OpenVINO Service
# Phase 1: Containerized AI Models
# Models: BAAI/bge-large-en-v1.5 (1024-dim), bge-reranker-base, flan-t5-small [Epic 47]
# Optimized: Multi-stage build with non-root user (slim base required for OpenVINO)

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Copy requirements first for better caching (production only -- HIGH-3)
COPY services/openvino-service/requirements.txt .

# Install Python dependencies with CPU-only torch wheels and cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Install runtime dependencies for OpenVINO and create non-root user
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
COPY services/openvino-service/src/ ./src/
COPY shared/ ./shared/

# Create models directory with a Docker volume mount point for caching
# LOW-9: Model cache persists across container restarts when a volume is mounted
RUN mkdir -p /app/models && \
    chown -R appuser:appgroup /app /home/appuser/.local

VOLUME ["/app/models"]

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/src
ENV MODELS_DIR=/app/models
ENV HF_HOME=/app/models
ENV MODEL_CACHE_DIR=/app/models

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8019

# Health check (start_period=300s for model loading)
HEALTHCHECK --interval=30s --timeout=10s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:8019/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8019"]
