import { test, expect } from '@playwright/test';

/**
 * Cross-Service Integration E2E Tests
 * Tests complete data flow and service interactions across the entire system
 */
test.describe('Cross-Service Integration Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // Ensure all services are healthy before testing (Epic 31)
    const services = [
      'http://localhost:8086/health',  // InfluxDB
      'http://localhost:8001/health',  // WebSocket Ingestion (direct InfluxDB writes)
      'http://localhost:8004/api/v1/health',  // Admin API
      'http://localhost:8080/health',   // Data Retention
      'http://localhost:8041/health'    // API Automation Edge (Epic C1)
    ];
    
    for (const serviceUrl of services) {
      const response = await page.request.get(serviceUrl);
      expect(response.status()).toBe(200);
    }
  });

  test.describe('Complete Data Flow Integration', () => {
    
    test('End-to-end data flow from ingestion to dashboard display', async ({ page }) => {
      // Step 1: Verify all services are healthy
      const healthResponse = await page.request.get('http://localhost:8004/api/v1/health');
      expect(healthResponse.status()).toBe(200);
      
      const healthData = await healthResponse.json();
      expect(healthData.overall_status).toBe('healthy');
      
      // Step 2: Verify WebSocket ingestion is connected
      expect(healthData.ingestion_service.websocket_connection.is_connected).toBe(true);
      
      // Step 3: Verify InfluxDB storage is connected
      expect(healthData.ingestion_service.influxdb_storage.is_connected).toBe(true);
      
      // Step 4: Verify enrichment pipeline is running
      expect(healthData.ingestion_service.weather_enrichment.enabled).toBe(true);
      
      // Step 5: Load dashboard and verify data flows through
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 6: Verify dashboard shows real data
      const healthCards = page.locator('[data-testid="health-card"]');
      await expect(healthCards).toHaveCount({ min: 1 });
      
      // Step 7: Verify WebSocket connection status in dashboard
      const wsCard = healthCards.filter({ hasText: 'WebSocket Connection' });
      await expect(wsCard).toBeVisible();
      
      // Step 8: Verify event processing metrics
      const eventCard = healthCards.filter({ hasText: 'Event Processing' });
      await expect(eventCard).toBeVisible();
      
      // Step 9: Verify InfluxDB storage status
      const storageCard = healthCards.filter({ hasText: 'InfluxDB Storage' });
      await expect(storageCard).toBeVisible();
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
      
      // 3. Admin API aggregates all service health (Epic 31: enrichment-pipeline removed)
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      expect(adminResponse.status()).toBe(200);
      const adminData = await adminResponse.json();
      expect(adminData.overall_status).toBe('healthy');
      
      // 5. Verify dependency relationships in admin API response
      expect(adminData.ingestion_service).toBeDefined();
      expect(adminData.ingestion_service.websocket_connection.is_connected).toBe(true);
      expect(adminData.ingestion_service.influxdb_storage.is_connected).toBe(true);
    });

    test('Real-time data synchronization across services', async ({ page }) => {
      // Step 1: Get initial system state
      const initialHealthResponse = await page.request.get('http://localhost:8004/api/v1/health');
      const initialHealthData = await initialHealthResponse.json();
      const initialTimestamp = initialHealthData.timestamp;
      
      // Step 2: Load dashboard
      await page.goto('http://localhost:3000');
      await page.waitForSelector('[data-testid="dashboard"]', { timeout: 15000 });
      
      // Step 3: Wait for potential updates
      await page.waitForTimeout(15000);
      
      // Step 4: Get updated system state
      const updatedHealthResponse = await page.request.get('http://localhost:8004/api/v1/health');
      const updatedHealthData = await updatedHealthResponse.json();
      const updatedTimestamp = updatedHealthData.timestamp;
      
      // Step 5: Verify timestamps are different (indicating updates)
      expect(updatedTimestamp).not.toBe(initialTimestamp);
      
      // Step 6: Verify dashboard reflects the updates
      const currentTimestamp = await page.locator('[data-testid="last-updated"]').textContent();
      expect(currentTimestamp).toMatch(/\d{2}:\d{2}:\d{2}/);
    });
  });

  test.describe('Service Communication Patterns', () => {
    
    test('WebSocket to Admin API communication', async ({ page }) => {
      // Step 1: Verify WebSocket service is healthy
      const wsResponse = await page.request.get('http://localhost:8001/health');
      expect(wsResponse.status()).toBe(200);
      const wsData = await wsResponse.json();
      expect(wsData.status).toBe('healthy');
      
      // Step 2: Verify Admin API reports WebSocket status
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      expect(adminResponse.status()).toBe(200);
      const adminData = await adminResponse.json();
      
      // Step 3: Verify WebSocket connection status is reported
      expect(adminData.ingestion_service.websocket_connection).toBeDefined();
      expect(adminData.ingestion_service.websocket_connection.is_connected).toBe(true);
      
      // Step 4: Verify connection details are available
      expect(adminData.ingestion_service.websocket_connection.last_connection_time).toBeDefined();
      expect(adminData.ingestion_service.websocket_connection.connection_attempts).toBeDefined();
    });

    test('Enrichment Pipeline to Admin API communication', async ({ page }) => {
      // Step 1: Verify Enrichment Pipeline is healthy
      const enrichResponse = await page.request.get('http://localhost:8002/health');
      expect(enrichResponse.status()).toBe(200);
      const enrichData = await enrichResponse.json();
      expect(enrichData.status).toBe('healthy');
      
      // Step 2: Verify Admin API reports enrichment status
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      expect(adminResponse.status()).toBe(200);
      const adminData = await adminResponse.json();
      
      // Step 3: Verify weather enrichment status is reported
      expect(adminData.ingestion_service.weather_enrichment).toBeDefined();
      expect(adminData.ingestion_service.weather_enrichment.enabled).toBe(true);
      
      // Step 4: Verify enrichment metrics are available
      expect(adminData.ingestion_service.weather_enrichment.cache_hits).toBeDefined();
      expect(adminData.ingestion_service.weather_enrichment.api_calls).toBeDefined();
    });

    test('API Automation Edge to Home Assistant communication', async ({ page }) => {
      // Step 1: Verify API Automation Edge is healthy
      const apiAutomationResponse = await page.request.get('http://localhost:8041/health');
      expect(apiAutomationResponse.status()).toBe(200);
      const apiAutomationData = await apiAutomationResponse.json();
      expect(apiAutomationData.status).toBe('healthy');
      
      // Step 2: Verify API Automation Edge can create specs
      const validSpec = {
        id: 'test_integration_spec',
        version: '1.0.0',
        name: 'Test Integration Spec',
        enabled: true,
        triggers: [
          {
            type: 'ha_event',
            event_type: 'state_changed'
          }
        ],
        actions: [
          {
            id: 'act1',
            capability: 'light.turn_on',
            target: { entity_id: 'light.test' },
            data: {}
          }
        ],
        policy: { risk: 'low' }
      };
      
      const createResponse = await page.request.post('http://localhost:8041/api/specs', {
        data: validSpec
      });
      
      // Should succeed (200) or fail gracefully (400) if HA unavailable
      expect([200, 400]).toContain(createResponse.status());
      
      // Step 3: Verify kill switch status endpoint works
      const killSwitchResponse = await page.request.get('http://localhost:8041/api/observability/kill-switch/status');
      expect(killSwitchResponse.status()).toBe(200);
      const killSwitchData = await killSwitchResponse.json();
      expect(killSwitchData.success).toBe(true);
      expect(killSwitchData.status).toHaveProperty('global_paused');
    });

    test('InfluxDB to all services communication', async ({ page }) => {
      // Step 1: Verify InfluxDB is healthy
      const influxResponse = await page.request.get('http://localhost:8086/health');
      expect(influxResponse.status()).toBe(200);
      const influxData = await influxResponse.json();
      expect(influxData.status).toBe('healthy');
      
      // Step 2: Verify WebSocket service reports InfluxDB connection
      const wsResponse = await page.request.get('http://localhost:8001/health');
      expect(wsResponse.status()).toBe(200);
      
      // Step 3: Verify Enrichment Pipeline reports InfluxDB connection
      const enrichResponse = await page.request.get('http://localhost:8002/health');
      expect(enrichResponse.status()).toBe(200);
      
      // Step 4: Verify Admin API reports InfluxDB connection
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      expect(adminResponse.status()).toBe(200);
      const adminData = await adminResponse.json();
      
      expect(adminData.ingestion_service.influxdb_storage.is_connected).toBe(true);
      expect(adminData.ingestion_service.influxdb_storage.last_write_time).toBeDefined();
      expect(adminData.ingestion_service.influxdb_storage.write_errors).toBeDefined();
    });
  });

  test.describe('Data Consistency Across Services', () => {
    
    test('Event data consistency between services', async ({ page }) => {
      // Step 1: Get events from Admin API
      const eventsResponse = await page.request.get('http://localhost:8006/api/v1/events?limit=10');
      expect(eventsResponse.status()).toBe(200);
      const eventsData = await eventsResponse.json();
      
      if (eventsData.length > 0) {
        const event = eventsData[0];
        
        // Step 2: Verify event structure is consistent
        expect(event).toHaveProperty('id');
        expect(event).toHaveProperty('timestamp');
        expect(event).toHaveProperty('entity_id');
        expect(event).toHaveProperty('event_type');
        
        // Step 3: Verify timestamp format is consistent
        const timestamp = new Date(event.timestamp);
        expect(timestamp.getTime()).not.toBeNaN();
        
        // Step 4: Verify ID format is consistent
        expect(typeof event.id).toBe('string');
        expect(event.id.length).toBeGreaterThan(0);
      }
    });

    test('Statistics consistency across service endpoints', async ({ page }) => {
      // Step 1: Get statistics from Admin API
      const statsResponse = await page.request.get('http://localhost:8004/api/v1/stats');
      expect(statsResponse.status()).toBe(200);
      const statsData = await statsResponse.json();
      
      // Step 2: Verify statistics structure is consistent
      expect(statsData).toHaveProperty('total_events');
      expect(statsData).toHaveProperty('events_per_minute');
      expect(statsData).toHaveProperty('last_event_time');
      
      // Step 3: Verify data types are consistent
      expect(typeof statsData.total_events).toBe('number');
      expect(typeof statsData.events_per_minute).toBe('number');
      expect(typeof statsData.last_event_time).toBe('string');
      
      // Step 4: Verify timestamp format is consistent
      const timestamp = new Date(statsData.last_event_time);
      expect(timestamp.getTime()).not.toBeNaN();
    });

    test('Health status consistency across all services', async ({ page }) => {
      // Step 1: Get health from all services
      const services = [
        { name: 'InfluxDB', url: 'http://localhost:8086/health' },
        { name: 'WebSocket Ingestion', url: 'http://localhost:8001/health' },
        { name: 'Enrichment Pipeline', url: 'http://localhost:8002/health' },
        { name: 'Admin API', url: 'http://localhost:8004/api/v1/health' },
        { name: 'Data Retention', url: 'http://localhost:8080/health' },
        { name: 'API Automation Edge', url: 'http://localhost:8041/health' }
      ];
      
      const healthStatuses = [];
      
      for (const service of services) {
        const response = await page.request.get(service.url);
        if (response.status() === 200) {
          const data = await response.json();
          healthStatuses.push({
            name: service.name,
            status: data.status || data.overall_status,
            timestamp: data.timestamp
          });
        }
      }
      
      // Step 2: Verify all services report healthy status
      healthStatuses.forEach(service => {
        expect(service.status).toBe('healthy');
      });
      
      // Step 3: Verify timestamps are recent
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

  test.describe('Service Failure Scenarios', () => {
    
    test('InfluxDB failure propagation', async ({ page }) => {
      // Step 1: Simulate InfluxDB being unavailable
      await page.route('http://localhost:8086/**', route => route.abort());
      
      // Step 2: Wait for error propagation
      await page.waitForTimeout(5000);
      
      // Step 3: Check that dependent services handle the error gracefully
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
      
      // Step 4: Check that admin API reports degraded status
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (adminResponse.status() === 200) {
        const adminData = await adminResponse.json();
        expect(['degraded', 'unhealthy']).toContain(adminData.overall_status);
      }
      
      // Step 5: Restore InfluxDB
      await page.unroute('http://localhost:8086/**');
      
      // Step 6: Wait for recovery
      await page.waitForTimeout(10000);
      
      // Step 7: Verify system recovers
      const recoveryResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (recoveryResponse.status() === 200) {
        const recoveryData = await recoveryResponse.json();
        expect(recoveryData.overall_status).toBe('healthy');
      }
    });

    test('WebSocket service failure handling', async ({ page }) => {
      // Step 1: Simulate WebSocket service failure
      await page.route('http://localhost:8001/**', route => route.abort());
      
      // Step 2: Wait for error propagation
      await page.waitForTimeout(5000);
      
      // Step 3: Check that admin API reports degraded status
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (adminResponse.status() === 200) {
        const adminData = await adminResponse.json();
        expect(['degraded', 'unhealthy']).toContain(adminData.overall_status);
        
        // WebSocket connection should be reported as disconnected
        expect(adminData.ingestion_service.websocket_connection.is_connected).toBe(false);
      }
      
      // Step 4: Restore WebSocket service
      await page.unroute('http://localhost:8001/**');
      
      // Step 5: Wait for recovery
      await page.waitForTimeout(10000);
      
      // Step 6: Verify system recovers
      const recoveryResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (recoveryResponse.status() === 200) {
        const recoveryData = await recoveryResponse.json();
        expect(recoveryData.overall_status).toBe('healthy');
        expect(recoveryData.ingestion_service.websocket_connection.is_connected).toBe(true);
      }
    });

    test('Enrichment pipeline failure handling', async ({ page }) => {
      // Step 1: Simulate Enrichment Pipeline failure
      await page.route('http://localhost:8002/**', route => route.abort());
      
      // Step 2: Wait for error propagation
      await page.waitForTimeout(5000);
      
      // Step 3: Check that admin API reports degraded status
      const adminResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (adminResponse.status() === 200) {
        const adminData = await adminResponse.json();
        expect(['degraded', 'unhealthy']).toContain(adminData.overall_status);
        
        // Weather enrichment should be reported as disabled
        expect(adminData.ingestion_service.weather_enrichment.enabled).toBe(false);
      }
      
      // Step 4: Restore Enrichment Pipeline
      await page.unroute('http://localhost:8002/**');
      
      // Step 5: Wait for recovery
      await page.waitForTimeout(10000);
      
      // Step 6: Verify system recovers
      const recoveryResponse = await page.request.get('http://localhost:8004/api/v1/health');
      if (recoveryResponse.status() === 200) {
        const recoveryData = await recoveryResponse.json();
        expect(recoveryData.overall_status).toBe('healthy');
        expect(recoveryData.ingestion_service.weather_enrichment.enabled).toBe(true);
      }
    });
  });

  test.describe('Configuration Propagation', () => {
    
    test('Configuration changes propagate across services', async ({ page }) => {
      // Step 1: Get current configuration
      const configResponse = await page.request.get('http://localhost:8004/api/v1/config');
      expect(configResponse.status()).toBe(200);
      
      const configData = await configResponse.json();
      const originalConfig = { ...configData };
      
      // Step 2: Update configuration
      const updatedConfig = {
        ...configData,
        refresh_interval: 60000
      };
      
      const updateResponse = await page.request.put('http://localhost:8004/api/v1/config', {
        data: updatedConfig
      });
      
      if (updateResponse.status() === 200) {
        // Step 3: Verify configuration was updated
        const verifyResponse = await page.request.get('http://localhost:8004/api/v1/config');
        const verifyData = await verifyResponse.json();
        
        expect(verifyData.refresh_interval).toBe(60000);
        
        // Step 4: Restore original configuration
        await page.request.put('http://localhost:8004/api/v1/config', {
          data: originalConfig
        });
      }
    });

    test('Service-specific configuration validation', async ({ page }) => {
      // Step 1: Test InfluxDB configuration
      const influxConfigResponse = await page.request.get('http://localhost:8004/api/v1/config');
      expect(influxConfigResponse.status()).toBe(200);
      
      const configData = await influxConfigResponse.json();
      expect(configData.influxdb).toBeDefined();
      expect(configData.influxdb.url).toBeDefined();
      expect(configData.influxdb.org).toBeDefined();
      expect(configData.influxdb.bucket).toBeDefined();
      
      // Step 2: Test service configuration structure
      expect(configData.services).toBeDefined();
      expect(typeof configData.services).toBe('object');
    });
  });
});
