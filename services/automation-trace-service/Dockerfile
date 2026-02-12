# Multi-stage build for Automation Trace Service
FROM python:3.12-alpine AS builder

WORKDIR /app
RUN pip install --upgrade pip==25.2
RUN apk add --no-cache gcc musl-dev linux-headers

COPY services/automation-trace-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app
RUN apk add --no-cache curl
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup services/automation-trace-service/src ./src
COPY --chown=appuser:appgroup shared ./shared

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8020}/health || exit 1

EXPOSE 8020
CMD ["python", "-m", "src.main"]
