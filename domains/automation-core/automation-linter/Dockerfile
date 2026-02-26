FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY domains/automation-core/automation-linter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install shared libs from libs/
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Copy service code
COPY domains/automation-core/automation-linter/src /app/src

# Copy UI
COPY domains/automation-core/automation-linter/ui /app/ui

# Expose port
EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8020/health', timeout=5.0)"

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]
