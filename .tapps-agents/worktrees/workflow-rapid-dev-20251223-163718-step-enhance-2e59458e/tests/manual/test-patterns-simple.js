const puppeteer = require('puppeteer');

async function testPatterns() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to patterns page...');
    await page.goto('http://localhost:3001/patterns', { waitUntil: 'networkidle2' });
    
    console.log('Waiting for patterns to load...');
    await new Promise(resolve => setTimeout(resolve, 5000)); // Wait for patterns to load
    
    console.log('Taking screenshot...');
    await page.screenshot({ path: 'patterns-test-2.png', fullPage: true });
    
    // Check pattern list text content
    const patternTexts = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      const texts = [];
      elements.forEach(el => {
        const text = el.textContent?.trim();
        if (text && text.length > 20 && text.length < 100 && 
            (text.includes('Co-occurrence') || text.includes('Pattern') || text.includes('occurrences'))) {
          texts.push(text);
        }
      });
      return [...new Set(texts)].slice(0, 10);
    });
    
    console.log('Found pattern texts:', patternTexts);
    
    // Check if we have readable names instead of just hashes
    const hasReadableNames = patternTexts.some(text => 
      text.includes('Co-occurrence') || 
      text.includes('Pattern') ||
      (!text.match(/^[a-f0-9]{32,}$/) && text.length < 80)
    );
    
    if (hasReadableNames) {
      console.log('✅ SUCCESS: Found readable pattern names!');
      console.log('Sample names:', patternTexts.slice(0, 3));
    } else {
      console.log('❌ FAILED: Still showing hash IDs instead of readable names');
      console.log('Sample texts:', patternTexts.slice(0, 3));
    }
    
    await browser.close();
    
  } catch (error) {
    console.error('Error:', error);
    await browser.close();
  }
}

testPatterns();
