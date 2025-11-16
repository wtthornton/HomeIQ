# Health Dashboard

**Real-Time System Monitoring and Configuration Interface for HomeIQ**

**Port:** 3000
**Technology:** React 18.3, TypeScript 5.6, Vite 5.4, TailwindCSS 3.4
**Container:** `homeiq-dashboard`

## Overview

The Health Dashboard is a modern React-based web interface that provides real-time monitoring, configuration management, and system administration for the HomeIQ system. It offers comprehensive visibility into all 24 microservices with real-time metrics, alerts, and configuration capabilities.

### Key Features

- **Real-Time Monitoring** - Live system health, metrics, and performance charts
- **Configuration Management** - Web-based service configuration with secure credential editing
- **Service Control** - Service status monitoring and management
- **Alert Management** - Real-time critical alert monitoring with automatic cleanup
- **Data Visualization** - Interactive charts and time-series analysis
- **Mobile-Responsive** - Works on desktop, tablet, and mobile devices
- **Modern UI** - Professional design with dark/light theme support

## Quick Start

### Prerequisites

- Node.js 18+ or 20+
- npm or yarn
- Admin API running (port 8004)
- Data API running (port 8006)

### Running Locally

```bash
cd services/health-dashboard

# Install dependencies
npm install

# Start dev server
npm run dev

# Access dashboard
open http://localhost:3000
```

### Running with Docker

```bash
# Build and start
docker compose up -d health-dashboard

# View logs
docker compose logs -f health-dashboard

# Access dashboard
open http://localhost:3000
```

### Build for Production

```bash
# Build production bundle
npm run build

# Preview production build
npm run preview
```

## Dashboard Tabs

### 📊 Overview (Default)
- System health summary with visual indicators
- Key metrics at a glance (CPU, memory, events/minute)
- Recent events from all services
- Quick actions and shortcuts
- Service uptime tracking

### 🔧 Services
- List of all 24 microservices
- Real-time health status for each service
- Service dependencies and relationships
- Configuration shortcuts
- Restart capabilities (when available)

### 🌐 Data Sources
- External data service integration status
- Integration health monitoring
- Data flow visualization
- Connection status for HA, InfluxDB, MQTT

### 📈 Analytics
- Performance analytics and trends
- Historical metrics over time
- Custom date range selection
- Event rate analysis
- Resource utilization charts

### 🚨 Alerts
- **Automatic Cleanup** - Stale alerts (timeout alerts >1 hour) automatically resolved
- Real-time critical alert monitoring
- Alert acknowledgment and resolution workflow
- Clean interface showing only relevant alerts
- Historical alert context with timestamps
- Alert filtering by severity (critical, warning, info)

### ⚙️ Configuration
**Web-Based Service Configuration:**

- **Home Assistant WebSocket** - Connection URL and access token
- **Weather API** - API key and default location
- **InfluxDB** - Connection URL, token, org, and bucket
- **Service Control** - View and manage all service configurations
- **Secure Editing** - Credentials masked as ••• in display mode
- **Real-Time Validation** - Configuration validation before save
- **One-Click Save** - Apply changes instantly

## Features

### Real-Time Monitoring

**System Health:**
- Overall system status (healthy/degraded/down)
- Individual service health checks
- Dependency health tracking
- Response time monitoring

**Live Metrics:**
- Events per second/minute
- Memory and CPU usage
- InfluxDB query performance
- WebSocket connection status
- Active API calls

**Performance Charts:**
- Event rate over time
- Service response times
- Resource utilization trends
- Historical comparisons

### Configuration Management

**Supported Services:**
1. **Home Assistant (websocket-ingestion)**
   - WebSocket URL
   - Long-lived access token
   - SSL verification settings

2. **Weather API (weather-api)**
   - OpenWeatherMap API key
   - Default location (City, State, Country)
   - Update frequency

3. **InfluxDB (all services)**
   - Connection URL
   - Authentication token
   - Organization name
   - Bucket name

**Security Features:**
- Credentials masked in UI (shown as •••)
- Secure transmission to admin-api
- Environment variable updates
- No credentials stored in browser

**Workflow:**
1. Navigate to Configuration tab
2. Select service card
3. Click "Edit" to reveal form
4. Update configuration values
5. Click "Save Changes"
6. Restart service to apply (via command line or Docker)

### Service Control

