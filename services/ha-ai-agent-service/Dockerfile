# Multi-stage build for HA AI Agent Service
# Epic AI-19: Foundation for conversational AI agent
# Optimized: Multi-stage build with Alpine base, non-root user

FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements and install Python dependencies
COPY services/ha-ai-agent-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app

# Install runtime dependencies (including su-exec for user switching)
RUN apk add --no-cache curl ca-certificates su-exec

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY services/ha-ai-agent-service/src/ ./src/
COPY shared/ ./shared/

# Create data directory for SQLite database and set ownership
RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app /home/appuser/.local

# Copy entrypoint script, convert to Unix line endings, and make it executable
COPY services/ha-ai-agent-service/docker-entrypoint.sh /docker-entrypoint.sh
RUN sed -i 's/\r$//' /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8030

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8030/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8030"]
