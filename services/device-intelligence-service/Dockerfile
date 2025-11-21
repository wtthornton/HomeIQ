# Multi-stage build for minimal image size
FROM python:3.12-slim AS builder

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY services/device-intelligence-service/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Copy shared utilities
COPY shared/ /app/shared

# Copy application source
COPY services/device-intelligence-service/src/ /app/src/

# Copy models directory (ML models for predictive analytics)
COPY services/device-intelligence-service/models/ /app/models/

# Set working directory
WORKDIR /app

# Add user packages to PATH
ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE 8019

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8019/health/ || exit 1

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8019"]