**Service List:**
- 24 microservices displayed with status
- Health indicator (green/yellow/red)
- Uptime since last restart
- Port and container information

**Health Checks:**
- Automatic health polling (every 30 seconds)
- Visual status indicators
- Dependency health tracking
- Error state detection

### Alert Management (Epic 17.4)

**Features:**
- Real-time alert polling from admin-api
- Automatic cleanup of timeout alerts >1 hour old
- Alert severity badges (critical, warning, info)
- Acknowledgment and resolution actions
- Timestamp tracking (created, acknowledged, resolved)

**Alert Workflow:**
1. Alert appears in Alerts tab automatically
2. Review alert details and metadata
3. Click "Acknowledge" to mark as seen
4. Investigate and resolve issue
5. Click "Resolve" to close alert
6. Stale timeout alerts auto-resolve after 1 hour

### Data Visualization

**Chart Types:**
- Line charts for time-series data
- Bar charts for comparisons
- Pie charts for distributions
- Real-time updating graphs

**Chart Library:**
- Chart.js 4.4.4 for interactive charts
- Recharts 3.4.1 for advanced visualizations
- React-ChartJS-2 5.3.0 for React integration

**Features:**
- Responsive design (scales to screen size)
- Tooltips with detailed information
- Legend toggling
- Export to PNG/CSV
- Custom date range selection

## Architecture

### Tech Stack

**Core:**
```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "typescript": "^5.6.3"
}
```

**Build Tools:**
```json
{
  "vite": "^5.4.8",
  "@vitejs/plugin-react": "^4.3.1"
}
```

**Styling:**
```json
{
  "tailwindcss": "^3.4.13",
  "autoprefixer": "^10.4.20",
  "postcss": "^8.4.41"
}
```

**Charts & Visualization:**
```json
{
  "chart.js": "^4.4.4",
  "react-chartjs-2": "^5.3.0",
  "recharts": "^3.4.1"
}
```

**Real-Time:**
```json
{
  "react-use-websocket": "^4.9.1"
}
```

**Testing:**
```json
{
  "vitest": "^3.2.4",
  "@testing-library/react": "^16.3.0",
  "@playwright/test": "^1.48.2",
  "msw": "^2.12.1"
}
```

### Component Structure

```
src/
├── components/
│   ├── AlertsTab.tsx              # Alert management interface
│   ├── ConfigurationTab.tsx       # Service configuration UI
│   ├── ServiceCard.tsx            # Service status display
│   ├── MetricsChart.tsx           # Chart components
│   └── HealthIndicator.tsx        # Status indicators
├── services/
│   └── api.ts                     # API client (admin-api, data-api)
├── hooks/
│   ├── useHealthStatus.ts         # Service health polling
│   ├── useAlerts.ts               # Alert management
│   └── useWebSocket.ts            # WebSocket connection
├── types/
│   └── index.ts                   # TypeScript definitions
├── App.tsx                        # Main application
└── main.tsx                       # Entry point
```

### API Integration

**Admin API (Port 8004):**
- `GET /health` - System health
- `GET /api/v1/health` - Enhanced health with dependencies
- `GET /api/v1/integrations` - Service list
- `GET /api/v1/integrations/{service}/config` - Get config
- `PUT /api/v1/integrations/{service}/config` - Update config
- `GET /api/v1/alerts/active` - Get active alerts
- `POST /api/v1/alerts/{id}/acknowledge` - Acknowledge alert
- `POST /api/v1/alerts/{id}/resolve` - Resolve alert
- `GET /api/v1/ha-proxy/states` - Sanitized Home Assistant state proxy (no tokens in browser)
- `GET /api/v1/ha-proxy/states/{entity_id}` - Individual HA entity state

**Data API (Port 8006):**
- `GET /api/v1/events` - Historical events
- `GET /api/devices` - Device list
- `GET /api/entities` - Entity list
- `GET /api/v1/events/stats` - Event statistics

**WebSocket (Port 8001):**
- `WS /ws` - Real-time event streaming

### Environment Configuration

**Development (.env.development):**
```bash
# Leave blank to use same-origin nginx/dev proxy routing
VITE_API_BASE_URL=
VITE_WS_URL=/ws

# Optional UI shortcuts
VITE_AI_AUTOMATION_UI_URL=
# VITE_HA_URL=

# Optional overrides when admin/data APIs run outside docker-compose
VITE_DEV_ADMIN_API=http://localhost:8004
VITE_DEV_ADMIN_WS=ws://localhost:8004
VITE_DEV_DATA_API=http://localhost:8006
```

