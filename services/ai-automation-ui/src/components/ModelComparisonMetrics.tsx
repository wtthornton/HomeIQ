/**
 * Model Comparison Metrics Component
 * 
 * Displays metrics and analytics for parallel model testing.
 * Shows cost, latency, and quality comparisons between models.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getModelComparisonMetrics,
  getModelComparisonSummary,
  type ModelComparisonMetrics,
  type ModelComparisonSummary,
} from '../api/settings';

interface ModelComparisonMetricsProps {
  darkMode?: boolean;
}

export const ModelComparisonMetricsComponent: React.FC<ModelComparisonMetricsProps> = ({
  darkMode = false,
}) => {
  const [selectedTaskType, setSelectedTaskType] = useState<string>('all');
  const [days, setDays] = useState<number>(7);

  const { data: metrics, isLoading: metricsLoading } = useQuery<ModelComparisonMetrics>({
    queryKey: ['model-comparison-metrics', selectedTaskType, days],
    queryFn: () => getModelComparisonMetrics(
      selectedTaskType === 'all' ? undefined : selectedTaskType,
      days
    ),
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
  });

  const { data: summary, isLoading: summaryLoading } = useQuery<ModelComparisonSummary>({
    queryKey: ['model-comparison-summary'],
    queryFn: getModelComparisonSummary,
    staleTime: 60000, // 1 minute
    refetchInterval: 120000, // Refetch every 2 minutes
  });

  const bgColor = darkMode ? 'bg-gray-800' : 'bg-white';
  const textColor = darkMode ? 'text-gray-100' : 'text-gray-900';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';
  const cardBg = darkMode ? 'bg-gray-700' : 'bg-gray-50';

  if (metricsLoading || summaryLoading) {
    return (
      <div className={`${bgColor} rounded-xl p-6 shadow-lg`}>
        <div className="text-center py-8">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className={`mt-4 ${textColor}`}>Loading metrics...</p>
        </div>
      </div>
    );
  }

  if (!metrics || metrics.total_comparisons === 0) {
    return (
      <div className={`${bgColor} rounded-xl p-6 shadow-lg`}>
        <h2 className={`text-xl font-bold mb-4 ${textColor}`}>
          📊 Model Comparison Metrics
        </h2>
        <div className={`${cardBg} rounded-lg p-8 text-center`}>
          <p className={textColor}>No comparison data available yet.</p>
          <p className={`text-sm mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Enable parallel testing and generate some suggestions/YAML to see metrics.
          </p>
        </div>
      </div>
    );
  }

  const { summary: metricsSummary, model_stats } = metrics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`${bgColor} rounded-xl p-6 shadow-lg`}>
        <div className="flex items-center justify-between mb-4">
          <h2 className={`text-xl font-bold ${textColor}`}>
            📊 Model Comparison Metrics
          </h2>
          <div className="flex gap-3">
            <select
              value={selectedTaskType}
              onChange={(e) => setSelectedTaskType(e.target.value)}
              className={`px-3 py-2 rounded-lg border text-sm ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value="all">All Tasks</option>
              <option value="suggestion">Suggestions</option>
              <option value="yaml">YAML Generation</option>
            </select>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className={`px-3 py-2 rounded-lg border text-sm ${
                darkMode
                  ? 'bg-gray-700 border-gray-600 text-white'
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              <option value="1">Last 1 day</option>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className={`${cardBg} rounded-lg p-4 border ${borderColor}`}>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Total Comparisons
            </div>
            <div className={`text-2xl font-bold mt-1 ${textColor}`}>
              {metrics.total_comparisons}
            </div>
          </div>
          <div className={`${cardBg} rounded-lg p-4 border ${borderColor}`}>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Cost Difference
            </div>
            <div className={`text-2xl font-bold mt-1 ${textColor}`}>
              ${metricsSummary.cost_difference_usd.toFixed(4)}
            </div>
            <div className={`text-xs mt-1 ${
              metricsSummary.cost_savings_percentage > 0
                ? 'text-green-500'
                : 'text-red-500'
            }`}>
              {metricsSummary.cost_savings_percentage > 0 ? '↓' : '↑'} {Math.abs(metricsSummary.cost_savings_percentage).toFixed(1)}%
            </div>
          </div>
          <div className={`${cardBg} rounded-lg p-4 border ${borderColor}`}>
            <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Latency Difference
            </div>
            <div className={`text-2xl font-bold mt-1 ${textColor}`}>
              {metricsSummary.latency_difference_ms.toFixed(0)}ms
            </div>
          </div>
        </div>

        {/* Model Comparison Table */}
        <div className={`${cardBg} rounded-lg p-4 border ${borderColor}`}>
          <h3 className={`font-semibold mb-4 ${textColor}`}>Model Performance</h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={`border-b ${borderColor}`}>
                  <th className={`text-left py-2 px-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    Metric
                  </th>
                  <th className={`text-right py-2 px-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {model_stats.model1.name}
                  </th>
                  <th className={`text-right py-2 px-4 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {model_stats.model2.name}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className={`border-b ${borderColor}`}>
                  <td className={`py-2 px-4 ${textColor}`}>Avg Cost per Request</td>
                  <td className={`text-right py-2 px-4 ${textColor}`}>
                    ${model_stats.model1.avg_cost_per_comparison.toFixed(4)}
                  </td>
                  <td className={`text-right py-2 px-4 ${textColor}`}>
                    ${model_stats.model2.avg_cost_per_comparison.toFixed(4)}
                  </td>
                </tr>
                <tr className={`border-b ${borderColor}`}>
                  <td className={`py-2 px-4 ${textColor}`}>Avg Latency</td>
                  <td className={`text-right py-2 px-4 ${textColor}`}>
                    {model_stats.model1.avg_latency_ms.toFixed(0)}ms
                  </td>
                  <td className={`text-right py-2 px-4 ${textColor}`}>
                    {model_stats.model2.avg_latency_ms.toFixed(0)}ms
                  </td>
                </tr>
                {model_stats.model1.approval_rate !== null && (
                  <tr className={`border-b ${borderColor}`}>
                    <td className={`py-2 px-4 ${textColor}`}>Approval Rate</td>
                    <td className={`text-right py-2 px-4 ${textColor}`}>
                      {model_stats.model1.approval_rate.toFixed(1)}%
                    </td>
                    <td className={`text-right py-2 px-4 ${textColor}`}>
                      {model_stats.model2.approval_rate?.toFixed(1) || 'N/A'}%
                    </td>
                  </tr>
                )}
                {model_stats.model1.yaml_validation_rate !== null && (
                  <tr>
                    <td className={`py-2 px-4 ${textColor}`}>YAML Validation Rate</td>
                    <td className={`text-right py-2 px-4 ${textColor}`}>
                      {model_stats.model1.yaml_validation_rate.toFixed(1)}%
                    </td>
                    <td className={`text-right py-2 px-4 ${textColor}`}>
                      {model_stats.model2.yaml_validation_rate?.toFixed(1) || 'N/A'}%
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recommendations */}
        {summary && summary.recommendations && (
          <div className={`${cardBg} rounded-lg p-4 border ${borderColor}`}>
            <h3 className={`font-semibold mb-4 ${textColor}`}>Recommendations</h3>
            <div className="space-y-3">
              <div>
                <div className={`font-medium ${textColor}`}>Suggestions:</div>
                <div className={`text-sm mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {typeof summary.recommendations.suggestion === 'object' && 'recommendation' in summary.recommendations.suggestion
                    ? `${summary.recommendations.suggestion.recommendation} - ${summary.recommendations.suggestion.reason}`
                    : String(summary.recommendations.suggestion)}
                </div>
              </div>
              <div>
                <div className={`font-medium ${textColor}`}>YAML Generation:</div>
                <div className={`text-sm mt-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  {typeof summary.recommendations.yaml === 'object' && 'recommendation' in summary.recommendations.yaml
                    ? `${summary.recommendations.yaml.recommendation} - ${summary.recommendations.yaml.reason}`
                    : String(summary.recommendations.yaml)}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

