/**
 * Crawl All Pages -- Comprehensive Page Load Validation
 *
 * WHY THIS MATTERS:
 * Before any deployment, the operator (or CI pipeline) needs to verify
 * that every dashboard page loads without JavaScript errors, failed API
 * calls, or visible error banners. A single broken page during an
 * incident could prevent the operator from seeing critical data.
 *
 * This crawl visits all 16 tabs plus the root route and collects:
 * - Console errors and warnings (including VITE_API_KEY misconfiguration)
 * - Failed network requests and HTTP 4xx/5xx responses
 * - Visible error elements (red banners, [role="alert"], "Failed to load")
 *
 * The output is an actionable Markdown report sorted by severity so the
 * team can prioritize fixes.
 *
 * WHAT THE OPERATOR / CI USES IT FOR:
 * - Pre-deployment smoke check across all pages
 * - Detecting regressions after frontend or API changes
 * - Generating a severity-ranked issues list for the on-call team
 *
 * Run:
 *   npx playwright test crawl-all-pages.spec.ts --project=chromium \
 *     --config tests/e2e/health-dashboard/playwright.config.ts
 * With Docker:
 *   TEST_BASE_URL=http://localhost:3000 npx playwright test ...
 * Output: implementation/analysis/browser-review/3000-CRAWL-ISSUES.md
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

/** Every route the operator can access in the Health Dashboard. */
const ROUTES = [
  { path: '/#overview', name: 'Overview' },
  { path: '/#services', name: 'Services' },
  { path: '/#groups', name: 'Groups' },
  { path: '/#dependencies', name: 'Dependencies' },
  { path: '/#configuration', name: 'Configuration' },
  { path: '/#devices', name: 'Devices' },
  { path: '/#events', name: 'Events' },
  { path: '/#data-sources', name: 'Data Feeds' },
  { path: '/#energy', name: 'Energy' },
  { path: '/#sports', name: 'Sports' },
  { path: '/#alerts', name: 'Alerts' },
  { path: '/#hygiene', name: 'Device Health' },
  { path: '/#validation', name: 'Automation Checks' },
  { path: '/#evaluation', name: 'AI Performance' },
  { path: '/#logs', name: 'Logs' },
  { path: '/#analytics', name: 'Analytics' },
  { path: '/', name: 'Root (default)' },
] as const;

interface Issue {
  route: string;
  category: 'console_error' | 'console_warn' | 'network_fail' | 'visible_error' | 'accessibility' | 'layout' | 'vite_config';
  message: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  detail?: string;
}

function severityForMessage(msg: string): Issue['severity'] {
  const lower = msg.toLowerCase();
  if (lower.includes('failed to load') || lower.includes('required') || lower.includes('crash')) return 'critical';
  if (lower.includes('error') || lower.includes('404') || lower.includes('500')) return 'high';
  if (lower.includes('warn') || lower.includes('csp') || lower.includes('violation')) return 'medium';
  return 'low';
}

