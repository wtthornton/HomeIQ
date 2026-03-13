# Model Preparation Container
# Pre-downloads and caches ML models for deterministic builds
#
# Purpose:
# - Pre-download models during CI/CD or local setup
# - Cache models in shared volume for all AI services
# - Ensure models are available before service containers start
# - Reduce startup time for AI services
#
# Usage:
#   docker build -t homeiq-model-prep -f services/model-prep/Dockerfile services/model-prep
#   docker run --rm -v homeiq_models:/app/models homeiq-model-prep

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends gcc git curl && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip==25.2

# Install model download dependencies
COPY domains/ml-engine/model-prep/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Install shared libs from libs/
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates git && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/false appuser

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy model preparation script
COPY domains/ml-engine/model-prep/download_all_models.py .

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

# Create models directory (will be mounted as volume)
RUN mkdir -p /app/models && \
    chown -R appuser:appgroup /app/models

# Switch to non-root user
USER appuser

# Run model download script
CMD ["python", "download_all_models.py"]
