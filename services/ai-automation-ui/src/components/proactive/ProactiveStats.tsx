/**
 * Proactive Stats Component
 * Epic AI-21: Display statistics for proactive suggestions
 */

import React from 'react';
import type { ProactiveSuggestionStats } from '../../types/proactive';
import { CONTEXT_TYPE_CONFIG, STATUS_CONFIG } from '../../types/proactive';

interface ProactiveStatsProps {
  stats: ProactiveSuggestionStats | null;
  loading: boolean;
  darkMode: boolean;
}

export const ProactiveStats: React.FC<ProactiveStatsProps> = ({
  stats,
  loading,
  darkMode,
}) => {
  if (loading) {
    return (
      <div className="flex items-center gap-4 animate-pulse">
        {[1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className={`h-6 w-20 rounded-full ${
              darkMode ? 'bg-slate-700' : 'bg-gray-200'
            }`}
          />
        ))}
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Total */}
      <div className={`
        flex items-center gap-2 px-3 py-1 rounded-full text-sm
        ${darkMode ? 'bg-slate-700/50 text-slate-300' : 'bg-gray-100 text-gray-700'}
      `}>
        <span>Total:</span>
        <span className="font-semibold">{stats.total}</span>
      </div>

      {/* By Context Type */}
      {Object.entries(stats.by_context_type).map(([type, count]) => {
        const config = CONTEXT_TYPE_CONFIG[type as keyof typeof CONTEXT_TYPE_CONFIG];
        if (!config || !count) return null;
        
        return (
          <div
            key={type}
            className={`
              flex items-center gap-1.5 px-3 py-1 rounded-full text-sm
              ${config.bgColor} ${config.color}
            `}
          >
            <span>{config.icon}</span>
            <span>{config.label}:</span>
            <span className="font-semibold">{count}</span>
          </div>
        );
      })}

      {/* Separator */}
      <div className={`w-px h-4 ${darkMode ? 'bg-slate-600' : 'bg-gray-300'}`} />

      {/* By Status */}
      {Object.entries(stats.by_status).map(([status, count]) => {
        const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG];
        if (!config || !count) return null;
        
        return (
          <div
            key={status}
            className={`
              flex items-center gap-1.5 px-2 py-1 rounded-full text-xs
              ${config.bgColor} ${config.color}
            `}
          >
            <span>{config.label}:</span>
            <span className="font-semibold">{count}</span>
          </div>
        );
      })}
    </div>
  );
};

export default ProactiveStats;
