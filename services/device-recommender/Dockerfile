FROM python:3.12-slim

WORKDIR /app

# Copy requirements
COPY services/device-recommender/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities
COPY shared/ /app/shared

# Copy source
COPY services/device-recommender/src/ ./src/

# Run service
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8023"]