**Production (nginx proxy):**
```bash
# Defaults rely on nginx routing, no VITE_* overrides required
```

### Nginx Configuration

The production nginx config handles:
- Serving static React build
- Proxying `/api/admin` to admin-api:8004
- Proxying `/api/data` to data-api:8006
- SPA routing (all routes → index.html)
- Gzip compression
- Cache headers

## Development

### NPM Scripts

```bash
# Development
npm run dev                # Start dev server with HMR
npm run build              # Build for production
npm run preview            # Preview production build

# Testing
npm run test               # Run unit tests
npm run test:ui            # Run tests with UI
npm run test:coverage      # Generate coverage report
npm run test:e2e           # Run Playwright E2E tests
npm run test:e2e:ui        # Run E2E tests with UI

# Linting & Type Checking
npm run lint               # Run ESLint
npm run lint:fix           # Fix ESLint errors
npm run type-check         # TypeScript type checking

# Code Quality
npm run analyze:duplication  # Check code duplication
npm run analyze:complexity   # Analyze code complexity
npm run analyze:all          # Run all quality checks

# Utilities
npm run clean              # Clean build artifacts
```

### Development Workflow

```bash
# 1. Install dependencies
npm install

# 2. Start dev server
npm run dev

# 3. Make changes (hot reload enabled)

# 4. Run tests
npm run test

# 5. Check types and lint
npm run type-check
npm run lint

# 6. Build for production
npm run build
```

### Adding New Features

**1. Create Component:**
```typescript
// src/components/MyComponent.tsx
import React from 'react';

interface MyComponentProps {
  title: string;
}

export const MyComponent: React.FC<MyComponentProps> = ({ title }) => {
  return (
    <div className="p-4 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold">{title}</h2>
    </div>
  );
};
```

**2. Add to App:**
```typescript
// src/App.tsx
import { MyComponent } from './components/MyComponent';

// Add to appropriate tab
```

**3. Add Tests:**
```typescript
// src/components/MyComponent.test.tsx
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders title', () => {
    render(<MyComponent title="Test" />);
    expect(screen.getByText('Test')).toBeInTheDocument();
  });
});
```

## Testing

### Unit Tests (Vitest)

```bash
# Run all tests
npm run test

# Run with UI
npm run test:ui

# Generate coverage
npm run test:coverage
```

**Coverage targets:**
- Statements: >80%
- Branches: >75%
- Functions: >80%
- Lines: >80%

### E2E Tests (Playwright)

```bash
# Run E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run in headed mode
npm run test:e2e:headed

# Debug mode
npm run test:e2e:debug
```

**Test Coverage:**
- Navigation between tabs
- Service status updates
- Alert management workflow
- Configuration editing
- Chart interactions

### Manual Testing Checklist

**Health Monitoring:**
- [ ] Dashboard loads successfully
- [ ] System health status displays correctly
- [ ] Individual service statuses update
- [ ] Charts render and update
- [ ] Metrics show current values

**Configuration:**
- [ ] Configuration tab loads
- [ ] Service cards display
- [ ] Edit mode reveals form fields
- [ ] Credentials are masked (•••)
- [ ] Save button works
- [ ] Success message appears

**Alerts:**
- [ ] Alerts tab shows active alerts
- [ ] Critical alerts highlighted
- [ ] Acknowledge button works
- [ ] Resolve button works
- [ ] Stale alerts auto-cleanup (>1 hour)

**Responsiveness:**
- [ ] Mobile view works (< 640px)
- [ ] Tablet view works (640-1024px)
- [ ] Desktop view works (> 1024px)
- [ ] Charts scale appropriately

## Performance

### Performance Targets

- **Initial Load:** <2s
- **Time to Interactive:** <3s
- **First Contentful Paint:** <1.5s
- **Bundle Size:** <500KB gzipped

### Optimization

- **Code Splitting:** React Router lazy loading
- **Tree Shaking:** Vite automatically removes unused code
- **Minification:** Production builds minified
- **Compression:** Gzip enabled in nginx

### Resource Usage

- **Memory:** ~50-100MB (browser)
- **Network:** Minimal after initial load
- **Polling:** 30-second intervals for health checks
- **WebSocket:** Persistent connection for real-time updates

