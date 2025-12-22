# Model Preparation Container
# Pre-downloads and caches ML models for deterministic builds
#
# Purpose:
# - Pre-download models during CI/CD or local setup
# - Cache models in shared volume for all AI services
# - Ensure models are available before service containers start
# - Reduce startup time for AI services
#
# Usage:
#   docker build -t homeiq-model-prep -f services/model-prep/Dockerfile services/model-prep
#   docker run --rm -v homeiq_models:/app/models homeiq-model-prep

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip==25.2

# Install model download dependencies
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

# Copy model preparation script
COPY download_all_models.py .

# Set HuggingFace cache directory
ENV HF_HOME=/app/models
ENV TRANSFORMERS_CACHE=/app/models

# Create models directory (will be mounted as volume)
RUN mkdir -p /app/models

# Run model download script
CMD ["python", "download_all_models.py"]

