# Multi-stage build for ML Service
# Phase 1: Containerized AI Models
# Libraries: scikit-learn, numpy, scipy
# Optimized: Multi-stage build with non-root user (slim base for ML libraries)

FROM python:3.12-slim AS builder

WORKDIR /app

# Upgrade pip to latest version
RUN pip install --upgrade pip==25.2

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY services/ml-service/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Install runtime dependencies and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* && \
    groupadd -g 1001 appgroup && \
    useradd -r -u 1001 -g appgroup appuser

# Copy Python dependencies from builder stage to user directory
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY services/ml-service/src/ ./src/
COPY shared/ ./shared/

# Set ownership
RUN chown -R appuser:appgroup /app /home/appuser/.local

# Set environment variables (only /app to avoid ambiguous imports)
ENV PYTHONPATH=/app
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8020/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]
