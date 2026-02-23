# Multi-stage build for HA Simulator Service
# Optimized: Multi-stage build with Alpine base, non-root user

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements and install Python dependencies
COPY domains/core-platform/ha-simulator/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Install shared libs
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache curl ca-certificates

# Create non-root user (consistent UID/GID with other services)
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY domains/core-platform/ha-simulator/src/ ./src/
COPY domains/core-platform/ha-simulator/config/ ./config/
COPY domains/core-platform/ha-simulator/data/ ./data/

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8123

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8123/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
