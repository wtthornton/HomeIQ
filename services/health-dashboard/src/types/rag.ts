/**
 * RAG (Red/Amber/Green) State Types
 * 
 * Defines types for RAG state tracking and calculation
 */

export type RAGState = 'green' | 'amber' | 'red';

export interface ComponentMetrics {
  latency?: number; // milliseconds
  errorRate?: number; // percentage (0-100)
  throughput?: number; // events per minute
  queueSize?: number; // number of items in queue
  availability?: number; // percentage (0-100)
  responseTime?: number; // milliseconds
}

export interface RAGThresholds {
  websocket: {
    green: { latency: number; errorRate: number };
    amber: { latency: number; errorRate: number };
  };
  processing: {
    green: { throughput: number; queueSize: number };
    amber: { throughput: number; queueSize: number };
  };
  storage: {
    green: { latency: number; errorRate: number };
    amber: { latency: number; errorRate: number };
  };
}

export interface ComponentRAGState {
  component: 'websocket' | 'processing' | 'storage';
  state: RAGState;
  metrics: ComponentMetrics;
  reasons: string[]; // Reasons for current RAG state
  lastUpdated: Date;
}

export interface RAGStatus {
  overall: RAGState;
  components: {
    websocket: ComponentRAGState;
    processing: ComponentRAGState;
    storage: ComponentRAGState;
  };
  lastUpdated: Date;
}

// Default thresholds for RAG calculation
export const DEFAULT_RAG_THRESHOLDS: RAGThresholds = {
  websocket: {
    green: { latency: 50, errorRate: 0.5 },
    amber: { latency: 100, errorRate: 2.0 }
  },
  processing: {
    green: { throughput: 100, queueSize: 10 },
    amber: { throughput: 50, queueSize: 50 }
  },
  storage: {
    green: { latency: 20, errorRate: 0.1 },
    amber: { latency: 50, errorRate: 1.0 }
  }
};

