# Multi-stage Docker build for YAML Validation Service
# Epic 51, Story 51.4: Create Unified Validation Service

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Copy requirements from service directory
COPY services/yaml-validation-service/requirements.txt .

# Install Python dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Final stage
# ============================================================================
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy service code
COPY services/yaml-validation-service/src ./src
COPY shared ./shared

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8026

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8026/health || exit 1

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8026"]

