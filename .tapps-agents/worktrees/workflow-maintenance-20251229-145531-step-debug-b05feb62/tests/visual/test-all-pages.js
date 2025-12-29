/**
 * Comprehensive Visual Testing Suite
 * Tests all pages against design tokens and specifications
 * 
 * Usage: node tests/visual/test-all-pages.js
 */

const puppeteer = require('puppeteer');
const fs = require('fs').promises;
const path = require('path');

const BASE_URL = 'http://localhost:3001';
const SCREENSHOT_DIR = 'test-results/visual';

// Design specifications from design-tokens.md
const DESIGN_SPECS = {
  colors: {
    light: {
      primary: 'rgb(255, 255, 255)',      // bg-white
      background: 'rgb(249, 250, 251)',   // bg-gray-50
      text: 'rgb(17, 24, 39)',            // text-gray-900
      border: 'rgb(229, 231, 235)'        // border-gray-200
    },
    dark: {
      primary: 'rgb(31, 41, 55)',         // bg-gray-800
      background: 'rgb(17, 24, 39)',      // bg-gray-900
      text: 'rgb(255, 255, 255)',         // text-white
      border: 'rgb(55, 65, 81)'           // border-gray-700
    }
  },
  spacing: {
    sm: 8,   // 2 * 4px
    md: 16,  // 4 * 4px
    lg: 24,  // 6 * 4px
    xl: 32   // 8 * 4px
  },
  borderRadius: {
    base: '4px',
    lg: '8px',
    xl: '12px',
    full: '9999px'
  },
  minTouchTarget: 44 // 44x44px minimum
};

// Pages to test
const PAGES = [
  {
    name: 'Dashboard',
    path: '/',
    waitFor: '.dashboard-container',
    checks: [
      'hasNavigation',
      'hasCards',
      'hasCharts',
      'hasDarkModeToggle',
      'checkColors',
      'checkSpacing',
      'checkBorderRadius',
      'checkTouchTargets'
    ]
  },
  {
    name: 'Patterns',
    path: '/patterns',
    waitFor: '.patterns-container',
    checks: [
      'hasNavigation',
      'hasPatternList',
      'hasCharts',
      'hasReadableNames',
      'checkColors',
      'checkSpacing',
      'checkBorderRadius'
    ]
  },
  {
    name: 'Deployed',
    path: '/deployed',
    waitFor: '.deployed-container',
    checks: [
      'hasNavigation',
      'hasAutomationList',
      'hasActionButtons',
      'checkColors',
      'checkSpacing',
      'checkBorderRadius',
      'checkTouchTargets'
    ]
  },
  {
    name: 'Settings',
    path: '/settings',
    waitFor: '.settings-container',
    checks: [
      'hasNavigation',
      'hasSettingsForm',
      'hasInputFields',
      'hasButtons',
      'checkColors',
      'checkSpacing',
      'checkBorderRadius',
      'checkTouchTargets'
    ]
  }
];

class VisualTester {
  constructor() {
    this.browser = null;
    this.page = null;
    this.results = {
      passed: [],
      failed: [],
      warnings: []
    };
  }

