/**
 * Performance Tracking Utility
 * 
 * Tracks performance metrics for the send button flow and other operations.
 * Provides detailed timing information for optimization analysis.
 */

export interface PerformanceMetric {
  name: string;
  startTime: number;
  endTime?: number;
  duration?: number;
  metadata?: Record<string, any>;
}

export interface PerformanceReport {
  operation: string;
  totalDuration: number;
  metrics: PerformanceMetric[];
  timestamp: number;
}

class PerformanceTracker {
  private metrics: Map<string, PerformanceMetric> = new Map();
  private reports: PerformanceReport[] = [];
  private maxReports = 100; // Keep last 100 reports

  /**
   * Start tracking a metric
   */
  start(name: string, metadata?: Record<string, any>): string {
    const id = `${name}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    this.metrics.set(id, {
      name,
      startTime: performance.now(),
      metadata,
    });
    return id;
  }

  /**
   * End tracking a metric
   */
  end(id: string, metadata?: Record<string, any>): PerformanceMetric | null {
    const metric = this.metrics.get(id);
    if (!metric) {
      console.warn(`Performance metric ${id} not found`);
      return null;
    }

    const endTime = performance.now();
    const duration = endTime - metric.startTime;

    const completedMetric: PerformanceMetric = {
      ...metric,
      endTime,
      duration,
      metadata: {
        ...metric.metadata,
        ...metadata,
      },
    };

    this.metrics.set(id, completedMetric);
    return completedMetric;
  }

  /**
   * Create a performance report for an operation
   */
  createReport(operation: string, metricIds: string[]): PerformanceReport {
    const metrics = metricIds
      .map((id) => this.metrics.get(id))
      .filter((m): m is PerformanceMetric => m !== undefined && m.duration !== undefined);

    const totalDuration = metrics.reduce((sum, m) => sum + (m.duration || 0), 0);

    const report: PerformanceReport = {
      operation,
      totalDuration,
      metrics,
      timestamp: Date.now(),
    };

    // Keep only last N reports
    this.reports.push(report);
    if (this.reports.length > this.maxReports) {
      this.reports.shift();
    }

    // Log to console for debugging
    console.log(`[Performance] ${operation}:`, {
      totalDuration: `${totalDuration.toFixed(2)}ms`,
      metrics: metrics.map((m) => ({
        name: m.name,
        duration: `${m.duration?.toFixed(2)}ms`,
        metadata: m.metadata,
      })),
    });

    return report;
  }

  /**
   * Get all reports
   */
  getReports(): PerformanceReport[] {
    return [...this.reports];
  }

  /**
   * Get reports for a specific operation
   */
  getReportsForOperation(operation: string): PerformanceReport[] {
    return this.reports.filter((r) => r.operation === operation);
  }

  /**
   * Get average duration for an operation
   */
  getAverageDuration(operation: string): number {
    const reports = this.getReportsForOperation(operation);
    if (reports.length === 0) return 0;
    const total = reports.reduce((sum, r) => sum + r.totalDuration, 0);
    return total / reports.length;
  }

  /**
   * Clear all metrics and reports
   */
  clear(): void {
    this.metrics.clear();
    this.reports = [];
  }

  /**
   * Export reports as JSON
   */
  exportReports(): string {
    return JSON.stringify(this.reports, null, 2);
  }
}

// Singleton instance
export const performanceTracker = new PerformanceTracker();

// Export convenience functions
export const startTracking = (name: string, metadata?: Record<string, any>) =>
  performanceTracker.start(name, metadata);

export const endTracking = (id: string, metadata?: Record<string, any>) =>
  performanceTracker.end(id, metadata);

export const createReport = (operation: string, metricIds: string[]) =>
  performanceTracker.createReport(operation, metricIds);

