# Simple Integration Management - KISS Approach

## Overview
Simple dashboard to manage external API credentials and control integrations. No over-engineering - just edit configs and restart services.

**Principle:** Keep It Simple, Stupid (KISS)

---

## 🎯 What You Get

### 1. Configuration Manager Page
Simple UI to edit API keys and settings for all external services.

```
┌──────────────────────────────────────────────┐
│  🔧 Integration Configuration                │
├──────────────────────────────────────────────┤
│                                              │
│  🏠 Home Assistant                           │
│  ├─ WebSocket URL: [ws://192.168.1.100...  ]│
│  ├─ Access Token:  [••••••••5678] [Show]    │
│  └─ [Save Changes] [Restart Service]        │
│                                              │
│  ☁️ Weather API (OpenWeatherMap)             │
│  ├─ API Key:      [••••••••abcd] [Show]     │
│  ├─ Latitude:     [51.5074         ]        │
│  ├─ Longitude:    [-0.1278         ]        │
│  └─ [Save Changes] [Restart Service]        │
│                                              │
│  💾 InfluxDB                                 │
│  ├─ URL:          [http://influxdb:8086]    │
│  ├─ Token:        [••••••••9xyz] [Show]     │
│  ├─ Organization: [home-assistant  ]        │
│  ├─ Bucket:       [ha_events       ]        │
│  └─ [Save Changes] [Restart Service]        │
│                                              │
│  [Test All Connections]                     │
└──────────────────────────────────────────────┘
```

### 2. Service Control
Simple buttons to start/stop/restart services.

```
┌──────────────────────────────────────────────┐
│  🎛️ Service Control                          │
├──────────────────────────────────────────────┤
│                                              │
│  Service Name          Status    Actions     │
│  ─────────────────────────────────────────  │
│  websocket-ingestion   🟢 Running [Restart]  │
│  enrichment-pipeline   🟢 Running [Restart]  │
│  weather-api           🟢 Running [Restart]  │
│  data-retention        🟢 Running [Restart]  │
│                                              │
│  [Restart All Services]                     │
└──────────────────────────────────────────────┘
```

---

## 🏗️ Simple Architecture

### How It Works

```
User Changes Config → Save to .env File → Restart Service → Service Reads New Config
```

**That's it!** No database, no complex encryption, no hot-reload.

---

## 📝 Configuration Files

### Simple .env Files (One per service)

```bash
# infrastructure/.env.websocket
HA_URL=ws://192.168.1.100:8123/api/websocket
HA_TOKEN=your_home_assistant_token_here
HA_SSL_VERIFY=true
HA_RECONNECT_DELAY=5

# infrastructure/.env.weather
WEATHER_API_KEY=your_openweathermap_key
WEATHER_LAT=51.5074
WEATHER_LON=-0.1278
WEATHER_UNITS=metric
WEATHER_CACHE_SECONDS=300

# infrastructure/.env.influxdb
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=home-assistant
INFLUXDB_BUCKET=ha_events
```

---

## 💻 Implementation

### Backend (FastAPI) - Simple Endpoints

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import subprocess

app = FastAPI()

class ConfigUpdate(BaseModel):
    settings: dict[str, str]

# Read config
@app.get("/api/config/{service}")
def get_config(service: str):
    """Read .env file for a service"""
    env_file = f"infrastructure/.env.{service}"
    
    if not os.path.exists(env_file):
        raise HTTPException(404, "Service not found")
    
    config = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config[key] = value
    
    return {"service": service, "settings": config}

# Update config
@app.put("/api/config/{service}")
def update_config(service: str, update: ConfigUpdate):
    """Write new values to .env file"""
    env_file = f"infrastructure/.env.{service}"
    
    # Read existing
    lines = []
    with open(env_file) as f:
        lines = f.readlines()
    
    # Update values
    new_lines = []
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            key = line.split('=')[0]
            if key in update.settings:
                new_lines.append(f"{key}={update.settings[key]}\n")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    return {
        "status": "saved",
        "message": "Configuration updated. Restart service to apply.",
        "restart_required": True
    }

# Restart service
@app.post("/api/services/{service}/restart")
def restart_service(service: str):
    """Restart Docker container"""
    try:
        result = subprocess.run(
            ["docker", "compose", "restart", service],
            capture_output=True,
            text=True,
            check=True
        )
        return {"status": "success", "message": f"{service} restarted"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"Failed to restart: {e.stderr}")

# Get service status
@app.get("/api/services/{service}/status")
def get_service_status(service: str):
    """Check if service is running"""
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", service],
            capture_output=True,
            text=True
        )
        is_running = "Up" in result.stdout
        return {
            "service": service,
            "running": is_running,
            "status": "running" if is_running else "stopped"
        }
    except Exception as e:
        return {"service": service, "running": False, "error": str(e)}
