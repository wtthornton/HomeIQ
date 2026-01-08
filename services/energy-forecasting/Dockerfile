# Energy Forecasting Service Dockerfile

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

# Copy application code
COPY src/ ./src/
COPY models/ ./models/ 2>/dev/null || true

# Create models directory
RUN mkdir -p /app/models

# Environment variables
ENV PORT=8037
ENV HOST=0.0.0.0
ENV MODEL_PATH=/app/models/energy_forecaster
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8037/api/v1/health')" || exit 1

EXPOSE 8037

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8037"]
