# homeiq-mcp — the HomeIQ MCP server (TAP-5293)
# Build context is the repo root (compose: context: ../..).

FROM python:3.12-alpine AS builder

WORKDIR /app
RUN pip install --upgrade pip==25.2
RUN apk add --no-cache gcc musl-dev linux-headers

COPY domains/core-platform/homeiq-mcp/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-alpine AS production

RUN apk add --no-cache --upgrade openssl

RUN apk add --no-cache curl \
    && addgroup -g 1001 -S appgroup \
    && adduser -S appuser -u 1001 -G appgroup

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY domains/core-platform/homeiq-mcp/src/ ./src/
# The normative tool catalogue ships inside the image so list_tools cannot drift from docs/mcp.
COPY docs/mcp/homeiq-mcp-tools.schema.json ./catalogue/homeiq-mcp-tools.schema.json

RUN chown -R appuser:appgroup /app
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HOMEIQ_MCP_CATALOGUE_PATH=/app/catalogue/homeiq-mcp-tools.schema.json

EXPOSE 8050
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8050/health || exit 1

CMD ["python", "-m", "src.main"]