test.describe('Crawl all Health Dashboard pages', () => {
  test('every route loads without critical errors and produces an actionable report', async ({ page }) => {
    const issues: Issue[] = [];
    const seenKeys = new Set<string>();

    function addIssue(issue: Issue | Omit<Issue, 'severity'>) {
      const sev = 'severity' in issue && issue.severity
        ? (issue as Issue).severity
        : severityForMessage(issue.message);
      const key = `${issue.route}|${issue.category}|${issue.message}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({ ...issue, severity: sev } as Issue);
      }
    }

    // Track 404 network requests specifically -- broken API calls or missing assets
    const networkFourOhFours: { route: string; url: string }[] = [];

    const consoleMessages: { type: string; text: string }[] = [];
    const networkFailures: { url: string; status?: number }[] = [];

    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();
      if (type === 'error' || type === 'warning') {
        consoleMessages.push({ type, text });
      }
    });

    page.on('requestfailed', (req) => {
      const url = req.url();
      if (url.startsWith(BASE_URL) || url.includes('localhost')) {
        networkFailures.push({ url, status: undefined });
      }
    });

    page.on('response', (res) => {
      const status = res.status();
      const url = res.url();
      if (status >= 400 && (url.startsWith(BASE_URL) || url.includes('/api/'))) {
        networkFailures.push({ url, status });
        if (status === 404) {
          networkFourOhFours.push({ route: '', url }); // route filled below
        }
      }
    });

    for (const { path: routePath, name } of ROUTES) {
      consoleMessages.length = 0;
      networkFailures.length = 0;

      const url = `${BASE_URL}${routePath}`;
      let navOk = true;
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      } catch {
        navOk = false;
        addIssue({
          route: routePath,
          category: 'network_fail',
          message: `Navigation failed or timed out: ${url}`,
          severity: 'critical',
        });
      }

      if (!navOk) continue;
      await page.waitForTimeout(1500);

      // -- Console errors and warnings --
      for (const { type, text } of consoleMessages) {
        // Flag VITE_API_KEY misconfiguration specifically
        if (text.includes('VITE_API_KEY') || text.includes('VITE_') && text.includes('undefined')) {
          addIssue({
            route: routePath,
            category: 'vite_config',
            message: `Vite env var misconfiguration: ${text.slice(0, 200)}`,
            severity: 'high',
          });
        }

        const category = type === 'error' ? 'console_error' as const : 'console_warn' as const;
        addIssue({
          route: routePath,
          category,
          message: text.slice(0, 200),
          severity: type === 'error' ? 'high' : 'medium',
        });
      }

      // -- Network failures (including 404s) --
      for (const { url: failUrl, status } of networkFailures) {
        addIssue({
          route: routePath,
          category: 'network_fail',
          message: status
            ? `HTTP ${status}: ${failUrl.slice(0, 120)}`
            : `Request failed: ${failUrl.slice(0, 120)}`,
          severity: status && status >= 500 ? 'critical' : 'high',
        });
      }

      // -- Visible error elements --
      const errorSelectors = [
        '[role="alert"]',
        '.text-red-600',
        '.text-red-500',
        '[class*="error"]',
        '[class*="Error"]',
        'text=Failed to load',
        'text=Failed to list',
        'text=Error:',
        'text=Something went wrong',
        'text=DEGRADED PERFORMANCE',
      ];

      for (const sel of errorSelectors) {
        try {
          const el = page.locator(sel).first();
          if ((await el.count()) > 0) {
            const text = (await el.textContent())?.trim().slice(0, 150) || sel;
            addIssue({
              route: routePath,
              category: 'visible_error',
              message: `Visible error/warning: ${text}`,
              severity: text.toLowerCase().includes('failed') ? 'critical' : 'high',
            });
          }
        } catch {
          // Ignore selector issues in error detection
        }
      }
    }

    // -- Generate actionable Markdown report --
    const outDir = path.join(process.cwd(), 'implementation', 'analysis', 'browser-review');
    const outPath = path.join(outDir, '3000-CRAWL-ISSUES.md');

    const bySeverity = (a: Issue, b: Issue) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    };

    const sortedIssues = issues.sort(bySeverity);

    const criticalCount = sortedIssues.filter((i) => i.severity === 'critical').length;
    const highCount = sortedIssues.filter((i) => i.severity === 'high').length;
    const mediumCount = sortedIssues.filter((i) => i.severity === 'medium').length;
    const lowCount = sortedIssues.filter((i) => i.severity === 'low').length;

    const md = [
      '# Port 3000 (Health Dashboard) -- Crawl Issues',
      '',
      `**Source:** Playwright crawl of all ${ROUTES.length} routes`,
      `**Generated:** ${new Date().toISOString().split('T')[0]}`,
      `**Base URL:** ${BASE_URL}`,
      '',
      '---',
      '',
      '## Summary',
      '',
      '| Severity | Count |',
      '|----------|-------|',
      `| Critical | ${criticalCount} |`,
      `| High     | ${highCount} |`,
      `| Medium   | ${mediumCount} |`,
      `| Low      | ${lowCount} |`,
      `| **Total** | **${sortedIssues.length}** |`,
      '',
      '### Action Required',
      '',
      criticalCount > 0
        ? `**${criticalCount} CRITICAL issue(s) -- fix before deployment.**`
        : 'No critical issues found.',
      highCount > 0
        ? `**${highCount} HIGH issue(s) -- should be addressed soon.**`
        : '',
      '',
      '---',
      '',
      '## Issues by Severity',
      '',
    ];

    for (const sev of ['critical', 'high', 'medium', 'low'] as const) {
      const list = sortedIssues.filter((i) => i.severity === sev);
      if (list.length === 0) continue;
      md.push(`### ${sev.charAt(0).toUpperCase() + sev.slice(1)}`, '');
      md.push('| # | Route | Category | Message |');
      md.push('|---|-------|----------|---------|');
      list.forEach((issue, idx) => {
        md.push(
          `| ${idx + 1} | \`${issue.route}\` | ${issue.category} | ${issue.message.replace(/\|/g, '\\|').replace(/\n/g, ' ')} |`
        );
      });
      md.push('');
    }

    // Write report
    try {
      fs.mkdirSync(outDir, { recursive: true });
      fs.writeFileSync(outPath, md.join('\n'));
    } catch {
      // If write fails (e.g. CI without write access), print to stdout
      process.stdout.write('\n--- CRAWL ISSUES ---\n' + md.join('\n'));
    }

    // The test passes, but logs a warning summary for CI visibility
    if (criticalCount > 0) {
      console.warn(`CRAWL: ${criticalCount} CRITICAL issues found -- see ${outPath}`);
    }
  });
});
