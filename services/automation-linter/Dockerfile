FROM python:3.11-slim

WORKDIR /app

# Copy shared module first
COPY shared/ha_automation_lint /app/shared/ha_automation_lint

# Add shared to Python path
ENV PYTHONPATH="/app/shared:${PYTHONPATH}"

# Install dependencies
COPY services/automation-linter/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/automation-linter/src /app/src

# Copy UI
COPY services/automation-linter/ui /app/ui

# Expose port
EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8020/health', timeout=5.0)"

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]
