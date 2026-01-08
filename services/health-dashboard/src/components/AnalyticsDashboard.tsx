/**
 * Analytics Dashboard Component
 * 
 * Displays progress toward target metrics from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md:
 * - Automation Adoption Rate: 30%
 * - Automation Success Rate: 85%
 * - Pattern Quality: 90%
 * - User Satisfaction: 4.0+
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface TargetProgress {
  target: number;
  actual: number;
  achieved: boolean;
  progress_pct: number;
}

interface TargetProgressData {
  adoption_rate: TargetProgress;
  success_rate: TargetProgress;
  pattern_quality: TargetProgress;
  user_satisfaction: TargetProgress;
}

interface TrendingBlueprint {
  blueprint_id: string;
  deployment_count: number;
  success_rate: number | null;
  average_rating: number | null;
}

interface AnalyticsDashboardProps {
  refreshInterval?: number;
  totalSynergies?: number;
}

// API configuration
const API_BASE_URL = import.meta.env.VITE_AI_PATTERN_SERVICE_URL || 'http://localhost:8020';

// Progress ring component
const ProgressRing: React.FC<{
  progress: number;
  target: number;
  achieved: boolean;
  size?: number;
  strokeWidth?: number;
}> = ({ progress, target, achieved, size = 80, strokeWidth = 8 }) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const progressPct = Math.min(100, (progress / target) * 100);
  const offset = circumference - (progressPct / 100) * circumference;

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        {/* Background circle */}
        <circle
          className="text-gray-700"
          strokeWidth={strokeWidth}
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        {/* Progress circle */}
        <circle
          className={achieved ? 'text-green-500' : 'text-blue-500'}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          stroke="currentColor"
          fill="transparent"
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{ transition: 'stroke-dashoffset 0.5s ease-in-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`text-sm font-bold ${achieved ? 'text-green-400' : 'text-white'}`}>
          {progressPct.toFixed(0)}%
        </span>
      </div>
    </div>
  );
};

