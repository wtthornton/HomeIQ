# Multi-stage build for Zeek Network Intelligence Service
# Epic 72, Story 72.3
FROM python:3.12-alpine AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apk add --no-cache gcc musl-dev libffi-dev linux-headers

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/ \
    /tmp/libs/homeiq-memory/

# Copy requirements and install remaining dependencies
COPY domains/data-collectors/zeek-network-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# IEEE OUI dataset (~577 KB gz, ~53.7k assignments). The curated fallback in
# oui_lookup.py resolved 0 of 54 devices on the reference network, so vendor
# identity depends on this file being present and current.
#
# Vendored, not fetched at build time: IEEE blocks datacenter/CI egress IPs,
# so a build-time `RUN` fetch here (the previous approach) fails on
# GitHub-hosted runners with httpx.ConnectError: [Errno 111] Connection
# refused, even though the same fetch succeeds from a developer machine.
# scripts/fetch_ieee_oui.py remains in the repo as the documented refresh
# tool -- see its docstring for the refresh procedure.
COPY domains/data-collectors/zeek-network-service/scripts/fetch_ieee_oui.py ./scripts/
COPY domains/data-collectors/zeek-network-service/data/ieee-oui.tsv.gz /app/data/ieee-oui.tsv.gz

# Production stage
FROM python:3.12-alpine AS production

RUN apk add --no-cache --upgrade openssl

WORKDIR /app

# Install runtime dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup

# Persistent state directory for log seek offsets
RUN mkdir -p /app/state && chown appuser:appgroup /app/state

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup domains/data-collectors/zeek-network-service/src ./src
COPY --from=builder --chown=appuser:appgroup /app/data ./data

# Copy Alembic config
COPY --chown=appuser:appgroup domains/data-collectors/zeek-network-service/alembic.ini .
COPY --chown=appuser:appgroup domains/data-collectors/zeek-network-service/alembic ./alembic

# Set environment variables
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${SERVICE_PORT:-8048}/health || exit 1

# Expose port
EXPOSE 8048

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8048"]
