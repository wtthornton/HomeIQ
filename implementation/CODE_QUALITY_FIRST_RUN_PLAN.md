# Code Quality Tools - First Run Plan

**Date:** January 2025  
**Purpose:** Step-by-step guide for your first code quality analysis

## 🎯 Goal

Run your first comprehensive code quality analysis, understand the results, and create an action plan for improvements.

---

## 📋 Pre-Flight Checklist

Before starting, verify everything is ready:

- [x] Ruff installed (`python -m ruff --version`)
- [x] mypy installed (`python -m mypy --version`)
- [x] ESLint complexity plugin installed
- [x] Configuration files in place (`pyproject.toml`, `.eslintrc.cjs`)
- [x] Quality analysis script updated

**Status:** ✅ All tools ready!

---

## 🚀 Step-by-Step First Run

### Step 1: Quick Ruff Check (2 minutes)

**Purpose:** Get a quick overview of linting issues

```bash
# Run Ruff on all services
python -m ruff check services/ > reports/quality/first-run-ruff.txt 2>&1

# View results
cat reports/quality/first-run-ruff.txt
```

**What to expect:**
- Unused imports
- Line length violations
- Import sorting issues
- Code style issues

**Action:**
- Note the total number of issues
- Don't fix anything yet - just observe

---

### Step 2: Auto-Fix Safe Issues (5 minutes)

**Purpose:** Let Ruff fix issues that are safe to auto-fix

```bash
# Auto-fix safe issues (non-destructive)
python -m ruff check --fix services/

# See what was fixed
python -m ruff check services/ > reports/quality/after-auto-fix.txt 2>&1
```

**What will be fixed:**
- Unused imports (removed)
- Import sorting (reorganized)
- Some formatting issues

**What won't be fixed:**
- Line length (requires manual review)
- Logic issues
- Type errors

**Action:**
- Review the diff to see what changed
- Commit the auto-fixes if they look good

---

### Step 3: Type Checking with mypy (5-10 minutes)

**Purpose:** Find type-related issues

```bash
# Run mypy (this may take a few minutes first time)
python -m mypy services/ > reports/quality/first-run-mypy.txt 2>&1

# Count errors
Select-String -Path reports/quality/first-run-mypy.txt -Pattern "error:" | Measure-Object | Select-Object -ExpandProperty Count
```

**What to expect:**
- Many errors on first run (this is normal!)
- Missing type hints
- Type mismatches
- Import errors

**Action:**
- Don't panic - this is expected
- Note the error count
- We'll prioritize fixes later

**Tip:** If there are too many errors, you can start with one service:
```bash
python -m mypy services/data-api/src/ > reports/quality/mypy-data-api.txt 2>&1
```

---

### Step 4: ESLint Check (2 minutes)

**Purpose:** Check TypeScript/JavaScript code quality

```bash
cd services/health-dashboard
npm run lint > ../../reports/quality/first-run-eslint.txt 2>&1
cd ../..
```

**What to expect:**
- Complexity warnings
- Unused variables
- Type issues
- Code style issues

**Action:**
- Review the output
- Note any high-complexity functions

---

### Step 5: Complexity Analysis (3 minutes)

**Purpose:** Find overly complex code

```bash
# Run existing complexity analysis
python -m radon cc services/ -n C -s > reports/quality/first-run-complexity.txt 2>&1

# Or if radon not installed
pip install radon
python -m radon cc services/ -n C -s > reports/quality/first-run-complexity.txt 2>&1
```

**What to look for:**
- Functions with complexity > 15 (C rating)
- Functions with complexity > 20 (D rating)
- Functions with complexity > 50 (F rating - urgent!)

**Action:**
- List the top 10 most complex functions
- These are candidates for refactoring

---

### Step 6: Full Analysis Script (10-15 minutes)

**Purpose:** Comprehensive analysis with all tools

```bash
# Run the full analysis script
./scripts/analyze-code-quality.sh

# Or on Windows PowerShell
bash scripts/analyze-code-quality.sh
```

**What this does:**
- Runs Ruff linting
- Runs mypy type checking
- Runs ESLint
- Runs complexity analysis (radon)
- Runs duplication detection (jscpd)
- Generates summary report

**Output location:**
- `reports/quality/` - All reports
- `reports/quality/SUMMARY.md` - Summary report

**Action:**
- Review the summary report
- Note key metrics

---

## 📊 Understanding Your Results

### Metrics to Track

Create a baseline document with these metrics:

```markdown
# Code Quality Baseline - First Run

**Date:** [Today's Date]

## Ruff Linting
- Total issues found: ___
- Issues after auto-fix: ___
- Remaining issues: ___

## mypy Type Checking
- Total errors: ___
- Services with errors: ___
- Most problematic service: ___

## ESLint
- Total warnings: ___
- Complexity warnings: ___
- High-complexity functions: ___

## Complexity Analysis
- Functions with complexity > 15: ___
- Functions with complexity > 20: ___
- Functions with complexity > 50: ___

## Priority Actions
1. [Top priority issue]
2. [Second priority]
3. [Third priority]
```

