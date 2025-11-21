# 📖 HomeIQ - User Manual

**Last Updated:** November 2025  
**Deployment:** Single NUC (Intel NUC or similar), Docker Compose

## 🎯 **Getting Started**

### **What is HomeIQ?**
HomeIQ is an AI-powered Home Assistant intelligence platform that captures, enriches, and stores Home Assistant events with multi-source data enrichment (weather, energy pricing, air quality, sports, carbon intensity), providing real-time monitoring, advanced analytics, conversational AI automation, and production-ready deployment capabilities.

**Deployment Model:** Single NUC deployment - all 24 microservices run on one machine, connecting to Home Assistant on the local network (typically `192.168.1.86:8123`).

### **Key Features**
- **🤖 AI-Powered Automation** - Conversational automation creation via natural language
- **🚀 Interactive Deployment Wizard** - Guided setup in 30-60 minutes
- **✅ Connection Validator** - Pre-deployment testing and validation
- **Real-time Event Capture** - Direct WebSocket connection to Home Assistant
- **Multi-Source Data Enrichment** - OpenWeatherMap, WattTime, Awattar, AirNow, ESPN APIs
- **Calendar Integration** - Event-based automation triggers (optional, currently disabled)
- **Smart Meter Integration** - SMETS2/P1 protocol support for real-time energy consumption
- **Advanced Data Storage** - Hybrid architecture: InfluxDB (time-series) + SQLite (metadata)
- **Web Dashboards** - Health Dashboard (port 3000) and AI Automation UI (port 3001)
- **Data Export** - Multiple formats (CSV, JSON, PDF, Excel)
- **Mobile Support** - Responsive design with touch gestures

### **🚀 Quick Start with Deployment Wizard (Recommended)**

The fastest way to get started:

```bash
# 1. Clone the repository
git clone <repository-url>
cd homeiq

# 2. Run the deployment wizard
./scripts/deploy-wizard.sh

# 3. Start services
docker-compose up -d

# 4. Access dashboard
open http://localhost:3000
```

The deployment wizard will:
- ✅ Guide you through deployment options (same machine, separate NUC, remote)
- ✅ Configure Home Assistant connection (typically `192.168.1.86:8123`)
- ✅ Auto-detect system resources (RAM, disk space)
- ✅ Generate secure configuration files (`.env`)
- ✅ Validate connectivity before deployment

**See:** [`docs/DEPLOYMENT_WIZARD_GUIDE.md`](DEPLOYMENT_WIZARD_GUIDE.md) for detailed wizard usage.

### **🔍 Validate Your Setup**

Before deployment, test your configuration:

```bash
./scripts/validate-ha-connection.sh
```

The validator will:
- Test TCP/IP connectivity
- Validate HTTP/HTTPS endpoint
- Test WebSocket connection
- Verify authentication
- Check API access
- Generate detailed report

### **Alternative Manual Setup**

If you prefer manual configuration:

1. **Copy Environment Template**
   ```bash
   cp infrastructure/env.example .env
   ```

2. **Edit Configuration**
   ```bash
   nano .env
   # Configure HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN, etc.
   ```

3. **Deploy**
   ```bash
   docker-compose up -d
   ```

## 🖥️ **Web Dashboard**

### **Accessing the Dashboard**
1. Open your web browser
2. Navigate to `http://localhost:3000`
3. The dashboard will load automatically

### **Dashboard Sections**

#### **1. System Health Overview**
- **Service Status** - Real-time status of all services
- **Connection Health** - WebSocket connection status
- **Event Metrics** - Events processed, error rates, processing latency
- **System Resources** - CPU, memory, disk usage

#### **2. Recent Events Feed**
- **Latest Events** - Most recent Home Assistant events
- **Event Details** - Entity ID, state changes, timestamps
- **Weather Context** - Weather data at time of event
- **Filtering** - Filter by entity, event type, time range

#### **3. Data Query Interface**
- **Time Range Selector** - Predefined and custom date ranges
- **Entity Filter** - Search and filter by specific entities
- **Weather Context Filter** - Filter by temperature and conditions
- **Export Options** - Download data in multiple formats

#### **4. Configuration Management**
- **Home Assistant Settings** - Connection configuration
- **Weather API Settings** - API key and location
- **Data Retention Policies** - Storage and cleanup settings
- **System Configuration** - Environment variables and settings

## 📊 **Monitoring & Alerts**

### **Real-time Monitoring**
- **Service Health** - Continuous monitoring of all services
- **Performance Metrics** - Real-time performance tracking
- **Error Tracking** - Error rates and failure patterns
- **Resource Usage** - System resource monitoring

### **Alerting System**
- **Configurable Alerts** - Set thresholds for critical metrics
- **Multiple Channels** - Email, Slack, Webhook notifications
- **Alert Management** - Acknowledge, resolve, and suppress alerts
- **Alert History** - Complete audit trail of all alerts

## 🔧 **Configuration**

### **Home Assistant Configuration**
1. **Generate Long-Lived Access Token**
   - Go to Home Assistant → Profile → Long-lived access tokens
   - Create a new token with appropriate permissions
   - Copy the token for configuration

2. **Configure Connection**
   - Set `HA_HTTP_URL` or `HOME_ASSISTANT_URL` to your Home Assistant HTTP URL (e.g., `http://192.168.1.86:8123`)
   - Set `HA_WS_URL` to your Home Assistant WebSocket URL (e.g., `ws://192.168.1.86:8123` - `/api/websocket` is auto-appended if missing)
   - Set `HA_TOKEN` or `HOME_ASSISTANT_TOKEN` to your long-lived token
   - Configure entity filters if needed

