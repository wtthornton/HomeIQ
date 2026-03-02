import React, { useState, useEffect, useMemo } from 'react';
import { SkeletonCard } from './skeletons';
import { adminApi, GroupHealthResponse } from '../services/api';
import type { ServiceStatus, ServiceDefinition, ServiceGroupId } from '../types';
import type { ServicesHealthResponse } from '../types/health';
import { SERVICE_DEFINITIONS, GROUP_DEFINITIONS } from './ServicesTab';
import { Icon, ChevronDown, ChevronRight, CheckCircle, AlertTriangle, AlertCircle } from './ui/icons';
import type { ContainerInfo } from '../services/api';

interface GroupsTabProps {
  darkMode: boolean;
}

type GroupAggregateStatus = 'healthy' | 'degraded' | 'unhealthy' | 'empty';

interface GroupData {
  id: ServiceGroupId;
  label: string;
  description: string;
  services: Array<{
    definition: ServiceDefinition;
    status: ServiceStatus | null;
  }>;
  aggregateStatus: GroupAggregateStatus;
  healthyCount: number;
  degradedCount: number;
  totalCount: number;
}

// --- Teal palette + liquid glass tokens ---
const TEAL = {
  50: '#f0fdfa',
  100: '#ccfbf1',
  200: '#99f6e4',
  300: '#5eead4',
  400: '#2dd4bf',
  500: '#14b8a6',
  600: '#0d9488',
  700: '#0f766e',
  800: '#115e59',
  900: '#134e4a',
};

const glass = {
  card: 'backdrop-blur-md bg-white/70 border border-white/30 shadow-lg shadow-black/5',
  cardDark: 'backdrop-blur-md bg-gray-900/70 border border-white/10 shadow-lg shadow-black/20',
  elevated: 'backdrop-blur-xl bg-white/80 border border-white/40 shadow-xl shadow-black/8',
  elevatedDark: 'backdrop-blur-xl bg-gray-900/80 border border-white/15 shadow-xl shadow-black/30',
};

