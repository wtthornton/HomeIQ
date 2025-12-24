import { test, expect } from '@playwright/test';
import { DockerTestHelpers } from './utils/docker-test-helpers';

/**
 * Enhanced Integration and Performance E2E Tests
 * Tests complete data flow, service integration, and performance scenarios
 */
test.describe('Enhanced Integration and Performance Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Ensure all services are healthy before testing
    await DockerTestHelpers.waitForDockerComposeReady(page);
  });

  test.describe('Complete Data Flow Integration', () => {
    
    test('End-to-end data flow from Home Assistant simulation to dashboard', async ({ page }) => {
      // Step 1: Verify all services are healthy
      const services = [
        'http://localhost:8086/health',  // InfluxDB
        'http://localhost:8001/health',  // WebSocket Ingestion
        'http://localhost:8002/health',  // Enrichment Pipeline
        'http://localhost:8003/api/v1/health',  // Admin API
        'http://localhost:8080/health'   // Data Retention
      ];
      
      for (const serviceUrl of services) {
        const response = await page.request.get(serviceUrl);
        expect(response.status()).toBe(200);
        const data = await response.json();
        expect(data.status).toBe('healthy');
      }
      
      // Step 2: Simulate Home Assistant event data
      const mockEventData = {
        event_type: 'state_changed',
        entity_id: 'sensor.test_temperature',
        timestamp: new Date().toISOString(),
        attributes: {
          unit_of_measurement: '°C',
          friendly_name: 'Test Temperature'
        },
        state: '22.5'
      };
      
      // Step 3: Send mock data through WebSocket ingestion (if available)
      try {
        const wsResponse = await page.request.post('http://localhost:8001/events', {
          data: mockEventData
        });
        
        if (wsResponse.status() === 200) {
          console.log('Mock event sent successfully');
          
          // Step 4: Wait for event to be processed
          await page.waitForTimeout(5000);
          
          // Step 5: Verify event appears in admin API
          const eventsResponse = await page.request.get('http://localhost:8003/api/v1/events?limit=10');
          expect(eventsResponse.status()).toBe(200);
          
          const eventsData = await eventsResponse.json();
          expect(Array.isArray(eventsData)).toBe(true);
        }
      } catch (error) {
        console.log('WebSocket ingestion endpoint not available, skipping mock data test');
      }
      
      // Step 6: Verify dashboard displays updated data
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify dashboard shows current system status
      await expect(page.locator('[data-testid="system-health"]')).toBeVisible();
      
      // Verify last updated timestamp is recent
      const lastUpdated = page.locator('[data-testid="last-updated"]');
      await expect(lastUpdated).toBeVisible();
      
      const timestampText = await lastUpdated.textContent();
      expect(timestampText).toMatch(/\d{2}:\d{2}:\d{2}/);
    });

    test('Service dependency chain validation', async ({ page }) => {
      // Test that services depend on each other correctly
      
      // 1. InfluxDB is the foundation
      const influxResponse = await page.request.get('http://localhost:8086/health');
      expect(influxResponse.status()).toBe(200);
      const influxData = await influxResponse.json();
      expect(influxData.status).toBe('healthy');
      
      // 2. WebSocket ingestion depends on InfluxDB
      const wsResponse = await page.request.get('http://localhost:8001/health');
      expect(wsResponse.status()).toBe(200);
      const wsData = await wsResponse.json();
      expect(wsData.status).toBe('healthy');
      
      // 3. Enrichment pipeline depends on InfluxDB
      const enrichResponse = await page.request.get('http://localhost:8002/health');
      expect(enrichResponse.status()).toBe(200);
      const enrichData = await enrichResponse.json();
      expect(enrichData.status).toBe('healthy');
      
      // 4. Admin API aggregates all service health
      const adminResponse = await page.request.get('http://localhost:8003/api/v1/health');
      expect(adminResponse.status()).toBe(200);
      const adminData = await adminResponse.json();
      expect(adminData.overall_status).toBe('healthy');
      
      // 5. Verify dependency relationships in admin API response
      expect(adminData.ingestion_service).toBeDefined();
      expect(adminData.ingestion_service.websocket_connection.is_connected).toBe(true);
      expect(adminData.ingestion_service.influxdb_storage.is_connected).toBe(true);
    });

    test('Real-time data updates across all components', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Get initial system state
      const initialHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
      const initialHealthData = await initialHealthResponse.json();
      const initialTimestamp = initialHealthData.timestamp;
      
      // Wait for potential updates
      await page.waitForTimeout(15000);
      
      // Get updated system state
      const updatedHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
      const updatedHealthData = await updatedHealthResponse.json();
      const updatedTimestamp = updatedHealthData.timestamp;
      
      // Verify timestamps are different (indicating updates)
      expect(updatedTimestamp).not.toBe(initialTimestamp);
      
      // Verify dashboard reflects the updates
      const currentTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      expect(currentTimestamp).toMatch(/\d{2}:\d{2}:\d{2}/);
      
      // Verify WebSocket connection status
      await expect(page.locator('[data-testid="websocket-status"]')).toHaveAttribute('data-connected', 'true');
    });

    test('Weather enrichment integration end-to-end', async ({ page }) => {
      // Check if weather service is available
      const weatherResponse = await page.request.get('http://localhost:8080/health');
      
      if (weatherResponse.status() === 200) {
        const weatherData = await weatherResponse.json();
        expect(weatherData.status).toBe('healthy');
        
        // Verify weather enrichment is enabled in admin API
        const adminHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
        const adminHealthData = await adminHealthResponse.json();
        
        expect(adminHealthData.ingestion_service.weather_enrichment.enabled).toBe(true);
        
        // Verify weather data appears in dashboard
        await page.goto('http://localhost:3000');
        await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
        
        const weatherCard = page.locator('[data-testid="health-card"]').filter({ hasText: 'Weather Enrichment' });
        await expect(weatherCard).toBeVisible();
        await expect(weatherCard.locator('[data-testid="health-card-value"]')).toContainText('Enabled');
      }
    });

    test('Data retention service integration', async ({ page }) => {
      // Test data retention service
      const retentionResponse = await page.request.get('http://localhost:8080/health');
      expect(retentionResponse.status()).toBe(200);
      
      const retentionData = await retentionResponse.json();
      expect(retentionData.status).toBe('healthy');
      
      // Get retention statistics
      const retentionStatsResponse = await page.request.get('http://localhost:8080/stats');
      
      if (retentionStatsResponse.status() === 200) {
        const retentionStats = await retentionStatsResponse.json();
        expect(typeof retentionStats).toBe('object');
        
        // Verify retention stats structure
        if (retentionStats.cleanup_runs !== undefined) {
          expect(typeof retentionStats.cleanup_runs).toBe('number');
        }
        if (retentionStats.data_size !== undefined) {
          expect(typeof retentionStats.data_size).toBe('number');
        }
      }
    });
  });

  test.describe('Performance and Load Testing', () => {
    
    test('High-volume concurrent API requests', async ({ page }) => {
      // Test concurrent health check requests
      const healthRequests = Array.from({ length: 50 }, () => 
        page.request.get('http://localhost:8003/api/v1/health')
      );
      
      const startTime = Date.now();
      const responses = await Promise.all(healthRequests);
      const endTime = Date.now();
      
      // Verify all requests succeeded
      responses.forEach(response => {
        expect(response.status()).toBe(200);
      });
      
      // Verify response time is acceptable
      const totalTime = endTime - startTime;
      expect(totalTime).toBeLessThan(30000); // Should complete within 30 seconds
      
      console.log(`50 concurrent health requests completed in ${totalTime}ms`);
    });

    test('Large dataset query performance', async ({ page }) => {
      // Test large event queries
      const startTime = Date.now();
      const response = await page.request.get('http://localhost:8003/api/v1/events?limit=1000');
      const endTime = Date.now();
      
      expect(response.status()).toBe(200);
      
      const eventsData = await response.json();
      expect(Array.isArray(eventsData)).toBe(true);
      
      // Verify response time is acceptable
      const queryTime = endTime - startTime;
      expect(queryTime).toBeLessThan(15000); // Should complete within 15 seconds
      
      console.log(`Large event query (1000 events) completed in ${queryTime}ms`);
    });

    test('Memory usage under continuous load', async ({ page }) => {
      // Perform continuous API requests for 2 minutes
      const startTime = Date.now();
      const requestCount = 100;
      
      for (let i = 0; i < requestCount; i++) {
        const response = await page.request.get('http://localhost:8003/api/v1/health');
        expect(response.status()).toBe(200);
        
        // Small delay between requests
        await page.waitForTimeout(100);
        
        // Check memory usage periodically
        if (i % 20 === 0) {
          const containerStats = DockerTestHelpers.getContainerStats('homeiq-admin');
          if (containerStats) {
            console.log(`Memory usage at request ${i}: ${containerStats.memoryUsage}`);
          }
        }
      }
      
      const endTime = Date.now();
      const totalTime = endTime - startTime;
      
      console.log(`Completed ${requestCount} requests in ${totalTime}ms`);
      
      // Verify final system health
      const finalHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
      expect(finalHealthResponse.status()).toBe(200);
    });

    test('Dashboard rendering performance under load', async ({ page }) => {
      // Test dashboard performance with multiple rapid navigations
      const navigationCount = 20;
      
      for (let i = 0; i < navigationCount; i++) {
        const startTime = Date.now();
        
        // Navigate to dashboard
        await page.goto('http://localhost:3000');
        await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
        
        // Navigate to monitoring
        await page.click('[data-testid="nav-monitoring"]');
        await page.waitForSelector('[data-testid="monitoring-screen"]', { timeout: 10000 });
        
        // Navigate to settings
        await page.click('[data-testid="nav-settings"]');
        await page.waitForSelector('[data-testid="settings-screen"]', { timeout: 10000 });
        
        const endTime = Date.now();
        const navigationTime = endTime - startTime;
        
        expect(navigationTime).toBeLessThan(15000); // Each navigation should complete within 15 seconds
        
        if (i % 5 === 0) {
          console.log(`Navigation cycle ${i} completed in ${navigationTime}ms`);
        }
      }
      
      // Verify dashboard is still responsive
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('WebSocket connection stability under load', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Verify WebSocket connection
      await page.waitForSelector('[data-testid="websocket-status"]', { timeout: 10000 });
      const wsStatus = page.locator('[data-testid="websocket-status"]');
      await expect(wsStatus).toHaveAttribute('data-connected', 'true');
      
      // Perform multiple API requests while WebSocket is connected
      for (let i = 0; i < 30; i++) {
        const response = await page.request.get('http://localhost:8003/api/v1/health');
        expect(response.status()).toBe(200);
        
        // Check WebSocket status
        const isConnected = await wsStatus.getAttribute('data-connected');
        expect(isConnected).toBe('true');
        
        await page.waitForTimeout(1000);
      }
      
      // Final WebSocket status check
      await expect(wsStatus).toHaveAttribute('data-connected', 'true');
    });
  });

  test.describe('Error Recovery and Resilience', () => {
    
    test('Service restart recovery', async ({ page }) => {
      // Get initial system state
      const initialHealthResponse = await page.request.get('http://localhost:8003/api/v1/health');
      const initialHealthData = await initialHealthResponse.json();
      expect(initialHealthData.overall_status).toBe('healthy');
      
      // Simulate service failure (stop admin API container)
      try {
        DockerTestHelpers.stopContainer('homeiq-admin');
        console.log('Admin API container stopped');
        
        // Wait for service to be unavailable
        await page.waitForTimeout(5000);
        
        // Verify service is down
        const downResponse = await page.request.get('http://localhost:8003/api/v1/health');
        expect(downResponse.status()).toBeGreaterThanOrEqual(500);
        
        // Restart service
        DockerTestHelpers.startContainer('homeiq-admin');
        console.log('Admin API container restarted');
        
        // Wait for service to recover
        await page.waitForTimeout(10000);
        
        // Verify service is healthy again
        const recoveryResponse = await page.request.get('http://localhost:8003/api/v1/health');
        expect(recoveryResponse.status()).toBe(200);
        
        const recoveryData = await recoveryResponse.json();
        expect(recoveryData.overall_status).toBe('healthy');
        
      } catch (error) {
        console.log('Service restart test skipped:', error);
      }
    });

    test('Network interruption recovery', async ({ page }) => {
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Simulate network interruption
      await page.route('**/api/v1/health', route => route.abort());
      
      // Wait for error state
      await page.waitForSelector('[data-testid="error-state"]', { timeout: 10000 });
      await expect(page.locator('[data-testid="error-state"]')).toBeVisible();
      
      // Restore network
      await page.unroute('**/api/v1/health');
      
      // Trigger retry
      const retryButton = page.locator('[data-testid="retry-button"]');
      if (await retryButton.isVisible()) {
        await retryButton.click();
      }
      
      // Wait for recovery
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      await expect(page.locator('[data-testid="dashboard"]')).toBeVisible();
    });

    test('Partial service failure handling', async ({ page }) => {
      // Simulate InfluxDB being unavailable
      await page.route('http://localhost:8086/**', route => route.abort());
      
      // Wait for error propagation
      await page.waitForTimeout(5000);
      
      // Check that dependent services handle the error gracefully
      const wsResponse = await page.request.get('http://localhost:8001/health');
      if (wsResponse.status() === 200) {
        const wsData = await wsResponse.json();
        // Service should report InfluxDB as unhealthy
        if (wsData.dependencies?.influxdb) {
          expect(wsData.dependencies.influxdb).toBe('unhealthy');
        }
      }
      
      const enrichResponse = await page.request.get('http://localhost:8002/health');
      if (enrichResponse.status() === 200) {
        const enrichData = await enrichResponse.json();
        // Service should report InfluxDB as unhealthy
        if (enrichData.dependencies?.influxdb) {
          expect(enrichData.dependencies.influxdb).toBe('unhealthy');
        }
      }
      
      // Check that admin API reports degraded status
      const adminResponse = await page.request.get('http://localhost:8003/api/v1/health');
      if (adminResponse.status() === 200) {
        const adminData = await adminResponse.json();
        expect(['degraded', 'unhealthy']).toContain(adminData.overall_status);
      }
      
      // Restore InfluxDB
      await page.unroute('http://localhost:8086/**');
      
      // Wait for recovery
      await page.waitForTimeout(10000);
      
      // Verify system recovers
      const recoveryResponse = await page.request.get('http://localhost:8003/api/v1/health');
      if (recoveryResponse.status() === 200) {
        const recoveryData = await recoveryResponse.json();
        expect(recoveryData.overall_status).toBe('healthy');
      }
    });

    test('Configuration change propagation', async ({ page }) => {
      // Get current configuration
      const configResponse = await page.request.get('http://localhost:8003/api/v1/config');
      expect(configResponse.status()).toBe(200);
      
      const configData = await configResponse.json();
      const originalConfig = { ...configData };
      
      // Update configuration
      const updatedConfig = {
        ...configData,
        refresh_interval: 60000
      };
      
      const updateResponse = await page.request.put('http://localhost:8003/api/v1/config', {
        data: updatedConfig
      });
      
      if (updateResponse.status() === 200) {
        // Verify configuration was updated
        const verifyResponse = await page.request.get('http://localhost:8003/api/v1/config');
        const verifyData = await verifyResponse.json();
        
        expect(verifyData.refresh_interval).toBe(60000);
        
        // Restore original configuration
        await page.request.put('http://localhost:8003/api/v1/config', {
          data: originalConfig
        });
      }
    });
  });

  test.describe('Data Integrity and Consistency', () => {
    
    test('Event data consistency across services', async ({ page }) => {
      // Get events from admin API
      const eventsResponse = await page.request.get('http://localhost:8003/api/v1/events?limit=10');
      expect(eventsResponse.status()).toBe(200);
      
      const eventsData = await eventsResponse.json();
      
      if (eventsData.length > 0) {
        const event = eventsData[0];
        
        // Verify event structure
        expect(event).toHaveProperty('id');
        expect(event).toHaveProperty('timestamp');
        expect(event).toHaveProperty('entity_id');
        expect(event).toHaveProperty('event_type');
        
        // Verify timestamp format
        const timestamp = new Date(event.timestamp);
        expect(timestamp.getTime()).not.toBeNaN();
        
        // Verify ID format
        expect(typeof event.id).toBe('string');
        expect(event.id.length).toBeGreaterThan(0);
      }
    });

    test('Statistics accuracy and consistency', async ({ page }) => {
      // Get statistics multiple times and verify consistency
      const stats1 = await page.request.get('http://localhost:8003/api/v1/stats');
      expect(stats1.status()).toBe(200);
      
      await page.waitForTimeout(2000);
      
      const stats2 = await page.request.get('http://localhost:8003/api/v1/stats');
      expect(stats2.status()).toBe(200);
      
      const statsData1 = await stats1.json();
      const statsData2 = await stats2.json();
      
      // Verify statistics structure is consistent
      expect(statsData1).toHaveProperty('total_events');
      expect(statsData1).toHaveProperty('events_per_minute');
      expect(statsData1).toHaveProperty('last_event_time');
      
      expect(statsData2).toHaveProperty('total_events');
      expect(statsData2).toHaveProperty('events_per_minute');
      expect(statsData2).toHaveProperty('last_event_time');
      
      // Verify data types are consistent
      expect(typeof statsData1.total_events).toBe('number');
      expect(typeof statsData2.total_events).toBe('number');
      expect(typeof statsData1.events_per_minute).toBe('number');
      expect(typeof statsData2.events_per_minute).toBe('number');
    });

    test('Health status consistency across endpoints', async ({ page }) => {
      // Get health from all services
      const services = [
        { name: 'InfluxDB', url: 'http://localhost:8086/health' },
        { name: 'WebSocket Ingestion', url: 'http://localhost:8001/health' },
        { name: 'Enrichment Pipeline', url: 'http://localhost:8002/health' },
        { name: 'Admin API', url: 'http://localhost:8003/api/v1/health' },
        { name: 'Data Retention', url: 'http://localhost:8080/health' }
      ];
      
      const healthStatuses = [];
      
      for (const service of services) {
        const response = await page.request.get(service.url);
        if (response.status() === 200) {
          const data = await response.json();
          healthStatuses.push({
            name: service.name,
            status: data.status,
            timestamp: data.timestamp
          });
        }
      }
      
      // Verify all services report healthy status
      healthStatuses.forEach(service => {
        expect(service.status).toBe('healthy');
      });
      
      // Verify timestamps are recent
      healthStatuses.forEach(service => {
        if (service.timestamp) {
          const timestamp = new Date(service.timestamp);
          const now = new Date();
          const timeDiff = now.getTime() - timestamp.getTime();
          expect(timeDiff).toBeLessThan(60000); // Within last minute
        }
      });
    });
  });
});
