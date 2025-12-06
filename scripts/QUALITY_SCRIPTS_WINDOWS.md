# Quality Scripts - Windows Usage Guide (2025)

All quality scripts are now available for Windows PowerShell. Python scripts work on both Windows and Linux.

## Quick Reference

| Order | Script | Windows Command | Frequency | Duration |
|-------|--------|----------------|-----------|----------|
| **Setup** | Setup Tools | `.\scripts\setup-quality-tools.ps1` | Once | 2-5 min |
| **1** | Quick Check | `.\scripts\quick-quality-check.ps1` | Daily/Pre-commit | 2-5 min |
| **2** | Full Analysis | `.\scripts\analyze-code-quality.ps1` | Weekly | 15-30 min |
| **3** | Database Quality | `python scripts\check_database_quality.py --all` | Weekly | 5-10 min |
| **4** | InfluxDB Optimization | `python scripts\optimize_influxdb_shards.py` | Monthly | 5-15 min |

---

## Detailed Usage

### Setup (One-Time)

**Windows:**
```powershell
.\scripts\setup-quality-tools.ps1
```

**What it does:**
- Installs Python quality tools (Ruff, mypy, radon, etc.)
- Installs Node.js tools (jscpd)
- Sets up frontend dependencies for both TypeScript services
- Creates report directories
- Verifies installation

**Requirements:**
- Python 3.10+ with pip
- Node.js with npm

---

### 1. Quick Quality Check (Daily/Pre-commit)

**Windows:**
```powershell
.\scripts\quick-quality-check.ps1
```

**What it checks:**
- Python complexity (radon)
- Python linting (Ruff - 2025 standard)
- TypeScript linting (both services)
- TypeScript type checking (both services)
- Code duplication (quick scan)

**Exit codes:**
- `0` = Pass (may have warnings)
- `1` = Fail (has errors)

**Use cases:**
- Pre-commit hooks
- Quick validation before pushing
- Daily health checks

---

### 2. Full Code Analysis (Weekly)

**Windows:**
```powershell
.\scripts\analyze-code-quality.ps1
```

**What it analyzes:**
- Python complexity (radon) - full report
- Python linting (Ruff) - 2025 standard
- Python type checking (mypy) - strict mode
- TypeScript analysis (both services)
- Code duplication (jscpd) - comprehensive
- Dependency analysis
- Maintainability metrics

**Output:**
- Reports in `reports/quality/`
- JSON reports for programmatic analysis
- Summary report: `reports/quality/SUMMARY.md`

**Use cases:**
- Weekly code reviews
- Before releases
- Technical debt assessment

---

### 3. Database Quality Check (Weekly)

**Windows:**
```powershell
# Check all databases
python scripts\check_database_quality.py --all

# Check specific database
python scripts\check_database_quality.py metadata
python scripts\check_database_quality.py ai_automation
```

**What it checks:**
- All SQLite databases in the project
- Data quality issues
- Missing required fields
- Orphaned records
- Inconsistent data
- Provides recommendations

**Supported databases (2025):**
- `metadata.db` (data-api)
- `ai_automation.db` (ai-automation-service)
- `ha_ai_agent.db` (ha-ai-agent-service)
- `proactive_agent.db` (proactive-agent-service)
- `device_intelligence.db` (device-intelligence-service)
- `ha-setup.db` (ha-setup-service)
- `automation_miner.db` (automation-miner)

**Use cases:**
- Weekly database health checks
- Before migrations
- Data integrity validation

---

### 4. InfluxDB Optimization (Monthly)

**Windows:**
```powershell
python scripts\optimize_influxdb_shards.py
```

**What it does:**
- Analyzes InfluxDB query patterns
- Recommends optimal shard duration
- Analyzes storage efficiency
- Provides optimization recommendations

**Requirements:**
- InfluxDB running and accessible
- Environment variables:
  - `INFLUXDB_URL` (default: `http://localhost:8086`)
  - `INFLUXDB_TOKEN`
  - `INFLUXDB_ORG`
  - `INFLUXDB_BUCKET` (default: `home_assistant_events`)

**Use cases:**
- Monthly performance optimization
- Before scaling
- Storage efficiency reviews

---

## 2025 Updates

### New Features
- **Ruff Integration**: Primary Python linter (10-100x faster than pylint)
- **mypy Type Checking**: Strict type checking for Python
- **Multi-Service Support**: Both TypeScript services analyzed (health-dashboard + ai-automation-ui)
- **Multi-Database Support**: All SQLite databases checked
- **Windows Native**: All scripts have PowerShell versions

### Tool Changes
- **Ruff** replaces pylint as primary linter (pylint still available as legacy option)
- **mypy** added for strict type checking
- **jscpd** for cross-language duplication detection
- **radon** for complexity analysis

---

## Recommended Workflow

### Daily
```powershell
.\scripts\quick-quality-check.ps1
```

### Weekly
```powershell
# 1. Full code analysis
.\scripts\analyze-code-quality.ps1

# 2. Database quality check
python scripts\check_database_quality.py --all
```

### Monthly
```powershell
# 1. Full code analysis
.\scripts\analyze-code-quality.ps1

# 2. Database quality check
python scripts\check_database_quality.py --all

# 3. InfluxDB optimization
python scripts\optimize_influxdb_shards.py
```

---

## Troubleshooting

### PowerShell Execution Policy
If you get execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Or run with bypass:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\quick-quality-check.ps1
```

### Missing Tools
If tools are missing, run setup:
```powershell
.\scripts\setup-quality-tools.ps1
```

### Python Scripts Not Found
Ensure Python is in your PATH:
```powershell
python --version
# Should show Python 3.10+
```

---

## File Locations

**Scripts:**
- `scripts\setup-quality-tools.ps1` - Setup script
- `scripts\quick-quality-check.ps1` - Quick check
- `scripts\analyze-code-quality.ps1` - Full analysis
- `scripts\check_database_quality.py` - Database quality
- `scripts\optimize_influxdb_shards.py` - InfluxDB optimization

**Reports:**
- `reports\quality\` - Quality analysis reports
- `reports\duplication\` - Duplication reports
- `reports\coverage\` - Coverage reports

---

**Last Updated:** December 2025  
**Status:** ✅ All scripts Windows-compatible

