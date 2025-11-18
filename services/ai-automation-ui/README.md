# AI Automation UI

**Conversational automation suggestion refinement interface for Home Assistant**

**Port:** 3001
**Technology:** React 18.3, TypeScript 5.6, Vite 5.4, TailwindCSS 3.4
**Container:** `homeiq-ai-automation-ui`

## Overview

The AI Automation UI provides a user-friendly, conversational interface for reviewing, refining, and deploying AI-generated automation suggestions. Built on **Story AI1.23-24** (Conversational Suggestion Refinement), it replaces the traditional YAML-first approach with a description-first workflow.

### Key Features

- 💬 **Conversational Refinement** - Edit suggestions with natural language ("make it 6:30am instead")
- 📝 **Description-First** - See automation ideas in plain English before any code
- ✅ **YAML on Approval** - Code only generated after you approve the description
- 🚀 **One-Click Deploy** - Push approved automations directly to Home Assistant
- 🎨 **Beautiful UI** - Modern, responsive design with dark mode support
- ⚡ **Real-Time Updates** - Live status updates for automation suggestions
- 📊 **Analytics** - View patterns, synergies, and device intelligence
- 🔍 **Device Discovery** - Explore device capabilities and features

## Quick Start

### Prerequisites

- Node.js 18+ or 20+
- npm or yarn
- AI Automation Service running (port 8024/8018)

### Running with Docker (Recommended)

```bash
# From project root
docker compose up -d ai-automation-ui

# Access UI
open http://localhost:3001
```

### Building Locally

```bash
cd services/ai-automation-ui

# Install dependencies
npm install

# Build production bundle
npm run build

# Preview production build locally
npm run preview
```

### Build for Production

```bash
# Build production bundle
npm run build

# Preview production build
npm run preview
```

## User Interface

### Main Dashboard (ConversationalDashboard)

The main interface displays suggestions in a card-based layout with status tabs:

- **📝 Draft** - New suggestions (description only, no YAML yet)
- **✏️ Refining** - Suggestions you're editing with conversational AI
- **✅ Ready** - Approved suggestions with generated YAML, ready to deploy
- **🚀 Deployed** - Automations running in Home Assistant

### Conversational Flow

```
1. View Draft Suggestion
   └─> "Turn on office lights at 7:00am every morning"

2. Click "Refine" (Optional)
   └─> Type: "Make it 6:30am instead"
   └─> AI updates: "Turn on office lights at 6:30am every morning"
   └─> Type: "And only on weekdays"
   └─> AI updates: "Turn on office lights at 6:30am on weekdays"

3. Click "Approve"
   └─> AI generates Home Assistant YAML
   └─> Shows automation code
   └─> Status changes to "Ready"

4. Click "Deploy"
   └─> Pushes to Home Assistant
   └─> Status changes to "Deployed"
```

## Pages & Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | ConversationalDashboard | Main suggestion feed (description-first) |
| `/patterns` | Patterns | View detected patterns (time-of-day, co-occurrence) |
| `/synergies` | Synergies | Cross-device automation opportunities |
| `/deployed` | Deployed | Active automations in Home Assistant |
| `/discovery` | Discovery | Device exploration and capability analysis |
| `/settings` | Settings | UI preferences, feature flags & configuration |

## Architecture

### Status States (Story AI1.23)

```
draft → refining → yaml_generated → deployed
  ↓                      ↓
rejected            rejected
```

**Status Definitions:**
- `draft` - New suggestion, description only, no YAML
- `refining` - User is editing with conversational AI
- `yaml_generated` - User approved, YAML created, ready to deploy
- `deployed` - Automation active in Home Assistant
- `rejected` - User rejected the suggestion

### API Integration

**Backend:** `ai-automation-service` (port 8024 external, 8018 internal)

**Key Endpoints:**
- `GET /api/suggestions/list?status=draft` - Load suggestions
- `POST /api/v1/suggestions/{id}/refine` - Conversational editing
- `POST /api/v1/suggestions/{id}/approve` - Generate YAML
- `POST /api/deploy/{id}` - Deploy to Home Assistant
- `GET /api/patterns/list` - Get detected patterns
- `GET /api/synergies` - Get device synergies
- `GET /api/deploy/automations` - Get deployed automations

**API Base URL:**
- Development: `http://localhost:8018/api` (direct)
- Production: `/api` (nginx proxy to ai-automation-service:8018)

