import { chromium, FullConfig } from '@playwright/test';
import { execSync } from 'child_process';

/**
 * Global setup for Docker deployment testing
 * Ensures the Docker environment is ready before running tests
 */
async function globalSetup(config: FullConfig) {
  console.log('Setting up Docker deployment test environment...');
  
  // Check if Docker is running
  try {
    execSync('docker ps', { stdio: 'pipe' });
    console.log('✓ Docker is running');
  } catch (error) {
    throw new Error('Docker is not running. Please start Docker before running tests.');
  }
  
  // Check if the HA Ingestor containers are running
  const requiredServices = [
    'homeiq-influxdb',
    'homeiq-websocket',
    'homeiq-admin',
    'homeiq-dashboard'
  ];
  
  for (const service of requiredServices) {
    try {
      execSync(`docker ps --filter name=${service} --format "{{.Names}}"`, { stdio: 'pipe' });
      console.log(`✓ ${service} is running`);
    } catch (error) {
      throw new Error(`${service} is not running. Please start the HA Ingestor Docker deployment first.`);
    }
  }
  
  // Launch browser for health checks
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  try {
    // Wait for all services to be healthy
    const services = [
      { name: 'InfluxDB', url: 'http://localhost:8086/health' },
      { name: 'WebSocket Ingestion', url: 'http://localhost:8001/health' },
      { name: 'Admin API', url: 'http://localhost:8004/health', optional: true }, // Use /health instead of /api/v1/health
      { name: 'Data Retention', url: 'http://localhost:8080/health', optional: true }
    ];
    
    for (const service of services) {
      let retries = 30; // 30 seconds timeout
      let isHealthy = false;
      
      while (retries > 0 && !isHealthy) {
        try {
          const response = await page.request.get(service.url);
          if (response.status() === 200) {
            const data = await response.json();
            // Handle different response formats
            const status = data.status || data.overall_status || data.data?.overall_status || data.data?.status;
            if (status === 'healthy' || status === 'pass') {
              isHealthy = true;
              console.log(`✓ ${service.name} is healthy`);
            }
          }
        } catch (error) {
          // Service not ready yet
        }
        
        if (!isHealthy) {
          await page.waitForTimeout(1000);
          retries--;
        }
      }
      
      if (!isHealthy) {
        if (service.optional) {
          console.warn(`⚠ ${service.name} is not healthy after 30 seconds, but it's optional. Continuing...`);
        } else {
          throw new Error(`${service.name} is not healthy after 30 seconds. Please check the Docker deployment.`);
        }
      }
    }
    
    // Optional: if ai-automation-ui project will run, ensure 3001 is up
    try {
      const aiUiResponse = await page.goto('http://localhost:3001', { waitUntil: 'domcontentloaded', timeout: 5000 });
      if (aiUiResponse?.status() === 200) {
        console.log('✓ AI Automation UI (3001) is accessible');
      }
    } catch {
      console.warn('⚠ AI Automation UI (3001) not reachable; ai-automation-ui tests may be skipped or fail.');
    }

    // Wait for the health dashboard to be accessible
    // Use domcontentloaded instead of networkidle for faster, more reliable loading
    // Some API calls may still be in flight, but the DOM is ready
    await page.goto('http://localhost:3000', { 
      waitUntil: 'domcontentloaded', 
      timeout: 60000 
    });
    
    // Wait a bit for React to hydrate and render
    await page.waitForTimeout(2000);
    
    // Verify the dashboard is accessible by checking for common elements
    // Try multiple selectors as the page may not have data-testid attributes yet
    const isDashboardAccessible = await page.evaluate(() => {
      // Check if the page has loaded React content
      const hasContent = document.body.innerText.length > 100;
      const hasReactRoot = document.querySelector('#root') !== null;
      return hasContent && hasReactRoot;
    });
    
    if (isDashboardAccessible) {
      console.log('✓ Health dashboard is accessible');
    } else {
      console.warn('⚠ Health dashboard loaded but may not be fully rendered');
    }
    
    // Test basic API endpoints (with timeout and error handling)
    try {
      const statsResponse = await page.request.get('http://localhost:8004/api/v1/stats', { timeout: 10000 });
      if (statsResponse.status() === 200) {
        console.log('✓ Admin API statistics endpoint is working');
      }
    } catch (error) {
      console.warn('⚠ Admin API statistics endpoint is slow or unavailable (this is OK for testing)');
    }
    
    try {
      const eventsResponse = await page.request.get('http://localhost:8006/api/v1/events?limit=10', { timeout: 10000 });
      if (eventsResponse.status() === 200) {
        console.log('✓ Admin API events endpoint is working');
      }
    } catch (error) {
      console.warn('⚠ Admin API events endpoint is slow or unavailable (this is OK for testing)');
    }
    
    console.log('✓ Docker deployment test environment setup completed successfully');
    
  } catch (error) {
    console.error('Docker deployment setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;
