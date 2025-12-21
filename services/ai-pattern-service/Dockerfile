# AI Pattern Service Dockerfile
# Epic 39, Story 39.5: Pattern Service Foundation

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt /app/requirements.txt

# Install Python dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY src /app/src
COPY ../shared /app/shared

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8020

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]

