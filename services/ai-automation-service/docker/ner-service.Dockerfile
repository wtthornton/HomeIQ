# NER Model Service Container
# Pre-built container with dslim/bert-base-NER model
FROM python:3.11-slim

WORKDIR /app

# Install minimal dependencies
RUN pip install --no-cache-dir \
    transformers==4.45.2 \
    torch \
    fastapi==0.104.1 \
    uvicorn==0.24.0

# Pre-download and cache the NER model
RUN python -c "from transformers import pipeline; print('Downloading NER model...'); ner = pipeline('ner', model='dslim/bert-base-NER'); print('NER model downloaded and cached')"

# Create model service
COPY services/ai-automation-service/src/model_services/ner_service.py ./ner_service.py

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8019/health || exit 1

EXPOSE 8019

CMD ["python", "-m", "uvicorn", "ner_service:app", "--host", "0.0.0.0", "--port", "8019"]
