# Data API Service - Production Dockerfile
# Multi-stage build for minimal image size

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev cargo

# Copy requirements
COPY services/data-api/requirements-prod.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements-prod.txt

# Production stage
FROM python:3.12-alpine

WORKDIR /app

# Install runtime dependencies only
RUN apk add --no-cache libffi openssl

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy shared utilities
COPY shared/ /app/shared

# Copy application code
COPY services/data-api/src/ /app/src/

# Copy Alembic migrations
COPY services/data-api/alembic/ /app/alembic/
COPY services/data-api/alembic.ini /app/

# Expose port
EXPOSE 8006

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8006/health')" || exit 1

# Run the service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8006"]

