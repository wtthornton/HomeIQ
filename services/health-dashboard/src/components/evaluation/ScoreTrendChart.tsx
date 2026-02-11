/**
 * ScoreTrendChart — Line charts for evaluation score trends over time
 * E4.S5: Recharts-based trend visualization with threshold lines
 */

import React, { useMemo, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';

export interface TrendData {
  /** evaluator_name -> [{timestamp, score}] */
  [evaluator: string]: Array<{ timestamp: string; score: number }>;
}

interface ScoreTrendChartProps {
  trends: TrendData;
  thresholds?: Record<string, number>;
  period: string;
  onPeriodChange?: (period: string) => void;
  darkMode: boolean;
}

const COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1',
];

const PERIODS = ['7d', '30d', '90d'];

/**
 * Merge per-evaluator time series into a flat array of rows:
 * [{timestamp, eval1: score, eval2: score, ...}]
 */
function mergeTimeSeries(trends: TrendData): Array<Record<string, any>> {
  const byTime = new Map<string, Record<string, any>>();

  for (const [evaluator, points] of Object.entries(trends)) {
    for (const p of points) {
      const key = p.timestamp;
      if (!byTime.has(key)) {
        byTime.set(key, { timestamp: key });
      }
      byTime.get(key)![evaluator] = p.score;
    }
  }

  return Array.from(byTime.values()).sort(
    (a, b) => a.timestamp.localeCompare(b.timestamp)
  );
}

function formatDate(ts: string): string {
  try {
    const d = new Date(ts);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`;
  } catch {
    return ts;
  }
}

export const ScoreTrendChart: React.FC<ScoreTrendChartProps> = ({
  trends,
  thresholds = {},
  period,
  onPeriodChange,
  darkMode,
}) => {
  const evaluators = useMemo(() => Object.keys(trends), [trends]);
  const data = useMemo(() => mergeTimeSeries(trends), [trends]);
  const [hiddenEvals, setHiddenEvals] = useState<Set<string>>(new Set());

  const toggleEvaluator = (name: string) => {
    setHiddenEvals(prev => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  if (evaluators.length === 0 || data.length === 0) {
    return (
      <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        No trend data available for the selected period.
      </div>
    );
  }

  // Use the most common threshold as the reference line
  const thresholdValues = Object.values(thresholds);
  const defaultThreshold = thresholdValues.length > 0
    ? thresholdValues.reduce((a, b) => a + b, 0) / thresholdValues.length
    : 0.7;

  return (
    <div>
      {/* Period selector */}
      {onPeriodChange && (
        <div className="flex gap-2 mb-4">
          {PERIODS.map(p => (
            <button
              key={p}
              onClick={() => onPeriodChange(p)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                period === p
                  ? 'bg-blue-500 text-white'
                  : darkMode
                    ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke={darkMode ? '#374151' : '#e5e7eb'}
          />
          <XAxis
            dataKey="timestamp"
            tickFormatter={formatDate}
            stroke={darkMode ? '#9ca3af' : '#6b7280'}
            fontSize={11}
          />
          <YAxis
            domain={[0, 1]}
            tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
            stroke={darkMode ? '#9ca3af' : '#6b7280'}
            fontSize={11}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: darkMode ? '#1f2937' : '#ffffff',
              border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
              borderRadius: '8px',
              fontSize: '12px',
            }}
            labelFormatter={formatDate}
            formatter={(value: number, name: string) => [
              `${(value * 100).toFixed(1)}%`,
              name,
            ]}
          />
          <Legend
            onClick={(e: any) => toggleEvaluator(e.value)}
            wrapperStyle={{ fontSize: '12px', cursor: 'pointer' }}
          />
          <ReferenceLine
            y={defaultThreshold}
            stroke={darkMode ? '#6b7280' : '#9ca3af'}
            strokeDasharray="5 5"
            label={{
              value: `Threshold ${(defaultThreshold * 100).toFixed(0)}%`,
              position: 'right',
              fontSize: 10,
              fill: darkMode ? '#6b7280' : '#9ca3af',
            }}
          />
          {evaluators.map((name, i) => (
            <Line
              key={name}
              type="monotone"
              dataKey={name}
              stroke={COLORS[i % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              hide={hiddenEvals.has(name)}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
