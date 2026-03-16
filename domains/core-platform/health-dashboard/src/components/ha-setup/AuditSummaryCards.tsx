import React from 'react';
import type { AuditScore, EntityRecord } from '../../hooks/useEntityAudit';

interface Props {
  entities: EntityRecord[];
  scores: AuditScore[];
  darkMode: boolean;
}

export const AuditSummaryCards: React.FC<Props> = ({ entities, scores, darkMode }) => {
  const total = entities.length;
  const compliant = scores.filter(s => s.total >= 70).length;
  const pct = total > 0 ? Math.round((compliant / total) * 100) : 0;

  const missingArea = scores.filter(s => !s.hasArea).length;
  const missingLabels = scores.filter(s => !s.hasLabels).length;
  const missingAliases = scores.filter(s => !s.hasAliases).length;
  const areaCompliant = total > 0 ? Math.round(((total - missingArea) / total) * 100) : 0;

  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';

  return (
    <div className="space-y-4">
      {/* Overall Score Bar */}
      <div className={`rounded-lg border p-4 ${bg}`}>
        <div className="flex items-center justify-between mb-2">
          <span className={`text-sm font-medium ${text}`}>Overall Compliance</span>
          <span className={`text-2xl font-bold ${pct >= 70 ? 'text-green-500' : pct >= 40 ? 'text-yellow-500' : 'text-red-500'}`}>
            {pct}%
          </span>
        </div>
        <div className={`w-full h-3 rounded-full ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <div
            className={`h-3 rounded-full transition-all ${pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <p className={`text-xs mt-1 ${muted}`}>
          {compliant}/{total} entities scoring 70+
        </p>
      </div>

      {/* Issue Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <IssueCard
          label="Missing Area"
          count={missingArea}
          total={total}
          icon="&#x26A0;"
          darkMode={darkMode}
        />
        <IssueCard
          label="No Labels"
          count={missingLabels}
          total={total}
          icon="&#x1F3F7;"
          darkMode={darkMode}
        />
        <IssueCard
          label="No Aliases"
          count={missingAliases}
          total={total}
          icon="&#x1F4AC;"
          darkMode={darkMode}
        />
        <IssueCard
          label="Area Convention"
          count={areaCompliant}
          total={100}
          icon="&#x2705;"
          isPercent
          darkMode={darkMode}
        />
      </div>
    </div>
  );
};

interface IssueCardProps {
  label: string;
  count: number;
  total: number;
  icon: string;
  isPercent?: boolean;
  darkMode: boolean;
}

const IssueCard: React.FC<IssueCardProps> = ({ label, count, total, icon, isPercent, darkMode }) => {
  const bg = darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200';
  const text = darkMode ? 'text-gray-200' : 'text-gray-900';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';

  return (
    <div className={`rounded-lg border p-3 ${bg}`}>
      <div className="flex items-center gap-1 mb-1">
        <span>{icon}</span>
        <span className={`text-xs font-medium ${muted}`}>{label}</span>
      </div>
      <span className={`text-lg font-bold ${text}`}>
        {isPercent ? `${count}%` : count}
      </span>
      {!isPercent && (
        <span className={`text-xs ml-1 ${muted}`}>/ {total}</span>
      )}
    </div>
  );
};