### **External Data Sources Configuration**

#### **Weather API (Required)**
1. **Get OpenWeatherMap API Key**
   - Sign up at https://openweathermap.org/api
   - Generate an API key
   - Set `WEATHER_API_KEY` in environment

2. **Set Location**
   - Configure `WEATHER_LOCATION` with your city and country
   - Format: "City,CountryCode" (e.g., "London,GB")

#### **Carbon Intensity Service (Optional)**
- Get API key from National Grid or equivalent
- Set `CARBON_INTENSITY_API_KEY` and `CARBON_INTENSITY_REGION`
- Provides carbon footprint data for automation

#### **Electricity Pricing Service (Optional)**
- Configure provider (Octopus Energy, etc.)
- Set `ELECTRICITY_PRICING_PROVIDER` and API key
- Enables cost-optimized automation

#### **Air Quality Service (Optional)**
- Get API key from OpenAQ or government sources
- Set `AIR_QUALITY_API_KEY`
- Monitor air quality and trigger automations

#### **Calendar Service (Optional)**
- Integrates with Home Assistant calendar entities
- Supports Google Calendar, iCloud, CalDAV, Office 365, and more
- Set `CALENDAR_ENTITIES` to your HA calendar entity IDs
- Provides occupancy prediction and work-from-home detection
- Enable event-based automation triggers

#### **Smart Meter Service (Optional)**
- Configure meter protocol (SMETS2, P1, etc.)
- Set `SMART_METER_PROTOCOL` and connection details
- Real-time energy consumption monitoring

### **Data Retention Configuration (Enhanced)**

1. **Tiered Retention Policies**
   - **Hot Storage** - Recent data (default: 7 days), full resolution
   - **Warm Storage** - Medium-term data (default: 30 days), 1-minute downsampling
   - **Cold Storage** - Long-term data (default: 365 days), 1-hour downsampling
   - Configure intervals: `HOT_RETENTION_DAYS`, `WARM_RETENTION_DAYS`, `COLD_RETENTION_DAYS`

2. **S3 Archival (Optional)**
   - Enable archival: `ENABLE_S3_ARCHIVAL=true`
   - Configure bucket: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
   - Automatic archival to Amazon S3 or Glacier
   - Cost-effective long-term storage

3. **Materialized Views**
   - Pre-computed aggregations for fast queries
   - Automatic refresh and maintenance
   - Significant query performance improvement

4. **Backup Settings**
   - Configure backup schedules and intervals
   - Set backup retention periods
   - Local and S3 backup support

## 📈 **Data Analysis**

### **Querying Data**
1. **Select Time Range**
   - Choose predefined ranges (hour, day, week, month)
   - Set custom date ranges
   - Apply time zone settings

2. **Filter Data**
   - Filter by specific entities
   - Filter by event types
   - Filter by weather conditions
   - Apply custom filters

3. **Export Data**
   - Export in CSV format for spreadsheet analysis
   - Export in JSON format for programmatic analysis
   - Export in PDF format for reports
   - Export in Excel format for advanced analysis

### **Visualization**
- **Event Patterns** - Visualize event frequency over time
- **Trend Analysis** - Identify patterns and trends
- **Weather Correlation** - Analyze weather impact on events
- **Performance Metrics** - Monitor system performance

## 🛠️ **Maintenance**

### **Regular Maintenance**
1. **Monitor System Health**
   - Check service status daily
   - Review error logs weekly
   - Monitor resource usage

2. **Data Management**
   - Review data retention policies monthly
   - Clean up old backups quarterly
   - Monitor storage usage

3. **Security Updates**
   - Keep Docker images updated
   - Review access tokens quarterly
   - Update API keys as needed

### **Troubleshooting**
1. **Service Issues**
   - Check service logs for errors
   - Verify configuration settings
   - Restart services if needed

2. **Connection Problems**
   - Verify Home Assistant connectivity
   - Check WebSocket connection status
   - Validate access tokens

3. **Performance Issues**
   - Monitor resource usage
   - Check for high error rates
   - Review data volume and retention

## 📱 **Mobile Access**

### **Mobile Dashboard**
- **Responsive Design** - Optimized for mobile devices
- **Touch Gestures** - Swipe, pinch, and tap support
- **Mobile Navigation** - Touch-friendly navigation
- **Offline Support** - Basic functionality when offline

### **Mobile Features**
- **Real-time Monitoring** - Mobile-optimized health dashboard
- **Event Notifications** - Push notifications for critical events
- **Quick Actions** - Mobile-friendly configuration updates
- **Data Export** - Mobile-optimized export functionality

## 🔒 **Security**

### **Access Control**
- **API Authentication** - Secure API key authentication
- **User Permissions** - Role-based access control
- **Session Management** - Secure session handling
- **Audit Trail** - Complete access logging

### **Data Protection**
- **Encrypted Storage** - Secure data storage
- **Secure Transmission** - Encrypted data transmission
- **Access Logging** - Complete audit trail
- **Backup Security** - Encrypted backup storage

## 📞 **Support**

### **Documentation**
- **API Documentation** - Complete API reference
- **Configuration Guide** - Detailed configuration instructions
- **Troubleshooting Guide** - Common issues and solutions
- **CLI Reference** - Command-line tool documentation

### **Getting Help**
1. **Check Documentation** - Review user manual and guides
2. **Check Logs** - Review system logs for errors
3. **Verify Configuration** - Ensure all settings are correct
4. **Contact Support** - Reach out for additional assistance

---

**🎉 Enjoy using your Home Assistant Ingestor system!**
