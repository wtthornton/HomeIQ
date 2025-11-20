# Simple Code Quality Plan for NUC Deployment

**Last Updated:** January 2025  
**For:** Single-home, NUC-based HomeIQ deployment

## 🎯 The Simple Approach

This is a **practical, lightweight** plan focused on tools that:
- ⚡ Run fast (seconds, not minutes)
- 💾 Use minimal resources (important for NUC)
- 🎯 Provide immediate value
- 🔧 Are easy to set up and maintain

---

## ✅ Essential Tools (Do This)

### 1. Ruff - Fast Python Linter
**Why:** 10-100x faster than pylint, uses less RAM

```bash
# Install
pip install ruff

# Use it
ruff check services/
ruff check --fix services/  # Auto-fix issues
```

**Time:** 5 minutes to set up  
**Resource:** <50MB RAM, runs in seconds

### 2. mypy - Type Checking (Optional but Recommended)
**Why:** Catches bugs before runtime

```bash
# Install
pip install mypy

# Use it
mypy services/
```

**Time:** 10 minutes to configure  
**Resource:** <100MB RAM, runs in seconds

### 3. ESLint - Already Configured ✅
**Why:** Already working, just enhance it

```bash
# Add complexity plugin (optional)
cd services/health-dashboard
npm install --save-dev eslint-plugin-complexity
```

**Time:** 5 minutes  
**Resource:** Already running

---

## ⏸️ Optional Tools (Run Occasionally)

### bandit - Security Scanning
**When:** Run weekly/monthly, not every commit

```bash
pip install bandit
bandit -r services/
```

### vulture - Dead Code Detection
**When:** Run occasionally to clean up

```bash
pip install vulture
vulture services/ --min-confidence 80
```

---

## ❌ Skip These (Too Heavy for NUC)

- **SonarQube** - Needs 2GB+ RAM Docker container
- **wily** - Trend tracking (not needed)
- **CodeScene** - Enterprise-focused
- **plato** - Heavy visualization
- **Lizard** - Duplicate of radon/ESLint

---

## 📋 Quick Setup (30 minutes)

1. **Install Ruff** (5 min)
   ```bash
   pip install ruff
   ruff check services/
   ```

2. **Install mypy** (10 min)
   ```bash
   pip install mypy
   # Add basic config to pyproject.toml
   mypy services/
   ```

3. **Enhance ESLint** (5 min)
   ```bash
   cd services/health-dashboard
   npm install --save-dev eslint-plugin-complexity
   ```

4. **Update existing scripts** (10 min)
   - Replace pylint with ruff in `scripts/analyze-code-quality.sh`
   - Add mypy check

**Total time:** ~30 minutes  
**Total resource overhead:** <200MB RAM

---

## 🎯 Daily Workflow

### Before Committing
```bash
# Quick check (takes seconds)
ruff check services/
mypy services/  # if configured
```

### Weekly
```bash
# Security scan
bandit -r services/

# Dead code cleanup
vulture services/
```

---

## 💡 Key Principles

1. **Keep it simple** - Don't over-engineer
2. **Fast feedback** - Tools should run in seconds
3. **Low overhead** - Minimal resource usage
4. **Practical value** - Focus on fixing issues, not tracking trends
5. **Incremental** - Add tools as needed, not all at once

---

## 📊 What You Get

- ✅ Fast linting (Ruff)
- ✅ Type safety (mypy)
- ✅ Complexity checks (ESLint + existing radon)
- ✅ Security scanning (bandit, occasional)
- ✅ Dead code cleanup (vulture, occasional)

**No heavy infrastructure, no Docker containers, no complex setup.**

---

## 🆘 Troubleshooting

**Ruff too strict?**
- Start with basic rules, add more over time
- Use `--select` to choose specific rule sets

**mypy too many errors?**
- Start with `--ignore-missing-imports`
- Fix incrementally, don't try to fix everything at once

**ESLint complexity warnings?**
- Review and refactor complex functions
- Or temporarily increase threshold

---

**Remember:** This is for a single-home project. Keep it simple, keep it fast, keep it practical.