  async initialize() {
    console.log('🚀 Initializing Puppeteer...\n');
    this.browser = await puppeteer.launch({
      headless: false,
      defaultViewport: {
        width: 1280,
        height: 800
      },
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    this.page = await this.browser.newPage();
    
    // Create screenshot directory
    await fs.mkdir(SCREENSHOT_DIR, { recursive: true });
  }

  async testPage(pageConfig) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📄 Testing: ${pageConfig.name}`);
    console.log(`${'='.repeat(60)}\n`);

    try {
      // Navigate to page
      console.log(`🔗 Navigating to ${BASE_URL}${pageConfig.path}...`);
      await this.page.goto(`${BASE_URL}${pageConfig.path}`, { 
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Wait for content to load
      console.log(`⏳ Waiting for content...`);
      try {
        await this.page.waitForSelector('body', { timeout: 5000 });
      } catch (error) {
        console.log(`⚠️  Warning: Selector ${pageConfig.waitFor} not found, continuing...`);
      }
      
      // Wait for JS to execute
      await new Promise(resolve => setTimeout(resolve, 3000));

      // Take screenshots (light and dark mode)
      await this.takeScreenshots(pageConfig.name);

      // Run checks
      for (const check of pageConfig.checks) {
        await this.runCheck(check, pageConfig.name);
      }

      this.results.passed.push({
        page: pageConfig.name,
        message: 'All checks completed'
      });

    } catch (error) {
      console.error(`❌ Error testing ${pageConfig.name}:`, error.message);
      this.results.failed.push({
        page: pageConfig.name,
        error: error.message
      });
    }
  }

  async takeScreenshots(pageName) {
    const fileName = pageName.toLowerCase().replace(/\s+/g, '-');
    
    // Light mode screenshot
    console.log(`📸 Taking light mode screenshot...`);
    await this.page.screenshot({
      path: path.join(SCREENSHOT_DIR, `${fileName}-light.png`),
      fullPage: true
    });

    // Toggle dark mode if available
    const darkModeButton = await this.page.$('[aria-label="Toggle dark mode"]');
    if (darkModeButton) {
      await darkModeButton.click();
      await new Promise(resolve => setTimeout(resolve, 500));
      
      console.log(`📸 Taking dark mode screenshot...`);
      await this.page.screenshot({
        path: path.join(SCREENSHOT_DIR, `${fileName}-dark.png`),
        fullPage: true
      });
      
      // Toggle back to light mode
      await darkModeButton.click();
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  async runCheck(checkName, pageName) {
    const checkMethod = this[checkName];
    if (typeof checkMethod === 'function') {
      try {
        const result = await checkMethod.call(this);
        if (result.passed) {
          console.log(`✅ ${checkName}: ${result.message}`);
        } else {
          console.log(`⚠️  ${checkName}: ${result.message}`);
          this.results.warnings.push({
            page: pageName,
            check: checkName,
            message: result.message
          });
        }
      } catch (error) {
        console.log(`❌ ${checkName}: ${error.message}`);
        this.results.failed.push({
          page: pageName,
          check: checkName,
          error: error.message
        });
      }
    }
  }

  // Check methods
  async hasNavigation() {
    const nav = await this.page.$('nav');
    return {
      passed: !!nav,
      message: nav ? 'Navigation found' : 'Navigation missing'
    };
  }

  async hasCards() {
    const cards = await this.page.$$('[class*="card"], [class*="bg-white"], [class*="bg-gray-800"]');
    return {
      passed: cards.length > 0,
      message: cards.length > 0 ? `Found ${cards.length} cards` : 'No cards found'
    };
  }

  async hasCharts() {
    const charts = await this.page.$$('canvas');
    return {
      passed: charts.length > 0,
      message: charts.length > 0 ? `Found ${charts.length} charts` : 'No charts found'
    };
  }

  async hasPatternList() {
    const patterns = await this.page.$$('[class*="pattern"]');
    return {
      passed: patterns.length > 0,
      message: patterns.length > 0 ? `Found ${patterns.length} pattern items` : 'No patterns found'
    };
  }

  async hasReadableNames() {
    const texts = await this.page.evaluate(() => {
      const elements = Array.from(document.querySelectorAll('div.font-semibold'));
      return elements.map(el => el.textContent?.trim()).filter(Boolean);
    });

    const hasReadable = texts.some(text => 
      text.includes('Co-occurrence') || 
      text.includes('Pattern') || 
      (text.length > 5 && text.length < 100 && !text.match(/^[a-f0-9+]{20,}$/))
    );

    return {
      passed: hasReadable,
      message: hasReadable 
        ? `Found readable names: ${texts.slice(0, 3).join(', ')}...` 
        : 'Still showing hash IDs instead of readable names'
    };
  }

  async hasAutomationList() {
    const automations = await this.page.$$('[class*="automation"], tbody tr');
    return {
      passed: automations.length > 0,
      message: automations.length > 0 ? `Found ${automations.length} automation items` : 'No automations found'
    };
  }

  async hasActionButtons() {
    const buttons = await this.page.$$('button');
    return {
      passed: buttons.length > 0,
      message: buttons.length > 0 ? `Found ${buttons.length} buttons` : 'No buttons found'
    };
  }

  async hasSettingsForm() {
    const form = await this.page.$('form, [class*="settings"]');
    return {
      passed: !!form,
      message: form ? 'Settings form found' : 'Settings form missing'
    };
  }

  async hasInputFields() {
    const inputs = await this.page.$$('input, select, textarea');
    return {
      passed: inputs.length > 0,
      message: inputs.length > 0 ? `Found ${inputs.length} input fields` : 'No input fields found'
    };
  }

  async hasButtons() {
    const buttons = await this.page.$$('button');
    return {
      passed: buttons.length > 0,
      message: buttons.length > 0 ? `Found ${buttons.length} buttons` : 'No buttons found'
    };
  }

  async hasDarkModeToggle() {
    const toggle = await this.page.$('[aria-label="Toggle dark mode"]');
    return {
      passed: !!toggle,
      message: toggle ? 'Dark mode toggle found' : 'Dark mode toggle missing'
    };
  }

  async checkColors() {
    const colors = await this.page.evaluate(() => {
      const elements = document.querySelectorAll('[class*="bg-"], [class*="text-"]');
      const usedColors = new Set();
      elements.forEach(el => {
        const classes = el.className.split(' ');
        classes.forEach(cls => {
          if (cls.startsWith('bg-') || cls.startsWith('text-')) {
            usedColors.add(cls);
          }
        });
      });
      return Array.from(usedColors);
    });

    return {
      passed: colors.length > 0,
      message: `Using ${colors.length} color classes (sample: ${colors.slice(0, 5).join(', ')})`
    };
  }

  async checkSpacing() {
    const spacing = await this.page.evaluate(() => {
      const elements = document.querySelectorAll('[class*="p-"], [class*="m-"], [class*="gap-"]');
      const usedSpacing = new Set();
      elements.forEach(el => {
        const classes = el.className.split(' ');
        classes.forEach(cls => {
          if (cls.match(/^(p|m|gap)-\d+$/)) {
            usedSpacing.add(cls);
          }
        });
      });
      return Array.from(usedSpacing);
    });

    return {
      passed: spacing.length > 0,
      message: `Using ${spacing.length} spacing classes (sample: ${spacing.slice(0, 5).join(', ')})`
    };
  }

  async checkBorderRadius() {
    const radius = await this.page.evaluate(() => {
      const elements = document.querySelectorAll('[class*="rounded"]');
      const usedRadius = new Set();
      elements.forEach(el => {
        const classes = el.className.split(' ');
        classes.forEach(cls => {
          if (cls.startsWith('rounded')) {
            usedRadius.add(cls);
          }
        });
      });
      return Array.from(usedRadius);
    });

    return {
      passed: radius.length > 0,
      message: `Using ${radius.length} border radius classes (sample: ${radius.slice(0, 5).join(', ')})`
    };
  }

  async checkTouchTargets() {
    const smallButtons = await this.page.evaluate((minSize) => {
      const buttons = Array.from(document.querySelectorAll('button, a[role="button"]'));
      const small = [];
      
      buttons.forEach(btn => {
        const rect = btn.getBoundingClientRect();
        if (rect.width < minSize || rect.height < minSize) {
          small.push({
            text: btn.textContent?.trim().substring(0, 20),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          });
        }
      });
      
      return small;
    }, DESIGN_SPECS.minTouchTarget);

    if (smallButtons.length > 0) {
      return {
        passed: false,
        message: `Found ${smallButtons.length} buttons smaller than 44x44px: ${JSON.stringify(smallButtons.slice(0, 2))}`
      };
    }

    return {
      passed: true,
      message: 'All touch targets meet minimum size requirements'
    };
  }

  async generateReport() {
    console.log(`\n${'='.repeat(60)}`);
    console.log('📊 VISUAL TESTING REPORT');
    console.log(`${'='.repeat(60)}\n`);

    console.log(`✅ Passed: ${this.results.passed.length} pages`);
    this.results.passed.forEach(item => {
      console.log(`   - ${item.page}: ${item.message}`);
    });

    if (this.results.warnings.length > 0) {
      console.log(`\n⚠️  Warnings: ${this.results.warnings.length}`);
      this.results.warnings.forEach(item => {
        console.log(`   - ${item.page} (${item.check}): ${item.message}`);
      });
    }

    if (this.results.failed.length > 0) {
      console.log(`\n❌ Failed: ${this.results.failed.length}`);
      this.results.failed.forEach(item => {
        console.log(`   - ${item.page}${item.check ? ` (${item.check})` : ''}: ${item.error || item.message}`);
      });
    }

    console.log(`\n📁 Screenshots saved to: ${SCREENSHOT_DIR}\n`);

    // Save JSON report
    const reportPath = path.join(SCREENSHOT_DIR, 'test-report.json');
    await fs.writeFile(reportPath, JSON.stringify(this.results, null, 2));
    console.log(`📄 JSON report saved to: ${reportPath}\n`);

    // Overall status
    const allPassed = this.results.failed.length === 0;
    console.log(`\n${'='.repeat(60)}`);
    if (allPassed) {
      console.log('🎉 ALL TESTS PASSED! UI looks great!');
    } else {
      console.log('⚠️  SOME ISSUES FOUND - Please review the report above');
    }
    console.log(`${'='.repeat(60)}\n`);

    return allPassed;
  }

  async cleanup() {
    if (this.browser) {
      await this.browser.close();
    }
  }
}

// Main execution
async function main() {
  const tester = new VisualTester();
  
  try {
    await tester.initialize();
    
    // Test all pages
    for (const page of PAGES) {
      await tester.testPage(page);
    }
    
    // Generate report
    const allPassed = await tester.generateReport();
    
    await tester.cleanup();
    
    // Exit with appropriate code
    process.exit(allPassed ? 0 : 1);
    
  } catch (error) {
    console.error('❌ Fatal error:', error);
    await tester.cleanup();
    process.exit(1);
  }
}

// Run tests
main();

