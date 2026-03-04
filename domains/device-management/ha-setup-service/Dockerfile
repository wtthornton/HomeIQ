# Multi-stage build for production optimization
FROM python:3.12-alpine AS builder

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev

WORKDIR /app

# Install shared libs first
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy requirements and install dependencies with cache mount
COPY domains/device-management/ha-setup-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine

# Add non-root user for security
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup domains/device-management/ha-setup-service/src/ ./src/
COPY --chown=appuser:appgroup domains/device-management/ha-setup-service/alembic/ ./alembic/
COPY --chown=appuser:appgroup domains/device-management/ha-setup-service/alembic.ini ./alembic.ini

# Create data directory
RUN mkdir -p /app/data && chown -R appuser:appgroup /app/data

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/health')"

# Expose port
EXPOSE 8020

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]

