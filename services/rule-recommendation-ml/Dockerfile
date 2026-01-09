# Rule Recommendation ML Service Dockerfile
# Multi-stage build for production deployment

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.12-slim as runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create models directory
RUN mkdir -p /app/models

# Copy application code
COPY src/ ./src/

# Copy models if they exist (optional - models can be trained in container)
# Models directory will be mounted as a volume in production

# Environment variables
ENV PORT=8035
ENV HOST=0.0.0.0
ENV MODEL_PATH=/app/models/rule_recommender.pkl
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8035/api/v1/health')" || exit 1

EXPOSE 8035

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8035"]
