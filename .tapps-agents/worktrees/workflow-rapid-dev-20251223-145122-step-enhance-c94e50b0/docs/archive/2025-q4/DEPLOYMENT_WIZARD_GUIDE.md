# 🚀 Deployment Wizard & Connection Validator - User Guide

**Version:** 1.0.0  
**Status:** Production Ready  
**Platform:** Linux, macOS, Windows (WSL/Cygwin)

---

## 📋 Overview

The HA-Ingestor Deployment Wizard and Connection Validator are interactive command-line tools that simplify the deployment process by guiding you through configuration and validating your setup before deployment.

### What They Do

**Deployment Wizard (`deploy-wizard.sh`)**
- Guides you through deployment option selection
- Collects Home Assistant connection details
- Auto-detects system resources
- Generates secure configuration files
- Tests connectivity (optional)

**Connection Validator (`validate-ha-connection.sh`)**
- Tests TCP/IP connectivity
- Validates HTTP/HTTPS endpoint
- Tests WebSocket connections
- Verifies authentication
- Checks API access
- Generates detailed reports

---

## 🚀 Quick Start

### Step 1: Run the Deployment Wizard

```bash
cd homeiq
./scripts/deploy-wizard.sh
```

The wizard will guide you through:
1. Choosing your deployment option
2. Configuring Home Assistant connection
3. System resource detection
4. Configuration file generation

### Step 2: Deploy

```bash
docker-compose up -d
```

### Step 3: Verify

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Access dashboard
open http://localhost:3000
```

---

## 📖 Detailed Usage

### Deployment Wizard

#### Interactive Flow

**1. Deployment Option Selection**

Choose where HA-Ingestor will run:

- **Option 1: Same Machine** - Simplest, uses localhost
- **Option 2: Separate Machine** - Best for production
- **Option 3: Remote/Nabu Casa** - For cloud deployments
- **Option 4: Custom** - Advanced manual configuration

**2. Home Assistant Configuration**

The wizard will prompt for:
- Home Assistant URL (context-aware defaults provided)
- Long-lived access token
- Optional connection test

**3. Resource Detection**

Automatically checks:
- Operating system
- Available RAM
- Disk space
- CPU cores
- Docker installation
- Docker Compose version

**4. Configuration Generation**

Creates:
- `.env` file with all settings
- Secure randomly-generated passwords
- `CREDENTIALS.txt` with admin credentials

**5. Summary**

Shows next steps to deploy the system.

#### Example Session

```bash
$ ./scripts/deploy-wizard.sh

╔═══════════════════════════════════════════════════════════╗
║  🧙  HA-Ingestor Deployment Wizard  v1.0.0               ║
╚═══════════════════════════════════════════════════════════╝

Welcome to the HA-Ingestor Deployment Wizard!

This wizard will help you:
  • Choose the right deployment option
  • Configure Home Assistant connection
  • Detect system resources
  • Generate configuration files
  • Validate your setup

Press any key to continue...

━━━ Deployment Configuration ━━━

Where is your Home Assistant currently running?

1) Same Machine (localhost)
   ✅ Simplest setup, no network configuration
   ⚠️  Shares resources with Home Assistant
   📌 Best for: Testing, development

2) Separate Machine (Local Network)
   ✅ Resource isolation, better performance
   📌 Best for: Production, dedicated monitoring

3) Remote Access (Nabu Casa or Cloud)
   ✅ Access from anywhere
   📌 Best for: Cloud infrastructure

Select deployment option (1-3): 2

   ✅ Selected: Separate Machine deployment

━━━ Home Assistant Configuration ━━━

📌 Enter the IP address of your Home Assistant server
   Example: 192.168.1.100

Enter Home Assistant IP: 192.168.1.100
   ✅ IP address validated

