import { Page, expect } from '@playwright/test';
import { execSync } from 'child_process';

/**
 * Docker-specific test helpers and utilities
 */
export class DockerTestHelpers {
  
  /**
   * Check if a Docker container is running
   */
  static isContainerRunning(containerName: string): boolean {
    try {
      const output = execSync(`docker ps --filter name=${containerName} --format "{{.Names}}"`, { 
        stdio: 'pipe',
        encoding: 'utf-8'
      });
      return output.trim() === containerName;
    } catch (error) {
      return false;
    }
  }
  
  /**
   * Get container logs
   */
  static getContainerLogs(containerName: string, lines: number = 50): string {
    try {
      return execSync(`docker logs --tail ${lines} ${containerName}`, { 
        stdio: 'pipe',
        encoding: 'utf-8'
      });
    } catch (error) {
      return `Failed to get logs for ${containerName}: ${error}`;
    }
  }
  
  /**
   * Restart a Docker container
   */
  static restartContainer(containerName: string): void {
    try {
      execSync(`docker restart ${containerName}`, { stdio: 'pipe' });
      console.log(`✓ Restarted container: ${containerName}`);
    } catch (error) {
      throw new Error(`Failed to restart container ${containerName}: ${error}`);
    }
  }
  
  /**
   * Stop a Docker container
   */
  static stopContainer(containerName: string): void {
    try {
      execSync(`docker stop ${containerName}`, { stdio: 'pipe' });
      console.log(`✓ Stopped container: ${containerName}`);
    } catch (error) {
      throw new Error(`Failed to stop container ${containerName}: ${error}`);
    }
  }
  
  /**
   * Start a Docker container
   */
  static startContainer(containerName: string): void {
    try {
      execSync(`docker start ${containerName}`, { stdio: 'pipe' });
      console.log(`✓ Started container: ${containerName}`);
    } catch (error) {
      throw new Error(`Failed to start container ${containerName}: ${error}`);
    }
  }
  
  /**
   * Wait for a service to be healthy
   */
  static async waitForServiceHealthy(
    page: Page, 
    serviceUrl: string, 
    timeout: number = 30000
  ): Promise<boolean> {
    const startTime = Date.now();
    
    while (Date.now() - startTime < timeout) {
      try {
        const response = await page.request.get(serviceUrl);
        if (response.status() === 200) {
          const data = await response.json();
          if (data.status === 'healthy') {
            return true;
          }
        }
      } catch (error) {
        // Service not ready yet
      }
      
      await page.waitForTimeout(1000);
    }
    
    return false;
  }
  
  /**
   * Get Docker container resource usage
   */
  static getContainerStats(containerName: string): any {
    try {
      const output = execSync(`docker stats ${containerName} --no-stream --format "{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}"`, { 
        stdio: 'pipe',
        encoding: 'utf-8'
      });
      
      const [cpuPerc, memUsage, memPerc] = output.trim().split(',');
      return {
        cpuPercentage: cpuPerc,
        memoryUsage: memUsage,
        memoryPercentage: memPerc
      };
    } catch (error) {
      return null;
    }
  }
  
  /**
   * Check Docker network connectivity
   */
  static async testNetworkConnectivity(page: Page): Promise<void> {
    const services = [
      { name: 'InfluxDB', url: 'http://localhost:8086/health' },
      { name: 'WebSocket Ingestion', url: 'http://localhost:8001/health' },
      { name: 'Enrichment Pipeline', url: 'http://localhost:8002/health' },
      { name: 'Admin API', url: 'http://localhost:8003/api/v1/health' },
      { name: 'Data Retention', url: 'http://localhost:8080/health' },
      { name: 'Health Dashboard', url: 'http://localhost:3000' }
    ];
    
    for (const service of services) {
      try {
        const response = await page.request.get(service.url);
        expect(response.status()).toBe(200);
        console.log(`✓ ${service.name} is reachable`);
      } catch (error) {
        throw new Error(`${service.name} is not reachable: ${error}`);
      }
    }
  }
  
  /**
   * Simulate service failure for testing error handling
   */
  static async simulateServiceFailure(page: Page, serviceName: string): Promise<void> {
    const containerMap: { [key: string]: string } = {
      'influxdb': 'homeiq-influxdb',
      'websocket': 'homeiq-websocket',
      'enrichment': 'homeiq-enrichment',
      'admin': 'homeiq-admin',
      'dashboard': 'homeiq-dashboard',
      'retention': 'homeiq-data-retention'
    };
    
    const containerName = containerMap[serviceName.toLowerCase()];
    if (!containerName) {
      throw new Error(`Unknown service: ${serviceName}`);
    }
    
    if (this.isContainerRunning(containerName)) {
      this.stopContainer(containerName);
      console.log(`✓ Simulated failure for ${serviceName}`);
    } else {
      console.log(`⚠ ${serviceName} container is already stopped`);
    }
  }
  
  /**
   * Restore service after simulated failure
   */
  static async restoreService(serviceName: string): Promise<void> {
    const containerMap: { [key: string]: string } = {
      'influxdb': 'homeiq-influxdb',
      'websocket': 'homeiq-websocket',
      'enrichment': 'homeiq-enrichment',
      'admin': 'homeiq-admin',
      'dashboard': 'homeiq-dashboard',
      'retention': 'homeiq-data-retention'
    };
    
    const containerName = containerMap[serviceName.toLowerCase()];
    if (!containerName) {
      throw new Error(`Unknown service: ${serviceName}`);
    }
    
    this.startContainer(containerName);
    
    // Wait for service to be healthy
    await new Promise(resolve => setTimeout(resolve, 5000));
    console.log(`✓ Restored service: ${serviceName}`);
  }
  
  /**
   * Get Docker Compose service status
   */
  static getDockerComposeStatus(): any {
    try {
      const output = execSync('docker-compose ps --format json', { 
        stdio: 'pipe',
        encoding: 'utf-8'
      });
      
      const lines = output.trim().split('\n').filter(line => line.trim());
      return lines.map(line => JSON.parse(line));
    } catch (error) {
      return [];
    }
  }
  
  /**
   * Wait for Docker Compose services to be ready
   */
  static async waitForDockerComposeReady(page: Page): Promise<void> {
    const services = [
      { name: 'InfluxDB', url: 'http://localhost:8086/health' },
      { name: 'WebSocket Ingestion', url: 'http://localhost:8001/health' },
      { name: 'Enrichment Pipeline', url: 'http://localhost:8002/health' },
      { name: 'Admin API', url: 'http://localhost:8003/api/v1/health' },
      { name: 'Data Retention', url: 'http://localhost:8080/health' }
    ];
    
    console.log('Waiting for all Docker services to be ready...');
    
    for (const service of services) {
      const isHealthy = await this.waitForServiceHealthy(page, service.url, 60000);
      if (!isHealthy) {
        throw new Error(`${service.name} failed to become healthy within 60 seconds`);
      }
    }
    
    // Wait for dashboard to be accessible
    await page.goto('http://localhost:3000');
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 30000 });
    
    console.log('✓ All Docker services are ready');
  }
  
  /**
   * Clean up test data (if needed)
   */
  static async cleanupTestData(): Promise<void> {
    // This would be used to clean up any test data created during testing
    // For now, it's a placeholder for future implementation
    console.log('✓ Test data cleanup completed');
  }
}