## Components

### ConversationalSuggestionCard

Main card component for displaying suggestions with:
- Description display (collapsible for long text)
- Refinement input (inline editing with AI)
- Action buttons (Refine, Approve, Deploy, Reject)
- YAML code block (syntax highlighted, only shown after approval)
- Confidence meter (visual indicator of suggestion quality)
- Category badges (pattern, feature, synergy)
- Source information (which pattern or device triggered suggestion)

### Key Features:
- **Inline Editing**: Click "Refine" to edit without modal disruption
- **Optimistic Updates**: UI updates immediately, API call in background
- **Error Handling**: Graceful fallbacks if API fails with retry options
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode**: Automatic theme switching based on system preferences

## Tech Stack

### Core Dependencies

```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "react-router-dom": "^6.27.0"
}
```

### State Management & Data Fetching

```json
{
  "zustand": "^4.5.0",
  "@tanstack/react-query": "^5.40.0"
}
```

### UI & Animation

```json
{
  "framer-motion": "^11.2.0",
  "tailwindcss": "^3.4.13",
  "react-hot-toast": "^2.5.1"
}
```

### Charts & Visualizations

```json
{
  "chart.js": "^4.4.4",
  "react-chartjs-2": "^5.3.0"
}
```

### Development Tools

```json
{
  "vite": "^5.4.8",
  "typescript": "^5.6.3",
  "@vitejs/plugin-react": "^4.3.1",
  "eslint": "^9.39.1",
  "autoprefixer": "^10.4.20",
  "postcss": "^8.4.41"
}
```

## Development

### File Structure

```
ai-automation-ui/
├── src/
│   ├── pages/
│   │   ├── ConversationalDashboard.tsx  # Main dashboard (root route)
│   │   ├── Patterns.tsx                 # Pattern detection view
│   │   ├── Synergies.tsx                # Device synergy view
│   │   ├── Deployed.tsx                 # Deployed automations
│   │   ├── Discovery.tsx                # Device discovery
│   │   └── Settings.tsx                 # UI settings & config
│   ├── components/
│   │   ├── ConversationalSuggestionCard.tsx  # Main suggestion card
│   │   ├── Navigation.tsx               # Top navigation bar
│   │   ├── CustomToast.tsx              # Toast notifications
│   │   ├── PatternCard.tsx              # Pattern display card
│   │   └── SynergyCard.tsx              # Synergy display card
│   ├── services/
│   │   └── api.ts                       # API client with error handling
│   ├── hooks/
│   │   └── useApiQuery.ts               # Custom React Query hooks
│   ├── types/
│   │   └── index.ts                     # TypeScript type definitions
│   ├── store.ts                         # Zustand global state
│   ├── App.tsx                          # Routes & layout
│   └── main.tsx                         # Application entry point
├── public/                              # Static assets
├── Dockerfile                           # Multi-stage Docker build
├── nginx.conf                           # Production nginx config
├── vite.config.ts                       # Vite configuration
├── tailwind.config.js                   # TailwindCSS configuration
├── tsconfig.json                        # TypeScript configuration
└── package.json                         # Dependencies & scripts
```

### State Management

**Zustand Store (`store.ts`):**
- `suggestions` - Array of automation suggestions
- `selectedStatus` - Current status filter (draft/refining/yaml_generated/deployed)
- `darkMode` - UI theme preference (auto/light/dark)
- `scheduleInfo` - Daily analysis job status and timing
- `patterns` - Detected patterns from pattern detection
- `synergies` - Device synergy opportunities

**React Query:**
- Handles all API calls with caching
- Automatic refetch on window focus
- Retry logic for failed requests
- Loading and error states

### Environment Variables

```env
# Development (services/ai-automation-ui/.env.development)
VITE_API_URL=http://localhost:8018/api

# Production (Docker)
# nginx proxies /api to http://ai-automation-service:8018/api
# No VITE_API_URL needed - uses relative paths
```

### NPM Scripts

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview

# Run ESLint
npm run lint
```

## Building & Deployment

### Docker Build (Multi-Stage)

```dockerfile
# Stage 1: Install dependencies
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Stage 2: Build production bundle
FROM node:18-alpine AS builder
WORKDIR /app
COPY . .
RUN npm ci
RUN npm run build

