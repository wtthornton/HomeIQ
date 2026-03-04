# Multi-stage build for HA Device Control Service
FROM python:3.12-alpine AS builder

WORKDIR /app
RUN pip install --upgrade pip==25.2
RUN apk add --no-cache gcc musl-dev linux-headers

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy requirements and install remaining dependencies
COPY domains/automation-core/ha-device-control/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-alpine AS production

WORKDIR /app
RUN apk add --no-cache curl
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup domains/automation-core/ha-device-control/src ./src

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8040}/health || exit 1

EXPOSE 8040
CMD ["python", "-m", "src.main"]