## Troubleshooting

### Dashboard Won't Load

**Check backend services:**
```bash
curl http://localhost:8004/health  # Admin API
curl http://localhost:8006/health  # Data API
```

**Check nginx (Docker):**
```bash
docker compose logs health-dashboard
```

**Check browser console:**
- Open DevTools → Console
- Look for network errors or CORS issues

### Configuration Not Saving

**Symptoms:**
- Save button doesn't work
- Error message appears
- Configuration reverts

**Solutions:**
1. Check admin-api is running: `curl http://localhost:8004/health`
2. Verify CORS settings allow frontend origin
3. Check browser console for errors
4. Ensure credentials have proper permissions

### Alerts Not Updating

**Check:**
1. Admin API alerts endpoint: `curl http://localhost:8004/api/v1/alerts/active`
2. Browser console for polling errors
3. Network tab for failed requests

### Charts Not Rendering

**Common Issues:**
- Chart.js not loaded → Check bundle
- Data format incorrect → Check API response
- Container size zero → Check CSS

**Solutions:**
```bash
# Rebuild node_modules
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
npm run clean
npm run build
```

### WebSocket Connection Failed

**Check WebSocket service:**
```bash
curl http://localhost:8001/health
```

**Test WebSocket:**
```bash
wscat -c ws://localhost:8001/ws
```

**Fix:**
- Verify WS_URL in .env
- Check nginx WebSocket proxying (upgrade headers)
- Ensure websocket-ingestion service is running

## Security

- **CORS:** Configured to allow dashboard origin only
- **Credentials:** Masked in UI, transmitted securely
- **Authentication:** Optional API key authentication
- **HTTPS:** Use HTTPS in production
- **CSP:** Content Security Policy configured in nginx
- **CSRF Protection:** All unsafe requests require the `homeiq_csrf` cookie + `X-CSRF-Token` header (token is generated automatically by the dashboard and enforced by nginx)
- **HA Token Safety:** The browser no longer talks to Home Assistant directly; admin-api proxies `/api/v1/ha-proxy/*` and keeps HA tokens server-side

## Deployment

### Docker Build

```dockerfile
# Multi-stage build
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY . .
RUN npm ci
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

### Production Deployment

```bash
# Build and start
docker compose up -d --build health-dashboard

# Check status
docker compose ps health-dashboard

# View logs
docker compose logs -f health-dashboard

# Restart
docker compose restart health-dashboard
```

## Dependencies

### Core Dependencies

```
react@^18.3.1                   # UI library
react-dom@^18.3.1               # React DOM rendering
typescript@^5.6.3               # Type safety
```

### Build & Development

```
vite@^5.4.8                     # Build tool
@vitejs/plugin-react@^4.3.1     # React plugin
tailwindcss@^3.4.13             # CSS framework
```

### Charts & Visualization

```
chart.js@^4.4.4                 # Chart library
react-chartjs-2@^5.3.0          # React wrapper
recharts@^3.4.1                 # Advanced charts
```

### Real-Time

```
react-use-websocket@^4.9.1      # WebSocket hook
```

### Testing

```
vitest@^3.2.4                   # Unit testing
@playwright/test@^1.48.2        # E2E testing
@testing-library/react@^16.3.0  # React testing
msw@^2.12.1                     # API mocking
```

## Related Documentation

- [Admin API](../admin-api/README.md) - Backend API for configuration
- [Data API](../data-api/README.md) - Data query interface
- [API Reference](../../docs/api/API_REFERENCE.md) - Complete API docs
- [Architecture](../../docs/architecture/) - System architecture
- [CLAUDE.md](../../CLAUDE.md) - AI assistant guide

## Support

- **Issues:** https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** `/docs` directory
- **Dashboard:** http://localhost:3000
- **API Docs:** http://localhost:8004/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive testing section
- Updated tech stack versions (React 18.3, TypeScript 5.6, Vite 5.4)
- Improved troubleshooting guide
- Added performance optimization details
- Updated admin-api port reference (8003 → 8004)

### 2.0 (October 2025)
- Added alert management with auto-cleanup
- Enhanced configuration management UI
- Added service control features
- Improved mobile responsiveness

### 1.0 (Initial Release)
- Real-time health monitoring
- Basic configuration management
- Chart visualization
- Service status tracking

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 3000
**Framework:** React 18.3 + TypeScript 5.6 + Vite 5.4
