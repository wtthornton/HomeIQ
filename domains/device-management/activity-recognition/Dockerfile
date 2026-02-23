# Activity Recognition Service Dockerfile
# Optimized for NUC deployment with ONNX Runtime

FROM python:3.12-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Install shared libs
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/


FROM python:3.12-slim as runtime

WORKDIR /app

# Create non-root user first
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -d /home/appuser appuser

# Copy installed packages from builder to appuser directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code and health check script
COPY src/ ./src/
COPY healthcheck.py ./healthcheck.py

# Create models directory
RUN mkdir -p /app/models

# Set ownership of all files to appuser
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PORT=8036
ENV HOST=0.0.0.0
ENV MODEL_PATH=/app/models/activity_lstm.onnx
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Limit ONNX Runtime threads for NUC
ENV OMP_NUM_THREADS=4

USER appuser

# Health check - accept 200 (healthy) or 503 (degraded/no model) as server running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD ["python", "/app/healthcheck.py"]

EXPOSE 8036

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8036"]
