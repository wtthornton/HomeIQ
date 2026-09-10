# automation-domain (TAP-7275): agent chat + automation authoring + proactive
# suggestions in one process. Replaces the ha-ai-agent-service,
# ai-automation-service-new and proactive-agent-service images.
#
# No OpenAI or Anthropic SDK is installed: every model call is an AgentForge
# workflow run over HTTP, so this image carries no provider credential.

FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --upgrade pip==25.2

# Install shared libs first (required by requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/ \
    /tmp/libs/homeiq-memory/

COPY domains/automation-core/automation-domain/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# ============================================================================
# Final stage
# ============================================================================
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends --only-upgrade openssl libssl3t64 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

COPY --from=builder /root/.local /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app:/app/src

COPY domains/automation-core/automation-domain/src ./src
COPY domains/automation-core/automation-domain/alembic ./alembic
COPY domains/automation-core/automation-domain/alembic.ini ./alembic.ini

RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app /home/appuser/.local

USER appuser

EXPOSE 8030

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8030/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8030"]
