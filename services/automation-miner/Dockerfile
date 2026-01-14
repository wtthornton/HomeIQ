# Multi-stage build for Automation Miner service
# Optimized: Proper multi-stage build with non-root user

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements and install Python dependencies
COPY services/automation-miner/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app

# Install runtime dependencies (including su-exec for user switching)
RUN apk add --no-cache curl ca-certificates su-exec

# Create non-root user (consistent UID/GID with other services)
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code
COPY services/automation-miner/src/ ./src/
COPY services/automation-miner/alembic/ ./alembic/
COPY services/automation-miner/alembic.ini .
COPY shared/ ./shared/

# Copy entrypoint script and fix line endings (Windows CRLF -> Unix LF)
COPY services/automation-miner/docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Create data directory and set ownership
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Use entrypoint script (runs as root to fix permissions, then switches to appuser)
ENTRYPOINT ["/docker-entrypoint.sh"]

# Expose port
EXPOSE 8019

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8019/health || exit 1

# Run application (entrypoint will switch to appuser before executing)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8019"]
