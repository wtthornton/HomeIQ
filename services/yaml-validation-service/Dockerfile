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

# Install runtime dependencies and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

# Copy Python packages from builder to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/src

# Copy service code
COPY services/yaml-validation-service/src ./src
COPY shared ./shared

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set working directory
WORKDIR /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8037

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8037/health || exit 1

# Run service (port will be overridden by SERVICE_PORT env var if set)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8037"]

