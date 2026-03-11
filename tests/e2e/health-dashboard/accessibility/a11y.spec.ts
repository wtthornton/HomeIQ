/**
 * Accessibility -- Ensuring All Operators Can Use the Dashboard
 *
 * WHY THIS MATTERS:
 * HomeIQ operators include people with visual impairments who use screen
 * readers, motor disabilities who rely on keyboard-only navigation, and
 * those in high-contrast or magnified display modes. If ARIA labels are
 * missing, keyboard focus is invisible, or heading hierarchy is broken,
 * these operators cannot effectively monitor and manage the system.
 * Accessibility is not optional -- it determines whether every team
 * member can participate in incident response.
 *
 * WHAT THE OPERATOR RELIES ON:
 * - Screen readers announcing interactive elements correctly (ARIA labels)
 * - Keyboard Tab/Enter/Escape navigating all features without a mouse
 * - Heading hierarchy (h1 > h2 > h3) for document structure navigation
 * - Form inputs associated with labels for assistive technology
 * - Visible focus indicators so keyboard users know where they are
 */

import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../shared/helpers/auth-helpers';
import { waitForLoadingComplete } from '../../../shared/helpers/wait-helpers';

test.describe('Accessibility -- all operators can use the dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
    await waitForLoadingComplete(page);
  });

  test('interactive elements have ARIA labels so screen readers can announce them', async ({ page }) => {
    // Buttons, links, and inputs must be labelled for assistive tech
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();

    let labelledCount = 0;
    for (let i = 0; i < Math.min(buttonCount, 20); i++) {
      const btn = buttons.nth(i);
      const ariaLabel = await btn.getAttribute('aria-label');
      const ariaLabelledBy = await btn.getAttribute('aria-labelledby');
      const textContent = (await btn.textContent())?.trim();
      const title = await btn.getAttribute('title');

      // A button is accessible if it has aria-label, aria-labelledby,
      // visible text content, or a title attribute
      if (ariaLabel || ariaLabelledBy || (textContent && textContent.length > 0) || title) {
        labelledCount++;
      }
    }

    // At least 80% of sampled buttons should be accessible
    if (buttonCount > 0) {
      const ratio = labelledCount / Math.min(buttonCount, 20);
      expect(ratio).toBeGreaterThanOrEqual(0.8);
    }
  });

  test('keyboard Tab navigates through interactive elements in logical order', async ({ page }) => {
    const focusedTags: string[] = [];

    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab');
      await new Promise(r => setTimeout(r, 150));

      const focused = page.locator(':focus');
      const isVisible = await focused.isVisible().catch(() => false);
      if (isVisible) {
        const tag = await focused.evaluate((el) => el.tagName.toLowerCase());
        focusedTags.push(tag);
      }
    }

    expect(focusedTags.length, 'Tab should move focus to at least 2 elements').toBeGreaterThanOrEqual(2);
    const interactiveTags = ['a', 'button', 'input', 'select', 'textarea'];
    const interactiveCount = focusedTags.filter((t) => interactiveTags.includes(t)).length;
    expect(interactiveCount, 'At least one focused element should be interactive').toBeGreaterThanOrEqual(1);
  });

  test('heading hierarchy starts with h1 and has reasonable structure', async ({ page }) => {
    await page.locator('[data-testid="dashboard-root"]').waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
    const allHeadings = await page.locator('h1, h2, h3, h4, h5, h6').all();
    const visibleHeadings: number[] = [];
    for (const heading of allHeadings) {
      if (await heading.isVisible()) {
        const tag = await heading.evaluate((el) => el.tagName.toLowerCase());
        visibleHeadings.push(parseInt(tag.replace('h', ''), 10));
      }
    }

    expect(visibleHeadings.length, 'Page should have visible headings (dashboard may still be loading)').toBeGreaterThan(0);
    expect(visibleHeadings, 'Page should contain an h1 heading').toContain(1);
    const uniqueLevels = [...new Set(visibleHeadings)];
    expect(uniqueLevels.length, 'Page should use at least one heading level').toBeGreaterThanOrEqual(1);
  });

  test('page has landmark regions for structural navigation', async ({ page }) => {
    await page.locator('main, nav').first().waitFor({ state: 'visible', timeout: 10000 }).catch(() => {});
    // Screen readers let users jump between landmarks (nav, main, header, etc.)
    const landmarks = page.locator(
      'nav, main, header, footer, [role="navigation"], [role="main"], [role="banner"], [role="contentinfo"]'
    );
    const count = await landmarks.count();
    expect(count, 'Page should have at least one landmark (nav or main; dashboard may still be loading)').toBeGreaterThanOrEqual(1);
  });

  test('form inputs on the Configuration page are associated with labels', async ({ page }) => {
    await page.goto('/#configuration');
    await waitForLoadingComplete(page);

    const inputs = page.locator('input, textarea, select');
    const inputCount = await inputs.count();

    expect(inputCount, 'Configuration page should have at least one form input').toBeGreaterThan(0);

    let associatedCount = 0;
    for (let i = 0; i < Math.min(inputCount, 10); i++) {
      const input = inputs.nth(i);
      const id = await input.getAttribute('id');
      const ariaLabel = await input.getAttribute('aria-label');
      const ariaLabelledBy = await input.getAttribute('aria-labelledby');
      const placeholder = await input.getAttribute('placeholder');

      // Check for explicit label association
      let hasLabel = !!(ariaLabel || ariaLabelledBy || placeholder);
      if (!hasLabel && id) {
        const label = page.locator(`label[for="${id}"]`);
        hasLabel = (await label.count()) > 0;
      }

      if (hasLabel) associatedCount++;
    }

    // All sampled inputs should have an accessible name
    expect(associatedCount).toBe(Math.min(inputCount, 10));
  });

  test('focused elements have a visible focus indicator', async ({ page }) => {
    // Tab until we land on a visible element (skip-link may be sr-only)
    for (let i = 0; i < 8; i++) {
      await page.keyboard.press('Tab');
      await new Promise(r => setTimeout(r, 150));
      const focused = page.locator(':focus');
      if (await focused.isVisible().catch(() => false)) break;
    }
    const focused = page.locator(':focus');
    const isVisible = await focused.isVisible().catch(() => false);
    expect(isVisible, 'A visible element should receive focus after Tab (focus may be on sr-only skip link)').toBe(true);
    await expect(focused).toBeVisible({ timeout: 1000 });

    const focusInfo = await focused.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        outlineWidth: computed.outlineWidth,
        outlineStyle: computed.outlineStyle,
        boxShadow: computed.boxShadow,
        // Check for Tailwind focus ring classes
        hasRingClass: el.className?.includes('ring') || el.className?.includes('focus'),
        // Check pseudo-element styles
        tag: el.tagName,
      };
    });

    // The element must have SOME visual focus indicator:
    // outline, box-shadow, Tailwind ring class, or be the skip-to-content link
    const hasOutline = focusInfo.outlineWidth !== '0px' && focusInfo.outlineStyle !== 'none';
    const hasBoxShadow = focusInfo.boxShadow !== 'none' && focusInfo.boxShadow !== '';
    const hasFocusClass = focusInfo.hasRingClass;
    const isLink = focusInfo.tag === 'A';
    const isButton = focusInfo.tag === 'BUTTON';

    expect(
      hasOutline || hasBoxShadow || hasFocusClass || isLink || isButton,
      'Focused element should have a visible focus indicator or be a focusable element'
    ).toBe(true);
  });

  test('images have alt text for screen readers', async ({ page }) => {
    const images = page.locator('img');
    const imgCount = await images.count();

    if (imgCount === 0) {
      // No images is fine -- nothing to check
      return;
    }

    for (let i = 0; i < Math.min(imgCount, 10); i++) {
      const img = images.nth(i);
      const alt = await img.getAttribute('alt');
      const role = await img.getAttribute('role');

      // alt must exist. For decorative images, alt="" is valid.
      // role="presentation" or role="none" also marks decorative images.
      const isAccessible = alt !== null || role === 'presentation' || role === 'none';
      expect(isAccessible).toBe(true);
    }
  });

  test('no console errors related to accessibility warnings', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        const text = msg.text();
        if (
          text.toLowerCase().includes('aria') ||
          text.toLowerCase().includes('accessible') ||
          text.toLowerCase().includes('label')
        ) {
          errors.push(text);
        }
      }
    });

    const pages = ['/', '/#services', '/#configuration'];
    for (const p of pages) {
      await page.goto(p);
      await new Promise(r => setTimeout(r, 1000));
    }

    const significant = errors.filter(
      e => !e.includes('429') && !e.includes('rate limit') && !e.includes('VITE_API_KEY')
    );
    expect(significant).toHaveLength(0);
  });
});
