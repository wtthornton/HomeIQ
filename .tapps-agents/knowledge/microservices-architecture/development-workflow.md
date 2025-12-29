# Development Workflow

### Local Development Setup

#### Prerequisites
```bash
# Required software
- Docker Desktop 24+
- Docker Compose 2.20+
- Node.js 18+ (for frontend development)
- Python 3.11+ (for local testing)
- Git
```

#### Initial Setup

**Option 1: Quick Start with Deployment Wizard (Recommended)**

```bash
# Clone repository
git clone <repository-url>
cd homeiq

# Run interactive deployment wizard
./scripts/deploy-wizard.sh

# Start development environment
docker-compose -f docker-compose.dev.yml up -d
```

The wizard will:
- Guide you through configuration
- Auto-detect system resources
- Generate secure `.env` file
- Validate Home Assistant connection

**Option 2: Manual Setup**

```bash
# Clone repository
git clone <repository-url>
cd homeiq

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env

# Validate configuration (optional but recommended)
./scripts/validate-ha-connection.sh

# Start development environment
docker-compose -f docker-compose.dev.yml up -d
```

#### Development Commands
```bash
# Start all services
docker-compose -f docker-compose.dev.yml up

# Start frontend only (with hot reload)
cd frontend && npm run dev

# Start backend services only (Epic 31 - no enrichment-pipeline)
docker-compose -f docker-compose.dev.yml up websocket-ingestion data-api admin-api influxdb

# Run tests
docker-compose -f docker-compose.dev.yml run --rm websocket-ingestion pytest
docker-compose -f docker-compose.dev.yml run --rm data-api pytest
docker-compose -f docker-compose.dev.yml run --rm admin-api pytest
cd frontend && npm test

# View logs
docker-compose -f docker-compose.dev.yml logs -f websocket-ingestion
docker-compose -f docker-compose.dev.yml logs -f data-api
docker-compose -f docker-compose.dev.yml logs -f admin-api

# Note: enrichment-pipeline was deprecated in Epic 31 (October 2025)
# All normalization now happens inline in websocket-ingestion
```

### Environment Configuration

#### Environment Variables
```bash
# Frontend (.env.local)
VITE_API_BASE_URL=http://localhost:8080/api

# Backend (.env)
# Home Assistant Configuration
HA_URL=ws://homeassistant.local:8123/api/websocket
HA_ACCESS_TOKEN=your_long_lived_access_token_here

# Weather API Configuration
WEATHER_API_KEY=your_openweathermap_api_key_here
WEATHER_LOCATION=Your City, Country
WEATHER_CACHE_MINUTES=15

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token_here
INFLUXDB_ORG=home_assistant
INFLUXDB_BUCKET=events

# Admin API Configuration
ADMIN_API_HOST=0.0.0.0
ADMIN_API_PORT=8080

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Shared
ENVIRONMENT=development
```

