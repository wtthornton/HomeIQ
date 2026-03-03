/**
 * Playwright crawl: visit all Health Dashboard pages and collect issues.
 * Run: npx playwright test crawl-all-pages.spec.ts --project=chromium --config tests/e2e/health-dashboard/playwright.config.ts
 * With Docker: TEST_BASE_URL=http://localhost:3000 npx playwright test ...
 * Output: implementation/analysis/browser-review/3000-CRAWL-ISSUES.md
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3000';

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
];

interface Issue {
  route: string;
  category: 'console_error' | 'console_warn' | 'network_fail' | 'visible_error' | 'accessibility' | 'layout';
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
  test('visit all routes and collect issues', async ({ page }) => {
    const issues: Issue[] = [];
    const seenKeys = new Set<string>();

    function addIssue(issue: Omit<Issue, 'severity'>) {
      const sev = 'severity' in issue ? (issue as Issue).severity : severityForMessage(issue.message);
      const key = `${issue.route}|${issue.category}|${issue.message}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({ ...issue, severity: sev });
      }
    }

    const consoleErrors: { type: string; text: string }[] = [];
    const networkFailures: { url: string; status?: number }[] = [];

    page.on('console', (msg) => {
      const type = msg.type();
      const text = msg.text();
      if (type === 'error') consoleErrors.push({ type, text });
      if (type === 'warning') consoleErrors.push({ type, text });
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
      }
    });

    for (const { path: routePath, name } of ROUTES) {
      consoleErrors.length = 0;
      networkFailures.length = 0;

      const url = `${BASE_URL}${routePath}`;
      let navOk = true;
      try {
        await page.goto(url, { waitUntil: 'networkidle', timeout: 15000 });
      } catch {
        navOk = false;
        addIssue({ route: routePath, category: 'network_fail', message: `Navigation failed or timed out: ${url}` });
      }

      if (navOk) {
        await page.waitForTimeout(1500);

        for (const { type, text } of consoleErrors) {
          const category = type === 'error' ? 'console_error' : 'console_warn';
          addIssue({
            route: routePath,
            category,
            message: text.slice(0, 200),
            severity: type === 'error' ? 'high' : 'medium',
          });
        }

        for (const { url: failUrl, status } of networkFailures) {
          addIssue({
            route: routePath,
            category: 'network_fail',
            message: status ? `HTTP ${status}: ${failUrl.slice(0, 120)}` : `Request failed: ${failUrl.slice(0, 120)}`,
            severity: status && status >= 500 ? 'critical' : 'high',
          });
        }

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
            // ignore selector issues
          }
        }

        // Note: "Loading…" in Overview KPIs is documented in 3000-overview.md
      }
    }

    const outDir = path.join(process.cwd(), 'implementation', 'analysis', 'browser-review');
    const outPath = path.join(outDir, '3000-CRAWL-ISSUES.md');

    const bySeverity = (a: Issue, b: Issue) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    };

    const uniqueIssues = issues.sort(bySeverity);

    const md = [
      '# Port 3000 (Health Dashboard) – Crawl Issues',
      '',
      `**Source:** Playwright crawl of all routes  \n**Generated:** ${new Date().toISOString().split('T')[0]}`,
      `**Base URL:** ${BASE_URL}`,
      '',
      '---',
      '',
      '## Summary',
      '',
      `| Severity | Count |`,
      `|----------|-------|`,
      `| Critical | ${uniqueIssues.filter((i) => i.severity === 'critical').length} |`,
      `| High     | ${uniqueIssues.filter((i) => i.severity === 'high').length} |`,
      `| Medium   | ${uniqueIssues.filter((i) => i.severity === 'medium').length} |`,
      `| Low      | ${uniqueIssues.filter((i) => i.severity === 'low').length} |`,
      `| **Total** | **${uniqueIssues.length}** |`,
      '',
      '---',
      '',
      '## Issues',
      '',
    ];

    for (const s of ['critical', 'high', 'medium', 'low']) {
      const list = uniqueIssues.filter((i) => i.severity === s);
      if (list.length === 0) continue;
      md.push(`### ${s.charAt(0).toUpperCase() + s.slice(1)}`, '');
      md.push(`| # | Route | Category | Message |`);
      md.push(`|---|-------|----------|---------|`);
      list.forEach((issue, idx) => {
        md.push(`| ${idx + 1} | \`${issue.route}\` | ${issue.category} | ${issue.message.replace(/\|/g, '\\|').replace(/\n/g, ' ')} |`);
      });
      md.push('');
    }

    try {
      fs.mkdirSync(outDir, { recursive: true });
      fs.writeFileSync(outPath, md.join('\n'));
    } catch (e) {
      process.stdout.write('\n--- CRAWL ISSUES ---\n' + md.join('\n'));
    }
  });
});