function formatTimeAgo(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ago`;
}

export const GroupsTab: React.FC<GroupsTabProps> = ({ darkMode }) => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [groupHealth, setGroupHealth] = useState<GroupHealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const loadServices = async () => {
    try {
      const [servicesHealth, containersData, groupData] = await Promise.all([
        adminApi.getServicesHealth(),
        adminApi.getContainers().catch(() => [] as ContainerInfo[]),
        adminApi.getGroupHealth().catch(() => null),
      ]);

      const mappedServices: ServiceStatus[] = Object.entries(servicesHealth as ServicesHealthResponse).map(
        ([serviceName, health]) => {
          const container = containersData.find((c: ContainerInfo) => c.service_name === serviceName);
          const containerStatus = container?.status?.toLowerCase();

          let normalized: string;

          if (container && containerStatus) {
            if (containerStatus === 'stopped' || containerStatus === 'exited') {
              normalized = 'stopped';
            } else if (containerStatus === 'running') {
              if (health.status === 'healthy' || health.status === 'pass') {
                normalized = 'running';
              } else if (health.status === 'degraded') {
                normalized = 'degraded';
              } else if (health.status === 'unhealthy' || health.status === 'error') {
                normalized = 'error';
              } else {
                normalized = 'running';
              }
            } else {
              if (health.status === 'healthy' || health.status === 'pass') {
                normalized = 'running';
              } else if (health.status === 'degraded') {
                normalized = 'degraded';
              } else if (health.status === 'unhealthy' || health.status === 'error') {
                normalized = 'error';
              } else {
                normalized = 'stopped';
              }
            }
          } else {
            if (health.status === 'healthy' || health.status === 'pass') {
              normalized = 'running';
            } else if (health.status === 'degraded') {
              normalized = 'degraded';
            } else if (health.status === 'unhealthy' || health.status === 'error') {
              normalized = 'error';
            } else {
              normalized = 'stopped';
            }
          }

          return {
            service: serviceName,
            running: normalized === 'running' || normalized === 'degraded',
            status: normalized as ServiceStatus['status'],
            timestamp: health.last_check,
          };
        }
      );

      setServices(mappedServices);
      setGroupHealth(groupData);
      setError('');
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load services');
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServices();

    if (autoRefresh) {
      const interval = setInterval(loadServices, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const expandAll = () => {
    const allIds = Object.keys(GROUP_DEFINITIONS);
    setExpandedGroups(new Set(allIds));
  };

  const collapseAll = () => {
    setExpandedGroups(new Set());
  };

  const getServiceStatus = (serviceId: string): ServiceStatus | null => {
    return services.find(s => s.service === serviceId) || null;
  };

  const groups: GroupData[] = useMemo(() => {
    const groupIds = Object.keys(GROUP_DEFINITIONS) as ServiceGroupId[];

    return groupIds.map(groupId => {
      const groupDef = GROUP_DEFINITIONS[groupId];
      const groupServices = SERVICE_DEFINITIONS
        .filter(def => def.group === groupId)
        .map(def => ({
          definition: def,
          status: getServiceStatus(def.id),
        }));

      const totalCount = groupServices.length;
      const healthyCount = groupServices.filter(
        s => s.status && s.status.status === 'running'
      ).length;
      const degradedCount = groupServices.filter(
        s => s.status && s.status.status === 'degraded'
      ).length;

      let aggregateStatus: GroupAggregateStatus;
      if (totalCount === 0) {
        aggregateStatus = 'empty';
      } else if (healthyCount + degradedCount === totalCount) {
        aggregateStatus = degradedCount > 0 ? 'degraded' : 'healthy';
      } else if (healthyCount + degradedCount === 0) {
        aggregateStatus = 'unhealthy';
      } else {
        aggregateStatus = 'degraded';
      }

      return {
        id: groupId,
        label: groupDef.label,
        description: groupDef.description,
        services: groupServices,
        aggregateStatus,
        healthyCount,
        degradedCount,
        totalCount,
      };
    });
  }, [services]);

  // Compute overview stats
  const overview = useMemo(() => {
    const activeGroups = groups.filter(g => g.totalCount > 0);
    return {
      totalGroups: activeGroups.length,
      healthyGroups: activeGroups.filter(g => g.aggregateStatus === 'healthy').length,
      degradedGroups: activeGroups.filter(g => g.aggregateStatus === 'degraded').length,
      unhealthyGroups: activeGroups.filter(g => g.aggregateStatus === 'unhealthy').length,
      totalServices: groups.reduce((a, g) => a + g.totalCount, 0),
      healthyServices: groups.reduce((a, g) => a + g.healthyCount + g.degradedCount, 0),
    };
  }, [groups]);

  const statusColors: Record<GroupAggregateStatus, {
    ring: string;
    badge: string;
    badgeDark: string;
    progress: string;
    dot: string;
    icon: typeof CheckCircle;
    label: string;
  }> = {
    healthy: {
      ring: `border-l-4` ,
      badge: `text-green-800 bg-green-100`,
      badgeDark: `text-green-200 bg-green-900/40`,
      progress: 'bg-green-500',
      dot: 'bg-green-500',
      icon: CheckCircle,
      label: 'Healthy',
    },
    degraded: {
      ring: `border-l-4`,
      badge: `text-yellow-800 bg-yellow-100`,
      badgeDark: `text-yellow-200 bg-yellow-900/40`,
      progress: 'bg-yellow-500',
      dot: 'bg-yellow-500',
      icon: AlertTriangle,
      label: 'Degraded',
    },
    unhealthy: {
      ring: `border-l-4`,
      badge: `text-red-800 bg-red-100`,
      badgeDark: `text-red-200 bg-red-900/40`,
      progress: 'bg-red-500',
      dot: 'bg-red-500',
      icon: AlertCircle,
      label: 'Unhealthy',
    },
    empty: {
      ring: `border-l-4`,
      badge: `text-gray-600 bg-gray-100`,
      badgeDark: `text-gray-400 bg-gray-800`,
      progress: 'bg-gray-400',
      dot: 'bg-gray-400',
      icon: AlertCircle,
      label: 'No Services',
    },
  };

  // Ring color based on status (applied as border-left color via style)
  const ringColor = (status: GroupAggregateStatus) => {
    switch (status) {
      case 'healthy': return TEAL[500];
      case 'degraded': return '#eab308';
      case 'unhealthy': return '#ef4444';
      default: return '#9ca3af';
    }
  };

  if (loading) {
    return (
      <div className="space-y-8">
        <div>
          <h2 className={`text-xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Deployment Groups
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={`group-${i}`} variant="service" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`rounded-xl p-6 ${darkMode ? glass.cardDark : glass.card}`}>
        <div className="text-center">
          <Icon icon={AlertCircle} size="xl" className="mx-auto text-red-500 mb-4" />
          <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Error Loading Groups
          </h3>
          <p className={`mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{error}</p>
          <button
            onClick={loadServices}
            className="px-4 py-2 rounded-lg font-medium transition-colors duration-200 text-white"
            style={{ backgroundColor: TEAL[600] }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = TEAL[700])}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = TEAL[600])}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Summary Banner */}
      <div className={`rounded-xl p-6 ${darkMode ? glass.elevatedDark : glass.elevated}`}>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Domain Groups
            </h2>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              {overview.healthyServices}/{overview.totalServices} services operational across {overview.totalGroups} groups
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Expand/Collapse */}
            <button
              onClick={expandedGroups.size > 0 ? collapseAll : expandAll}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                darkMode
                  ? 'bg-gray-800 hover:bg-gray-700 text-gray-300'
                  : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              {expandedGroups.size > 0 ? 'Collapse All' : 'Expand All'}
            </button>

            {/* Auto-refresh */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors text-white"
              style={{ backgroundColor: autoRefresh ? TEAL[600] : (darkMode ? '#374151' : '#d1d5db'), color: autoRefresh ? '#fff' : (darkMode ? '#d1d5db' : '#374151') }}
            >
              {autoRefresh ? 'Live' : 'Paused'}
            </button>

            {/* Manual Refresh */}
            <button
              onClick={loadServices}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors text-white"
              style={{ backgroundColor: TEAL[600] }}
              onMouseEnter={e => (e.currentTarget.style.backgroundColor = TEAL[700])}
              onMouseLeave={e => (e.currentTarget.style.backgroundColor = TEAL[600])}
            >
              Refresh
            </button>
          </div>
        </div>

        {/* Summary Stat Chips */}
        <div className="flex flex-wrap gap-3 mt-4">
          <StatChip
            label="Healthy"
            count={overview.healthyGroups}
            color={TEAL[500]}
            darkMode={darkMode}
          />
          <StatChip
            label="Degraded"
            count={overview.degradedGroups}
            color="#eab308"
            darkMode={darkMode}
          />
          <StatChip
            label="Unhealthy"
            count={overview.unhealthyGroups}
            color="#ef4444"
            darkMode={darkMode}
          />
        </div>

        {/* Timestamp */}
        <div className={`text-xs mt-3 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
          Updated {formatTimeAgo(lastUpdate)}
        </div>
      </div>

      {/* Empty State */}
      {groups.filter(g => g.totalCount > 0).length === 0 && (
        <div className={`rounded-xl p-12 text-center ${darkMode ? glass.cardDark : glass.card}`}>
          <div className="text-6xl mb-4">📦</div>
          <h3 className={`text-xl font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            No Domain Groups Found
          </h3>
          <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            No services are registered in any domain group. Check service configuration.
          </p>
          <button
            onClick={loadServices}
            className="mt-4 px-4 py-2 rounded-lg font-medium text-white transition-colors"
            style={{ backgroundColor: TEAL[600] }}
            onMouseEnter={e => (e.currentTarget.style.backgroundColor = TEAL[700])}
            onMouseLeave={e => (e.currentTarget.style.backgroundColor = TEAL[600])}
          >
            Retry
          </button>
        </div>
      )}

      {/* Group Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-5">
        {groups.filter(g => g.totalCount > 0).map(group => {
          const sc = statusColors[group.aggregateStatus];
          const isExpanded = expandedGroups.has(group.id);
          const pct = group.totalCount > 0
            ? ((group.healthyCount + group.degradedCount) / group.totalCount) * 100
            : 0;

          return (
            <div
              key={group.id}
              className={`rounded-xl transition-all duration-200 ${darkMode ? glass.cardDark : glass.card} ${sc.ring}`}
              style={{ borderLeftColor: ringColor(group.aggregateStatus) }}
            >
              {/* Header */}
              <button
                onClick={() => toggleGroup(group.id)}
                className="w-full text-left p-5 focus-visible:outline-none focus-visible:ring-2 rounded-xl"
                style={{ '--tw-ring-color': TEAL[400] } as React.CSSProperties}
                aria-expanded={isExpanded}
                aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${group.label}`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-base font-semibold truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {group.label}
                    </h3>
                    <p className={`text-xs mt-0.5 ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                      {group.description}
                    </p>
                  </div>
                  <span className={`ml-3 flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${
                    darkMode ? sc.badgeDark : sc.badge
                  }`}>
                    <Icon icon={sc.icon} size="xs" />
                    {sc.label}
                  </span>
                </div>

                {/* Stats row */}
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {group.healthyCount + group.degradedCount}/{group.totalCount} services up
                    {group.degradedCount > 0 && (
                      <span className="text-yellow-500 ml-1">({group.degradedCount} degraded)</span>
                    )}
                  </span>
                  <Icon
                    icon={isExpanded ? ChevronDown : ChevronRight}
                    size="sm"
                    className={darkMode ? 'text-gray-500' : 'text-gray-400'}
                  />
                </div>

                {/* Progress bar */}
                <div className={`mt-3 w-full rounded-full h-1.5 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                  <div
                    className={`h-1.5 rounded-full transition-all duration-500 ${sc.progress}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              </button>

              {/* Expanded Service List */}
              {isExpanded && group.services.length > 0 && (
                <div className={`border-t ${darkMode ? 'border-white/10' : 'border-gray-200/60'}`}>
                  <ul className={`divide-y ${darkMode ? 'divide-white/5' : 'divide-gray-100'}`}>
                    {group.services.map(({ definition, status }) => {
                      const isRunning = status?.status === 'running';
                      const isDegraded = status?.status === 'degraded';
                      const isUp = isRunning || isDegraded;

                      return (
                        <li
                          key={definition.id}
                          className={`px-5 py-3 flex items-center justify-between transition-colors ${
                            darkMode ? 'hover:bg-white/5' : 'hover:bg-gray-50/80'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-base flex-shrink-0">{definition.icon}</span>
                            <div className="min-w-0">
                              <p className={`text-sm font-medium truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                {definition.name}
                              </p>
                              {definition.port && (
                                <p className={`text-xs ${darkMode ? 'text-gray-600' : 'text-gray-400'}`}>
                                  :{definition.port}
                                </p>
                              )}
                            </div>
                          </div>
                          <ServiceStatusBadge
                            isUp={isUp}
                            isDegraded={isDegraded}
                            isRunning={isRunning}
                            status={status}
                            darkMode={darkMode}
                          />
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// --- Sub-components ---

const StatChip: React.FC<{
  label: string;
  count: number;
  color: string;
  darkMode: boolean;
}> = ({ label, count, color, darkMode }) => (
  <div
    className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${
      darkMode ? 'bg-white/5' : 'bg-white/60'
    }`}
  >
    <span
      className="w-2.5 h-2.5 rounded-full"
      style={{ backgroundColor: color }}
    />
    <span className={darkMode ? 'text-gray-300' : 'text-gray-700'}>
      {count} {label}
    </span>
  </div>
);

const ServiceStatusBadge: React.FC<{
  isUp: boolean;
  isDegraded: boolean;
  isRunning: boolean;
  status: ServiceStatus | null;
  darkMode: boolean;
}> = ({ isUp, isDegraded, isRunning, status, darkMode }) => {
  let dotColor: string;
  let label: string;
  let badgeClasses: string;

  if (isDegraded) {
    dotColor = 'bg-yellow-500';
    label = 'Degraded';
    badgeClasses = darkMode ? 'bg-yellow-900/30 text-yellow-300' : 'bg-yellow-50 text-yellow-700';
  } else if (isRunning) {
    dotColor = `bg-green-500`;
    label = 'Running';
    badgeClasses = darkMode ? 'bg-green-900/30 text-green-300' : 'bg-green-50 text-green-700';
  } else {
    dotColor = 'bg-red-500';
    label = status?.status || 'Unknown';
    badgeClasses = darkMode ? 'bg-red-900/30 text-red-300' : 'bg-red-50 text-red-700';
  }

  return (
    <span className={`flex-shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${badgeClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
};