# Stage 3: Serve with nginx
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3001
CMD ["nginx", "-g", "daemon off;"]
```

### Production Deployment

```bash
# Build and start
docker compose up -d --build ai-automation-ui

# Check status
docker ps | grep ai-automation-ui

# View logs
docker compose logs -f ai-automation-ui

# Restart service
docker compose restart ai-automation-ui
```

### Nginx Configuration

The production nginx config handles:
- Serving static React build from `/usr/share/nginx/html`
- Proxying `/api` requests to `ai-automation-service:8018`
- SPA routing (all routes → index.html)
- Gzip compression
- Cache headers for static assets

## Testing

### Manual Testing

**1. View Draft Suggestions:**
- Navigate to http://localhost:3001/
- Should see suggestions with descriptions only
- No YAML code visible in draft status

**2. Test Refinement:**
- Click "Refine" on any draft suggestion
- Type: "change the time to 8am"
- Verify description updates
- Try multiple refinements in sequence

**3. Test Approval:**
- Click "Approve" on refined (or draft) suggestion
- Verify YAML code appears in code block
- Verify status changes to "Ready"
- Check YAML syntax highlighting

**4. Test Deployment:**
- Click "Deploy" on ready suggestion
- Check Home Assistant for new automation
- Verify status changes to "Deployed"
- Check automation is enabled in HA

**5. Test Pattern View:**
- Navigate to `/patterns`
- Should see detected patterns (time-of-day, co-occurrence)
- Verify chart visualizations load

**6. Test Synergy View:**
- Navigate to `/synergies`
- Should see device synergy opportunities
- Filter by synergy type (device_pair, weather_context, etc.)

**7. Test Discovery View:**
- Navigate to `/discovery`
- Should see device list with capabilities
- Check feature utilization percentages

**8. Test Dark Mode:**
- Toggle dark mode in settings
- Verify all pages respect theme
- Check system preference auto-detection

### Automated Testing

```bash
# Run unit tests (if configured)
npm run test

# Run E2E tests (if configured)
npm run test:e2e
```

**Note:** Automated test framework is being rebuilt as of November 2025. Use manual testing in the meantime.

## Troubleshooting

### "No Draft Suggestions"

**Cause:** New suggestions not yet generated or old data has YAML

**Fix:** Trigger new analysis:
```bash
curl -X POST http://localhost:8024/api/analysis/trigger
```

Wait for 3-5 minutes for analysis to complete, then refresh the UI.

### "API Connection Failed"

**Cause:** Backend service not running or incorrect URL

**Fix:** Check backend status:
```bash
docker ps | grep ai-automation-service
docker compose logs ai-automation-service
```

**Local Build:** Verify `VITE_API_URL` in `.env.development` if building locally

**Production:** Check nginx proxy configuration

### "YAML Appears in Draft"

**Cause:** Old suggestions created before Story AI1.24

**Fix:** Delete old suggestions or run database migration:
```sql
-- Connect to ai_automation.db
UPDATE suggestions
SET automation_yaml = NULL, yaml_generated_at = NULL
WHERE status = 'draft';
```

Or trigger new analysis to get fresh suggestions:
```bash
curl -X POST http://localhost:8024/api/analysis/trigger
```

### "Build Fails"

**Common issues:**
- Node version mismatch → Use Node 18+ or 20+
- Missing dependencies → Run `npm install`
- TypeScript errors → Run `npm run lint` to see all errors
- Vite cache issues → Delete `node_modules/.vite` and rebuild

**Fix:**
```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite

