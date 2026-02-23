/**
 * Validation Tab - Home Assistant Configuration Validation
 * Epic 32: Home Assistant Configuration Validation & Suggestions
 */
import React, { useEffect, useMemo, useState } from 'react';
import { setupApi } from '../../services/api';
import { LoadingSpinner } from '../LoadingSpinner';
import type { TabProps } from './types';

interface ValidationIssue {
  entity_id: string;
  category: string;
  current_area: string | null;
  suggestions: Array<{
    area_id: string;
    area_name: string;
    confidence: number;
    reasoning: string;
  }>;
  device_id: string | null;
  entity_name: string | null;
  confidence: number;
}

interface ValidationSummary {
  total_issues: number;
  by_category: Record<string, number>;
  scan_timestamp: string;
  ha_version: string | null;
}

interface ValidationResult {
  summary: ValidationSummary;
  issues: ValidationIssue[];
}

type FilterState = {
  category: string;
  minConfidence: number;
};

const CATEGORY_OPTIONS: { label: string; value: string }[] = [
  { label: 'All categories', value: '' },
  { label: 'Missing Area Assignment', value: 'missing_area_assignment' },
  { label: 'Incorrect Area Assignment', value: 'incorrect_area_assignment' },
];

const CONFIDENCE_OPTIONS = [
  { label: 'All suggestions', value: 0 },
  { label: 'High confidence (≥80%)', value: 80 },
  { label: 'Medium confidence (≥60%)', value: 60 },
  { label: 'Low confidence (≥40%)', value: 40 },
];

