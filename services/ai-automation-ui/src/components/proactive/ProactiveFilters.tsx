/**
 * Proactive Filters Component
 * Epic AI-21: Filter proactive suggestions by type and status
 */

import React from 'react';
import type { ProactiveSuggestionFilters, ProactiveContextType, ProactiveSuggestionStatus } from '../../types/proactive';
import { CONTEXT_TYPE_CONFIG, STATUS_CONFIG } from '../../types/proactive';

interface ProactiveFiltersProps {
  filters: ProactiveSuggestionFilters;
  onFilterChange: (filters: ProactiveSuggestionFilters) => void;
  darkMode: boolean;
}

export const ProactiveFilters: React.FC<ProactiveFiltersProps> = ({
  filters,
  onFilterChange,
  darkMode,
}) => {
  const handleContextTypeChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as ProactiveContextType | '';
    onFilterChange({
      ...filters,
      context_type: value || null,
    });
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value as ProactiveSuggestionStatus | '';
    onFilterChange({
      ...filters,
      status: value || null,
    });
  };

  const handleClearFilters = () => {
    onFilterChange({
      context_type: null,
      status: null,
      limit: filters.limit,
      offset: 0,
    });
  };

  const hasActiveFilters = filters.context_type || filters.status;

  const selectClassName = `
    px-3 py-2 rounded-lg text-sm font-medium
    ${darkMode 
      ? 'bg-slate-700 border-slate-600 text-slate-200 focus:border-sky-500' 
      : 'bg-white border-gray-300 text-gray-700 focus:border-sky-500'
    }
    border focus:outline-none focus:ring-1 focus:ring-sky-500/50
    transition-colors cursor-pointer
  `;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Context Type Filter */}
      <div className="flex items-center gap-2">
        <label 
          htmlFor="context-type-filter" 
          className={`text-sm ${darkMode ? 'text-slate-400' : 'text-gray-500'}`}
        >
          Type:
        </label>
        <select
          id="context-type-filter"
          value={filters.context_type || ''}
          onChange={handleContextTypeChange}
          className={selectClassName}
        >
          <option value="">All Types</option>
          {Object.entries(CONTEXT_TYPE_CONFIG).map(([type, config]) => (
            <option key={type} value={type}>
              {config.icon} {config.label}
            </option>
          ))}
        </select>
      </div>

      {/* Status Filter */}
      <div className="flex items-center gap-2">
        <label 
          htmlFor="status-filter" 
          className={`text-sm ${darkMode ? 'text-slate-400' : 'text-gray-500'}`}
        >
          Status:
        </label>
        <select
          id="status-filter"
          value={filters.status || ''}
          onChange={handleStatusChange}
          className={selectClassName}
        >
          <option value="">All Status</option>
          {Object.entries(STATUS_CONFIG).map(([status, config]) => (
            <option key={status} value={status}>
              {config.label}
            </option>
          ))}
        </select>
      </div>

      {/* Clear Filters Button */}
      {hasActiveFilters && (
        <button
          onClick={handleClearFilters}
          className={`
            px-3 py-2 rounded-lg text-sm font-medium transition-colors
            ${darkMode 
              ? 'text-slate-400 hover:text-slate-200 hover:bg-slate-700' 
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            }
          `}
        >
          ✕ Clear Filters
        </button>
      )}
    </div>
  );
};

export default ProactiveFilters;
