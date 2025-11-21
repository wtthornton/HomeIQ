FROM python:3.12-slim

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/ai-code-executor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY services/ai-code-executor/src/ ./src/

# Create MCP workspace directory
RUN mkdir -p /tmp/mcp_workspace

# Expose port
EXPOSE 8030

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8030/health', timeout=5.0)"

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8030"]
