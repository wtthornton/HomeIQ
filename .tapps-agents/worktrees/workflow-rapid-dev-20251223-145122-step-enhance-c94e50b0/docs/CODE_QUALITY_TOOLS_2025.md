# Code Quality & Maintainability Tools - 2025 Recommendations

**Last Updated:** January 2025  
**Status:** Recommendations for HomeIQ Project (Single-Home, NUC Deployment)

## Overview

This document provides **lightweight, practical** recommendations for free, open-source tools to analyze code maintainability and complexity in the HomeIQ project. These recommendations are tailored for a **single-home, NUC-based deployment** - focusing on tools that are:
- ⚡ **Fast** - Quick feedback without slowing development
- 💾 **Lightweight** - Minimal resource usage (important for NUC)
- 🎯 **Practical** - Focus on actionable insights, not enterprise metrics
- 🔧 **Simple** - Easy setup and maintenance

These tools focus on **analysis and reporting only** - they do not modify your code logic.

---

## 🐍 Python Tools & Libraries

### 1. **Ruff** (Recommended - Modern & Fast) ⭐
**Status:** Already mentioned in project rules, but not fully configured

**What it does:**
- Ultra-fast Python linter written in Rust (10-100x faster than pylint/flake8)
- Replaces: flake8, isort, pyupgrade, autoflake, and more
- 2025 best practice: Industry standard for Python linting

**Installation:**
```bash
pip install ruff
```

**Configuration:** Create `pyproject.toml` or `ruff.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "ARG", # flake8-unused-arguments
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
    "PTH", # flake8-use-pathlib
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.lint.mccabe]
max-complexity = 15  # Warn on complexity > 15

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

**Usage:**
```bash
# Check all Python files
ruff check services/

# Auto-fix issues
ruff check --fix services/

# Format code
ruff format services/
```

**Benefits:**
- ⚡ 10-100x faster than pylint/flake8
- 🔧 Can auto-fix many issues
- 📊 Built-in complexity checking (MCCabe)
- 🎯 2025 industry standard

---

### 2. **Radon** (Already in use - Enhance it)
**Status:** Already configured in `scripts/analyze-code-quality.sh`

**Enhancements for 2025:**
```bash
# Install with additional metrics
pip install radon[all]

# Generate comprehensive reports
radon cc services/ --min B --show-complexity --average
radon mi services/ --min B
radon raw services/ --summary  # Raw metrics
radon hal services/  # Halstead metrics
```

**Recommended thresholds:**
- Cyclomatic Complexity: < 15 (warn), < 20 (error)
- Maintainability Index: > 65 (B grade)
- Halstead Volume: < 1000 (low complexity)

---

### 3. **Vulture** (Dead Code Detection)
**What it does:**
- Finds unused code (dead code)
- Identifies unused imports, functions, classes, variables
- Helps reduce technical debt

**Installation:**
```bash
pip install vulture
```

**Usage:**
```bash
# Find dead code
vulture services/ --min-confidence 80

# Exclude test files
vulture services/ --exclude tests/ --min-confidence 80

# Generate report
vulture services/ --min-confidence 80 > reports/quality/dead-code.txt
```

**Configuration:** Create `.vulture.ini`:
```ini
[vulture]
exclude = tests/, migrations/, alembic/
min_confidence = 80
paths = services/
```

---

### 4. **mypy** (Type Checking)
**Status:** Mentioned in rules, but not configured

**What it does:**
- Static type checker for Python
- Catches type errors before runtime
- Improves code maintainability through type safety

**Installation:**
```bash
pip install mypy
```

**Configuration:** Create `mypy.ini` or add to `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # Start lenient, tighten over time
disallow_incomplete_defs = false
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "tests.*",
    "alembic.*",
]
ignore_errors = true
```

**Usage:**
```bash
# Type check all services
mypy services/

# Generate report
mypy services/ --html-report reports/quality/mypy-report
```

---

### 5. **bandit** (Security Linting)
**What it does:**
- Security linter for Python
- Finds common security issues
- 2025 best practice: Security-first development

**Installation:**
```bash
pip install bandit
```

**Usage:**
```bash
# Scan for security issues
bandit -r services/ -f json -o reports/quality/bandit-report.json