```

---

### Frontend (React) - Simple Components

```typescript
// Simple config form component
interface ServiceConfig {
  service: string;
  settings: Record<string, string>;
}

export const ConfigForm: React.FC<{ service: string }> = ({ service }) => {
  const [config, setConfig] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  
  // Load config on mount
  useEffect(() => {
    fetch(`/api/config/${service}`)
      .then(res => res.json())
      .then(data => setConfig(data.settings));
  }, [service]);
  
  // Save changes
  const handleSave = async () => {
    setLoading(true);
    try {
      await fetch(`/api/config/${service}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: config })
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setLoading(false);
    }
  };
  
  // Restart service
  const handleRestart = async () => {
    setLoading(true);
    try {
      await fetch(`/api/services/${service}/restart`, { method: 'POST' });
      alert(`${service} restarted successfully!`);
    } finally {
      setLoading(false);
    }
  };
  
  // Mask sensitive values
  const isSensitive = (key: string) => 
    key.toLowerCase().includes('token') ||
    key.toLowerCase().includes('key') ||
    key.toLowerCase().includes('password');
  
  return (
    <div className="config-form">
      <h3>{service}</h3>
      
      {Object.entries(config).map(([key, value]) => (
        <div key={key} className="form-field">
          <label>{key}</label>
          <input
            type={isSensitive(key) ? 'password' : 'text'}
            value={value}
            onChange={e => setConfig({...config, [key]: e.target.value})}
          />
        </div>
      ))}
      
      <div className="actions">
        <button onClick={handleSave} disabled={loading}>
          {saved ? '✓ Saved' : 'Save Changes'}
        </button>
        <button onClick={handleRestart} disabled={loading}>
          Restart Service
        </button>
      </div>
    </div>
  );
};

// Simple service control component
export const ServiceControl: React.FC = () => {
  const services = [
    'websocket-ingestion',
    'enrichment-pipeline',
    'weather-api',
    'data-retention'
  ];
  
  const [statuses, setStatuses] = useState<Record<string, string>>({});
  
  useEffect(() => {
    // Check status every 5 seconds
    const check = () => {
      services.forEach(async service => {
        const res = await fetch(`/api/services/${service}/status`);
        const data = await res.json();
        setStatuses(prev => ({ ...prev, [service]: data.status }));
      });
    };
    check();
    const interval = setInterval(check, 5000);
    return () => clearInterval(interval);
  }, []);
  
  const restart = async (service: string) => {
    await fetch(`/api/services/${service}/restart`, { method: 'POST' });
  };
  
  return (
    <div className="service-control">
      <h2>Service Control</h2>
      <table>
        <thead>
          <tr>
            <th>Service</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {services.map(service => (
            <tr key={service}>
              <td>{service}</td>
              <td>{statuses[service] === 'running' ? '🟢' : '🔴'} {statuses[service]}</td>
              <td>
                <button onClick={() => restart(service)}>Restart</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
```

---

## 🔒 Simple Security

### File Permissions
```bash
# Restrict .env files to owner only
chmod 600 infrastructure/.env.*
```

### UI Masking
- API keys show as `••••••••` by default
- Click "Show" to reveal (client-side only)
- No complex encryption needed

### Docker Secrets (Optional)
For production, you can use Docker secrets instead:
```yaml
services:
  websocket-ingestion:
    secrets:
      - ha_token
secrets:
  ha_token:
    file: ./secrets/ha_token.txt
```

---

## 📅 Implementation Timeline

### Week 1: Backend (2-3 days)
- [ ] Add config read/write endpoints
- [ ] Add service control endpoints
- [ ] Test with one service (Home Assistant)
- [ ] Add basic validation

### Week 2: Frontend (2-3 days)
- [ ] Build config form component
- [ ] Build service control component
- [ ] Add to dashboard as new page
- [ ] Test workflow end-to-end

### Week 3: Polish (1-2 days)
- [ ] Add all services (Weather, InfluxDB, etc.)
- [ ] Improve UI/UX
- [ ] Add error handling
- [ ] Write simple docs

**Total: 5-8 days**

---

## 🎯 Services to Configure

### Core Services (Must Have)
1. **Home Assistant** - WebSocket URL + Token
2. **Weather API** - API Key + Location
3. **InfluxDB** - URL + Token + Org + Bucket

### Optional Services (Nice to Have)
4. **Carbon Intensity** - API Key + Region
5. **Electricity Pricing** - API Key + Account
6. **Air Quality** - API Key + Location
7. **Calendar** - OAuth tokens (more complex, v2)
8. **Smart Meter** - Connection details
9. **S3/Glacier** - AWS credentials
10. **Email/SMTP** - SMTP settings

**Start with 1-3, add others later**

---

## ✅ Simple Workflow

### For Users

1. **Open Dashboard** → Go to "Configuration" page
2. **Select Service** → Click on service to edit
3. **Update Values** → Change API keys, URLs, etc.
4. **Save** → Click "Save Changes"
5. **Restart** → Click "Restart Service"
6. **Done!** → Service uses new settings

**No complexity, no confusion, just works.**

---

## 🚫 What We're NOT Doing

To keep it simple:

- ❌ **No database** - Just read/write .env files
- ❌ **No encryption** - Use file permissions
- ❌ **No hot-reload** - Just restart the service
- ❌ **No version control** - Keep it simple
- ❌ **No complex validation** - Basic checks only
- ❌ **No JWT/sessions** - Admin API already has auth
- ❌ **No OAuth flows** - Store tokens directly
- ❌ **No backup/restore** - Use git for .env files
- ❌ **No audit log** - Git history is enough

---

## 🎨 UI Mockup

### Configuration Page
```
┌─────────────────────────────────────────────────┐
│  Dashboard > Configuration                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  Select a service to configure:                 │
│                                                 │
│  [🏠 Home Assistant]  [☁️ Weather API]          │
│  [💾 InfluxDB]         [⚡ Electricity]          │
│  [🌫️ Air Quality]      [📅 Calendar]             │
│                                                 │
│  ─────────────────────────────────────────────  │
│                                                 │
│  🏠 Home Assistant Configuration                │
│                                                 │
│  WebSocket URL *                                │
│  ┌───────────────────────────────────────────┐ │
│  │ ws://192.168.1.100:8123/api/websocket    │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  Access Token * [Show]                          │
│  ┌───────────────────────────────────────────┐ │
│  │ ••••••••••••••••••••••••••5678           │ │
│  └───────────────────────────────────────────┘ │
│                                                 │
│  SSL Verify                                     │
│  ☑ Enabled                                      │
│                                                 │
│  Reconnect Delay (seconds)                      │
│  ┌─────┐                                        │
│  │  5  │                                        │
│  └─────┘                                        │
│                                                 │
│  Status: 🟢 Connected (last check: 1 min ago)  │
│                                                 │
│  [Test Connection]  [Save]  [Restart Service]  │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 📦 File Structure

```
services/admin-api/src/
├── config_manager.py         # .env file read/write
├── service_controller.py     # Docker restart logic
└── integration_endpoints.py  # API endpoints

services/health-dashboard/src/components/
├── ConfigurationPage.tsx     # Main config page
├── ConfigForm.tsx            # Config edit form
└── ServiceControl.tsx        # Service restart buttons

infrastructure/
├── .env.websocket            # Home Assistant config
├── .env.weather              # Weather API config
├── .env.influxdb             # InfluxDB config
├── .env.enrichment           # Enrichment services
└── .env.example              # Template

docker-compose.yml            # Uses env_file directive
```

---

## 🚀 Quick Start

### 1. Add Backend Endpoints
```bash
cd services/admin-api
# Add config_manager.py, service_controller.py
```

### 2. Add Frontend Components
```bash
cd services/health-dashboard
# Add ConfigurationPage.tsx
```

### 3. Create .env Files
```bash
cd infrastructure
cp .env.example .env.websocket
cp .env.example .env.weather
# Edit with your actual keys
```

### 4. Update docker-compose.yml
```yaml
services:
  websocket-ingestion:
    env_file:
      - infrastructure/.env.websocket
```

### 5. Test It Out
```bash
docker-compose up -d
# Open dashboard, go to Configuration
# Update a value, save, restart
```

---

## 💡 Key Simplifications

### 1. Direct File Access
- Read/write .env files directly
- No database overhead
- Simple and fast

### 2. Manual Restart
- User clicks "Restart" to apply changes
- No hot-reload complexity
- Clear workflow

### 3. Basic Validation
- Check required fields exist
- Check basic format (URL, number)
- Don't over-complicate

### 4. File-Based Security
- Use Unix file permissions
- No complex encryption
- Good enough for local deployment

### 5. One Service at a Time
- Configure one service, then restart it
- No batch operations complexity
- Clear cause and effect

---

## 🎯 Success Criteria

- [ ] Can edit Home Assistant config through UI
- [ ] Can edit Weather API config through UI
- [ ] Can edit InfluxDB config through UI
- [ ] Can restart services with button click
- [ ] API keys are masked in UI
- [ ] Changes persist after service restart
- [ ] Clear error messages if something fails
- [ ] Takes < 10 seconds to update a config

---

## 📝 Next Steps

**Ready to implement?** 

1. Confirm this simple approach works for you
2. Pick which services to start with (Home Assistant + Weather + InfluxDB?)
3. I'll implement in ~5-8 days

**Questions?**
- Should I start with just Home Assistant first?
- Any specific services most important?
- Want Docker secrets instead of .env files?

---

**Document Type:** Simple Implementation Plan  
**Complexity Level:** Low (intentionally)  
**Estimated Effort:** 5-8 days  
**Status:** Ready for approval

