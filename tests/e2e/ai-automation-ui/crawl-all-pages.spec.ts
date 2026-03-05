/**
 * Crawl All Pages Test - "Do all pages load without errors?"
 *
 * WHY THIS TEST EXISTS:
 * This is a broad smoke test that visits every route in the AI Automation UI
 * and collects console errors, network failures, and visible error messages.
 * It serves as a safety net to catch regressions that page-specific tests
 * might miss -- broken imports, API connection failures, or rendering crashes.
 *
 * WHAT THE USER NEEDS:
 * - Confidence that every page in the app loads without crashing
 * - Visibility into which pages have console errors or failed API calls
 * - A severity-ranked report of all issues found across the app
 *
 * WHAT OLD TESTS MISSED:
 * - The original was well-structured; this rewrite preserves the crawl approach
 *   while adding clearer intent documentation and tidying up the output path
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3001';

const ROUTES = [
  { path: '/', name: 'Ideas (Home)' },
  { path: '/chat', name: 'Chat' },
  { path: '/explore', name: 'Explore' },
  { path: '/insights', name: 'Insights' },
  { path: '/automations', name: 'Automations' },
  { path: '/settings', name: 'Settings' },
  { path: '/name-enhancement', name: 'Name Enhancement' },
  { path: '/?source=blueprints', name: 'Ideas (Blueprints tab)' },
  { path: '/?source=context', name: 'Ideas (Context tab)' },
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

test.describe('Crawl All Pages - Do all pages load without errors?', () => {
  test('visit all routes and collect issues', async ({ page }) => {
    const issues: Issue[] = [];
    const seenKeys = new Set<string>();

    function addIssue(issue: Omit<Issue, 'severity'> & { severity?: Issue['severity'] }) {
      const sev = issue.severity ?? severityForMessage(issue.message);
      const key = `${issue.route}|${issue.category}|${issue.message}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({ ...issue, severity: sev });
      }
    }

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
        addIssue({ route: routePath, category: 'network_fail', message: `Navigation failed or timed out: ${url}` });
      }

      if (navOk) {
        await page.waitForTimeout(1500);

        // Collect console errors and warnings
        for (const { type, text } of consoleMessages) {
          const category = type === 'error' ? 'console_error' : 'console_warn';
          addIssue({
            route: routePath,
            category,
            message: text.slice(0, 200),
            severity: type === 'error' ? 'high' : 'medium',
          });
        }

        // Collect network failures
        for (const { url: failUrl, status } of networkFailures) {
          addIssue({
            route: routePath,
            category: 'network_fail',
            message: status ? `HTTP ${status}: ${failUrl.slice(0, 120)}` : `Request failed: ${failUrl.slice(0, 120)}`,
            severity: status && status >= 500 ? 'critical' : 'high',
          });
        }

        // Check for visible error messages in the DOM
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
            // Ignore selector issues
          }
        }

        // Check for critical app-level errors
        const bodyText = await page.locator('body').textContent();
        if (bodyText?.includes('VITE_API_KEY is required')) {
          addIssue({
            route: routePath,
            category: 'console_error',
            message: 'VITE_API_KEY is required in production mode - app may crash',
            severity: 'critical',
          });
        }
      }
    }

    // Write issues report
    const outDir = path.join(process.cwd(), 'implementation', 'analysis', 'browser-review');
    const outPath = path.join(outDir, '3001-CRAWL-ISSUES.md');

    const bySeverity = (a: Issue, b: Issue) => {
      const order = { critical: 0, high: 1, medium: 2, low: 3 };
      return order[a.severity] - order[b.severity];
    };

    const uniqueIssues = issues.sort(bySeverity);

    const md = [
      '# Port 3001 (AI Automation UI) -- Crawl Issues',
      '',
      `**Source:** Playwright crawl of all routes`,
      `**Generated:** ${new Date().toISOString().split('T')[0]}`,
      `**Base URL:** ${BASE_URL}`,
      '',
      '---',
      '',
      '## Summary',
      '',
      '| Severity | Count |',
      '|----------|-------|',
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

    for (const s of ['critical', 'high', 'medium', 'low'] as const) {
      const list = uniqueIssues.filter((i) => i.severity === s);
      if (list.length === 0) continue;
      md.push(`### ${s.charAt(0).toUpperCase() + s.slice(1)}`, '');
      md.push('| # | Route | Category | Message |');
      md.push('|---|-------|----------|---------|');
      list.forEach((issue, idx) => {
        md.push(
          `| ${idx + 1} | \`${issue.route}\` | ${issue.category} | ${issue.message.replace(/\|/g, '\\|').replace(/\n/g, ' ')} |`
        );
      });
      md.push('');
    }

    try {
      fs.mkdirSync(outDir, { recursive: true });
      fs.writeFileSync(outPath, md.join('\n'));
    } catch {
      // Fallback: write to stdout
      process.stdout.write('\n--- CRAWL ISSUES ---\n' + md.join('\n'));
    }
  });
});
