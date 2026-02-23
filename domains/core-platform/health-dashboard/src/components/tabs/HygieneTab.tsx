import React, { useEffect, useMemo, useState } from 'react';
import { dataApi, HygieneIssue, HygieneStatus } from '../../services/api';
import { LoadingSpinner } from '../LoadingSpinner';
import type { TabProps } from './types';

type FilterState = {
  status: string;
  severity: string;
  issueType: string;
};

const STATUS_OPTIONS: { label: string; value: string }[] = [
  { label: 'All statuses', value: '' },
  { label: 'Open', value: 'open' },
  { label: 'Ignored', value: 'ignored' },
  { label: 'Resolved', value: 'resolved' },
];

const SEVERITY_OPTIONS = [
  { label: 'All severities', value: '' },
  { label: 'High', value: 'high' },
  { label: 'Medium', value: 'medium' },
  { label: 'Low', value: 'low' },
];

const ISSUE_TYPE_LABELS: Record<string, string> = {
  duplicate_name: 'Duplicate Name',
  placeholder_name: 'Placeholder Name',
  missing_area: 'Unassigned Area',
  pending_configuration: 'Pending Configuration',
  disabled_entity: 'Disabled Entity',
};

const SEVERITY_BADGE: Record<string, string> = {
  high: 'bg-red-100 text-red-800 border-red-200',
  medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
  low: 'bg-blue-100 text-blue-800 border-blue-200',
};

const STATUS_BADGE: Record<string, string> = {
  open: 'bg-amber-100 text-amber-800 border-amber-200',
  ignored: 'bg-gray-100 text-gray-600 border-gray-200',
  resolved: 'bg-green-100 text-green-800 border-green-200',
};

function formatDate(value?: string | null): string {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString();
  } catch (error) {
    return value;
  }
}

function summarizeIssues(issues: HygieneIssue[]) {
  const openCount = issues.filter((issue) => issue.status === 'open').length;
  const highSeverity = issues.filter((issue) => issue.severity === 'high' && issue.status === 'open').length;
  const pendingConfig = issues.filter((issue) => issue.issue_type === 'pending_configuration' && issue.status === 'open').length;

  return { openCount, highSeverity, pendingConfig };
}

const HygienicSummaryCard: React.FC<{ title: string; value: number; highlight?: boolean }> = ({ title, value, highlight }) => (
  <div className={`p-4 rounded-lg border ${highlight ? 'bg-amber-50 border-amber-200 text-amber-900' : 'bg-white border-gray-200 text-gray-900'} shadow-sm`}> 
    <p className="text-sm font-medium">{title}</p>
    <p className="text-2xl font-semibold mt-1">{value}</p>
  </div>
);

