# Code Quality Tools - Quick Start Guide

**Last Updated:** January 2025  
**Optimized for:** Single-home, NUC deployment

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Python Quality Tools

```bash
# Install essential tools only (lightweight, fast)
pip install ruff mypy

# Optional: Add security/dead code tools (run occasionally, not every time)
pip install bandit vulture
```

### Step 2: Install TypeScript/JavaScript Tools

```bash
cd services/health-dashboard
npm install --save-dev \
  eslint-plugin-complexity \
  eslint-plugin-sonarjs \
  dependency-cruiser \
  plato
```

### Step 3: Run Quick Quality Check

```bash
# Python: Fast linting with Ruff
ruff check services/

# Python: Type checking
mypy services/

# Python: Security scan
bandit -r services/

# TypeScript: Linting (already configured)
cd services/health-dashboard
npm run lint
```

---

## 📊 Quick Analysis Commands

### Python Complexity Analysis

```bash
# Check complexity (already configured)
radon cc services/ -n C -s

# Maintainability index
radon mi services/ -s

# Full report
radon cc services/ -a --json > reports/quality/complexity.json
```

### TypeScript Complexity

```bash
cd services/health-dashboard
npm run lint -- --format json > reports/quality/eslint-complexity.json
```

### Dead Code Detection

```bash
# Find unused Python code
vulture services/ --min-confidence 80
```

### Security Scan

```bash
# Python security issues
bandit -r services/ -ll

# JavaScript/TypeScript (via npm)
cd services/health-dashboard
npm audit
```

---

## 🎯 Recommended Daily Workflow

### Before Committing Code

```bash
# 1. Quick lint check
ruff check services/

# 2. Type check (if using mypy)
mypy services/

# 3. Run existing quality script
./scripts/quick-quality-check.sh
```

### Weekly Analysis

```bash
# Full quality analysis
./scripts/analyze-code-quality.sh

# Review reports in reports/quality/
```

---

## 🔧 Configuration Files to Create

### 1. `pyproject.toml` (Root level)

Add Ruff and mypy configuration (see full guide for details).

### 2. `.bandit` (Root level)

```ini
[bandit]
exclude_dirs = tests/,venv/,__pycache__
skips = B101
```

### 3. `.vulture.ini` (Root level)

```ini
[vulture]
exclude = tests/, migrations/, alembic/
min_confidence = 80
paths = services/
```

---

## 📈 Quality Thresholds

### Quick Reference

| Metric | Python | TypeScript | Status |
|--------|--------|------------|--------|
| Complexity | < 15 | < 15 | ⚠️ Warn |
| Complexity | < 20 | < 20 | ❌ Error |
| Test Coverage | > 80% | > 70% | ✅ Target |
| Code Duplication | < 3% | < 3% | ✅ Target |
| Security Issues | 0 high/critical | 0 high/critical | ❌ Block |

---

## 🆘 Troubleshooting

### Ruff not found
```bash
pip install ruff
```

### mypy errors too strict
```bash
# Start with lenient config, tighten over time
mypy services/ --ignore-missing-imports
```

### ESLint complexity warnings
```bash
# Review and refactor complex functions
# Or temporarily increase threshold in eslint config
```

---

## 📚 Next Steps

1. **Read full guide:** [CODE_QUALITY_TOOLS_2025.md](CODE_QUALITY_TOOLS_2025.md)
2. **Set up CI/CD integration** for automated checks
3. **Establish quality gates** for pull requests
4. **Track metrics over time** to measure improvement

---

## 💡 Pro Tips

1. **Start small:** Install Tier 1 tools first
2. **Fix incrementally:** Don't try to fix everything at once
3. **Use auto-fix:** `ruff check --fix` can fix many issues automatically
4. **Focus on new code:** Apply strict rules to new code, gradually improve old code
5. **Set realistic thresholds:** Start lenient, tighten over time

---

**For detailed information, see:** [CODE_QUALITY_TOOLS_2025.md](CODE_QUALITY_TOOLS_2025.md)

