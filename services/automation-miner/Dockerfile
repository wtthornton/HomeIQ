# Multi-stage build for Automation Miner service
FROM python:3.12-slim AS base

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/automation-miner/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY services/automation-miner/src/ ./src/
COPY services/automation-miner/alembic/ ./alembic/
COPY services/automation-miner/alembic.ini .

# Create data directory
RUN mkdir -p /app/data

# Run as non-root user
RUN useradd -m -u 1000 miner && chown -R miner:miner /app
USER miner

# Expose port
EXPOSE 8019

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8019/health || exit 1

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8019"]

