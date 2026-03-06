# Multi-stage build for Voice Gateway Service
FROM python:3.12-slim AS builder

WORKDIR /app
RUN pip install --upgrade pip==25.2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libsndfile1-dev && \
    rm -rf /var/lib/apt/lists/*

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy requirements and install dependencies
COPY domains/frontends/voice-gateway/requirements.txt .
# Install openwakeword without deps (tflite-runtime doesn't support Python 3.12)
# Then install onnxruntime as the backend
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user openwakeword --no-deps && \
    pip install --no-cache-dir --user onnxruntime>=1.18.0 && \
    pip install --no-cache-dir --user -r requirements.txt --ignore-installed openwakeword

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libsndfile1 && \
    rm -rf /var/lib/apt/lists/*
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -s /bin/bash appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup domains/frontends/voice-gateway/src ./src

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8041}/health || exit 1

EXPOSE 8041
CMD ["python", "-m", "src.main"]