# Include info-level issues
bandit -r services/ -ll -f txt -o reports/quality/bandit-report.txt
```

**Configuration:** Create `.bandit`:
```ini
[bandit]
exclude_dirs = tests/,venv/,__pycache__
skips = B101  # Skip assert_used (common in tests)
```

---

### 6. **pylint** (Already in use - Modernize)
**Status:** Already configured, but consider modernizing

**2025 Best Practices:**
- Use pylint with `pyproject.toml` configuration
- Focus on maintainability and complexity rules
- Disable overly pedantic style rules (let Ruff handle those)

**Configuration:** Create `pyproject.toml` section:
```toml
[tool.pylint.main]
max-line-length = 100
ignore = ["migrations", "alembic"]

[tool.pylint."messages control"]
disable = [
    "C0103",  # invalid-name (too strict)
    "C0111",  # missing-docstring (let ruff handle)
    "R0903",  # too-few-public-methods
    "R0913",  # too-many-arguments (use complexity tools instead)
]

[tool.pylint.design]
max-args = 7
max-locals = 15
max-returns = 6
max-branches = 12
max-statements = 50
max-parents = 7
max-attributes = 10
min-public-methods = 1
max-public-methods = 20
```

---

### 7. **wily** (Complexity Trend Tracking) ⏸️ Optional
**What it does:**
- Tracks code complexity over time
- Visualizes complexity trends

**Recommendation:** Skip for single-home project
- Nice-to-have but not essential
- Your existing radon checks are sufficient
- Focus on fixing issues, not tracking trends

---

### 8. **pydocstyle** (Docstring Linting)
**What it does:**
- Checks docstring conventions
- Enforces documentation standards
- Improves code documentation quality

**Installation:**
```bash
pip install pydocstyle
```

**Usage:**
```bash
# Check docstrings
pydocstyle services/ --convention=google

# Generate report
pydocstyle services/ --convention=google > reports/quality/docstrings.txt
```

---

## 📘 TypeScript/JavaScript Tools

### 1. **ESLint** (Already in use - Enhance)
**Status:** Already configured in `services/health-dashboard/.eslintrc.cjs`

**2025 Enhancements:**
- Migrate to ESLint 9+ flat config format
- Add more complexity rules
- Integrate with TypeScript strict mode

**Recommended additional plugins:**
```bash
npm install --save-dev \
  @typescript-eslint/eslint-plugin \
  eslint-plugin-complexity \
  eslint-plugin-sonarjs \
  eslint-plugin-unicorn \
  eslint-plugin-import
```

**Enhanced configuration:** Create `eslint.config.js` (flat config):
```javascript
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import complexity from 'eslint-plugin-complexity';
import sonarjs from 'eslint-plugin-sonarjs';

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    plugins: {
      complexity,
      sonarjs,
    },
    rules: {
      // Complexity rules
      'complexity': ['warn', { max: 15 }],
      'max-lines-per-function': ['warn', { max: 100, skipComments: true }],
      'max-depth': ['warn', 4],
      'max-params': ['warn', 5],
      
      // SonarJS rules (code smells)
      'sonarjs/cognitive-complexity': ['warn', 15],
      'sonarjs/no-duplicate-string': 'warn',
      'sonarjs/no-identical-functions': 'warn',
      'sonarjs/no-small-switch': 'warn',
      'sonarjs/prefer-immediate-return': 'warn',
      
      // TypeScript strict rules
      '@typescript-eslint/explicit-function-return-type': 'warn',
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/strict-boolean-expressions': 'warn',
    },
  }
);
```

---

### 2. **TypeScript Strict Mode**
**What it does:**
- Enforces strict type checking
- Catches type errors at compile time
- Improves code maintainability

**Configuration:** Update `tsconfig.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

---

