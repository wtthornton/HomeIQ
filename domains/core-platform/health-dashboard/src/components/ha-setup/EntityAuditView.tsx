import React, { useState, useMemo } from 'react';
import type { EntityRecord, AuditScore, AreaInfo } from '../../hooks/useEntityAudit';
import { AuditSummaryCards } from './AuditSummaryCards';
import { EntityAuditRow } from './EntityAuditRow';
import { BulkActionsBar } from './BulkActionsBar';
import { QuickActions } from './QuickActions';

interface Props {
  entities: EntityRecord[];
  scores: AuditScore[];
  areas: AreaInfo[];
  darkMode: boolean;
  onUpdateLabels: (entityId: string, labels: string[]) => Promise<void>;
  onUpdateAliases: (entityId: string, aliases: string[]) => Promise<void>;
  onUpdateName: (entityId: string, name: string) => Promise<void>;
  onBulkLabel: (entityIds: string[], addLabels: string[], removeLabels?: string[]) => Promise<void>;
}

type SortKey = 'score' | 'entity_id' | 'area' | 'labels' | 'aliases';
type IssueFilter = 'all' | 'missing-area' | 'missing-labels' | 'missing-aliases' | 'low-score';

export const EntityAuditView: React.FC<Props> = ({
  entities, scores, areas, darkMode,
  onUpdateLabels, onUpdateAliases, onUpdateName, onBulkLabel,
}) => {
  const [search, setSearch] = useState('');
  const [areaFilter, setAreaFilter] = useState('');
  const [domainFilter, setDomainFilter] = useState('');
  const [issueFilter, setIssueFilter] = useState<IssueFilter>('all');
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [sortAsc, setSortAsc] = useState(true);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showQuickActions, setShowQuickActions] = useState(false);

  const inputBg = darkMode ? 'bg-gray-700 text-gray-200 border-gray-600' : 'bg-white text-gray-900 border-gray-300';
  const muted = darkMode ? 'text-gray-400' : 'text-gray-500';
  const headerBg = darkMode ? 'bg-gray-800' : 'bg-gray-100';
  const areaNames = areas.map(a => a.display_name);

  // Score map for quick lookup
  const scoreMap = useMemo(() => {
    const map = new Map<string, AuditScore>();
    scores.forEach(s => map.set(s.entity_id, s));
    return map;
  }, [scores]);

  // Unique domains for filter
  const domains = useMemo(() =>
    Array.from(new Set(entities.map(e => e.domain))).sort(),
    [entities]
  );

  // Filter & sort
  const filtered = useMemo(() => {
    let result = entities;

    if (search) {
      const q = search.toLowerCase();
      result = result.filter(e =>
        e.entity_id.toLowerCase().includes(q) ||
        (e.friendly_name || '').toLowerCase().includes(q) ||
        (e.name || '').toLowerCase().includes(q)
      );
    }
    if (areaFilter) result = result.filter(e => e.area_id === areaFilter);
    if (domainFilter) result = result.filter(e => e.domain === domainFilter);

    if (issueFilter !== 'all') {
      result = result.filter(e => {
        const s = scoreMap.get(e.entity_id);
        if (!s) return false;
        switch (issueFilter) {
          case 'missing-area': return !s.hasArea;
          case 'missing-labels': return !s.hasLabels;
          case 'missing-aliases': return !s.hasAliases;
          case 'low-score': return s.total < 40;
          default: return true;
        }
      });
    }

    // Sort
    result = [...result].sort((a, b) => {
      const sa = scoreMap.get(a.entity_id);
      const sb = scoreMap.get(b.entity_id);
      let cmp = 0;
      switch (sortKey) {
        case 'score': cmp = (sa?.total || 0) - (sb?.total || 0); break;
        case 'entity_id': cmp = a.entity_id.localeCompare(b.entity_id); break;
        case 'area': cmp = (a.area_id || '').localeCompare(b.area_id || ''); break;
        case 'labels': cmp = (a.labels?.length || 0) - (b.labels?.length || 0); break;
        case 'aliases': cmp = (a.aliases?.length || 0) - (b.aliases?.length || 0); break;
      }
      return sortAsc ? cmp : -cmp;
    });

    return result;
  }, [entities, search, areaFilter, domainFilter, issueFilter, sortKey, sortAsc, scoreMap]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selectedIds.size === filtered.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filtered.map(e => e.entity_id)));
    }
  };

  return (
    <div className="space-y-4">
      <AuditSummaryCards entities={entities} scores={scores} darkMode={darkMode} />

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search entities..."
          className={`text-xs rounded border px-2 py-1 w-48 ${inputBg}`}
        />
        <select value={areaFilter} onChange={(e) => setAreaFilter(e.target.value)}
          className={`text-xs rounded border px-2 py-1 ${inputBg}`}>
          <option value="">All Areas</option>
          {areas.map(a => (
            <option key={a.area_id} value={a.area_id}>{a.display_name} ({a.entity_count})</option>
          ))}
        </select>
        <select value={domainFilter} onChange={(e) => setDomainFilter(e.target.value)}
          className={`text-xs rounded border px-2 py-1 ${inputBg}`}>
          <option value="">All Domains</option>
          {domains.map(d => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select value={issueFilter} onChange={(e) => setIssueFilter(e.target.value as IssueFilter)}
          className={`text-xs rounded border px-2 py-1 ${inputBg}`}>
          <option value="all">All Issues</option>
          <option value="missing-area">Missing Area</option>
          <option value="missing-labels">Missing Labels</option>
          <option value="missing-aliases">Missing Aliases</option>
          <option value="low-score">Low Score (&lt;40)</option>
        </select>
        <span className={`text-xs ${muted}`}>{filtered.length} entities</span>
        <button
          onClick={() => setShowQuickActions(!showQuickActions)}
          className={`text-xs px-2 py-1 ml-auto rounded ${darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'}`}
        >
          {showQuickActions ? 'Hide' : 'Show'} Quick Actions
        </button>
      </div>

      {/* Quick Actions Panel */}
      {showQuickActions && (
        <QuickActions entities={entities} darkMode={darkMode} onBulkLabel={onBulkLabel} />
      )}

      {/* Bulk Actions */}
      <BulkActionsBar
        selectedCount={selectedIds.size}
        selectedIds={Array.from(selectedIds)}
        darkMode={darkMode}
        onBulkLabel={onBulkLabel}
        onClearSelection={() => setSelectedIds(new Set())}
      />

      {/* Table Header */}
      <div className={`flex items-center gap-3 px-4 py-2 text-xs font-medium rounded-t-lg ${headerBg} ${muted}`}>
        <input
          type="checkbox"
          checked={filtered.length > 0 && selectedIds.size === filtered.length}
          onChange={selectAll}
          className="h-4 w-4 rounded"
        />
        <button className="flex-1 text-left" onClick={() => toggleSort('entity_id')}>
          Entity {sortKey === 'entity_id' ? (sortAsc ? '\u2191' : '\u2193') : ''}
        </button>
        <button className="w-20 text-center" onClick={() => toggleSort('area')}>
          Area {sortKey === 'area' ? (sortAsc ? '\u2191' : '\u2193') : ''}
        </button>
        <button className="w-14 text-center" onClick={() => toggleSort('labels')}>
          Labels {sortKey === 'labels' ? (sortAsc ? '\u2191' : '\u2193') : ''}
        </button>
        <button className="w-14 text-center" onClick={() => toggleSort('aliases')}>
          Aliases {sortKey === 'aliases' ? (sortAsc ? '\u2191' : '\u2193') : ''}
        </button>
        <button className="w-14 text-center" onClick={() => toggleSort('score')}>
          Score {sortKey === 'score' ? (sortAsc ? '\u2191' : '\u2193') : ''}
        </button>
        <div className="w-6" />
      </div>

      {/* Entity rows */}
      <div className={`border rounded-b-lg max-h-[600px] overflow-y-auto ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
        {filtered.length === 0 ? (
          <div className={`text-center py-8 ${muted}`}>
            {entities.length === 0 ? 'No entities found' : 'No entities match filters'}
          </div>
        ) : (
          filtered.map(entity => {
            const score = scoreMap.get(entity.entity_id);
            if (!score) return null;
            return (
              <EntityAuditRow
                key={entity.entity_id}
                entity={entity}
                score={score}
                areaNames={areaNames}
                darkMode={darkMode}
                selected={selectedIds.has(entity.entity_id)}
                onToggleSelect={toggleSelect}
                onUpdateLabels={onUpdateLabels}
                onUpdateAliases={onUpdateAliases}
                onUpdateName={onUpdateName}
              />
            );
          })
        )}
      </div>
    </div>
  );
};
