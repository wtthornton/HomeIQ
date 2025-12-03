# Proactive Agent Service - Context-aware automation suggestions
# Epic AI-21: Proactive Conversational Agent Service

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/proactive-agent-service/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY services/proactive-agent-service/src/ ./src/

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app/src

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose port
EXPOSE 8031

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8031/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8031"]