### 3. **plato** (JavaScript Complexity Analysis) ⏸️ Optional
**Recommendation:** Skip for NUC
- Heavy visualization tool
- ESLint complexity rules are sufficient
- Not needed for single-home project

---

### 4. **dependency-cruiser** (Dependency Analysis) ⏸️ Optional
**What it does:**
- Analyzes dependency graphs
- Finds circular dependencies
- Identifies architectural issues

**Installation:**
```bash
npm install --save-dev dependency-cruiser
```

**Usage:**
```bash
# Analyze dependencies
depcruise --output-type err services/health-dashboard/src

# Generate visual graph
depcruise --output-type dot services/health-dashboard/src | dot -T svg > reports/quality/dependencies.svg
```

---

## 🔍 Cross-Language Tools

### 1. **SonarQube Community Edition** ❌ Skip for NUC
**Why Skip:**
- Requires Docker container with 2GB+ RAM
- Heavy resource usage (not ideal for NUC)
- Overkill for single-home, single-developer project
- Complex setup and maintenance

**Alternative:** Use lightweight tools (Ruff, mypy, ESLint) instead

---

### 2. **jscpd** (Code Duplication - Already in use)
**Status:** Already configured in `scripts/analyze-code-quality.sh`

**2025 Enhancements:**
```bash
# Install globally or locally
npm install -g jscpd

# Enhanced usage with better reporting
jscpd services/ \
  --min-lines 5 \
  --min-tokens 50 \
  --threshold 3 \
  --format python,typescript,javascript \
  --reporters console,html,json \
  --output reports/duplication/
```

---

### 3. **CodeScene** (Behavioral Analysis) ❌ Skip for NUC
**Why Skip:**
- Enterprise-focused tool
- Requires GitHub integration
- Overkill for single-home, single-developer project
- Focus on fixing issues, not tracking social patterns

---

### 4. **Lizard** (Multi-Language Complexity) ⏸️ Optional
**Recommendation:** Skip - Radon already covers Python complexity
- Your existing radon checks are sufficient
- ESLint covers TypeScript complexity
- No need for duplicate analysis

---

## 📊 Reporting & Visualization Tools

### 1. **coverage.py** (Already in use - Enhance)
**Status:** Already configured for test coverage

**2025 Enhancements:**
```bash
# Generate comprehensive coverage report
coverage run -m pytest
coverage report --show-missing
coverage html -d reports/coverage/html
coverage xml -o reports/coverage/coverage.xml

# Set minimum thresholds
coverage report --fail-under=80
```

---

### 2. **pytest-benchmark** (Performance Tracking)
**What it does:**
- Tracks performance over time
- Identifies performance regressions
- Helps maintain code performance

**Installation:**
```bash
pip install pytest-benchmark
```

**Usage:**
```python
# In test files
def test_function_performance(benchmark):
    result = benchmark(my_function)
    assert result is not None
```

---

## 🎯 Recommended Tool Stack for HomeIQ (NUC-Optimized)

### Essential Tools (Start Here) - Lightweight & Fast
1. **Ruff** - Ultra-fast Python linter (replaces flake8/pylint)
   - ⚡ 10-100x faster than alternatives
   - 💾 Minimal memory footprint
   - ✅ Already mentioned in project rules

2. **mypy** - Type checking for Python
   - 🎯 Catches bugs before runtime
   - 💾 Lightweight static analysis
   - ⚡ Fast incremental checking

3. **ESLint** (enhanced) - TypeScript/JavaScript linting
   - ✅ Already configured
   - 🔧 Just add complexity plugin

### Optional (If Needed) - Still Lightweight
4. **bandit** - Security scanning (run occasionally)
   - 🔒 Important but doesn't need to run every time
   - 💾 Low resource usage

5. **vulture** - Dead code detection (run occasionally)
   - 🧹 Helps clean up unused code
   - 💾 Very lightweight

### ❌ Skip These (Too Heavy for NUC)
- **SonarQube** - Requires Docker container, 2GB+ RAM (overkill for single home)
- **wily** - Trend tracking (nice-to-have, not essential)
- **CodeScene** - Behavioral analysis (enterprise-focused)
- **plato** - Heavy visualization (use simpler tools)

