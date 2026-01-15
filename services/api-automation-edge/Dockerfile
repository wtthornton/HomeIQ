# Multi-stage build for API Automation Edge Service
FROM python:3.12-alpine AS builder

# Set working directory
WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements and install Python dependencies
COPY services/api-automation-edge/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache curl ca-certificates

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
# Note: schema.json is included in shared/ directory (copied with shared/)
# Tests are excluded - they are in tests/ directory, not in shared/
COPY services/api-automation-edge/src/ ./src/
COPY shared/ ./shared/

# Create data directory for database
RUN mkdir -p /app/data

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8025

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8025/health || exit 1

# Run the application
CMD ["python", "-m", "src.main"]
