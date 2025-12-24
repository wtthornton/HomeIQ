# Quick Start - Integration Management

## 🚀 Get Started in 5 Minutes

### Step 1: Setup Configuration Files

**Windows (PowerShell):**
```powershell
.\scripts\setup-config.ps1
```

**Linux/Mac (Bash):**
```bash
./scripts/setup-config.sh
```

This creates:
- `infrastructure/.env.websocket`
- `infrastructure/.env.weather`
- `infrastructure/.env.influxdb`

---

### Step 2: Start Services

```bash
docker-compose up -d
```

Wait ~30 seconds for services to start.

---

### Step 3: Open Dashboard

```
http://localhost:3000/
```

Then click the **"⚙️ Configuration"** tab in the top navigation.

---

### Step 4: Configure Your First Service

1. Click on "🏠 Home Assistant" card
2. Enter your Home Assistant details:
   - **WebSocket URL**: `ws://192.168.1.100:8123/api/websocket`
   - **Access Token**: `your_token_here`
3. Click **"Save Changes"**
4. Click **"Restart Service"**

Done! Home Assistant connection is configured.

---

## 📋 What to Configure

### Required (Minimum Setup)
- **Home Assistant** - To connect to your HA instance
- **InfluxDB** - For data storage

### Optional (For Features)
- **Weather API** - For weather enrichment

---

## 🔑 Getting API Keys

### Home Assistant Token
1. Open Home Assistant
2. Go to Profile (bottom left)
3. Scroll to "Long-Lived Access Tokens"
4. Click "Create Token"
5. Copy token and paste in dashboard

### OpenWeatherMap API Key
1. Go to https://openweathermap.org/api
2. Sign up for free account
3. Get API key from dashboard
4. Paste in weather configuration

### InfluxDB Token
1. Open InfluxDB UI: http://localhost:8086
2. Login (username: admin, password: admin123)
3. Go to "Data" → "Tokens"
4. Copy existing token or create new one
5. Paste in influxdb configuration

---

## ✅ Verify It's Working

### Check Service Status
1. Go to Configuration page
2. Scroll to "Service Control" section
3. All services should show 🟢 Running

### Check Dashboard
1. Go to main dashboard: http://localhost:3000
2. Should see data flowing if HA is connected

---

## 🐛 Quick Troubleshooting

### "Failed to load configuration"
- Run setup script first: `.\scripts\setup-config.ps1`
- Check files exist: `ls infrastructure/.env.*`

### "Service won't restart"
- Check Docker is running: `docker ps`
- Check logs: `docker logs homeiq-admin-dev`

### "Changes not applied"
- Make sure you clicked "Restart Service"
- Wait 10-15 seconds for restart to complete

---

## 📚 Full Documentation

- [Implementation Details](INTEGRATION_MANAGEMENT_IMPLEMENTATION.md)
- [Simple Approach Doc](SIMPLE_INTEGRATION_MANAGEMENT.md)
- [Configuration Summary](CONFIGURATION_MANAGEMENT_SUMMARY.md)

---

**That's it! Simple and working.** 🎉

