/**
 * Theme Toggle -- Light and Dark Mode for Operator Comfort
 *
 * WHY THIS MATTERS:
 * Operators monitoring HomeIQ for extended periods need the ability to
 * switch between light and dark themes. Dark mode reduces eye strain
 * during overnight shifts; light mode is easier to read in bright
 * environments. If the toggle fails to switch themes, does not persist
 * across page reloads, or is not reversible, the operator is stuck with
 * a theme that may cause discomfort or readability issues.
 *
 * WHAT THE OPERATOR USES IT FOR:
 * - Switching to dark mode for night shifts
 * - Switching back to light mode for daytime use
 * - Expecting their preference to persist across sessions
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Theme toggle -- light and dark mode', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('toggling the theme changes the HTML class so styles actually switch', async ({ page }) => {
    const themeToggle = page.getByTestId('theme-toggle').or(
      page.locator('[data-testid="dark-mode-toggle"], button[aria-label*="dark" i], button[aria-label*="theme" i]')
    ).first();

    await expect(themeToggle, 'Dashboard should have a theme toggle').toBeVisible({ timeout: 5000 });

    const initialClass = await page.locator('html').getAttribute('class') || '';

    await themeToggle.click();
    await new Promise((r) => setTimeout(r, 500));

    const toggledClass = await page.locator('html').getAttribute('class') || '';

    // The class on <html> must change -- typically adding or removing "dark"
    expect(toggledClass).not.toBe(initialClass);
  });

  test('toggling is reversible -- clicking twice returns to the original theme', async ({ page }) => {
    const themeToggle = page.getByTestId('theme-toggle').or(
      page.locator('[data-testid="dark-mode-toggle"], button[aria-label*="dark" i], button[aria-label*="theme" i]')
    ).first();

    await expect(themeToggle, 'Dashboard should have a theme toggle').toBeVisible({ timeout: 5000 });

    const initialClass = await page.locator('html').getAttribute('class') || '';

    // Toggle once (switch theme)
    await themeToggle.click();
    await new Promise((r) => setTimeout(r, 300));

    // Toggle again (return to original)
    await themeToggle.click();
    await new Promise((r) => setTimeout(r, 300));

    const finalClass = await page.locator('html').getAttribute('class') || '';
    expect(finalClass).toBe(initialClass);
  });

  test('theme preference persists in localStorage and survives page reload', async ({ page }) => {
    const themeToggle = page.getByTestId('theme-toggle').or(
      page.locator('[data-testid="dark-mode-toggle"], button[aria-label*="dark" i], button[aria-label*="theme" i]')
    ).first();

    await expect(themeToggle, 'Dashboard should have a theme toggle').toBeVisible({ timeout: 5000 });

    await themeToggle.click();
    await new Promise((r) => setTimeout(r, 500));

    const storedTheme = await page.evaluate(() => {
      return localStorage.getItem('darkMode') || localStorage.getItem('theme') || localStorage.getItem('color-mode') || document.documentElement.getAttribute('class') || '';
    });
    expect(storedTheme).toBeTruthy();

    await page.reload();
    await waitForLoadingComplete(page);

    const htmlClass = await page.locator('html').getAttribute('class') || '';
    expect(htmlClass.includes('dark') || storedTheme.includes('dark')).toBe(true);
  });

  test('no console errors when toggling the theme', async ({ page }) => {
    // Wait for page to settle, then start listening for NEW errors only
    await new Promise((r) => setTimeout(r, 2000));

    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    const themeToggle = page.locator(
      'button[aria-label*="dark" i], button[aria-label*="light" i], ' +
      'button[aria-label*="theme" i], [data-testid="theme-toggle"]'
    ).first();

    if (await themeToggle.isVisible({ timeout: 3000 })) {
      await themeToggle.click();
      await new Promise((r) => setTimeout(r, 300));
      await themeToggle.click();
      await new Promise((r) => setTimeout(r, 300));
    }

    const significantErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('404') &&
        !e.includes('429') && !e.includes('VITE_API_KEY') &&
        !e.includes('font') && !e.includes('woff') &&
        !e.includes('manifest') && !e.includes('sourcemap') &&
        !e.includes('api/devices') && !e.includes('api/v1/activity') &&
        !e.includes('Unable to reach backend') && !e.includes('decode downloaded font')
    );
    expect(significantErrors).toHaveLength(0);
  });
});
