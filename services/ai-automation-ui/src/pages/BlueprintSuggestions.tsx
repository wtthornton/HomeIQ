/**
 * Blueprint Suggestions Page
 * 
 * Displays scored blueprint suggestions with filters and accept/decline actions
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import {
  getSuggestions,
  acceptSuggestion,
  declineSuggestion,
  getStats,
  type BlueprintSuggestion,
  type SuggestionStats,
  BlueprintSuggestionsAPIError,
} from '../services/blueprintSuggestionsApi';

export const BlueprintSuggestions: React.FC = () => {
  const navigate = useNavigate();
  
  const [suggestions, setSuggestions] = useState<BlueprintSuggestion[]>([]);
  const [stats, setStats] = useState<SuggestionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    min_score: 0.6,
    use_case: '',
    status: 'pending',
    blueprint_id: '',
  });
  const [page, setPage] = useState({ limit: 50, offset: 0, total: 0 });

  const loadSuggestions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await getSuggestions({
        min_score: filters.min_score,
        use_case: filters.use_case || undefined,
        status: filters.status || undefined,
        blueprint_id: filters.blueprint_id || undefined,
        limit: page.limit,
        offset: page.offset,
      });
      setSuggestions(response.suggestions);
      setPage(prev => ({ ...prev, total: response.total }));
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      toast.error('Failed to load suggestions');
    } finally {
      setLoading(false);
    }
  }, [filters, page.limit, page.offset]);

  const loadStats = useCallback(async () => {
    try {
      const statsData = await getStats();
      setStats(statsData);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  }, []);

  useEffect(() => {
    loadSuggestions();
    loadStats();
  }, [loadSuggestions, loadStats]);

  const handleAccept = async (suggestion: BlueprintSuggestion) => {
    try {
      const response = await acceptSuggestion(suggestion.id);
      toast.success('Suggestion accepted!');
      
      // Navigate to Agent tab with blueprint context
      navigate('/ha-agent', {
        state: {
          blueprintContext: {
            blueprint_id: response.blueprint_id,
            blueprint_yaml: response.blueprint_yaml || '',
            blueprint_inputs: response.blueprint_inputs || {},
            matched_devices: response.matched_devices || [],
            suggestion_score: response.suggestion_score,
            blueprint_name: suggestion.blueprint_name,
          },
        },
      });
      
      // Reload suggestions to update status
      await loadSuggestions();
      await loadStats();
    } catch (error) {
      console.error('Failed to accept suggestion:', error);
      if (error instanceof BlueprintSuggestionsAPIError) {
        toast.error(`Failed to accept: ${error.message}`);
      } else {
        toast.error('Failed to accept suggestion');
      }
    }
  };

  const handleDecline = async (suggestionId: string) => {
    try {
      await declineSuggestion(suggestionId);
      toast.success('Suggestion declined');
      await loadSuggestions();
      await loadStats();
    } catch (error) {
      console.error('Failed to decline suggestion:', error);
      toast.error('Failed to decline suggestion');
    }
  };

  const formatScore = (score: number) => {
    return (score * 100).toFixed(0);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
            Blueprint Suggestions
          </h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Discover proven automations matched to your devices
          </p>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4">
              <div className="text-sm text-[var(--text-secondary)]">Total</div>
              <div className="text-2xl font-bold text-[var(--text-primary)]">{stats.total_suggestions}</div>
            </div>
            <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4">
              <div className="text-sm text-[var(--text-secondary)]">Pending</div>
              <div className="text-2xl font-bold text-[var(--text-primary)]">{stats.pending_count}</div>
            </div>
            <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4">
              <div className="text-sm text-[var(--text-secondary)]">Accepted</div>
              <div className="text-2xl font-bold text-[var(--accent-primary)]">{stats.accepted_count}</div>
            </div>
            <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4">
              <div className="text-sm text-[var(--text-secondary)]">Avg Score</div>
              <div className="text-2xl font-bold text-[var(--text-primary)]">
                {formatScore(stats.average_score)}%
              </div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Min Score
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={filters.min_score}
                onChange={(e) => setFilters(prev => ({ ...prev, min_score: parseFloat(e.target.value) }))}
                className="w-full"
              />
              <div className="text-xs text-[var(--text-secondary)] mt-1">
                {formatScore(filters.min_score)}%
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Use Case
              </label>
              <select
                value={filters.use_case}
                onChange={(e) => setFilters(prev => ({ ...prev, use_case: e.target.value }))}
                className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--card-border)] rounded text-[var(--text-primary)]"
              >
                <option value="">All</option>
                <option value="convenience">Convenience</option>
                <option value="security">Security</option>
                <option value="energy">Energy</option>
                <option value="comfort">Comfort</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Status
              </label>
              <select
                value={filters.status}
                onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--card-border)] rounded text-[var(--text-primary)]"
              >
                <option value="">All</option>
                <option value="pending">Pending</option>
                <option value="accepted">Accepted</option>
                <option value="declined">Declined</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-1">
                Blueprint ID
              </label>
              <input
                type="text"
                value={filters.blueprint_id}
                onChange={(e) => setFilters(prev => ({ ...prev, blueprint_id: e.target.value }))}
                placeholder="Filter by blueprint ID"
                className="w-full px-3 py-2 bg-[var(--bg-primary)] border border-[var(--card-border)] rounded text-[var(--text-primary)]"
              />
            </div>
          </div>
        </div>

        {/* Suggestions List */}
        {loading ? (
          <div className="text-center py-12">
            <div className="text-[var(--text-secondary)]">Loading suggestions...</div>
          </div>
        ) : suggestions.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-[var(--text-secondary)]">No suggestions found</div>
          </div>
        ) : (
          <div className="space-y-4">
            {suggestions.map((suggestion) => (
              <div
                key={suggestion.id}
                className="bg-[var(--card-bg)] border border-[var(--card-border)] rounded-lg p-6 hover:border-[var(--accent-primary)] transition-colors"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-1">
                      {suggestion.blueprint_name}
                    </h3>
                    {suggestion.blueprint_description && (
                      <p className="text-sm text-[var(--text-secondary)] mb-2">
                        {suggestion.blueprint_description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-[var(--text-secondary)]">
                        Score: <span className="font-semibold text-[var(--accent-primary)]">
                          {formatScore(suggestion.suggestion_score)}%
                        </span>
                      </span>
                      {suggestion.use_case && (
                        <span className="px-2 py-1 bg-[var(--hover-bg)] rounded text-[var(--text-secondary)]">
                          {suggestion.use_case}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAccept(suggestion)}
                      disabled={suggestion.status !== 'pending'}
                      className="px-4 py-2 bg-[var(--accent-primary)] text-white rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Accept
                    </button>
                    <button
                      onClick={() => handleDecline(suggestion.id)}
                      disabled={suggestion.status !== 'pending'}
                      className="px-4 py-2 bg-[var(--card-bg)] border border-[var(--card-border)] text-[var(--text-primary)] rounded hover:bg-[var(--hover-bg)] disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Decline
                    </button>
                  </div>
                </div>

                {/* Matched Devices */}
                <div className="mt-4">
                  <div className="text-sm font-medium text-[var(--text-secondary)] mb-2">
                    Matched Devices ({suggestion.matched_devices.length})
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {suggestion.matched_devices.map((device, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-1 bg-[var(--hover-bg)] rounded text-sm text-[var(--text-secondary)]"
                      >
                        {device.friendly_name || device.entity_id} ({device.domain})
                        {device.area_name && ` • ${device.area_name}`}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        {page.total > page.limit && (
          <div className="mt-6 flex justify-center gap-2">
            <button
              onClick={() => setPage(prev => ({ ...prev, offset: Math.max(0, prev.offset - prev.limit) }))}
              disabled={page.offset === 0}
              className="px-4 py-2 bg-[var(--card-bg)] border border-[var(--card-border)] rounded disabled:opacity-50"
            >
              Previous
            </button>
            <div className="px-4 py-2 text-[var(--text-secondary)]">
              {page.offset + 1}-{Math.min(page.offset + page.limit, page.total)} of {page.total}
            </div>
            <button
              onClick={() => setPage(prev => ({ ...prev, offset: prev.offset + prev.limit }))}
              disabled={page.offset + page.limit >= page.total}
              className="px-4 py-2 bg-[var(--card-bg)] border border-[var(--card-border)] rounded disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
