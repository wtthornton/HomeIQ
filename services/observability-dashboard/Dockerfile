# Observability Dashboard Service - Streamlit
# Python 3.11-slim for minimal image size

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements
COPY services/observability-dashboard/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared utilities (from root shared directory)
# Note: Build context must be root directory for this to work
COPY shared/ ./shared/

# Copy application code
COPY services/observability-dashboard/src/ ./src/

# Expose Streamlit port
EXPOSE 8501

# Health check (Streamlit health endpoint)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

# Run Streamlit
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
