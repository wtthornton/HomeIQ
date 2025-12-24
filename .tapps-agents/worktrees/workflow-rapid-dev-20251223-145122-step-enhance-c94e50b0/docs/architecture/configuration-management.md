# Configuration Management

This document describes the configuration system used throughout the Home Assistant Ingestor project, including core system settings and runtime configuration loading.

## Configuration Architecture

The project uses a **multi-layered configuration approach** with environment-based settings, Docker Compose orchestration, and service-specific configurations.

### Configuration Layers

1. **Environment Variables** - Base configuration values
2. **Docker Compose** - Service orchestration and networking
3. **Service-Specific Configs** - Individual service configurations
4. **Runtime Configuration** - Dynamic configuration loading

## Environment Configuration

### Environment Files

| File | Purpose | Environment | Docker Compose |
|------|---------|-------------|----------------|
| `infrastructure/env.example` | Template for all environment variables | Development | docker-compose.dev.yml |
| `infrastructure/env.production` | Production environment values | Production | docker-compose.prod.yml |
| `.env` | Local development overrides | Development | docker-compose.dev.yml |

### Core Environment Variables

```bash
# Home Assistant Integration
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token
ENABLE_HOME_ASSISTANT=true

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=homeiq-token
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events

# API Configuration
API_HOST=0.0.0.0
API_PORT=8004
ENABLE_AUTH=false
CORS_ORIGINS=*

# Logging Configuration
LOG_LEVEL=INFO

# Weather API (Optional)
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_API_URL=https://api.openweathermap.org/data/2.5
ENABLE_WEATHER_API=false

# Data Retention Configuration
CLEANUP_INTERVAL_HOURS=24
MONITORING_INTERVAL_MINUTES=5
BACKUP_INTERVAL_HOURS=24
```

## Docker Compose Configuration

### Main Configuration (`docker-compose.yml`)

```yaml
services:
  influxdb:
    image: influxdb:2.7
    environment:
      - DOCKER_INFLUXDB_INIT_USERNAME=${INFLUXDB_USERNAME:-admin}
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD:-admin123}
      - DOCKER_INFLUXDB_INIT_ORG=${INFLUXDB_ORG:-homeiq}
      - DOCKER_INFLUXDB_INIT_BUCKET=${INFLUXDB_BUCKET:-home_assistant_events}
    volumes:
      - influxdb_data:/var/lib/influxdb2
    networks:
      - homeiq-network

  admin-api:
    build: ./services/admin-api
    environment:
      - API_HOST=${API_HOST:-0.0.0.0}
      - API_PORT=${API_PORT:-8004}
      - ENABLE_AUTH=${ENABLE_AUTH:-false}
    depends_on:
      influxdb:
        condition: service_healthy
```

### Development Configuration (`docker-compose.dev.yml`)

```yaml
# Development overrides
services:
  admin-api:
    build:
      context: ./services/admin-api
      dockerfile: Dockerfile.dev
    volumes:
      - ./services/admin-api:/app
    environment:
      - RELOAD=true
      - LOG_LEVEL=DEBUG
```

### Production Configuration (`docker-compose.prod.yml`)

```yaml
# Production overrides with optimizations
services:
  admin-api:
    build:
      context: ./services/admin-api
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
      - ENABLE_AUTH=${ENABLE_AUTH:-true}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Service-Specific Configuration

### Admin API Configuration

```python
# services/admin-api/src/main.py
class AdminAPIService:
    def __init__(self):
        # Load configuration from environment
        self.api_host = os.getenv('API_HOST', '0.0.0.0')
        self.api_port = int(os.getenv('API_PORT', '8004'))
        self.enable_auth = os.getenv('ENABLE_AUTH', 'false').lower() == 'true'
        
        # CORS configuration
        self.cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
        self.cors_methods = os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE').split(',')
```

### WebSocket Ingestion Configuration

```python
# services/websocket-ingestion/src/main.py
class WebSocketIngestionService:
    def __init__(self):
        # Home Assistant configuration
        self.home_assistant_url = os.getenv('HOME_ASSISTANT_URL')
        self.home_assistant_token = os.getenv('HOME_ASSISTANT_TOKEN')
        self.home_assistant_enabled = os.getenv('ENABLE_HOME_ASSISTANT', 'true').lower() == 'true'
        
        # Processing configuration
        self.max_workers = int(os.getenv('MAX_WORKERS', '10'))
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.batch_timeout = float(os.getenv('BATCH_TIMEOUT', '5.0'))
```

### Health Dashboard Configuration

```typescript
// services/health-dashboard/vite.config.ts
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    server: {
      port: parseInt(env.VITE_PORT || '3000'),
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8003',
          changeOrigin: true,
        },
      },
    },
    define: {
      __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '1.0.0'),
      __ENVIRONMENT__: JSON.stringify(mode),
    },
  }
})
```

## Configuration Loading Patterns

### Python Services

```python
# Pattern: Environment-based configuration with defaults
import os
from typing import Optional

