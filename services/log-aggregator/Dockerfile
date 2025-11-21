# Multi-stage build for Log Aggregator Service
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/log-aggregator/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with docker group access
# Docker group GID is typically 999 or varies by system
# We'll add appuser to a group that matches docker GID
RUN groupadd -g 999 docker || true && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup -G docker appuser

# Copy Python dependencies from builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code and shared modules
COPY services/log-aggregator/src/ ./src/
COPY shared/ ./shared/

# Set ownership of all files to appuser
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Create log directory with proper permissions
RUN mkdir -p /var/log/homeiq && \
    chown -R appuser:appgroup /var/log/homeiq && \
    chmod -R 755 /var/log/homeiq

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8015

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8015/health || exit 1

# Start the service
CMD ["python", "-m", "src.main"]
