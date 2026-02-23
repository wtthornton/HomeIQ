# Multi-stage build for Data Retention Service
# Optimized: Combined RUN commands, optimized layer ordering, reduced image size

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip and install build dependencies in single layer
RUN pip install --upgrade pip==25.2 && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (optimized layer ordering)
COPY domains/core-platform/data-retention/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Install shared libs
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

# Install runtime dependencies and create user in single layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libopenblas0 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code
COPY domains/core-platform/data-retention/src/ ./src/

# Set ownership and create directories in single layer
RUN chown -R appuser:appgroup /app /home/appuser/.local && \
    mkdir -p /app/logs /backups && \
    chown -R appuser:appgroup /app/logs /backups && \
    chmod -R 755 /app/logs

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the service
CMD ["python", "-m", "src.main"]