export const HygieneTab: React.FC<TabProps> = ({ darkMode }) => {
  const [issues, setIssues] = useState<HygieneIssue[]>([]);
  const [filters, setFilters] = useState<FilterState>({ status: '', severity: '', issueType: '' });
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [busyIssue, setBusyIssue] = useState<string | null>(null);

  const summary = useMemo(() => summarizeIssues(issues), [issues]);

  const loadIssues = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await dataApi.getHygieneIssues({
        status: filters.status || undefined,
        severity: filters.severity || undefined,
        issue_type: filters.issueType || undefined,
      });
      setIssues(response.issues);
    } catch (err) {
      console.error('Failed to load hygiene issues', err);
      setError('Unable to load hygiene suggestions. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIssues();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.status, filters.severity, filters.issueType]);

  const handleStatusChange = async (issue: HygieneIssue, newStatus: HygieneStatus) => {
    try {
      setBusyIssue(issue.issue_key);
      const updated = await dataApi.updateHygieneIssueStatus(issue.issue_key, newStatus);
      setIssues((prev) => prev.map((item) => (item.issue_key === updated.issue_key ? updated : item)));
    } catch (err) {
      console.error('Status update failed', err);
      setError('Failed to update issue status.');
    } finally {
      setBusyIssue(null);
    }
  };

  const handleApplySuggestion = async (issue: HygieneIssue) => {
    if (!issue.suggested_action) {
      return handleStatusChange(issue, 'resolved');
    }

    try {
      setBusyIssue(issue.issue_key);
      const updated = await dataApi.applyHygieneIssueAction(issue.issue_key, issue.suggested_action, issue.suggested_value ?? undefined);
      setIssues((prev) => prev.map((item) => (item.issue_key === updated.issue_key ? updated : item)));
    } catch (err) {
      console.error('Apply action failed', err);
      setError('Unable to apply remediation. Review Home Assistant connectivity.');
    } finally {
      setBusyIssue(null);
    }
  };

  const filteredStates = (
    <div className="flex flex-col lg:flex-row gap-3">
      <select
        value={filters.status}
        onChange={(event) => setFilters((prev) => ({ ...prev, status: event.target.value }))}
        className="px-3 py-2 rounded-lg border border-gray-200 text-sm"
      >
        {STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={filters.severity}
        onChange={(event) => setFilters((prev) => ({ ...prev, severity: event.target.value }))}
        className="px-3 py-2 rounded-lg border border-gray-200 text-sm"
      >
        {SEVERITY_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <select
        value={filters.issueType}
        onChange={(event) => setFilters((prev) => ({ ...prev, issueType: event.target.value }))}
        className="px-3 py-2 rounded-lg border border-gray-200 text-sm"
      >
        <option value="">All issue types</option>
        {Object.entries(ISSUE_TYPE_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="space-y-6">
      <section>
        <h2 className="text-xl font-semibold mb-2">Device Hygiene Suggestions</h2>
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Review Home Assistant entities that could block automation success. Suggestions below consolidate duplicate names, disabled entities, and pending configurations.
        </p>
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <HygienicSummaryCard title="Open Issues" value={summary.openCount} highlight={summary.openCount > 0} />
        <HygienicSummaryCard title="High Severity" value={summary.highSeverity} highlight={summary.highSeverity > 0} />
        <HygienicSummaryCard title="Pending Config" value={summary.pendingConfig} highlight={summary.pendingConfig > 0} />
      </section>

      <section className="space-y-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {filteredStates}
          <button
            onClick={loadIssues}
            className="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-100"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-10">
            <LoadingSpinner label="Loading hygiene suggestions" />
          </div>
        ) : error ? (
          <div className="p-4 border border-red-200 bg-red-50 rounded-lg text-red-800 flex flex-col gap-2">
            <span>{error}</span>
            <button
              onClick={loadIssues}
              className="self-start px-3 py-2 rounded-lg bg-red-100 hover:bg-red-200 text-sm"
            >
              Retry
            </button>
          </div>
        ) : issues.length === 0 ? (
          <div className="p-6 border border-dashed border-gray-300 rounded-lg text-center text-gray-600 dark:text-gray-300">
            <p className="text-lg font-medium">All devices look healthy 🎉</p>
            <p className="text-sm">Clean names and configured entities help the automation engine pick the right targets.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {issues.map((issue) => {
              const actionLabel = issue.suggested_action ? 'Apply Suggestion' : 'Mark Resolved';
              const severityClass = SEVERITY_BADGE[issue.severity] || 'bg-gray-100 text-gray-700 border-gray-200';
              const statusClass = STATUS_BADGE[issue.status] || 'bg-gray-100 text-gray-700 border-gray-200';

              return (
                <div key={issue.issue_key} className="border border-gray-200 rounded-lg p-4 shadow-sm bg-white">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-lg font-semibold text-gray-900 dark:text-white">
                          {issue.name || 'Unnamed Device'}
                        </span>
                        <span className={`px-2 py-1 rounded-full border text-xs font-medium ${severityClass}`}>
                          Severity: {issue.severity.toUpperCase()}
                        </span>
                        <span className={`px-2 py-1 rounded-full border text-xs font-medium ${statusClass}`}>
                          {issue.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-300 mt-1">
                        {ISSUE_TYPE_LABELS[issue.issue_type] || issue.issue_type}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApplySuggestion(issue)}
                        disabled={busyIssue === issue.issue_key}
                        className={`px-3 py-2 rounded-lg text-sm font-medium ${busyIssue === issue.issue_key ? 'opacity-75 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-500'}`}
                      >
                        {busyIssue === issue.issue_key ? 'Applying…' : actionLabel}
                      </button>
                      {issue.status !== 'ignored' ? (
                        <button
                          onClick={() => handleStatusChange(issue, 'ignored')}
                          className="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-100"
                          disabled={busyIssue === issue.issue_key}
                        >
                          Ignore
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStatusChange(issue, 'open')}
                          className="px-3 py-2 rounded-lg border border-gray-200 text-sm hover:bg-gray-100"
                          disabled={busyIssue === issue.issue_key}
                        >
                          Reopen
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-2 sm:grid-cols-3 text-sm text-gray-600 dark:text-gray-300">
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-100">Suggested Action:</span>
                      <p className="mt-0.5">
                        {issue.suggested_action ? `${issue.suggested_action.replace('_', ' ')}${issue.suggested_value ? ` → ${issue.suggested_value}` : ''}` : 'Review manually'}
                      </p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-100">Detected:</span>
                      <p className="mt-0.5">{formatDate(issue.detected_at)}</p>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700 dark:text-gray-100">Last Updated:</span>
                      <p className="mt-0.5">{formatDate(issue.updated_at)}</p>
                    </div>
                  </div>

                  {issue.metadata?.conflicting_device_ids ? (
                    <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">
                      Conflicts with: {(issue.metadata.conflicting_device_ids as string[]).join(', ')}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
};

