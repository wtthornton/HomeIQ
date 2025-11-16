import { useState, useEffect } from 'react';
import { aiApi } from '../services/api';

// Export interfaces for reuse
export interface CallPatterns {
  direct_calls: number;
  orchestrated_calls: number;
}

export interface Performance {
  avg_direct_latency_ms: number;
  avg_orch_latency_ms: number;
}

export interface ModelUsage {
  total_queries: number;
  ner_success: number;
  openai_success: number;
  pattern_fallback: number;
  avg_processing_time: number;
  total_cost_usd: number;
}

export interface AIStatsData {
  call_patterns: CallPatterns;
  performance: Performance;
  model_usage: ModelUsage;
  error?: string;
}

// Export fetch function for reuse
export const fetchAIStats = async (): Promise<AIStatsData> => {
  return aiApi.getStats();
};

export const AIStats = () => {
  const [stats, setStats] = useState<AIStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await fetchAIStats();
        setStats(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stats');
      } finally {
        setLoading(false);
      }
    };

    loadStats();
    
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div>Loading AI service statistics...</div>;
  }

  if (error || stats?.error) {
    return <div>Error loading stats: {error || stats?.error}</div>;
  }

  if (!stats) {
    return <div>No stats available</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h2>AI Service Statistics</h2>
      
      <div style={{ marginTop: '20px' }}>
        <h3>Call Patterns</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px' }}>
          <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
            <div style={{ fontWeight: 'bold', fontSize: '24px' }}>{stats.call_patterns?.direct_calls || 0}</div>
            <div style={{ color: '#666' }}>Direct Calls</div>
          </div>
          <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
            <div style={{ fontWeight: 'bold', fontSize: '24px' }}>{stats.call_patterns?.orchestrated_calls || 0}</div>
            <div style={{ color: '#666' }}>Orchestrated Calls</div>
          </div>
        </div>
      </div>

      {stats.performance && (
        <div style={{ marginTop: '20px' }}>
          <h3>Performance</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '10px' }}>
            <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 'bold', fontSize: '20px' }}>
                {stats.performance.avg_direct_latency_ms?.toFixed(2) || '0.00'} ms
              </div>
              <div style={{ color: '#666' }}>Avg Direct Latency</div>
            </div>
            <div style={{ border: '1px solid #ccc', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontWeight: 'bold', fontSize: '20px' }}>
                {stats.performance.avg_orch_latency_ms?.toFixed(2) || '0.00'} ms
              </div>
              <div style={{ color: '#666' }}>Avg Orchestrated Latency</div>
            </div>
          </div>
        </div>
      )}

      {stats.model_usage && (
        <div style={{ marginTop: '20px' }}>
          <h3>Model Usage</h3>
          <div style={{ marginTop: '10px' }}>
            <div>Total Queries: {stats.model_usage.total_queries || 0}</div>
            <div>NER Success: {stats.model_usage.ner_success || 0}</div>
            <div>OpenAI Success: {stats.model_usage.openai_success || 0}</div>
            <div>Pattern Fallback: {stats.model_usage.pattern_fallback || 0}</div>
            <div>Avg Processing Time: {(stats.model_usage.avg_processing_time || 0).toFixed(3)}s</div>
            <div>Total Cost: ${(stats.model_usage.total_cost_usd || 0).toFixed(4)}</div>
          </div>
        </div>
      )}
    </div>
  );
};
