# Simple Configuration Management Pattern
**Context7 KB Cache - Simple Integration Management**

**Source:** FastAPI Pydantic Settings + Web Research  
**Topic:** Environment variable management, service configuration  
**Retrieved:** October 11, 2025  
**Pattern:** KISS (Keep It Simple, Stupid)

---

## Core Pattern: Pydantic BaseSettings

### FastAPI Configuration Management
From Context7 `/fastapi/fastapi` - Settings management

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Home Assistant
    ha_url: str
    ha_token: str
    
    # Weather API
    weather_api_key: str
    weather_location_lat: float = 51.5074
    weather_location_lon: float = -0.1278
    
    # InfluxDB
    influxdb_url: str = "http://influxdb:8086"
    influxdb_token: str
    influxdb_org: str = "home-assistant"
    influxdb_bucket: str = "ha_events"
    
    model_config = SettingsConfigDict(env_file=".env")
```

### Simple Pattern Benefits
- ✅ Type validation automatic
- ✅ Default values supported
- ✅ Reads from .env file
- ✅ No database needed
- ✅ Simple to test

---

## Simple UI Pattern

### Read-Only Display (Default View)
```typescript
interface ConfigDisplay {
  service: string;
  settings: Record<string, {
    value: string;
    masked: boolean; // mask API keys
    description: string;
  }>;
}
```

### Edit Mode (Simple Form)
```typescript
interface ConfigEdit {
  service: string;
  settings: Record<string, {
    current: string;
    new: string;
    type: 'text' | 'url' | 'number';
    required: boolean;
  }>;
}
```

---

## Simple Architecture

### Backend (FastAPI)
```python
# 1. Read current config
@app.get("/api/config/{service}")
def get_config(service: str):
    return read_env_file(service)

# 2. Update config
@app.put("/api/config/{service}")
def update_config(service: str, updates: dict):
    write_env_file(service, updates)
    return {"status": "saved", "restart_required": True}

# 3. Restart service
@app.post("/api/services/{service}/restart")
def restart_service(service: str):
    subprocess.run(["docker", "compose", "restart", service])
    return {"status": "restarted"}
```

### Frontend (React)
```typescript
// Simple config form
function ConfigForm({ service }) {
  const [config, setConfig] = useState({});
  const [edited, setEdited] = useState(false);
  
  const save = async () => {
    await api.put(`/api/config/${service}`, config);
    alert("Saved! Restart service to apply.");
  };
  
  return (
    <form>
      {Object.entries(config).map(([key, value]) => (
        <input 
          key={key}
          value={value}
          onChange={e => setConfig({...config, [key]: e.target.value})}
        />
      ))}
      <button onClick={save}>Save</button>
    </form>
  );
}
```

---

## File Organization

### Simple .env Structure
```
# .env files per service
infrastructure/
├── .env.websocket        # HA connection
├── .env.weather          # Weather API
├── .env.influxdb         # Database
├── .env.enrichment       # Data enrichment
└── .env.example          # Template
```

### Simple Docker Integration
```yaml
# docker-compose.yml
services:
  websocket-ingestion:
    env_file:
      - infrastructure/.env.websocket
```

---

## Simple Workflow

### User Workflow
1. **View Config** → See current settings (masked)
2. **Click Edit** → Enable edit mode
3. **Update Values** → Change API keys, URLs, etc.
4. **Save** → Write to .env file
5. **Restart** → Click restart button
6. **Done** → Service uses new config

### No Complexity Needed
- ❌ No encryption (file permissions handle it)
- ❌ No database
- ❌ No hot-reload
- ❌ No complex validation
- ❌ No JWT/auth overhead
- ✅ Just simple file editing

---

## Security Considerations

### File Permissions (Simple)
```bash
chmod 600 infrastructure/.env.*  # Owner read/write only
chown root:root infrastructure/.env.*
```

### Basic Masking (UI)
```typescript
function maskValue(key: string, value: string): string {
  const sensitiveKeys = ['token', 'key', 'password', 'secret'];
  if (sensitiveKeys.some(k => key.toLowerCase().includes(k))) {
    return '••••••••' + value.slice(-4);
  }
  return value;
}
```

---

## Implementation Checklist

### Phase 1: Backend (1-2 days)
- [ ] Create simple .env reader/writer
- [ ] Add config endpoints (get/update)
- [ ] Add service restart endpoint
- [ ] Basic validation

### Phase 2: Frontend (1-2 days)
- [ ] Config display page
- [ ] Edit form
- [ ] Save button
- [ ] Restart button

### Phase 3: Polish (1 day)
- [ ] Mask sensitive values
- [ ] Add descriptions/tooltips
- [ ] Test workflow
- [ ] Documentation

**Total: 4-5 days**

---

## Anti-Patterns to Avoid

### Don't Over-Engineer
- ❌ Complex encryption schemes
- ❌ Database storage for config
- ❌ Hot-reload mechanisms
- ❌ Version control for config
- ❌ Complex validation logic
- ❌ Multi-step workflows

### Keep It Simple
- ✅ Just edit files
- ✅ Restart to apply
- ✅ Basic validation
- ✅ Clear UI
- ✅ Direct approach

---

**Saved to Context7 KB:** 2025-10-11  
**Pattern Type:** Simple Configuration Management  
**Technologies:** FastAPI, Pydantic, React, Docker  
**Complexity:** Low (intentionally)

