import React, { useState, useEffect, useCallback } from 'react';
import { TabProps } from './types';
import { Card, CardHeader, CardTitle, CardContent } from '../ui/card';
import { SkeletonCard } from '../skeletons';
import { TrustScoreWidget, TrustScoreStats, useTrustScores } from '../TrustScores';

interface MemoryStats {
  total: number;
  by_type: Record<string, number>;
  by_confidence: { high: number; medium: number; low: number };
  recent_24h: number;
  archived: number;
  contradictions: number;
}

interface MemoryEntry {
  id: string;
  type: string;
  content: string;
  confidence: number;
  created_at: string;
  accessed_at: string;
  access_count: number;
  tier?: string;
  source?: string;
}

interface ConsolidationStatus {
  last_run: string | null;
  next_scheduled: string | null;
  status: 'idle' | 'running' | 'error';
  memories_processed?: number;
  memories_archived?: number;
  error_message?: string;
}

interface MemoryMetrics {
  counters: Record<string, number>;
  search_latency: { count: number; min: number; max: number; avg: number; p50: number; p95: number; p99: number };
  embedding_latency: { count: number; min: number; max: number; avg: number; p50: number; p95: number; p99: number };
}

const API_BASE = '/api/v1';

export const MemoryTab: React.FC<TabProps> = ({ darkMode }) => {
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [recentMemories, setRecentMemories] = useState<MemoryEntry[]>([]);
  const [consolidation, setConsolidation] = useState<ConsolidationStatus | null>(null);
  const [metrics, setMetrics] = useState<MemoryMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const { scores: trustScores } = useTrustScores();

  const fetchData = useCallback(async () => {
    try {
      setError(null);

      const [statsRes, memoriesRes, consolidationRes, metricsRes] = await Promise.allSettled([
        fetch(`${API_BASE}/memories/stats`),
        fetch(`${API_BASE}/memories?limit=10&sort=created_at:desc`),
        fetch(`${API_BASE}/memories/consolidation/status`),
        fetch(`${API_BASE}/memories/metrics`)
      ]);

      if (statsRes.status === 'fulfilled' && statsRes.value.ok) {
        setStats(await statsRes.value.json());
      }

      if (memoriesRes.status === 'fulfilled' && memoriesRes.value.ok) {
        const data = await memoriesRes.value.json();
        setRecentMemories(data.memories || data.items || []);
      }

      if (consolidationRes.status === 'fulfilled' && consolidationRes.value.ok) {
        setConsolidation(await consolidationRes.value.json());
      }

      if (metricsRes.status === 'fulfilled' && metricsRes.value.ok) {
        setMetrics(await metricsRes.value.json());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load memory data');
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerAction = useCallback(async (action: string) => {
    setActionStatus(`Running ${action}...`);
    try {
      const res = await fetch(`${API_BASE}/memories/${action}`, { method: 'POST' });
      if (res.ok) {
        setActionStatus(`${action} completed successfully`);
        fetchData();
      } else {
        setActionStatus(`${action} failed: ${res.statusText}`);
      }
    } catch (err) {
      setActionStatus(`${action} failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
    setTimeout(() => setActionStatus(null), 5000);
  }, [fetchData]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return darkMode ? 'text-green-400' : 'text-green-600';
    if (confidence >= 0.5) return darkMode ? 'text-yellow-400' : 'text-yellow-600';
    return darkMode ? 'text-red-400' : 'text-red-600';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const getTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      architectural: '🏗️',
      pattern: '🔄',
      context: '📝',
      decision: '🎯',
      fact: '📌',
      preference: '⭐',
    };
    return icons[type.toLowerCase()] || '💭';
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🧠 Memory Brain
        </h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <SkeletonCard variant="metric" />
          <SkeletonCard variant="metric" />
          <SkeletonCard variant="metric" />
          <SkeletonCard variant="metric" />
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="space-y-6">
        <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🧠 Memory Brain
        </h1>
        <div className={`p-6 rounded-lg border ${
          darkMode ? 'bg-red-900/20 border-red-700' : 'bg-red-50 border-red-200'
        }`}>
          <p className={`font-medium ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
            Failed to load memory data
          </p>
          <p className={`text-sm mt-1 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
            {error}
          </p>
          <button
            onClick={fetchData}
            className={`mt-4 px-4 py-2 rounded text-sm font-medium ${
              darkMode ? 'bg-red-700 hover:bg-red-600 text-white' : 'bg-red-100 hover:bg-red-200 text-red-800'
            }`}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const totalByConfidence = stats ? (stats.by_confidence.high + stats.by_confidence.medium + stats.by_confidence.low) : 0;
  const highPercent = totalByConfidence > 0 ? Math.round((stats?.by_confidence.high || 0) / totalByConfidence * 100) : 0;
  const mediumPercent = totalByConfidence > 0 ? Math.round((stats?.by_confidence.medium || 0) / totalByConfidence * 100) : 0;
  const lowPercent = totalByConfidence > 0 ? Math.round((stats?.by_confidence.low || 0) / totalByConfidence * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🧠 Memory Brain
        </h1>
        <button
          onClick={fetchData}
          className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
            darkMode ? 'bg-gray-700 hover:bg-gray-600 text-white' : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
          }`}
        >
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>Total Memories</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-3xl">📚</span>
              <span className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {stats?.total ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>Recent (24h)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-3xl">⏰</span>
              <span className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {stats?.recent_24h ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>Archived</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-3xl">📦</span>
              <span className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {stats?.archived ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>Contradictions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-3xl">⚠️</span>
              <span className={`text-3xl font-bold ${
                (stats?.contradictions ?? 0) > 0 
                  ? (darkMode ? 'text-yellow-400' : 'text-yellow-600')
                  : (darkMode ? 'text-white' : 'text-gray-900')
              }`}>
                {stats?.contradictions ?? 0}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Trust Score Stats Overview */}
      {trustScores.length > 0 && (
        <TrustScoreStats scores={trustScores} darkMode={darkMode} />
      )}

      {/* Confidence Distribution, Type Distribution, and Trust Scores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Confidence Distribution */}
        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>
              📈 Confidence Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* High Confidence */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className={darkMode ? 'text-green-400' : 'text-green-600'}>
                    High (&ge;80%)
                  </span>
                  <span className={darkMode ? 'text-gray-300' : 'text-gray-600'}>
                    {stats?.by_confidence.high ?? 0} ({highPercent}%)
                  </span>
                </div>
                <div className={`h-3 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div
                    className="h-full rounded-full bg-green-500 transition-all duration-500"
                    style={{ width: `${highPercent}%` }}
                  />
                </div>
              </div>

              {/* Medium Confidence */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className={darkMode ? 'text-yellow-400' : 'text-yellow-600'}>
                    Medium (50-79%)
                  </span>
                  <span className={darkMode ? 'text-gray-300' : 'text-gray-600'}>
                    {stats?.by_confidence.medium ?? 0} ({mediumPercent}%)
                  </span>
                </div>
                <div className={`h-3 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div
                    className="h-full rounded-full bg-yellow-500 transition-all duration-500"
                    style={{ width: `${mediumPercent}%` }}
                  />
                </div>
              </div>

              {/* Low Confidence */}
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className={darkMode ? 'text-red-400' : 'text-red-600'}>
                    Low (&lt;50%)
                  </span>
                  <span className={darkMode ? 'text-gray-300' : 'text-gray-600'}>
                    {stats?.by_confidence.low ?? 0} ({lowPercent}%)
                  </span>
                </div>
                <div className={`h-3 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div
                    className="h-full rounded-full bg-red-500 transition-all duration-500"
                    style={{ width: `${lowPercent}%` }}
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Type Distribution */}
        <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
          <CardHeader>
            <CardTitle className={darkMode ? 'text-gray-300' : ''}>
              📊 Memory Types
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats?.by_type && Object.entries(stats.by_type).length > 0 ? (
                Object.entries(stats.by_type)
                  .sort(([, a], [, b]) => b - a)
                  .map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span>{getTypeIcon(type)}</span>
                        <span className={`text-sm font-medium capitalize ${
                          darkMode ? 'text-gray-300' : 'text-gray-700'
                        }`}>
                          {type}
                        </span>
                      </div>
                      <span className={`text-sm font-semibold ${
                        darkMode ? 'text-white' : 'text-gray-900'
                      }`}>
                        {count}
                      </span>
                    </div>
                  ))
              ) : (
                <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                  No memory types available
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Trust Scores Widget */}
        <TrustScoreWidget darkMode={darkMode} />
      </div>

      {/* Consolidation Job Status */}
      <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
        <CardHeader>
          <CardTitle className={darkMode ? 'text-gray-300' : ''}>
            ⚙️ Consolidation Job
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <p className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Status
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className={`inline-block w-2 h-2 rounded-full ${
                  consolidation?.status === 'running' ? 'bg-blue-500 animate-pulse' :
                  consolidation?.status === 'error' ? 'bg-red-500' : 'bg-green-500'
                }`} />
                <span className={`text-sm font-medium capitalize ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}>
                  {consolidation?.status ?? 'Unknown'}
                </span>
              </div>
            </div>
            <div>
              <p className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Last Run
              </p>
              <p className={`text-sm mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {consolidation?.last_run ? formatDate(consolidation.last_run) : 'Never'}
              </p>
            </div>
            <div>
              <p className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Next Scheduled
              </p>
              <p className={`text-sm mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {consolidation?.next_scheduled ? formatDate(consolidation.next_scheduled) : 'N/A'}
              </p>
            </div>
            <div>
              <p className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                Last Processed
              </p>
              <p className={`text-sm mt-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {consolidation?.memories_processed ?? 0} processed, {consolidation?.memories_archived ?? 0} archived
              </p>
            </div>
          </div>
          {consolidation?.error_message && (
            <div className={`mt-4 p-3 rounded ${
              darkMode ? 'bg-red-900/20 border border-red-700' : 'bg-red-50 border border-red-200'
            }`}>
              <p className={`text-sm ${darkMode ? 'text-red-300' : 'text-red-700'}`}>
                {consolidation.error_message}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Operational Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Search Latency */}
          <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
            <CardHeader>
              <CardTitle className={darkMode ? 'text-gray-300' : ''}>
                Search Latency (ms)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-4 gap-3">
                {(['p50', 'p95', 'p99', 'avg'] as const).map((key) => (
                  <div key={key} className="text-center">
                    <p className={`text-xs font-medium uppercase ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {key}
                    </p>
                    <p className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {metrics.search_latency[key]?.toFixed(1) ?? '—'}
                    </p>
                  </div>
                ))}
              </div>
              <p className={`text-xs mt-3 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                {metrics.search_latency.count} searches recorded
              </p>
            </CardContent>
          </Card>

          {/* Operation Counters */}
          <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
            <CardHeader>
              <CardTitle className={darkMode ? 'text-gray-300' : ''}>
                Operation Counters
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(metrics.counters).length > 0 ? (
                  Object.entries(metrics.counters)
                    .sort(([, a], [, b]) => b - a)
                    .map(([name, count]) => (
                      <div key={name} className="flex items-center justify-between">
                        <span className={`text-sm font-mono ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          {name.replace('memory_', '').replace(/_/g, ' ')}
                        </span>
                        <span className={`text-sm font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                          {count}
                        </span>
                      </div>
                    ))
                ) : (
                  <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                    No operations recorded yet
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Admin Actions */}
      <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
        <CardHeader>
          <CardTitle className={darkMode ? 'text-gray-300' : ''}>
            Admin Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => triggerAction('reindex-embeddings')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-teal-700 hover:bg-teal-600 text-white'
                  : 'bg-teal-100 hover:bg-teal-200 text-teal-800'
              }`}
            >
              Reindex Embeddings
            </button>
            <button
              onClick={() => triggerAction('consolidate')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-blue-700 hover:bg-blue-600 text-white'
                  : 'bg-blue-100 hover:bg-blue-200 text-blue-800'
              }`}
            >
              Run Consolidation Now
            </button>
            <button
              onClick={() => triggerAction('garbage-collection')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-700 hover:bg-gray-600 text-white'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-800'
              }`}
            >
              Run Garbage Collection
            </button>
          </div>
          {actionStatus && (
            <p className={`mt-3 text-sm ${
              actionStatus.includes('failed')
                ? (darkMode ? 'text-red-400' : 'text-red-600')
                : (darkMode ? 'text-green-400' : 'text-green-600')
            }`}>
              {actionStatus}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Recent Memories Table */}
      <Card className={darkMode ? 'bg-gray-800 border-gray-700' : ''}>
        <CardHeader>
          <CardTitle className={darkMode ? 'text-gray-300' : ''}>
            📝 Recent Memories
          </CardTitle>
        </CardHeader>
        <CardContent>
          {recentMemories.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className={`border-b ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                    <th className={`text-left py-2 px-3 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Type
                    </th>
                    <th className={`text-left py-2 px-3 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Content
                    </th>
                    <th className={`text-left py-2 px-3 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Confidence
                    </th>
                    <th className={`text-left py-2 px-3 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Created
                    </th>
                    <th className={`text-left py-2 px-3 font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      Accesses
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {recentMemories.map((memory) => (
                    <tr
                      key={memory.id}
                      className={`border-b ${darkMode ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-100 hover:bg-gray-50'}`}
                    >
                      <td className="py-2 px-3">
                        <div className="flex items-center gap-2">
                          <span>{getTypeIcon(memory.type)}</span>
                          <span className={`capitalize ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                            {memory.type}
                          </span>
                        </div>
                      </td>
                      <td className={`py-2 px-3 max-w-md truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                        {memory.content}
                      </td>
                      <td className="py-2 px-3">
                        <span className={`font-medium ${getConfidenceColor(memory.confidence)}`}>
                          {Math.round(memory.confidence * 100)}% ({getConfidenceLabel(memory.confidence)})
                        </span>
                      </td>
                      <td className={`py-2 px-3 whitespace-nowrap ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(memory.created_at)}
                      </td>
                      <td className={`py-2 px-3 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {memory.access_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              No memories found. Memory entries will appear here as the system learns.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