Enter Home Assistant URL [http://192.168.1.100:8123]: 
   ✅ URL accepted: http://192.168.1.100:8123

Enter Home Assistant access token: ******************
   ✅ Token saved: eyJ0eXA...kpXVCJ9 (184 characters)

Would you like to test the connection now? (Y/n): y

   ➜ Testing connection to Home Assistant...
   ✅ Connection successful!
   ✅ Home Assistant is reachable and token is valid

━━━ System Resource Detection ━━━

   ℹ️  Operating System: Linux

   ℹ️  RAM: 8GB
   ✅ Sufficient RAM for full deployment
   ℹ️  Available Disk Space: 47GB
   ✅ Sufficient disk space
   ℹ️  CPU Cores: 4
   ✅ Sufficient CPU cores

   ➜ Checking Docker installation...
   ✅ Docker installed: 24.0.6
   ✅ Docker Compose installed: 2.21.0

   ✅ System meets all requirements!

━━━ Configuration Generation ━━━

   ➜ Generating secure passwords...
   ✅ Secure passwords generated
   ➜ Creating configuration file...
   ✅ Configuration saved to: .env
   ℹ️  File permissions: 600 (owner read/write only)

   ✅ Credentials saved to: CREDENTIALS.txt
   ⚠️  SAVE THESE CREDENTIALS AND DELETE CREDENTIALS.txt FOR SECURITY!

━━━ Setup Complete! ━━━

🚀 Congratulations! Your HA-Ingestor is configured.

Next Steps:

1. Review your configuration:
   cat .env

2. Start the services:
   docker-compose up -d

3. Monitor the logs:
   docker-compose logs -f

4. Access the dashboard:
   http://localhost:3000

Happy monitoring! 🧙
```

---

### Connection Validator

#### Basic Usage

```bash
./scripts/validate-ha-connection.sh
```

#### Options

```bash
./scripts/validate-ha-connection.sh [options]

Options:
  -v, --verbose     Verbose output (detailed test information)
  -q, --quiet       Quiet mode (errors only)
  -r, --report      Generate report file (default)
  --no-report       Don't generate report file
  -h, --help        Show help
```

#### Example Output

```bash
$ ./scripts/validate-ha-connection.sh

╔═══════════════════════════════════════════════════════════╗
║  Home Assistant Connection Validator  v1.0.0             ║
╚═══════════════════════════════════════════════════════════╝

━━━ Loading Configuration ━━━

   ✅ Configuration loaded from: .env

━━━ TCP/IP Connectivity Test ━━━

   ✅ TCP connection successful to 192.168.1.100:8123

━━━ HTTP Endpoint Test ━━━

   ✅ HTTP endpoint accessible (HTTP 200)

━━━ WebSocket Connection Test ━━━

   ✅ WebSocket connection successful

━━━ Authentication Test ━━━

   ✅ Authentication successful
   ✅ Token is valid

━━━ API Access Test ━━━

   ✅ API access confirmed (can read states)

━━━ Validation Summary ━━━

═══════════════════════════════════════════════════════════
Home Assistant Connection Validation Report
Generated: Sun Oct 12 14:32:15 PDT 2025
═══════════════════════════════════════════════════════════

Configuration:
  URL: http://192.168.1.100:8123
  Token: eyJ0eXA6...kpXVCJ9

Test Results:
  ✅ Passed: 5
  ❌ Failed: 0
  ⚠️  Warnings: 0
  📊 Total: 5

Detailed Results:
  ✅ TCP Connectivity: Successfully connected to 192.168.1.100:8123
  ✅ HTTP Endpoint: HTTP 200
  ✅ WebSocket Connection: Successfully connected
  ✅ Authentication: Token validated successfully
  ✅ API Access: Can read state data

🎉 All tests passed! Your Home Assistant connection is ready.

Next Steps:
  1. Start HA-Ingestor: docker-compose up -d
  2. Monitor logs: docker-compose logs -f
  3. Access dashboard: http://localhost:3000

═══════════════════════════════════════════════════════════

Report saved to: ha-connection-validation-20251012_143215.txt
```

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "Docker not found"

**Solution:**
```bash
# Install Docker
# Linux: https://docs.docker.com/engine/install/
# macOS: https://docs.docker.com/desktop/mac/install/
# Windows: https://docs.docker.com/desktop/windows/install/

# Verify installation
docker --version
```

#### Issue: "Authentication failed"

**Symptoms:**
- HTTP 401 errors
- "Authentication failed" message
- "Token validation failed"

**Solutions:**
1. **Regenerate token:**
   - Open Home Assistant
   - Go to Profile → Long-Lived Access Tokens
   - Delete old token
   - Create new token
   - Copy entire token (no extra spaces)

2. **Verify token length:**
   - Should be ~180 characters
   - Starts with `eyJ0`

3. **Check permissions:**
   - Ensure user has admin access
   - Token should have full API access

#### Issue: "Cannot reach Home Assistant"

**Symptoms:**
- TCP connection failed
- HTTP 000 error
- Timeout errors

**Solutions:**
1. **Verify Home Assistant is running:**
   ```bash
   # From another machine
   ping 192.168.1.100
   curl http://192.168.1.100:8123
   ```

2. **Check firewall:**
   ```bash
   # Allow port 8123
   sudo ufw allow 8123
   ```

3. **Verify URL:**
   - Use correct IP address
   - Include protocol (http:// or https://)
   - Default port is 8123

#### Issue: "WebSocket test failed"

**Solutions:**
1. **Install Python websockets:**
   ```bash
   pip install websockets
   ```

2. **Use correct protocol:**
   - HTTP → WebSocket (ws://)
   - HTTPS → Secure WebSocket (wss://)

3. **Check for proxies:**
   - Reverse proxies may block WebSocket
   - Configure proxy to allow WebSocket

---

## 📝 Generated Files

### `.env`
Main configuration file with:
- Home Assistant connection details
- InfluxDB settings
- Service ports
- Authentication settings
- Logging configuration

**Location:** Project root  
**Permissions:** 600 (owner read/write only)  
**Backup:** Auto-created before overwriting

### `CREDENTIALS.txt`
Sensitive credentials file with:
- Admin dashboard password
- InfluxDB credentials
- Generated tokens

**⚠️ IMPORTANT:** Save these credentials securely and delete this file!

### Validation Reports
Detailed test reports with:
- Configuration summary
- Test results
- Troubleshooting recommendations
- Next steps

**Location:** `ha-connection-validation-YYYYMMDD_HHMMSS.txt`  
**Generated:** When validation completes

---

## 🎯 Best Practices

### Security

1. **Delete CREDENTIALS.txt** after saving passwords securely
2. **Never commit `.env`** to version control (already in `.gitignore`)
3. **Use strong tokens** - regenerate if compromised
4. **Secure file permissions** - 600 for sensitive files
5. **Regular token rotation** - regenerate tokens periodically

### Deployment

1. **Run wizard first** before manual configuration
2. **Test connection** before full deployment
3. **Review configuration** before starting services
4. **Monitor logs** during first deployment
5. **Validate setup** after deployment

### Maintenance

1. **Backup `.env`** before making changes
2. **Re-run validator** after configuration changes
3. **Keep tokens secure** - never share or expose
4. **Update regularly** - check for script updates
5. **Document changes** - note any custom modifications

---

## 📞 Support

### Getting Help

1. **Run validator with verbose mode:**
   ```bash
   ./scripts/validate-ha-connection.sh -v
   ```

2. **Check logs:**
   ```bash
   docker-compose logs
   ```

3. **Review documentation:**
   - Main README: `README.md`
   - Troubleshooting: `docs/TROUBLESHOOTING_GUIDE.md`
   - API Docs: `docs/API_DOCUMENTATION.md`

### Reporting Issues

When reporting issues, include:
- Wizard/validator output
- Operating system and version
- Docker version
- Home Assistant version
- Error messages
- Validation report (if generated)

---

## 🔄 Re-running the Wizard

You can re-run the wizard at any time:

```bash
./scripts/deploy-wizard.sh
```

The wizard will:
- Backup existing `.env` file
- Guide you through configuration again
- Generate new credentials (optional)
- Create new configuration

**Previous configuration is saved as:** `.env.backup.YYYYMMDD_HHMMSS`

---

## ✅ Success Checklist

Before deploying, ensure:

- [ ] Wizard completed successfully
- [ ] Configuration file (`.env`) created
- [ ] Credentials saved securely
- [ ] CREDENTIALS.txt deleted
- [ ] Connection validator passed all tests
- [ ] Docker and Docker Compose installed
- [ ] Sufficient system resources available
- [ ] Home Assistant accessible and working
- [ ] Long-lived access token valid

---

**Ready to deploy!** Follow the next steps shown by the wizard to start your HA-Ingestor system.

For detailed documentation, see:
- **Deployment Plan:** `docs/HOME_ASSISTANT_DEPLOYMENT_PLAN.md`
- **Troubleshooting:** `docs/TROUBLESHOOTING_GUIDE.md`
- **User Manual:** `docs/USER_MANUAL.md`

