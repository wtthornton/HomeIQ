/**
 * RAG State Calculation Utilities
 * 
 * Calculates Red/Amber/Green states based on component metrics and thresholds
 */

import { 
  RAGState, 
  ComponentMetrics, 
  RAGThresholds, 
  ComponentRAGState,
  RAGStatus,
  DEFAULT_RAG_THRESHOLDS 
} from '../types/rag';
import { ServiceHealthResponse, DependencyHealth } from '../types/health';
import { Statistics } from '../types';

/**
 * Calculate RAG state for a single component
 */
export function calculateComponentRAG(
  component: 'websocket' | 'processing' | 'storage',
  metrics: ComponentMetrics,
  thresholds: RAGThresholds = DEFAULT_RAG_THRESHOLDS
): ComponentRAGState {
  const componentThresholds = thresholds[component];
  const reasons: string[] = [];
  let state: RAGState = 'green';

  // Check thresholds based on component type
  if (component === 'websocket') {
    const latency = metrics.latency ?? metrics.responseTime ?? 0;
    const errorRate = metrics.errorRate ?? 0;

    // Check red thresholds (2x amber)
    if (latency > componentThresholds.amber.latency * 2 || 
        errorRate > componentThresholds.amber.errorRate * 2) {
      state = 'red';
      if (latency > componentThresholds.amber.latency * 2) {
        reasons.push(`High latency: ${latency.toFixed(1)}ms (threshold: ${componentThresholds.amber.latency * 2}ms)`);
      }
      if (errorRate > componentThresholds.amber.errorRate * 2) {
        reasons.push(`High error rate: ${errorRate.toFixed(2)}% (threshold: ${componentThresholds.amber.errorRate * 2}%)`);
      }
    }
    // Check amber thresholds
    else if (latency > componentThresholds.amber.latency || 
             errorRate > componentThresholds.amber.errorRate) {
      state = 'amber';
      if (latency > componentThresholds.amber.latency) {
        reasons.push(`Elevated latency: ${latency.toFixed(1)}ms (threshold: ${componentThresholds.amber.latency}ms)`);
      }
      if (errorRate > componentThresholds.amber.errorRate) {
        reasons.push(`Elevated error rate: ${errorRate.toFixed(2)}% (threshold: ${componentThresholds.amber.errorRate}%)`);
      }
    } else {
      reasons.push('All metrics within normal thresholds');
    }
  } 
  else if (component === 'processing') {
    const throughput = metrics.throughput ?? undefined;
    const errorRate = metrics.errorRate ?? 0;
    const latency = metrics.latency ?? 0;

    // Context-aware threshold adjustment
    // If system is healthy (no errors, low latency), be more lenient with throughput
    // This prevents false positives during normal low-activity periods
    const isSystemHealthy = errorRate === 0 && latency < 20;
    const adjustedAmberThreshold = isSystemHealthy 
      ? componentThresholds.amber.throughput * 0.6  // 60% of threshold (3 evt/min when healthy)
      : componentThresholds.amber.throughput;       // Standard threshold (5 evt/min)

    // If throughput is undefined/null, we don't have data yet - default to green
    // This prevents false RED status when data is still loading
    if (throughput === undefined || throughput === null) {
      state = 'green';
      reasons.push('Metrics data not yet available - assuming healthy');
    }
    // Check red thresholds (throughput too low or error rate too high)
    else if (throughput < adjustedAmberThreshold * 0.5 || 
        errorRate > 5.0) {
      state = 'red';
      if (throughput < adjustedAmberThreshold * 0.5) {
        reasons.push(`Low throughput: ${throughput.toFixed(1)} evt/min (threshold: ${(adjustedAmberThreshold * 0.5).toFixed(1)} evt/min)`);
      }
      if (errorRate > 5.0) {
        reasons.push(`High error rate: ${errorRate.toFixed(2)}% (threshold: 5.0%)`);
      }
    }
    // Check amber thresholds
    else if (throughput < adjustedAmberThreshold || 
             errorRate > 2.0) {
      state = 'amber';
      if (throughput < adjustedAmberThreshold) {
        reasons.push(`Reduced throughput: ${throughput.toFixed(1)} evt/min (threshold: ${adjustedAmberThreshold.toFixed(1)} evt/min, ${isSystemHealthy ? 'adjusted for healthy system' : 'standard'})`);
      }
      if (errorRate > 2.0) {
        reasons.push(`Elevated error rate: ${errorRate.toFixed(2)}% (threshold: 2.0%)`);
      }
    } else {
      reasons.push('All metrics within normal thresholds');
    }
  }
  else if (component === 'storage') {
    const latency = metrics.latency ?? metrics.responseTime ?? 0;
    const errorRate = metrics.errorRate ?? 0;

    // Check red thresholds
    if (latency > componentThresholds.amber.latency * 2 || 
        errorRate > componentThresholds.amber.errorRate * 2) {
      state = 'red';
      if (latency > componentThresholds.amber.latency * 2) {
        reasons.push(`High latency: ${latency.toFixed(1)}ms (threshold: ${componentThresholds.amber.latency * 2}ms)`);
      }
      if (errorRate > componentThresholds.amber.errorRate * 2) {
        reasons.push(`High error rate: ${errorRate.toFixed(2)}% (threshold: ${componentThresholds.amber.errorRate * 2}%)`);
      }
    }
    // Check amber thresholds
    else if (latency > componentThresholds.amber.latency || 
             errorRate > componentThresholds.amber.errorRate) {
      state = 'amber';
      if (latency > componentThresholds.amber.latency) {
        reasons.push(`Elevated latency: ${latency.toFixed(1)}ms (threshold: ${componentThresholds.amber.latency}ms)`);
      }
      if (errorRate > componentThresholds.amber.errorRate) {
        reasons.push(`Elevated error rate: ${errorRate.toFixed(2)}% (threshold: ${componentThresholds.amber.errorRate}%)`);
      }
    } else {
      reasons.push('All metrics within normal thresholds');
    }
  }

  return {
    component,
    state,
    metrics,
    reasons,
    lastUpdated: new Date()
  };
}