# Rebuild
npm run build
```

### "Dark Mode Not Working"

**Cause:** TailwindCSS dark mode class not applied

**Fix:** Check `tailwind.config.js` has `darkMode: 'class'`

Verify Zustand store is applying dark mode class to document root.

### "Nginx 502 Bad Gateway"

**Cause:** Backend service not reachable from nginx container

**Fix:**
1. Check both services are on same Docker network
2. Verify service name in nginx.conf matches docker-compose.yml
3. Check ai-automation-service is healthy: `docker compose ps`

```bash
# Test from nginx container
docker exec ai-automation-ui wget -O- http://ai-automation-service:8018/health
```

## Performance

### Bundle Size Optimization

- **Code Splitting:** React Router lazy loading for routes
- **Tree Shaking:** Vite automatically removes unused code
- **Minification:** Production builds are minified
- **Compression:** Gzip enabled in nginx

**Target Metrics:**
- Initial bundle: <500KB gzipped
- First Contentful Paint: <1.5s
- Time to Interactive: <3s

### Runtime Performance

- **React.memo:** Prevents unnecessary re-renders
- **useMemo/useCallback:** Memoizes expensive calculations
- **Virtualization:** Large lists use virtual scrolling (if >100 items)
- **Debouncing:** User input debounced to reduce API calls

## Accessibility

- **Keyboard Navigation:** All interactive elements keyboard accessible
- **ARIA Labels:** Proper labels for screen readers
- **Color Contrast:** WCAG AA compliant color ratios
- **Focus Indicators:** Clear focus states for all interactive elements
- **Semantic HTML:** Proper heading hierarchy and landmarks

## Security

- **XSS Protection:** React escapes all user input by default
- **CSRF:** No cookies used, API is stateless
- **Content Security Policy:** Configured in nginx
- **HTTPS:** Use HTTPS in production
- **API Rate Limiting:** Handled by backend service

## Contributing

1. Follow React and TypeScript best practices
2. Use functional components with hooks
3. Add TypeScript types for all props and state
4. Use TailwindCSS for styling (avoid inline styles)
5. Add comments for complex logic
6. Update this README when adding features

### Code Style

```typescript
/**
 * Component for displaying automation suggestions
 */
import React, { useState } from 'react';

interface SuggestionCardProps {
  /** Unique suggestion identifier */
  id: string;
  /** Human-readable description */
  description: string;
  /** Current status of suggestion */
  status: 'draft' | 'refining' | 'yaml_generated' | 'deployed';
  /** Callback when refine button clicked */
  onRefine?: (id: string, refinement: string) => void;
}

export const SuggestionCard: React.FC<SuggestionCardProps> = ({
  id,
  description,
  status,
  onRefine
}) => {
  const [refinement, setRefinement] = useState('');

  const handleRefine = () => {
    if (onRefine && refinement) {
      onRefine(id, refinement);
      setRefinement('');
    }
  };

  return (
    <div className="p-4 border rounded-lg">
      <p className="text-gray-800 dark:text-gray-200">{description}</p>
      {status === 'draft' && (
        <div className="mt-4">
          <input
            type="text"
            value={refinement}
            onChange={(e) => setRefinement(e.target.value)}
            placeholder="Refine with natural language..."
            className="w-full px-3 py-2 border rounded"
          />
          <button onClick={handleRefine} className="mt-2 btn-primary">
            Refine
          </button>
        </div>
      )}
    </div>
  );
};
```

## Related Documentation

- **Backend Service:** `services/ai-automation-service/README.md`
- **Story AI1.23:** `docs/stories/story-ai1-23-conversational-refinement.md`
- **Story AI1.24:** `docs/stories/story-ai1-24-conversational-ui-cleanup.md`
- **Implementation:** `implementation/PHASE_2_BACKEND_CLEANUP_COMPLETE.md`
- **Call Tree:** `implementation/analysis/AI_AUTOMATION_CALL_TREE_INDEX.md`
- **API Reference:** `docs/api/API_REFERENCE.md`
- **CLAUDE.md:** `CLAUDE.md` (AI assistant development guide)

## Support

- **Issues:** File on GitHub at https://github.com/wtthornton/HomeIQ/issues
- **Documentation:** Check `/docs` directory
- **UI:** http://localhost:3001
- **API:** http://localhost:8024/docs

## Version History

### 2.1 (November 15, 2025)
- Updated documentation to 2025 standards
- Enhanced dependency documentation
- Added comprehensive component documentation
- Updated tech stack versions
- Improved troubleshooting section
- Added accessibility and security sections
- Enhanced performance optimization details

### 2.0 (October 2025)
- Story AI1.24 complete (Conversational UI Cleanup)
- Description-first workflow
- YAML generation on approval only
- Enhanced dark mode support

### 1.0 (Initial Release)
- Story AI1.23 complete (Conversational Refinement)
- Basic suggestion display
- Inline refinement editing
- Deployment to Home Assistant

---

**Last Updated:** November 15, 2025
**Version:** 2.1
**Status:** Production Ready ✅
**Port:** 3001
**Framework:** React 18.3 + TypeScript 5.6 + Vite 5.4
