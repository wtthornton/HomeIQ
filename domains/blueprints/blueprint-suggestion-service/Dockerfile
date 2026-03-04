# Blueprint Suggestion Service Dockerfile
# Multi-stage build for production optimization
FROM python:3.12-slim AS builder

WORKDIR /app

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy requirements and install remaining dependencies
COPY domains/blueprints/blueprint-suggestion-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV PYTHONPATH=/app

WORKDIR /app

# Create non-root user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/false appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY domains/blueprints/blueprint-suggestion-service/src/ ./src/

# Copy Alembic configuration for migrations
COPY domains/blueprints/blueprint-suggestion-service/alembic.ini ./
COPY domains/blueprints/blueprint-suggestion-service/alembic/ ./alembic/

# Create data directory
RUN mkdir -p /app/data

# Set ownership
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8032

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8032/health')"

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8032"]
