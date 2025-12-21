# Multi-stage build for Air Quality Service
FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

RUN apk add --no-cache gcc musl-dev linux-headers

COPY requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

FROM python:3.12-alpine AS production

WORKDIR /app
RUN apk add --no-cache curl

RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

COPY --from=builder /root/.local /home/appuser/.local
COPY src/ ./src/
COPY ../shared/ ./shared/

RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PYTHONUNBUFFERED=1
ENV PATH=/home/appuser/.local/bin:$PATH

USER appuser

EXPOSE 8012

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8012/health || exit 1

CMD ["python", "-m", "src.main"]