class Config:
    def __init__(self):
        # Required configuration
        self.influxdb_url = os.getenv('INFLUXDB_URL')
        if not self.influxdb_url:
            raise ValueError("INFLUXDB_URL environment variable is required")
        
        # Optional configuration with defaults
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.batch_size = int(os.getenv('BATCH_SIZE', '100'))
        self.enable_feature = os.getenv('ENABLE_FEATURE', 'false').lower() == 'true'
        
        # Validation
        self._validate_config()
    
    def _validate_config(self):
        if self.batch_size <= 0:
            raise ValueError("BATCH_SIZE must be positive")
```

### Frontend Services

```typescript
// Pattern: Environment-based configuration with type safety
interface Config {
  apiBaseUrl: string;
  wsUrl: string;
  environment: string;
  version: string;
}

const config: Config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003',
  wsUrl: import.meta.env.VITE_WS_URL || 'ws://localhost:8001',
  environment: import.meta.env.VITE_ENVIRONMENT || 'development',
  version: import.meta.env.VITE_APP_VERSION || '1.0.0',
};
```

## Configuration Validation

### Environment Validation Script

```bash
#!/bin/bash
# scripts/validate-config.sh

# Required environment variables
REQUIRED_VARS=(
  "HOME_ASSISTANT_URL"
  "HOME_ASSISTANT_TOKEN"
  "INFLUXDB_URL"
  "INFLUXDB_TOKEN"
)

# Check required variables
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "Error: $var environment variable is required"
    exit 1
  fi
done

echo "All required environment variables are set"
```

### Python Configuration Validation

```python
# Pattern: Configuration validation with detailed error messages
from typing import Dict, Any
import logging

class ConfigValidator:
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate configuration and return True if valid"""
        errors = []
        
        # Required fields
        required_fields = ['influxdb_url', 'influxdb_token']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"Missing required field: {field}")
        
        # URL validation
        if config.get('influxdb_url') and not config['influxdb_url'].startswith('http'):
            errors.append("INFLUXDB_URL must be a valid HTTP URL")
        
        # Port validation
        port = config.get('api_port', 8004)
        if not (1 <= port <= 65535):
            errors.append("API_PORT must be between 1 and 65535")
        
        if errors:
            for error in errors:
                logging.error(f"Configuration error: {error}")
            return False
        
        return True
```

## Configuration Management Best Practices

### 1. Environment Separation
- Use separate environment files for development, staging, and production
- Never commit sensitive configuration values to version control
- Use environment variable substitution in Docker Compose files

### 2. Default Values
- Provide sensible defaults for all optional configuration
- Document default values in configuration comments
- Use type conversion for environment variables (string to int, bool, etc.)

### 3. Validation
- Validate configuration at startup
- Provide clear error messages for missing or invalid configuration
- Fail fast if required configuration is missing

### 4. Security
- Never log sensitive configuration values
- Use secrets management for production deployments
- Rotate tokens and keys regularly

### 5. Documentation
- Document all configuration options
- Provide examples for common configurations
- Maintain configuration change logs

## Configuration Deployment

### Development Setup

```bash
# Copy environment template
cp infrastructure/env.example .env

# Edit environment variables
nano .env

# Start services
docker-compose up
```

### Production Deployment

```bash
# Use production environment
docker-compose -f docker-compose.prod.yml --env-file infrastructure/env.production up -d

# Verify configuration
docker-compose logs admin-api | grep "Configuration loaded"
```

## Configuration Monitoring

### Health Check Integration

```python
# Pattern: Configuration health check
@app.get("/health/config")
async def config_health():
    """Health check endpoint that verifies configuration"""
    try:
        # Validate critical configuration
        config_validator.validate(current_config)
        return {"status": "healthy", "config": "valid"}
    except Exception as e:
        return {"status": "unhealthy", "config": "invalid", "error": str(e)}
```

### Configuration Logging

```python
# Pattern: Safe configuration logging (no secrets)
import logging

def log_configuration(config: Dict[str, Any]):
    """Log configuration without sensitive values"""
    safe_config = {}
    sensitive_keys = ['token', 'password', 'key', 'secret']
    
    for key, value in config.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            safe_config[key] = "***REDACTED***"
        else:
            safe_config[key] = value
    
    logging.info(f"Configuration loaded: {safe_config}")
```

This configuration management system ensures consistent, secure, and maintainable configuration across all services in the Home Assistant Ingestor project.
