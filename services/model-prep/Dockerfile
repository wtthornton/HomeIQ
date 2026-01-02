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

FROM python:3.12-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers git curl

# Upgrade pip
RUN pip install --upgrade pip==25.2

# Install model download dependencies
COPY services/model-prep/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache curl ca-certificates git

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy model preparation script
COPY services/model-prep/download_all_models.py .

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
