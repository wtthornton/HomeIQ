FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY services/device-health-monitor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ /app/shared

# Copy source
COPY services/device-health-monitor/src/ ./src/

# Run service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8019"]

