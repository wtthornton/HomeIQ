# OpenAI Client Service Container
# Lightweight container for OpenAI API calls
FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies
RUN pip install --no-cache-dir \
    openai==1.12.0 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    httpx==0.25.2

# Create OpenAI service
COPY services/ai-automation-service/src/model_services/openai_service.py ./openai_service.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8020/health || exit 1

EXPOSE 8020

CMD ["python", "-m", "uvicorn", "openai_service:app", "--host", "0.0.0.0", "--port", "8020"]
