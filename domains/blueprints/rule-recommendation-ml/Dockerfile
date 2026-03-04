# Rule Recommendation ML Service Dockerfile
# Multi-stage build for production deployment

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install shared libs first
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Install Python dependencies
COPY domains/blueprints/rule-recommendation-ml/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/false appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Create models directory
RUN mkdir -p /app/models

# Copy application code
COPY domains/blueprints/rule-recommendation-ml/src/ ./src/

# Copy models if they exist (optional - models can be trained in container)
# Models directory will be mounted as a volume in production

# Environment variables
ENV PORT=8035
ENV HOST=0.0.0.0
ENV MODEL_PATH=/app/models/rule_recommender.pkl
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set ownership
RUN chown -R appuser:appgroup /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8035/api/v1/health')"

EXPOSE 8035

USER appuser

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8035"]
