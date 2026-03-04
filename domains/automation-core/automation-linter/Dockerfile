# Multi-stage build for Automation Linter Service
FROM python:3.12-slim AS builder

WORKDIR /app

# Install shared libs first (before requirements.txt)
COPY libs/ /tmp/libs/
RUN pip install --no-cache-dir --user \
    /tmp/libs/homeiq-patterns/ \
    /tmp/libs/homeiq-resilience/ \
    /tmp/libs/homeiq-observability/ \
    /tmp/libs/homeiq-data/ \
    /tmp/libs/homeiq-ha/

# Install Python dependencies
COPY domains/automation-core/automation-linter/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.12-slim AS production

WORKDIR /app

# Create non-root user
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -s /bin/false appuser

# Copy installed packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy service code
COPY domains/automation-core/automation-linter/src /app/src

# Copy UI
COPY domains/automation-core/automation-linter/ui /app/ui

# Set ownership
RUN chown -R appuser:appgroup /app

# Expose port
EXPOSE 8020

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8020/health')"

# Switch to non-root user
USER appuser

# Run service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8020"]
