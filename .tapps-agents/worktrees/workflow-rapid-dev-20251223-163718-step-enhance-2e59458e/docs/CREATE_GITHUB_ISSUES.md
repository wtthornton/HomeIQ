# How to Create GitHub Issues for Test Coverage

Since the GitHub CLI is not available in this environment, here are **3 easy ways** to create the 13 GitHub issues:

---

## Method 1: Direct GitHub Links (Fastest) ⭐

Click these links to create each issue with pre-filled content:

### P0 - Critical Issues

1. **[Create Issue #1: AI Automation UI Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP0%5D%20Add%20AI%20Automation%20UI%20Test%20Suite&labels=testing,P0,enhancement)**
   - Copy content from `.github/issue-templates/issue-01-ai-automation-ui-tests.md`

2. **[Create Issue #2: OpenVINO ML Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP0%5D%20Add%20OpenVINO%20Service%20ML%20Tests&labels=testing,P0,enhancement,AI)**
   - Copy from `GITHUB_ISSUES.md` Issue #2 section

3. **[Create Issue #3: ML Service Algorithm Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP0%5D%20Add%20ML%20Service%20Algorithm%20Tests&labels=testing,P0,enhancement,AI)**
   - Copy from `GITHUB_ISSUES.md` Issue #3 section

4. **[Create Issue #4: AI Core Service Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP0%5D%20Add%20AI%20Core%20Service%20Orchestration%20Tests&labels=testing,P0,enhancement,AI)**
   - Copy from `GITHUB_ISSUES.md` Issue #4 section

5. **[Create Issue #5: AI Code Executor Security Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP0%5D%20Add%20AI%20Code%20Executor%20Security%20Tests%20%28CRITICAL%29&labels=testing,P0,security,enhancement)**
   - Copy from `GITHUB_ISSUES.md` Issue #5 section

### P1 - High Priority Issues

6. **[Create Issue #6: Integration Tests (Testcontainers)](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP1%5D%20Add%20Integration%20Test%20Suite%20with%20Testcontainers&labels=testing,P1,enhancement)**
7. **[Create Issue #7: Performance Test Suite](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP1%5D%20Add%20Performance%20Test%20Suite&labels=testing,P1,enhancement)**
8. **[Create Issue #8: Database Migration Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP1%5D%20Add%20Database%20Migration%20Tests&labels=testing,P1,enhancement)**
9. **[Create Issue #9: Health Dashboard Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP1%5D%20Add%20Health%20Dashboard%20Frontend%20Tests&labels=testing,P1,enhancement)**

### P2 - Medium Priority Issues

10. **[Create Issue #10: Log Aggregator Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP2%5D%20Add%20Log%20Aggregator%20Tests&labels=testing,P2,enhancement)**
11. **[Create Issue #11: Disaster Recovery Tests](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP2%5D%20Add%20Disaster%20Recovery%20Tests&labels=testing,P2,enhancement)**
12. **[Create Issue #12: CI/CD Test Pipeline](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP2%5D%20Setup%20CI/CD%20Test%20Pipeline&labels=testing,P2,enhancement,ci/cd)**
13. **[Create Issue #13: Mutation Testing Baseline](https://github.com/wtthornton/HomeIQ/issues/new?title=%5BP2%5D%20Add%20Mutation%20Testing%20Baseline&labels=testing,P2,enhancement)**

---

## Method 2: Copy-Paste from GITHUB_ISSUES.md

1. Open https://github.com/wtthornton/HomeIQ/issues/new
2. Click "New Issue"
3. Copy the content for each issue from `GITHUB_ISSUES.md`
4. Paste into the issue description
5. Add labels manually: `testing`, `P0`/`P1`/`P2`, `enhancement`

---

## Method 3: Use GitHub CLI (If Available Locally)

If you have `gh` CLI installed on your local machine:

```bash
# Clone the repo locally
git clone https://github.com/wtthornton/HomeIQ.git
cd HomeIQ

# Pull latest changes
git pull origin claude/testing-mi0r3hr5boluh9i6-01WmLFKA4GJKucDLtsRzGqNS

# Run this script to create all issues
chmod +x create-issues.sh
./create-issues.sh
```

See `create-issues.sh` (created below) for the complete script.

---

## Quick Start (Recommended Workflow)

### Step 1: Create P0 Issues First (Most Critical)
Start with these 5 critical issues:
1. AI Automation UI Tests
2. OpenVINO ML Tests
3. ML Service Algorithm Tests
4. AI Core Service Tests
5. AI Code Executor Security Tests

### Step 2: Create P1 Issues (High Priority)
4 high-priority issues for next sprint

### Step 3: Create P2 Issues (Medium Priority)
4 medium-priority issues for future sprints

---

## Issue Content Location

All issue content is available in:
- **`GITHUB_ISSUES.md`** - Complete documentation with all 13 issues
- **`.github/issue-templates/`** - Individual markdown files (being created)

---

## Estimated Time

- **Method 1 (Links):** ~15-20 minutes for all 13 issues
- **Method 2 (Copy-Paste):** ~20-30 minutes for all 13 issues
- **Method 3 (CLI Script):** ~2 minutes if gh CLI available

---

**Status:** Ready to create issues
**Next Step:** Click the links above or use Method 2/3