// Metric card component
const MetricCard: React.FC<{
  title: string;
  value: number;
  target: number;
  unit: string;
  achieved: boolean;
  description: string;
}> = ({ title, value, target, unit, achieved, description }) => {
  return (
    <div className={`
      p-4 rounded-lg border transition-all
      ${achieved 
        ? 'bg-green-500/10 border-green-500/30' 
        : 'bg-gray-800/50 border-gray-700/50'
      }
    `}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-medium text-gray-300">{title}</h4>
        {achieved && (
          <span className="text-xs px-2 py-0.5 bg-green-500/20 text-green-400 rounded-full">
            ✓ Target Met
          </span>
        )}
      </div>
      
      <div className="flex items-center gap-4">
        <ProgressRing
          progress={value}
          target={target}
          achieved={achieved}
        />
        
        <div className="flex-1">
          <div className="flex items-baseline gap-1">
            <span className={`text-2xl font-bold ${achieved ? 'text-green-400' : 'text-white'}`}>
              {value.toFixed(1)}
            </span>
            <span className="text-sm text-gray-400">{unit}</span>
          </div>
          <div className="text-xs text-gray-500">
            Target: {target}{unit}
          </div>
          <p className="text-xs text-gray-400 mt-1">{description}</p>
        </div>
      </div>
    </div>
  );
};

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  refreshInterval = 60000,
  totalSynergies = 0,
}) => {
  const [targetProgress, setTargetProgress] = useState<TargetProgressData | null>(null);
  const [trendingBlueprints, setTrendingBlueprints] = useState<TrendingBlueprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Fetch analytics data
  const fetchAnalytics = useCallback(async () => {
    try {
      // Fetch target progress
      const progressResponse = await fetch(
        `${API_BASE_URL}/api/v1/analytics/target-progress?total_synergies=${totalSynergies}`
      );
      
      if (!progressResponse.ok) {
        throw new Error(`Failed to fetch target progress: ${progressResponse.status}`);
      }
      
      const progressData = await progressResponse.json();
      setTargetProgress(progressData);

      // Fetch trending blueprints
      const trendingResponse = await fetch(
        `${API_BASE_URL}/api/v1/analytics/trending-blueprints?limit=5`
      );
      
      if (trendingResponse.ok) {
        const trendingData = await trendingResponse.json();
        setTrendingBlueprints(trendingData);
      }

      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch analytics');
    } finally {
      setLoading(false);
    }
  }, [totalSynergies]);

  // Initial fetch and refresh interval
  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchAnalytics, refreshInterval]);

  // Calculate overall progress
  const overallProgress = targetProgress
    ? (
        (targetProgress.adoption_rate.progress_pct +
          targetProgress.success_rate.progress_pct +
          targetProgress.pattern_quality.progress_pct +
          targetProgress.user_satisfaction.progress_pct) /
        4
      ).toFixed(0)
    : 0;

  const targetsAchieved = targetProgress
    ? [
        targetProgress.adoption_rate.achieved,
        targetProgress.success_rate.achieved,
        targetProgress.pattern_quality.achieved,
        targetProgress.user_satisfaction.achieved,
      ].filter(Boolean).length
    : 0;

  if (loading) {
    return (
      <div className="bg-gray-900/50 rounded-lg border border-gray-700/50 p-6">
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-gray-400">Loading analytics...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900/50 rounded-lg border border-red-500/30 p-6">
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <span>⚠️</span>
          <span className="font-medium">Analytics Error</span>
        </div>
        <p className="text-sm text-gray-400">{error}</p>
        <button
          onClick={fetchAnalytics}
          className="mt-3 px-3 py-1 text-sm bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition-colors"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gray-900/50 rounded-lg border border-gray-700/50 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-700/50">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              📊 Target Metrics Progress
            </h3>
            <p className="text-sm text-gray-400 mt-1">
              From RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md
            </p>
          </div>
          
          <div className="text-right">
            <div className="text-2xl font-bold text-white">{overallProgress}%</div>
            <div className="text-xs text-gray-400">
              {targetsAchieved}/4 targets achieved
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="p-6">
        {targetProgress && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <MetricCard
              title="Automation Adoption Rate"
              value={targetProgress.adoption_rate.actual}
              target={targetProgress.adoption_rate.target}
              unit="%"
              achieved={targetProgress.adoption_rate.achieved}
              description="Synergies converted to automations"
            />
            
            <MetricCard
              title="Automation Success Rate"
              value={targetProgress.success_rate.actual}
              target={targetProgress.success_rate.target}
              unit="%"
              achieved={targetProgress.success_rate.achieved}
              description="Automations executing successfully"
            />
            
            <MetricCard
              title="Pattern Quality"
              value={targetProgress.pattern_quality.actual}
              target={targetProgress.pattern_quality.target}
              unit="%"
              achieved={targetProgress.pattern_quality.achieved}
              description="Patterns leading to successful automations"
            />
            
            <MetricCard
              title="User Satisfaction"
              value={targetProgress.user_satisfaction.actual}
              target={targetProgress.user_satisfaction.target}
              unit="/5"
              achieved={targetProgress.user_satisfaction.achieved}
              description="Average user rating"
            />
          </div>
        )}

        {/* Trending Blueprints */}
        {trendingBlueprints.length > 0 && (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-gray-300 mb-3">
              🔥 Trending Blueprints
            </h4>
            <div className="space-y-2">
              {trendingBlueprints.map((bp, index) => (
                <div
                  key={bp.blueprint_id}
                  className="flex items-center justify-between p-3 bg-gray-800/30 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-gray-500">#{index + 1}</span>
                    <div>
                      <div className="text-sm font-medium text-white truncate max-w-[200px]">
                        {bp.blueprint_id}
                      </div>
                      <div className="text-xs text-gray-400">
                        {bp.deployment_count} deployments
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-4 text-sm">
                    {bp.success_rate !== null && (
                      <div className={bp.success_rate >= 85 ? 'text-green-400' : 'text-yellow-400'}>
                        {bp.success_rate.toFixed(0)}% success
                      </div>
                    )}
                    {bp.average_rating !== null && (
                      <div className="text-yellow-400">
                        ⭐ {bp.average_rating.toFixed(1)}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-4 pt-4 border-t border-gray-700/50 flex items-center justify-between text-xs text-gray-500">
          <span>
            {lastUpdated && `Last updated: ${lastUpdated.toLocaleTimeString()}`}
          </span>
          <button
            onClick={fetchAnalytics}
            className="hover:text-gray-300 transition-colors"
          >
            ↻ Refresh
          </button>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
