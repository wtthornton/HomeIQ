# Multi-stage build for AI Core Service
# Phase 1: Containerized AI Models
# Responsibilities: Service orchestration, request routing, business logic
# Optimized: Multi-stage build with Alpine base, non-root user

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements and install Python dependencies
COPY domains/ml-engine/ai-core-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Install shared libs from libs/
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

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY domains/ml-engine/ai-core-service/src/ ./src/

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8018

# Health check is defined in docker-compose.yml (takes precedence over Dockerfile)
# Removed HEALTHCHECK to avoid dual healthcheck mismatch

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8018"]
