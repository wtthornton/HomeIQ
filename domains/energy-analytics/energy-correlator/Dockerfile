# Multi-stage build for Energy Correlator Service
FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy requirements and install remaining dependencies
COPY domains/energy-analytics/energy-correlator/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-alpine

# Install runtime dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -u 1001 -S appuser -G appgroup

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code
COPY domains/energy-analytics/energy-correlator/src/ ./src/

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Switch to non-root user
USER appuser

# Add local packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8017

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8017/health || exit 1

# Run service
CMD ["python", "-m", "src.main"]

