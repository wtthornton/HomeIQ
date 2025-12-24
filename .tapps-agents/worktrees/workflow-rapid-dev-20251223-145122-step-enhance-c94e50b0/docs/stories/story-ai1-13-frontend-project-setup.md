# Story AI1.13: Frontend - Project Setup and Dashboard Shell

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.13  
**Priority:** High  
**Estimated Effort:** 8-10 hours  
**Dependencies:** None (frontend can start in parallel after Story 1.2)

---

## User Story

**As a** frontend developer  
**I want** to set up the React project with tab navigation  
**so that** we have a foundation matching the Health Dashboard

---

## Business Value

- Establishes frontend foundation
- Ensures design consistency with existing Health Dashboard
- Enables parallel frontend/backend development
- Reuses proven patterns and components

---

## Acceptance Criteria

1. ✅ Project builds successfully with Vite
2. ✅ TailwindCSS config matches health-dashboard exactly
3. ✅ Dark mode toggle works with localStorage persistence
4. ✅ Tab navigation structure in place (4 tabs)
5. ✅ Error boundary catches and displays errors
6. ✅ Container runs on port 3002
7. ✅ Bundle size <500KB gzipped
8. ✅ Initial load time <2 seconds

---

## Technical Implementation Notes

### Project Setup

**Create: services/ai-automation-frontend/**

```bash
# Create React + TypeScript + Vite project
cd services
npm create vite@latest ai-automation-frontend -- --template react-ts
cd ai-automation-frontend
npm install

# Install dependencies matching health-dashboard
npm install tailwindcss@3.4.0 \
  @heroicons/react@2.2.0 \
  axios@1.6.0 \
  mqtt@5.3.0

# Dev dependencies
npm install -D @types/node vitest
```

### Copy TailwindCSS Config

**CRITICAL: Copy exactly from health-dashboard**

```bash
cp ../health-dashboard/tailwind.config.js ./
cp ../health-dashboard/src/index.css ./src/
```

**File: tailwind.config.js** (1:1 copy from health-dashboard)

### Dashboard Shell Component

**Create: src/components/Dashboard.tsx**

**Reference: health-dashboard/src/components/Dashboard.tsx**

```typescript
import React, { useState, useEffect } from 'react';
import { ErrorBoundary } from './ErrorBoundary';
import * as Tabs from './tabs';

// Tab configuration
const TAB_COMPONENTS: Record<string, React.FC<Tabs.TabProps>> = {
  suggestions: Tabs.SuggestionsTab,
  patterns: Tabs.PatternsTab,
  automations: Tabs.AutomationsTab,
  insights: Tabs.InsightsTab,
};

const TAB_CONFIG = [
  { id: 'suggestions', label: '💡 Suggestions', icon: '💡', shortLabel: 'Suggestions' },
  { id: 'patterns', label: '📊 Patterns', icon: '📊', shortLabel: 'Patterns' },
  { id: 'automations', label: '⚙️ Automations', icon: '⚙️', shortLabel: 'Autos' },
  { id: 'insights', label: '🔍 Insights', icon: '🔍', shortLabel: 'Insights' },
];

export const Dashboard: React.FC = () => {
  const [darkMode, setDarkMode] = useState(false);
  const [selectedTab, setSelectedTab] = useState('suggestions');
  
  // Apply dark mode to document
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);
  
  // Load dark mode preference from localStorage
  useEffect(() => {
    const savedMode = localStorage.getItem('ai-dashboard-dark-mode');
    if (savedMode === 'true') {
      setDarkMode(true);
    }
  }, []);
  
  // Save dark mode preference
  useEffect(() => {
    localStorage.setItem('ai-dashboard-dark-mode', darkMode.toString());
  }, [darkMode]);
  
  const TabComponent = TAB_COMPONENTS[selectedTab] || Tabs.SuggestionsTab;
  
  return (
    <div className={`min-h-screen ${darkMode ? 'bg-gray-900' : 'bg-gray-50'} transition-colors duration-300`}>
      {/* Header - Matches Health Dashboard */}
      <div className={`${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'} shadow-sm border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center py-4 sm:py-6 gap-4">
            <div className="w-full sm:w-auto">
              <h1 className={`text-xl sm:text-2xl lg:text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                🤖 AI Automation Advisor
              </h1>
              <p className={`text-xs sm:text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'} hidden sm:block`}>
                Intelligent Home Automation Suggestions
              </p>
            </div>
            
            {/* Dark Mode Toggle */}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className={`p-2.5 rounded-lg min-w-[44px] min-h-[44px] ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-100 hover:bg-gray-200'}`}
              aria-label={darkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
          
          {/* Tab Navigation */}
          <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
            <div className="flex space-x-2 sm:space-x-4 overflow-x-auto pb-2">
              {TAB_CONFIG.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setSelectedTab(tab.id)}
                  className={`flex-shrink-0 px-3 sm:px-4 py-2.5 rounded-lg font-medium transition-colors text-sm sm:text-base min-h-[44px] ${
                    selectedTab === tab.id
                      ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700'
                      : darkMode ? 'text-gray-300 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <span className="hidden sm:inline">{tab.label}</span>
                  <span className="sm:hidden">{tab.icon} {tab.shortLabel}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <ErrorBoundary>
          <TabComponent darkMode={darkMode} />
        </ErrorBoundary>
      </main>
    </div>
  );
};
```

### Placeholder Tab Components

**Create: src/components/tabs/index.ts**

```typescript
// Placeholder tabs (will be implemented in Stories 14-17)
export { SuggestionsTab } from './SuggestionsTab';
export { PatternsTab } from './PatternsTab';
export { AutomationsTab } from './AutomationsTab';
export { InsightsTab } from './InsightsTab';
export type { TabProps } from './types';
```

**Create stub files for each tab (implemented in later stories)**

### Dockerfile

**Create: Dockerfile**

**Reference: services/health-dashboard/Dockerfile**

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### Add to Docker Compose

```yaml
services:
  ai-automation-frontend:
    build: ./services/ai-automation-frontend
    container_name: ai-automation-frontend
    ports:
      - "3002:80"
    environment:
      - AI_API_URL=http://localhost:8011
      - DATA_API_URL=http://localhost:8006
      - HA_API_URL=http://localhost:8123
    depends_on:
      - ai-automation-service
    networks:
      - ha-network
    restart: unless-stopped
```

---

## Integration Verification

**IV1: Frontend accessible at http://localhost:3002**
- Browser loads page without errors
- Tab navigation works
- Dark mode toggle functional

**IV2: Design matches health-dashboard aesthetics**
- Colors match (blue theme)
- Spacing and typography consistent
- Animations match (fade-in, slide-up)

**IV3: No port conflicts**
- Port 3002 available
- nginx serves correctly
- No 404 errors

**IV4: nginx configuration correct**
- Static files served
- Routing works (SPA)
- Gzip compression enabled

---

## Tasks Breakdown

1. **Create React + Vite project** (1 hour)
2. **Install and configure TailwindCSS** (1 hour)
3. **Copy design system from health-dashboard** (1.5 hours)
4. **Create Dashboard shell component** (2 hours)
5. **Implement tab navigation** (1.5 hours)
6. **Add dark mode** (1 hour)
7. **Create placeholder tab components** (1 hour)
8. **Create Dockerfile and nginx config** (1.5 hours)
9. **Add to docker-compose** (0.5 hours)
10. **Testing and optimization** (1 hour)

**Total:** 8-10 hours

---

## Definition of Done

- [ ] React + TypeScript + Vite project created
- [ ] TailwindCSS configured (exact copy of health-dashboard)
- [ ] Dashboard shell with tab navigation
- [ ] Dark mode toggle with localStorage
- [ ] Error boundary implemented
- [ ] Placeholder tabs created
- [ ] Docker container builds and runs
- [ ] Accessible on port 3002
- [ ] Bundle size <500KB gzipped
- [ ] Initial load <2 seconds
- [ ] Design matches health-dashboard
- [ ] Code reviewed and approved

---

## Reference Files

**COPY these files exactly:**
- `health-dashboard/tailwind.config.js` → Copy 1:1
- `health-dashboard/src/components/Dashboard.tsx` → Reference structure
- `health-dashboard/src/components/ErrorBoundary.tsx` → Copy
- `health-dashboard/Dockerfile` → Reference
- `health-dashboard/nginx.conf` → Copy

---

## Notes

- **Copy, don't reinvent** the design system
- TailwindCSS config must match exactly (CSS variables)
- Tab structure proven pattern (keep it)
- Dark mode persistence improves UX
- Placeholder tabs prevent build errors (implement in later stories)

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

