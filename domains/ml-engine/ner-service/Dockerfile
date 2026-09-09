# NER Service - Entity extraction using transformers
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip

# Install shared libraries. homeiq-observability declares homeiq-data[auth] as a
# dependency (TAP-6037), so both local paths must be in one pip invocation —
# installing observability alone makes pip look for homeiq-data on PyPI, where it
# does not exist, and the build fails. Same grouping as openvino-service and
# rag-service.
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-resilience/

# Install dependencies
COPY domains/ml-engine/ner-service/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Production stage
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends --only-upgrade openssl libssl3t64 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --gid 1001 appgroup && \
    adduser --disabled-password --uid 1001 --ingroup appgroup appuser

COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH

COPY domains/ml-engine/ner-service/src/ner_service.py ./ner_service.py

RUN chown -R appuser:appgroup /app /home/appuser/.local

USER appuser

EXPOSE 8031

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8031/health || exit 1

CMD ["python", "-m", "uvicorn", "ner_service:app", "--host", "0.0.0.0", "--port", "8031"]
