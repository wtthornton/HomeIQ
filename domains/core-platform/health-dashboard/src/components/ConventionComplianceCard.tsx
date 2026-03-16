/**
 * Convention Compliance Card (Epic 64, Story 64.3).
 *
 * Shows aggregate naming compliance %, top 3 issues with counts,
 * and "Fix" links to HA Setup tab. Auto-refreshes every 5 minutes.
 */
import React, { useState, useEffect, useCallback } from 'react';

interface TopIssue {
  issue: string;
  count: number;
}

interface AuditData {
  total_entities: number;
  average_score: number;
  compliance_pct: number;
  top_issues: TopIssue[];
  score_distribution: {
    excellent: number;
    good: number;
    fair: number;
    poor: number;
  };
}

interface Props {
  darkMode: boolean;
  onNavigateToSetup?: () => void;
}

const REFRESH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export const ConventionComplianceCard: React.FC<Props> = ({ darkMode, onNavigateToSetup }) => {
  const [audit, setAudit] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAudit = useCallback(async () => {
    try {
      const baseUrl = import.meta.env.VITE_DEVICE_INTELLIGENCE_URL || 'http://localhost:8019';
      const resp = await fetch(`${baseUrl}/api/naming/audit?limit=500`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setAudit(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAudit();
    const interval = setInterval(fetchAudit, REFRESH_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchAudit]);

  const getComplianceColor = (pct: number) => {
    if (pct >= 80) return darkMode ? 'text-green-400' : 'text-green-600';
    if (pct >= 60) return darkMode ? 'text-yellow-400' : 'text-yellow-600';
    return darkMode ? 'text-red-400' : 'text-red-600';
  };

  const getBarColor = (pct: number) => {
    if (pct >= 80) return 'bg-green-500';
    if (pct >= 60) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  if (loading) {
    return (
      <div className={`rounded-lg shadow p-6 animate-pulse ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <div className={`h-4 rounded w-1/3 mb-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} />
        <div className={`h-8 rounded w-1/4 mb-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} />
        <div className={`h-3 rounded w-full mb-2 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} />
        <div className={`h-3 rounded w-2/3 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`} />
      </div>
    );
  }

  if (error || !audit) {
    return (
      <div
        className={`rounded-lg shadow p-6 border ${
          darkMode ? 'bg-gray-800 border-gray-700 text-gray-400' : 'bg-white border-gray-200 text-gray-500'
        }`}
        data-testid="convention-compliance-card"
      >
        <h3 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Naming Convention Compliance
        </h3>
        <p className="text-sm">
          {error ? `Unable to load: ${error}` : 'No data available'}
        </p>
      </div>
    );
  }

  return (
    <div
      className={`rounded-lg shadow p-6 border ${
        darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}
      data-testid="convention-compliance-card"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          Naming Convention Compliance
        </h3>
        <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          {audit.total_entities} entities
        </span>
      </div>

      {/* Score */}
      <div className="flex items-baseline gap-2 mb-3">
        <span className={`text-3xl font-bold ${getComplianceColor(audit.compliance_pct)}`}>
          {Math.round(audit.compliance_pct)}%
        </span>
        <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          compliant (avg {Math.round(audit.average_score)}/100)
        </span>
      </div>

      {/* Progress bar */}
      <div className={`w-full h-2 rounded-full mb-4 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
        <div
          className={`h-2 rounded-full transition-all ${getBarColor(audit.compliance_pct)}`}
          style={{ width: `${Math.min(100, audit.compliance_pct)}%` }}
        />
      </div>

      {/* Distribution */}
      <div className="flex gap-3 mb-4 text-xs">
        {audit.score_distribution && (
          <>
            <span className={darkMode ? 'text-green-400' : 'text-green-600'}>
              {audit.score_distribution.excellent} excellent
            </span>
            <span className={darkMode ? 'text-blue-400' : 'text-blue-600'}>
              {audit.score_distribution.good} good
            </span>
            <span className={darkMode ? 'text-yellow-400' : 'text-yellow-600'}>
              {audit.score_distribution.fair} fair
            </span>
            <span className={darkMode ? 'text-red-400' : 'text-red-600'}>
              {audit.score_distribution.poor} poor
            </span>
          </>
        )}
      </div>

      {/* Top Issues */}
      {audit.top_issues.length > 0 && (
        <div className="space-y-2">
          <h4 className={`text-xs font-medium ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            Top Issues
          </h4>
          {audit.top_issues.slice(0, 3).map((issue, idx) => (
            <div key={idx} className="flex items-center justify-between">
              <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                {issue.issue}
              </span>
              <div className="flex items-center gap-2">
                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  {issue.count}
                </span>
                {onNavigateToSetup && (
                  <button
                    onClick={onNavigateToSetup}
                    className={`text-xs px-2 py-0.5 rounded ${
                      darkMode
                        ? 'text-blue-400 hover:bg-blue-900/30'
                        : 'text-blue-600 hover:bg-blue-50'
                    }`}
                  >
                    Fix
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