/**
 * Calculate overall RAG state from component states
 */
export function calculateOverallRAG(components: {
  websocket: ComponentRAGState;
  processing: ComponentRAGState;
  storage: ComponentRAGState;
}): RAGState {
  const states = [components.websocket.state, components.processing.state, components.storage.state];
  
  // If any component is red, overall is red
  if (states.includes('red')) return 'red';
  
  // If any component is amber, overall is amber
  if (states.includes('amber')) return 'amber';
  
  // All components are green
  return 'green';
}

/**
 * Extract metrics from health and statistics data
 */
export function extractComponentMetrics(
  enhancedHealth: ServiceHealthResponse | null,
  statistics: Statistics | null
): {
  websocket: ComponentMetrics;
  processing: ComponentMetrics;
  storage: ComponentMetrics;
} {
  // Extract WebSocket metrics
  const websocketDependency = enhancedHealth?.dependencies?.find(d => 
    d.name === 'WebSocket Ingestion' || d.type === 'websocket'
  );
  const websocketStats = statistics?.metrics?.['websocket-ingestion'];
  
  const websocketMetrics: ComponentMetrics = {
    latency: websocketDependency?.response_time_ms ?? websocketStats?.response_time_ms,
    errorRate: websocketStats?.error_rate ?? (websocketDependency?.status === 'unhealthy' ? 5.0 : 0),
    throughput: websocketStats?.events_per_minute,
    availability: websocketDependency?.status === 'healthy' ? 100 : 
                  websocketDependency?.status === 'degraded' ? 75 : 0
  };

  // Extract Processing metrics (using websocket-ingestion as proxy)
  // Note: queue_size is not available in Statistics, using throughput as primary indicator
  // Only set throughput if we have actual data (not 0 or undefined)
  // Use websocket latency as proxy for processing latency (processing is part of websocket-ingestion)
  const processingMetrics: ComponentMetrics = {
    throughput: websocketStats?.events_per_minute && websocketStats.events_per_minute > 0 
      ? websocketStats.events_per_minute 
      : undefined,
    queueSize: 0, // Not available in current Statistics API
    errorRate: websocketStats?.error_rate ?? 0,
    latency: websocketDependency?.response_time_ms ?? websocketStats?.response_time_ms
  };

  // Extract Storage metrics
  const storageDependency = enhancedHealth?.dependencies?.find(d => 
    d.name === 'InfluxDB' || d.type === 'database'
  );
  
  const storageMetrics: ComponentMetrics = {
    latency: storageDependency?.response_time_ms,
    errorRate: storageDependency?.status === 'unhealthy' ? 5.0 : 
               storageDependency?.status === 'degraded' ? 1.0 : 0,
    availability: storageDependency?.status === 'healthy' ? 100 : 
                  storageDependency?.status === 'degraded' ? 75 : 0,
    responseTime: storageDependency?.response_time_ms
  };

  return {
    websocket: websocketMetrics,
    processing: processingMetrics,
    storage: storageMetrics
  };
}

/**
 * Calculate complete RAG status from health and statistics data
 */
export function calculateRAGStatus(
  enhancedHealth: ServiceHealthResponse | null,
  statistics: Statistics | null,
  thresholds: RAGThresholds = DEFAULT_RAG_THRESHOLDS
): RAGStatus {
  const metrics = extractComponentMetrics(enhancedHealth, statistics);

  const websocket = calculateComponentRAG('websocket', metrics.websocket, thresholds);
  const processing = calculateComponentRAG('processing', metrics.processing, thresholds);
  const storage = calculateComponentRAG('storage', metrics.storage, thresholds);

  const overall = calculateOverallRAG({ websocket, processing, storage });

  return {
    overall,
    components: {
      websocket,
      processing,
      storage
    },
    lastUpdated: new Date()
  };
}

