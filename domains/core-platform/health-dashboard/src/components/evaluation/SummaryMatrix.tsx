/**
 * SummaryMatrix — 5-level evaluation pyramid display
 * E4.S4: Color-coded pass/fail indicators per evaluator
 */

import React from 'react';

export interface MetricScore {
  evaluator_name: string;
  level: string;
  score: number;
  label: string;
  timestamp: string;
}

interface SummaryMatrixProps {
  scores: MetricScore[];
  thresholds?: Record<string, number>;
  darkMode: boolean;
}

interface LevelGroup {
  level: string;
  label: string;
  metrics: MetricScore[];
}

const LEVEL_ORDER = ['L1_OUTCOME', 'L2_PATH', 'L3_DETAILS', 'L4_QUALITY', 'L5_SAFETY'];

const LEVEL_LABELS: Record<string, string> = {
  L1_OUTCOME: 'L1 Outcome',
  L2_PATH: 'L2 Path',
  L3_DETAILS: 'L3 Details',
  L4_QUALITY: 'L4 Quality',
  L5_SAFETY: 'L5 Safety',
};

function getScoreColor(score: number, threshold: number): string {
  if (score >= threshold) return 'text-green-500';
  if (score >= threshold * 0.95) return 'text-yellow-500';
  return 'text-red-500';
}

function getScoreBg(score: number, threshold: number): string {
  if (score >= threshold) return 'bg-green-500/10 border-green-500/30';
  if (score >= threshold * 0.95) return 'bg-yellow-500/10 border-yellow-500/30';
  return 'bg-red-500/10 border-red-500/30';
}

function groupByLevel(scores: MetricScore[]): LevelGroup[] {
  const groups = new Map<string, MetricScore[]>();
  for (const s of scores) {
    const existing = groups.get(s.level) || [];
    // Deduplicate — keep latest per evaluator
    const idx = existing.findIndex(e => e.evaluator_name === s.evaluator_name);
    if (idx >= 0) {
      existing[idx] = s;
    } else {
      existing.push(s);
    }
    groups.set(s.level, existing);
  }

  return LEVEL_ORDER
    .filter(l => groups.has(l))
    .map(l => ({
      level: l,
      label: LEVEL_LABELS[l] || l,
      metrics: groups.get(l)!,
    }));
}

export const SummaryMatrix: React.FC<SummaryMatrixProps> = ({
  scores,
  thresholds = {},
  darkMode,
}) => {
  const levels = groupByLevel(scores);
  const defaultThreshold = 0.7;

  if (levels.length === 0) {
    return (
      <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        No evaluation data available. Run an evaluation to see the summary matrix.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {levels.map(group => (
        <div key={group.level}>
          <h4 className={`text-sm font-semibold mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            {group.label}
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {group.metrics.map(metric => {
              const threshold = thresholds[metric.evaluator_name] ?? defaultThreshold;
              const passed = metric.score >= threshold;
              return (
                <div
                  key={metric.evaluator_name}
                  className={`p-3 rounded-lg border ${getScoreBg(metric.score, threshold)} ${
                    darkMode ? 'border-opacity-50' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className={`text-xs font-medium truncate ${
                      darkMode ? 'text-gray-300' : 'text-gray-600'
                    }`}>
                      {metric.evaluator_name}
                    </span>
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                      passed
                        ? 'bg-green-500/20 text-green-500'
                        : 'bg-red-500/20 text-red-500'
                    }`}>
                      {passed ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                  <div className="flex items-end gap-2">
                    <span className={`text-2xl font-bold ${getScoreColor(metric.score, threshold)}`}>
                      {(metric.score * 100).toFixed(0)}%
                    </span>
                    <span className={`text-xs mb-1 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                      / {(threshold * 100).toFixed(0)}%
                    </span>
                  </div>
                  {/* Score bar */}
                  <div className={`mt-2 h-1.5 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                    <div
                      className={`h-full rounded-full transition-all ${
                        passed ? 'bg-green-500' : metric.score >= threshold * 0.95 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}
                      style={{ width: `${Math.min(metric.score * 100, 100)}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
