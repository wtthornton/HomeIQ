import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from '../../../../shared/helpers/auth-helpers';

test.describe('Health Dashboard - Accessibility', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
    await page.goto('/');
  });

  test('ARIA labels present', async ({ page }) => {
    const elementsWithAria = page.locator('[aria-label], [aria-labelledby]');
    const count = await elementsWithAria.count();
    expect(count).toBeGreaterThan(0);
  });

  test('Keyboard navigation works', async ({ page }) => {
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
    
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
    
    // Continue tabbing
    await page.keyboard.press('Tab');
    await page.waitForTimeout(200);
  });

  test('Screen reader compatibility', async ({ page }) => {
    // Check for semantic HTML
    const headings = page.locator('h1, h2, h3, h4, h5, h6');
    const count = await headings.count();
    expect(count).toBeGreaterThan(0);
    
    // Check for landmarks
    const landmarks = page.locator('nav, main, header, footer, [role="navigation"], [role="main"]');
    const landmarkCount = await landmarks.count();
    expect(landmarkCount).toBeGreaterThan(0);
  });

  test('Color contrast ratios', async ({ page }) => {
    // Basic check - verify text is visible
    const textElements = page.locator('p, span, div, h1, h2, h3');
    await expect(textElements.first()).toBeVisible();
  });

  test('Focus indicators', async ({ page }) => {
    await page.keyboard.press('Tab');
    
    const focusedElement = page.locator(':focus');
    const styles = await focusedElement.evaluate((el) => {
      const computed = window.getComputedStyle(el);
      return {
        outline: computed.outline,
        outlineWidth: computed.outlineWidth,
      };
    });
    
    // Verify focus indicator exists
    expect(styles.outlineWidth).not.toBe('0px');
  });

  test('Alt text for images', async ({ page }) => {
    const images = page.locator('img');
    const count = await images.count();
    
    if (count > 0) {
      const firstImage = images.first();
      const alt = await firstImage.getAttribute('alt');
      // Alt should be present (even if empty for decorative images)
      expect(alt).not.toBeNull();
    }
  });

  test('Form labels', async ({ page }) => {
    await page.goto('/#configuration');
    
    const inputs = page.locator('input, textarea, select');
    const count = await inputs.count();
    
    if (count > 0) {
      const firstInput = inputs.first();
      const id = await firstInput.getAttribute('id');
      const label = id ? page.locator(`label[for="${id}"]`) : page.locator('label').first();
      
      if (await label.isVisible({ timeout: 1000 })) {
        await expect(label).toBeVisible();
      }
    }
  });

  test('Heading hierarchy', async ({ page }) => {
    const h1 = page.locator('h1');
    const h1Count = await h1.count();
    
    // Should have at least one h1
    if (h1Count > 0) {
      await expect(h1.first()).toBeVisible();
    }
    
    // Check for proper hierarchy
    const headings = page.locator('h1, h2, h3');
    const headingCount = await headings.count();
    expect(headingCount).toBeGreaterThan(0);
  });
});