---

## 🎯 Creating Your Action Plan

### Priority 1: Quick Wins (Do First)

**Time:** 30 minutes

1. **Auto-fix Ruff issues**
   ```bash
   python -m ruff check --fix services/
   ```

2. **Fix obvious unused imports**
   - Review Ruff output
   - Remove clearly unused imports

3. **Fix line length issues**
   - Break long lines
   - Use Ruff's suggestions

**Expected impact:** 20-40% reduction in issues

---

### Priority 2: Type Safety (Do Next)

**Time:** 1-2 hours per service

1. **Start with one service**
   - Pick the smallest or most critical service
   - Fix mypy errors one by one

2. **Add type hints gradually**
   - Start with function parameters
   - Add return types
   - Fix type mismatches

3. **Example workflow:**
   ```bash
   # Focus on one service
   python -m mypy services/data-api/src/
   
   # Fix errors one at a time
   # Test after each fix
   ```

**Expected impact:** Better code reliability, fewer runtime errors

---

### Priority 3: Complexity Reduction (Ongoing)

**Time:** 30 minutes per complex function

1. **Identify top 5 most complex functions**
   - From complexity analysis
   - Focus on D and F ratings first

2. **Refactoring strategies:**
   - Extract methods
   - Break into smaller functions
   - Simplify conditionals
   - Use early returns

3. **Test after each refactor**
   - Ensure functionality unchanged
   - Run unit tests

**Expected impact:** More maintainable code

---

### Priority 4: ESLint Issues (As Needed)

**Time:** 15-30 minutes

1. **Fix complexity warnings**
   - Functions with complexity > 15
   - Refactor if needed

2. **Fix unused variables**
   - Remove or use them
   - Prefix with `_` if intentionally unused

**Expected impact:** Cleaner TypeScript code

---

## 📈 Success Metrics

Track these over time:

### Week 1 Goals
- [ ] Ruff issues reduced by 50%
- [ ] Auto-fixes applied and committed
- [ ] Baseline metrics documented

### Month 1 Goals
- [ ] One service fully type-checked (mypy clean)
- [ ] Top 5 complex functions refactored
- [ ] ESLint warnings reduced by 30%

### Quarter 1 Goals
- [ ] All services type-checked
- [ ] No functions with complexity > 20
- [ ] ESLint complexity warnings < 10

---

## 🛠️ Troubleshooting

### Too Many mypy Errors?

**Solution:** Start lenient, tighten over time
```bash
# Use ignore-missing-imports for now
python -m mypy services/ --ignore-missing-imports

# Fix one service at a time
python -m mypy services/data-api/src/
```

### Ruff Too Strict?

**Solution:** Adjust configuration in `pyproject.toml`
```toml
[tool.ruff.lint]
ignore = [
    "E501",  # Line too long (if needed)
    # Add more as needed
]
```

### ESLint Complexity Too Strict?

**Solution:** Adjust threshold in `.eslintrc.cjs`
```javascript
'complexity': ['warn', { max: 20 }],  // Increase from 15 to 20
```

---

## 📝 First Run Checklist

Use this checklist during your first run:

- [ ] Step 1: Quick Ruff check completed
- [ ] Step 2: Auto-fix applied
- [ ] Step 3: mypy run completed
- [ ] Step 4: ESLint check completed
- [ ] Step 5: Complexity analysis completed
- [ ] Step 6: Full analysis script run
- [ ] Baseline metrics documented
- [ ] Action plan created
- [ ] Priority 1 items identified

---

## 🎯 Recommended First Run Workflow

### Option A: Quick Overview (15 minutes)

1. Run Ruff auto-fix
2. Run full analysis script
3. Review summary report
4. Document baseline

### Option B: Comprehensive (1 hour)

1. Run all steps above
2. Create detailed baseline
3. Prioritize top 10 issues
4. Create action plan
5. Fix Priority 1 items

### Option C: Deep Dive (2-3 hours)

1. Run all steps
2. Analyze each service individually
3. Create service-specific action plans
4. Start fixing Priority 1 and 2 items
5. Set up weekly review process

---

## 📚 Next Steps After First Run

1. **Document your baseline** - Save metrics for comparison
2. **Create issues/tickets** - Track improvements
3. **Set up weekly reviews** - Run analysis weekly
4. **Integrate into workflow** - Use before commits
5. **Celebrate progress** - Track improvements over time

---

## 💡 Pro Tips

1. **Don't try to fix everything at once** - Focus on one priority at a time
2. **Auto-fix first** - Let tools fix what they can
3. **Start small** - One service, one function at a time
4. **Test after fixes** - Ensure nothing breaks
5. **Track progress** - Compare metrics over time
6. **Be patient** - Code quality improvement is a journey

---

## 🎉 Ready to Start?

Run this command to begin:

```bash
# Quick start - auto-fix and full analysis
python -m ruff check --fix services/
./scripts/analyze-code-quality.sh
cat reports/quality/SUMMARY.md
```

**Good luck with your first run!** 🚀

