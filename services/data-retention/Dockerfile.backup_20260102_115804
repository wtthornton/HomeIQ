# Multi-stage build for Data Retention Service
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies with pre-compiled wheels
COPY services/data-retention/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Production stage
FROM python:3.12-slim AS production

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    libopenblas0 \
    liblapack3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user first
RUN groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code and shared modules
COPY services/data-retention/src/ ./src/
COPY shared/ ./shared/

# Set ownership of all files to appuser
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Create log directory with proper permissions
RUN mkdir -p /app/logs && \
    chown -R appuser:appgroup /app/logs && \
    chmod -R 755 /app/logs

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Create backups directory with proper permissions
RUN mkdir -p /backups && \
    chown -R appuser:appgroup /backups

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the service
CMD ["python", "-m", "src.main"]