const CONFIDENCE_BADGE: Record<string, string> = {
  high: 'bg-green-100 text-green-800 border-green-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

function getConfidenceLevel(confidence: number): string {
  if (confidence >= 80) return 'high';
  if (confidence >= 60) return 'medium';
  return 'low';
}

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

const SummaryCard: React.FC<{ title: string; value: number; highlight?: boolean; darkMode: boolean }> = ({ 
  title, 
  value, 
  highlight,
  darkMode 
}) => (
  <div className={`p-4 rounded-lg border ${
    highlight 
      ? darkMode ? 'bg-amber-900/30 border-amber-700 text-amber-200' : 'bg-amber-50 border-amber-200 text-amber-900'
      : darkMode ? 'bg-gray-800 border-gray-700 text-gray-200' : 'bg-white border-gray-200 text-gray-900'
  } shadow-sm`}>
    <p className="text-sm font-medium">{title}</p>
    <p className="text-2xl font-semibold mt-1">{value}</p>
  </div>
);

export const ValidationTab: React.FC<TabProps> = ({ darkMode }) => {
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [filters, setFilters] = useState<FilterState>({ category: '', minConfidence: 0 });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [applyingFixes, setApplyingFixes] = useState<Set<string>>(new Set());
  const [selectedIssues, setSelectedIssues] = useState<Set<string>>(new Set());

  const filteredIssues = useMemo(() => {
    if (!validationResult) return [];
    
    return validationResult.issues.filter(issue => {
      if (filters.category && issue.category !== filters.category) return false;
      if (filters.minConfidence > 0 && issue.confidence < filters.minConfidence) return false;
      return true;
    });
  }, [validationResult, filters]);

  const loadValidation = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await setupApi.getValidationResults({
        category: filters.category || undefined,
        min_confidence: filters.minConfidence > 0 ? filters.minConfidence : undefined,
      });
      setValidationResult(result);
    } catch (err) {
      console.error('Failed to load validation results', err);
      setError(err instanceof Error ? err.message : 'Unable to load validation results. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadValidation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.category, filters.minConfidence]);

  const handleApplyFix = async (entityId: string, areaId: string) => {
    try {
      setApplyingFixes(prev => new Set(prev).add(entityId));
      await setupApi.applyValidationFix(entityId, areaId);
      // Reload validation results
      await loadValidation();
    } catch (err) {
      console.error('Failed to apply fix', err);
      alert(err instanceof Error ? err.message : 'Failed to apply fix');
    } finally {
      setApplyingFixes(prev => {
        const next = new Set(prev);
        next.delete(entityId);
        return next;
      });
    }
  };

  const handleBulkApply = async () => {
    if (selectedIssues.size === 0) return;
    
    const fixes = Array.from(selectedIssues).map(entityId => {
      const issue = validationResult?.issues.find(i => i.entity_id === entityId);
      if (!issue || !issue.suggestions.length) return null;
      return {
        entity_id: entityId,
        area_id: issue.suggestions[0].area_id,
      };
    }).filter((f): f is { entity_id: string; area_id: string } => f !== null);

    if (fixes.length === 0) return;

    try {
      setLoading(true);
      const result = await setupApi.applyBulkFixes(fixes);
      alert(`Applied ${result.applied} fixes${result.failed > 0 ? `, ${result.failed} failed` : ''}`);
      setSelectedIssues(new Set());
      await loadValidation();
    } catch (err) {
      console.error('Failed to apply bulk fixes', err);
      alert(err instanceof Error ? err.message : 'Failed to apply bulk fixes');
    } finally {
      setLoading(false);
    }
  };

  const toggleIssueSelection = (entityId: string) => {
    setSelectedIssues(prev => {
      const next = new Set(prev);
      if (next.has(entityId)) {
        next.delete(entityId);
      } else {
        next.add(entityId);
      }
      return next;
    });
  };

  if (loading && !validationResult) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 rounded-lg border ${
        darkMode ? 'bg-red-900/20 border-red-800 text-red-200' : 'bg-red-50 border-red-200 text-red-700'
      }`}>
        <p className="font-semibold">Error</p>
        <p className="mt-1">{error}</p>
        <button
          onClick={loadValidation}
          className={`mt-4 px-4 py-2 rounded ${
            darkMode ? 'bg-blue-600 hover:bg-blue-700 text-white' : 'bg-blue-500 hover:bg-blue-600 text-white'
          }`}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className={`p-4 rounded-lg border ${
        darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <h2 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🔍 Home Assistant Configuration Validation
        </h2>
        <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Validate your Home Assistant setup and get suggestions for fixing configuration issues
        </p>
      </div>

      {/* Summary Cards */}
      {validationResult && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <SummaryCard
            title="Total Issues"
            value={validationResult.summary.total_issues}
            highlight={validationResult.summary.total_issues > 0}
            darkMode={darkMode}
          />
          <SummaryCard
            title="Missing Areas"
            value={validationResult.summary.by_category.missing_area_assignment || 0}
            darkMode={darkMode}
          />
          <SummaryCard
            title="Incorrect Areas"
            value={validationResult.summary.by_category.incorrect_area_assignment || 0}
            darkMode={darkMode}
          />
          <SummaryCard
            title="HA Version"
            value={validationResult.summary.ha_version || 'Unknown'}
            darkMode={darkMode}
          />
        </div>
      )}

      {/* Filters */}
      <div className={`p-4 rounded-lg border ${
        darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'
      }`}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Category
            </label>
            <select
              value={filters.category}
              onChange={(e) => setFilters(prev => ({ ...prev, category: e.target.value }))}
              className={`w-full px-3 py-2 rounded border ${
                darkMode 
                  ? 'bg-gray-700 border-gray-600 text-white' 
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              {CATEGORY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Min Confidence
            </label>
            <select
              value={filters.minConfidence}
              onChange={(e) => setFilters(prev => ({ ...prev, minConfidence: Number(e.target.value) }))}
              className={`w-full px-3 py-2 rounded border ${
                darkMode 
                  ? 'bg-gray-700 border-gray-600 text-white' 
                  : 'bg-white border-gray-300 text-gray-900'
              }`}
            >
              {CONFIDENCE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button
              onClick={loadValidation}
              className={`w-full px-4 py-2 rounded ${
                darkMode 
                  ? 'bg-blue-600 hover:bg-blue-700 text-white' 
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              🔄 Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Bulk Actions */}
      {selectedIssues.size > 0 && (
        <div className={`p-4 rounded-lg border ${
          darkMode ? 'bg-blue-900/20 border-blue-700' : 'bg-blue-50 border-blue-200'
        }`}>
          <div className="flex items-center justify-between">
            <span className={darkMode ? 'text-blue-200' : 'text-blue-900'}>
              {selectedIssues.size} issue{selectedIssues.size !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setSelectedIssues(new Set())}
                className={`px-4 py-2 rounded ${
                  darkMode 
                    ? 'bg-gray-700 hover:bg-gray-600 text-white' 
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                }`}
              >
                Clear Selection
              </button>
              <button
                onClick={handleBulkApply}
                disabled={loading}
                className={`px-4 py-2 rounded ${
                  darkMode 
                    ? 'bg-green-600 hover:bg-green-700 text-white disabled:opacity-50' 
                    : 'bg-green-500 hover:bg-green-600 text-white disabled:opacity-50'
                }`}
              >
                Apply {selectedIssues.size} Fix{selectedIssues.size !== 1 ? 'es' : ''}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Issues List */}
      <div className={`rounded-lg border ${
        darkMode ? 'border-gray-700' : 'border-gray-200'
      } overflow-hidden`}>
        {filteredIssues.length === 0 ? (
          <div className={`p-8 text-center ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {validationResult?.summary.total_issues === 0 
              ? '✅ No validation issues found!' 
              : 'No issues match the current filters'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className={`min-w-full text-sm ${darkMode ? 'text-gray-200' : 'text-gray-700'}`}>
              <thead className={darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600'}>
                <tr>
                  <th className="px-4 py-2 text-left">
                    <input
                      type="checkbox"
                      checked={selectedIssues.size === filteredIssues.length && filteredIssues.length > 0}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedIssues(new Set(filteredIssues.map(i => i.entity_id)));
                        } else {
                          setSelectedIssues(new Set());
                        }
                      }}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-2 text-left">Entity</th>
                  <th className="px-4 py-2 text-left">Category</th>
                  <th className="px-4 py-2 text-left">Current Area</th>
                  <th className="px-4 py-2 text-left">Suggestions</th>
                  <th className="px-4 py-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredIssues.map((issue) => (
                  <tr
                    key={issue.entity_id}
                    className={darkMode ? 'odd:bg-gray-800 even:bg-gray-900/40 border-b border-gray-700' : 'odd:bg-white even:bg-gray-50 border-b border-gray-200'}
                  >
                    <td className="px-4 py-2">
                      <input
                        type="checkbox"
                        checked={selectedIssues.has(issue.entity_id)}
                        onChange={() => toggleIssueSelection(issue.entity_id)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-2">
                      <div>
                        <div className="font-medium">{issue.entity_id}</div>
                        {issue.entity_name && (
                          <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                            {issue.entity_name}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-1 rounded text-xs ${
                        darkMode ? 'bg-yellow-900/30 text-yellow-300' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {issue.category.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-2">
                      {issue.current_area || (
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>—</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {issue.suggestions.length > 0 ? (
                        <div className="space-y-1">
                          {issue.suggestions.slice(0, 2).map((suggestion, idx) => (
                            <div key={idx} className="flex items-center gap-2">
                              <span className={`px-2 py-1 rounded text-xs ${
                                CONFIDENCE_BADGE[getConfidenceLevel(suggestion.confidence)]
                              }`}>
                                {suggestion.area_name} ({suggestion.confidence}%)
                              </span>
                              {idx === 0 && (
                                <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                                  {suggestion.reasoning}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <span className={darkMode ? 'text-gray-500' : 'text-gray-400'}>No suggestions</span>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {issue.suggestions.length > 0 && (
                        <button
                          onClick={() => handleApplyFix(issue.entity_id, issue.suggestions[0].area_id)}
                          disabled={applyingFixes.has(issue.entity_id)}
                          className={`px-3 py-1 rounded text-xs ${
                            darkMode
                              ? 'bg-green-600 hover:bg-green-700 text-white disabled:opacity-50'
                              : 'bg-green-500 hover:bg-green-600 text-white disabled:opacity-50'
                          }`}
                        >
                          {applyingFixes.has(issue.entity_id) ? 'Applying...' : 'Apply Fix'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Last Scan Info */}
      {validationResult && (
        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          Last scan: {formatDate(validationResult.summary.scan_timestamp)}
        </div>
      )}
    </div>
  );
};