---

## 📋 Implementation Plan (Simplified for NUC)

### Phase 1: Essential Setup (1-2 hours)
1. Install Ruff (replaces flake8/pylint for speed)
2. Add mypy configuration (optional but recommended)
3. Enhance ESLint with complexity plugin (5 minutes)
4. Update existing quality scripts to use Ruff

### Phase 2: Optional Enhancements (As Needed)
1. Add bandit for occasional security scans
2. Add vulture for occasional dead code cleanup
3. Run existing radon complexity checks (already configured)

### ❌ Skip These Phases
- No need for SonarQube (too heavy for NUC)
- No need for trend tracking (single developer/small team)
- No need for complex CI/CD integration (unless you want it)
- Focus on practical, immediate value

---

## 🔧 Integration with Existing Scripts

### Update `scripts/analyze-code-quality.sh`

Add these sections:

```bash
# Ruff linting (fast alternative to pylint)
if command -v ruff &> /dev/null; then
    echo "Running Ruff..."
    ruff check services/ --output-format=json > reports/quality/ruff-report.json
    ruff check services/ > reports/quality/ruff-report.txt
fi

# mypy type checking
if command -v mypy &> /dev/null; then
    echo "Running mypy..."
    mypy services/ --html-report reports/quality/mypy-report || true
fi

# bandit security scanning
if command -v bandit &> /dev/null; then
    echo "Running bandit..."
    bandit -r services/ -f json -o reports/quality/bandit-report.json || true
fi

# vulture dead code detection
if command -v vulture &> /dev/null; then
    echo "Running vulture..."
    vulture services/ --min-confidence 80 > reports/quality/dead-code.txt || true
fi
```

---

## 📈 Quality Thresholds (2025 Best Practices)

### Python
- **Cyclomatic Complexity:** < 15 (warn), < 20 (error)
- **Maintainability Index:** > 65 (B grade)
- **Test Coverage:** > 80%
- **Type Coverage:** > 70% (mypy)
- **Code Duplication:** < 3%

### TypeScript/JavaScript
- **Cyclomatic Complexity:** < 15 (warn), < 20 (error)
- **Cognitive Complexity:** < 15 (SonarJS)
- **Max Lines per Function:** < 100
- **Max Nesting Depth:** < 4
- **Test Coverage:** > 70%

### Security
- **Bandit:** 0 high/critical issues
- **npm audit:** 0 high/critical vulnerabilities
- **Dependency vulnerabilities:** 0 unpatched

---

## 📚 Additional Resources

### 2025 Best Practices Documents
- [Python Enhancement Proposals (PEP)](https://peps.python.org/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/intro.html)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

### Tool Documentation
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [SonarQube Documentation](https://docs.sonarqube.org/)
- [ESLint Documentation](https://eslint.org/docs/latest/)

---

## 🎓 Training & Learning

### Code Quality Concepts
1. **Cyclomatic Complexity:** Measure of code complexity
2. **Maintainability Index:** Overall code maintainability score
3. **Technical Debt:** Cost of maintaining suboptimal code
4. **Code Smells:** Indicators of potential problems

### Refactoring Patterns
1. **Extract Method:** Break down large functions
2. **Extract Class:** Separate concerns
3. **Simplify Conditionals:** Reduce nesting
4. **Eliminate Duplication:** DRY principle

---

## ✅ Next Steps

1. **Review this document** with your team
2. **Prioritize tools** based on your needs
3. **Start with Tier 1 tools** (quick wins)
4. **Set up automated reporting** in CI/CD
5. **Establish quality gates** for PRs
6. **Track metrics over time** to measure improvement

---

## 📝 Notes

- All tools listed are **free and open-source**
- Tools are **analysis-only** - they don't modify your code logic
- Recommendations based on **2025 industry best practices**
- Tools can be integrated incrementally
- Focus on **actionable insights** over perfect scores

---

**Last Updated:** January 2025  
**Maintained by:** Development Team  
**Review Frequency:** Quarterly

