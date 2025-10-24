#!/bin/bash
"""
Deployment script for Multi-Model Entity Extraction
Handles model downloads, configuration, and service startup
"""

set -e

echo "🚀 Deploying Multi-Model Entity Extraction System"
echo "================================================="

# Configuration
SERVICE_NAME="ai-automation-service"
MODEL_CACHE_DIR="/app/models"
DATA_DIR="/app/data"
LOG_LEVEL="INFO"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in Docker
if [ -f /.dockerenv ]; then
    log_info "Running inside Docker container"
    IS_DOCKER=true
else
    log_info "Running on host system"
    IS_DOCKER=false
fi

# Create directories
log_info "Creating directories..."
mkdir -p "$MODEL_CACHE_DIR" "$DATA_DIR"

# Check Python dependencies
log_info "Checking Python dependencies..."
python -c "import transformers, openai, spacy" || {
    log_error "Missing required dependencies"
    exit 1
}

# Download spaCy model if not present
log_info "Checking spaCy English model..."
python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || {
    log_info "Downloading spaCy English model..."
    python -m spacy download en_core_web_sm || {
        log_warning "Failed to download spaCy model, will retry on startup"
    }
}

# Test model loading
log_info "Testing model loading..."

# Test NER model
log_info "Testing NER model (dslim/bert-base-NER)..."
python -c "
from transformers import pipeline
try:
    ner = pipeline('ner', model='dslim/bert-base-NER')
    result = ner('Test query')
    print('✅ NER model loaded successfully')
except Exception as e:
    print(f'❌ NER model failed: {e}')
    exit(1)
" || {
    log_warning "NER model test failed, will retry on startup"
}

# Test OpenAI client (if API key provided)
if [ -n "$OPENAI_API_KEY" ]; then
    log_info "Testing OpenAI client..."
    python -c "
from openai import AsyncOpenAI
import asyncio
async def test():
    try:
        client = AsyncOpenAI(api_key='$OPENAI_API_KEY')
        # Just test initialization, don't make actual API call
        print('✅ OpenAI client initialized successfully')
    except Exception as e:
        print(f'❌ OpenAI client failed: {e}')
        exit(1)
asyncio.run(test())
" || {
        log_warning "OpenAI client test failed, will retry on startup"
    }
else
    log_warning "No OpenAI API key provided, OpenAI features will be disabled"
fi

# Test device intelligence service connectivity
log_info "Testing device intelligence service..."
python -c "
import httpx
import asyncio
async def test():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get('http://device-intelligence-service:8021/', timeout=5.0)
            if response.status_code == 200:
                print('✅ Device intelligence service is accessible')
            else:
                print(f'❌ Device intelligence service returned {response.status_code}')
                exit(1)
    except Exception as e:
        print(f'❌ Device intelligence service not accessible: {e}')
        exit(1)
asyncio.run(test())
" || {
    log_warning "Device intelligence service not accessible, will use fallback"
}

# Run database migrations
log_info "Running database migrations..."
alembic upgrade head || {
    log_warning "Database migration failed, continuing anyway"
}

# Set up logging
log_info "Configuring logging..."
export LOG_LEVEL="$LOG_LEVEL"

# Start the service
log_info "Starting AI Automation Service with Multi-Model Entity Extraction..."

if [ "$IS_DOCKER" = true ]; then
    # Running in Docker - use uvicorn directly
    exec python -m uvicorn src.main:app --host 0.0.0.0 --port 8018 --log-level "$LOG_LEVEL"
else
    # Running on host - use docker-compose
    log_info "Starting with docker-compose..."
    docker-compose up --build "$SERVICE_NAME"
fi

log_success "Multi-Model Entity Extraction System deployed successfully!"
