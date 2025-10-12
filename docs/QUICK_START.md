# ⚡ HA-Ingestor Quick Start Guide

**Get up and running in under 5 minutes!**

---

## 🚀 Super Fast Start (Recommended)

```bash
# 1. Clone
git clone <repository-url>
cd ha-ingestor

# 2. Run wizard
./scripts/deploy-wizard.sh

# 3. Deploy
docker-compose up -d

# 4. Access
open http://localhost:3000
```

**Done!** ✅ Your HA-Ingestor is running.

---

## 📋 What You Need

- ✅ Docker & Docker Compose
- ✅ Home Assistant instance
- ✅ Long-lived access token from Home Assistant
- ✅ 4GB RAM minimum
- ✅ 20GB storage

---

## 🧙 About the Deployment Wizard

The wizard will:
- ✅ Guide you through 4 deployment options
- ✅ Configure Home Assistant connection
- ✅ Auto-detect system resources
- ✅ Generate secure configuration
- ✅ Validate connectivity
- ✅ Provide next steps

**Takes 30-60 minutes** (vs 2-4 hours manual setup)

---

## 🔍 Validate Before Deploy

Test your configuration:

```bash
./scripts/validate-ha-connection.sh
```

Get instant feedback on:
- TCP/IP connectivity ✅
- HTTP endpoint ✅
- WebSocket connection ✅
- Authentication ✅
- API access ✅

---

## 📖 Need More Help?

- **Wizard Guide:** [`docs/DEPLOYMENT_WIZARD_GUIDE.md`](DEPLOYMENT_WIZARD_GUIDE.md)
- **Full Deployment:** [`docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md)
- **Troubleshooting:** [`docs/TROUBLESHOOTING_GUIDE.md`](TROUBLESHOOTING_GUIDE.md)
- **User Manual:** [`docs/USER_MANUAL.md`](USER_MANUAL.md)

---

## 🎯 Deployment Options

### Option 1: Same Machine as Home Assistant
- **URL:** `http://localhost:8123`
- **Best for:** Testing, development
- **Resources:** 8GB+ RAM recommended

### Option 2: Separate Machine (Recommended)
- **URL:** `http://192.168.1.X:8123`
- **Best for:** Production
- **Resources:** 4GB+ RAM

### Option 3: Remote/Nabu Casa
- **URL:** `https://xxxxx.ui.nabu.casa`
- **Best for:** Cloud, remote access
- **Requires:** Nabu Casa or exposed HA

---

## ⚡ Commands Cheat Sheet

```bash
# Deployment
./scripts/deploy-wizard.sh          # Interactive setup
./scripts/validate-ha-connection.sh # Test configuration
docker-compose up -d                # Start services
docker-compose down                 # Stop services

# Monitoring
docker-compose ps                   # Check status
docker-compose logs -f              # View logs
docker-compose logs service-name    # Service logs

# Maintenance
docker-compose restart              # Restart all
docker-compose restart service-name # Restart one
docker-compose pull                 # Update images
```

---

## 🔒 Security Quick Tips

1. ✅ **Save credentials** from `CREDENTIALS.txt`
2. ✅ **Delete `CREDENTIALS.txt`** after saving
3. ✅ **Never commit `.env`** to git (already in `.gitignore`)
4. ✅ **Use strong tokens** - regenerate if compromised
5. ✅ **Set file permissions** - wizard does this automatically

---

## ✅ Success Checklist

- [ ] Wizard completed successfully
- [ ] Configuration file created
- [ ] Credentials saved securely
- [ ] CREDENTIALS.txt deleted
- [ ] Validator passed all tests
- [ ] Services started successfully
- [ ] Dashboard accessible at `http://localhost:3000`
- [ ] Events flowing from Home Assistant

---

## 🎉 You're All Set!

Your HA-Ingestor is now:
- ✅ Capturing Home Assistant events
- ✅ Enriching data with external sources
- ✅ Storing in InfluxDB
- ✅ Displaying on dashboard
- ✅ Ready for monitoring and analysis

**Happy monitoring!** 🚀

---

## 🆘 Something Wrong?

1. **Check validator output:** `./scripts/validate-ha-connection.sh -v`
2. **View logs:** `docker-compose logs -f`
3. **Read troubleshooting:** [`docs/TROUBLESHOOTING_GUIDE.md`](TROUBLESHOOTING_GUIDE.md)
4. **Re-run wizard:** `./scripts/deploy-wizard.sh`

---

**Questions?** All features are documented in the user manual and deployment guide!

