# Step 3: Architecture Design - Proactive Agent Service UI Integration

## System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          User Browser                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ai-automation-ui (Port 3001)                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         nginx (Port 80)                          │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │ /api/proactive/* → proactive-agent-service:8031 [NEW]    │   │   │
│  │  │ /api/*          → ai-automation-service-new:8025         │   │   │
│  │  │ /api/data/*     → data-api:8006                          │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      React Application                           │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │   │
│  │  │ Suggestions  │  │   Patterns   │  │  Proactive   │  [NEW]   │   │
│  │  │     Page     │  │     Page     │  │     Page     │          │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘          │   │
│  │                          │                   │                   │   │
│  │                          ▼                   ▼                   │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │                  Services Layer                           │   │
│  │  │  ┌─────────┐  ┌─────────────────┐  ┌───────────────────┐ │   │   │
│  │  │  │ api.ts  │  │  proactiveApi.ts │  │  Other services  │ │   │   │
│  │  │  └─────────┘  └─────────────────┘  └───────────────────┘ │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
┌──────────────────────┐ ┌──────────────────────┐ ┌──────────────────────┐
│  proactive-agent     │ │ ai-automation-service │ │      data-api       │
│      (8031)          │ │       (8025)          │ │       (8006)        │
│                      │ │                       │ │                     │
│  ┌────────────────┐  │ │  ┌─────────────────┐  │ │  ┌───────────────┐  │
│  │ SQLite DB      │  │ │  │ ai_automation.db│  │ │  │ devices.db    │  │
│  │ (suggestions)  │  │ │  │ (suggestions)   │  │ │  │ (entities)    │  │
│  └────────────────┘  │ │  └─────────────────┘  │ │  └───────────────┘  │
│                      │ │                       │ │                     │
│  Context Sources:    │ └───────────────────────┘ └─────────────────────┘
│  - Weather API       │
│  - Carbon Intensity  │
│  - Data API (events) │
│  - HA AI Agent       │
└──────────────────────┘
```

## Data Flow

### Proactive Suggestions Flow

```
1. User opens /proactive page
         │
         ▼
2. React component mounts
         │
         ▼
3. proactiveApi.getSuggestions() called
         │
         ▼
4. HTTP GET /api/proactive/suggestions
         │
         ▼
5. nginx proxies to proactive-agent-service:8031
         │
         ▼
6. proactive-agent-service queries SQLite
         │
         ▼
7. Returns JSON response
         │
         ▼
8. React updates state, renders cards
```

### Suggestion Action Flow

```
1. User clicks "Approve" on suggestion card
         │
         ▼
2. proactiveApi.updateSuggestion(id, {status: 'approved'})
         │
         ▼
3. HTTP PATCH /api/proactive/suggestions/{id}
         │
         ▼
4. nginx proxies to proactive-agent-service:8031
         │
         ▼
5. proactive-agent-service updates SQLite
         │
         ▼
6. Returns updated suggestion
         │
         ▼
7. React updates local state (optimistic)
         │
         ▼
8. Toast notification shown
```

## Component Architecture

### New Files to Create

```
services/ai-automation-ui/
├── src/
│   ├── services/
│   │   └── proactiveApi.ts        [NEW] API client
│   │
│   ├── pages/
│   │   └── ProactiveSuggestions.tsx [NEW] Main page
│   │
│   ├── components/
│   │   └── proactive/
│   │       ├── index.ts           [NEW] Barrel export
│   │       ├── ProactiveSuggestionCard.tsx [NEW]
│   │       ├── ProactiveFilters.tsx [NEW]
│   │       └── ProactiveStats.tsx [NEW]
│   │
│   └── types/
│       └── proactive.ts           [NEW] TypeScript types
│
└── nginx.conf                     [MODIFY] Add proxy route
```

### Modified Files

| File | Changes |
|------|---------|
| `src/App.tsx` | Add route for `/proactive` |
| `src/components/Navigation.tsx` | Add "Proactive" nav item |
| `nginx.conf` | Add `/api/proactive/*` location block |

## State Management

### Page State

```typescript
interface ProactiveSuggestionsState {
  suggestions: ProactiveSuggestion[];
  loading: boolean;
  error: string | null;
  filters: {
    contextType: string | null;
    status: string | null;
  };
  stats: ProactiveSuggestionStats | null;
  pagination: {
    limit: number;
    offset: number;
    total: number;
  };
}
```

### Hooks-Based Approach (Following Existing Patterns)

```typescript
// Custom hook for proactive suggestions
function useProactiveSuggestions(filters: Filters) {
  const [suggestions, setSuggestions] = useState<ProactiveSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  useEffect(() => {
    // Fetch logic
  }, [filters]);
  
  const updateStatus = async (id: string, status: string) => {
    // Optimistic update logic
  };
  
  return { suggestions, loading, error, updateStatus };
}
```

## API Integration

### Nginx Configuration Addition

```nginx
# API proxy to proactive-agent-service
location ~* ^/api/proactive/(.*) {
    resolver 127.0.0.11 valid=30s;
    resolver_timeout 5s;

    set $backend http://proactive-agent-service:8031;
    proxy_pass $backend/api/v1/$1;

    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Authorization $http_authorization;
    proxy_set_header X-HomeIQ-API-Key $http_x_homeiq_api_key;
    proxy_pass_request_headers on;

    proxy_connect_timeout 60s;
    proxy_send_timeout 120s;
    proxy_read_timeout 120s;

    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'Content-Type, Authorization, X-HomeIQ-API-Key' always;

    if ($request_method = 'OPTIONS') {
        return 204;
    }
}
```

## Error Handling Strategy

### API Error Handling

```typescript
try {
  const suggestions = await proactiveApi.getSuggestions(filters);
  setSuggestions(suggestions);
} catch (error) {
  if (error instanceof APIError) {
    if (error.status === 503) {
      setError('Proactive service is unavailable. The 3 AM job may be running.');
    } else if (error.status === 404) {
      setError('Proactive suggestions endpoint not found.');
    } else {
      setError(error.message);
    }
  } else {
    setError('An unexpected error occurred.');
  }
}
```

### Graceful Degradation

- If proactive-agent-service is down, show informative message
- If no suggestions exist, show "No suggestions yet" with trigger button
- If filters return empty, show "No matching suggestions" with clear filters option

## Performance Considerations

1. **Pagination**: Limit 50 suggestions per page
2. **Optimistic Updates**: Update UI before API confirms
3. **Debounced Filters**: Debounce filter changes (300ms)
4. **Skeleton Loading**: Show skeleton while loading
5. **Error Boundaries**: Catch component errors gracefully

## Security Considerations

1. **Authentication**: Forward existing API key headers
2. **CORS**: Configure nginx to allow frontend origin
3. **Input Validation**: Validate status values before API calls
4. **XSS Prevention**: Sanitize any user-generated content

---
*Generated by Simple Mode Build Workflow*
*Timestamp: 2026-01-07*
