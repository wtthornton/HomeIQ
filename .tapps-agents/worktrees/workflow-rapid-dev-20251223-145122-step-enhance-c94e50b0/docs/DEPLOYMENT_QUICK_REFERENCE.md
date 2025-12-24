# 🚀 Quick Reference - Deploying to Running Home Assistant

## TL;DR - What You Need to Know

**Important:** HA-Ingestor is a **separate application** that runs **alongside** Home Assistant (not inside it).

### Minimum Requirements
- ✅ Docker & Docker Compose
- ✅ 4GB RAM, 2 CPU cores, 20GB storage
- ✅ Home Assistant with long-lived access token
- ✅ Network access to Home Assistant

### Fastest Path to Deployment

1. **Get Home Assistant Token**
   ```
   Home Assistant → Profile → Long-Lived Access Tokens → Create Token
   ```

2. **Clone & Configure**
   ```bash
   git clone <repo>
   cd homeiq
   ./scripts/setup-secure-env.sh  # Interactive setup
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   ```

4. **Access Dashboard**
   ```
   http://localhost:3000
   ```

---

## Deployment Location Options

### Same Machine as Home Assistant
```yaml
HOME_ASSISTANT_URL=ws://localhost:8123/api/websocket
```
**Best for:** Testing, small setups  
**Resources:** Need 8GB+ total RAM

### Separate Machine (Recommended)
```yaml
HOME_ASSISTANT_URL=ws://192.168.1.100:8123/api/websocket
```
**Best for:** Production  
**Resources:** 4GB+ RAM on separate machine

### Remote/Cloud
```yaml
HOME_ASSISTANT_URL=wss://xxxxx.ui.nabu.casa/api/websocket
```
**Best for:** Advanced users, remote monitoring  
**Requires:** Nabu Casa or exposed HA instance

---

## Service Profiles

### Minimal (Testing)
**Services:** influxdb, websocket-ingestion, enrichment-pipeline, admin-api, dashboard  
**RAM:** 2-3GB | **Storage:** 10GB | **Time:** 1-2 hours

### Standard (Production)
**Services:** Core + weather-api + data-retention  
**RAM:** 4GB | **Storage:** 30GB | **Time:** 2-3 hours

### Full Featured
**Services:** All services enabled  
**RAM:** 6-8GB | **Storage:** 50-100GB | **Time:** 3-4 hours

---

## Critical Questions Checklist

Before starting, know these answers:

- [ ] Where is Home Assistant running? (URL)
- [ ] Where will HA-Ingestor run? (same machine / separate / cloud)
- [ ] How much RAM is available?
- [ ] Can I create Home Assistant long-lived token?
- [ ] Is Docker installed?
- [ ] Can deployment machine reach Home Assistant?
- [ ] Do I have OpenWeatherMap API key? (optional)
- [ ] How long should data be retained?

---

## Common Pitfalls

❌ **Don't:** Try to install as Home Assistant add-on (won't work)  
❌ **Don't:** Use default passwords in production  
❌ **Don't:** Commit `.env` files to git  
❌ **Don't:** Skip health checks and validation  

✅ **Do:** Use provided setup scripts  
✅ **Do:** Start with minimal config, scale up  
✅ **Do:** Test Home Assistant connectivity first  
✅ **Do:** Monitor resource usage  

---

## Troubleshooting Quick Fixes

**Connection Failed?**
```bash
# Test Home Assistant connectivity
curl http://192.168.1.100:8123

# Check logs
docker-compose logs websocket-ingestion
```

**Out of Memory?**
```bash
# Check resource usage
docker stats

# Reduce services in docker-compose.yml
# Disable optional services
```

**Dashboard Not Loading?**
```bash
# Check service health
docker-compose ps

# Restart services
docker-compose restart
```

---

## Next Steps

1. 📖 Read full deployment plan: `docs/HOME_ASSISTANT_DEPLOYMENT_PLAN.md`
2. 🔬 Review research summary: `docs/DEPLOYMENT_RESEARCH_SUMMARY.md`
3. ✅ Answer critical questions
4. 🚀 Get customized deployment guide

---

**Ready?** Provide answers to the questions, and let's deploy! 🎉

