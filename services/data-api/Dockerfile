# Data API Service - Production Dockerfile
# Multi-stage build for minimal image size

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version (allow automatic updates)
RUN pip install --upgrade pip

# Install build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev cargo

# Copy requirements
COPY services/data-api/requirements-prod.txt .

# Install Python dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Production stage
FROM python:3.12-alpine

WORKDIR /app

# Install runtime dependencies and create non-root user
RUN apk add --no-cache libffi openssl curl ca-certificates && \
    addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python packages from builder to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Make sure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/src

# Copy shared utilities (from root shared directory)
# Note: Build context must be root directory for this to work
COPY shared/ ./shared/

# Copy application code
COPY services/data-api/src/ ./src/

# Copy Alembic migrations
COPY services/data-api/alembic/ ./alembic/
COPY services/data-api/alembic.ini ./

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')" || exit 1

# Run the service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8006"]

