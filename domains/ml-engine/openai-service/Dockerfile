# OpenAI Service - Thin wrapper for OpenAI API
FROM python:3.12-alpine AS builder

WORKDIR /app

RUN pip install --upgrade pip

# Install shared libraries
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user /tmp/libs/homeiq-observability/

COPY domains/ml-engine/openai-service/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Production stage
FROM python:3.12-alpine

WORKDIR /app

RUN apk add --no-cache curl && \
    addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH

COPY domains/ml-engine/openai-service/src/openai_service.py ./openai_service.py

RUN chown -R appuser:appgroup /app /home/appuser/.local

USER appuser

EXPOSE 8020

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

CMD ["python", "-m", "uvicorn", "openai_service:app", "--host", "0.0.0.0", "--port", "8020"]
