/**
 * Simple Health Dashboard Test - No Puppeteer
 * 
 * Usage: node tests/visual/test-simple-dashboard.js
 */

const http = require('http');

const BASE_URL = 'http://localhost:3000';

async function testSimpleDashboard() {
  console.log(`🔍 Simple Dashboard Test`);
  console.log(`📍 URL: ${BASE_URL}\n`);

  return new Promise((resolve, reject) => {
    const startTime = Date.now();
    
    const req = http.get(BASE_URL, (res) => {
      const endTime = Date.now();
      const responseTime = endTime - startTime;
      
      console.log(`📊 Response Status: ${res.statusCode}`);
      console.log(`⏱️ Response Time: ${responseTime}ms`);
      console.log(`📏 Content Length: ${res.headers['content-length'] || 'unknown'}`);
      
      let data = '';
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        console.log(`📄 HTML Length: ${data.length} characters`);
        
        // Check for ErrorBoundary content
        if (data.includes('Something went wrong')) {
          console.log('🚨 ErrorBoundary Active: YES');
        } else if (data.includes('HA Ingestor Dashboard')) {
          console.log('✅ Dashboard Content: YES');
        } else {
          console.log('❓ Dashboard Status: UNKNOWN');
        }
        
        // Check for React root
        if (data.includes('id="root"')) {
          console.log('✅ React Root: YES');
        } else {
          console.log('❌ React Root: NO');
        }
        
        console.log('\n✅ Simple test complete!\n');
        resolve();
      });
    });
    
    req.on('error', (error) => {
      console.error('❌ Error:', error.message);
      reject(error);
    });
    
    req.setTimeout(5000, () => {
      console.error('❌ Request timeout after 5 seconds');
      req.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

testSimpleDashboard().catch(console.error);
