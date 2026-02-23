import React, { useState, useEffect, useMemo } from 'react';
import { SkeletonCard } from './skeletons';
import { apiService, ContainerInfo, adminApi } from '../services/api';
import type { ServiceStatus, ServiceDefinition, ServiceGroupId } from '../types';
import type { ServicesHealthResponse } from '../types/health';
import { SERVICE_DEFINITIONS, GROUP_DEFINITIONS } from './ServicesTab';
import { Icon, ChevronDown, ChevronRight, CheckCircle, AlertTriangle, AlertCircle } from './ui/icons';

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
  totalCount: number;
}

export const GroupsTab: React.FC<GroupsTabProps> = ({ darkMode }) => {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

  const loadServices = async () => {
    try {
      const [servicesHealth, containersData] = await Promise.all([
        adminApi.getServicesHealth(),
        apiService.getContainers().catch(() => [] as ContainerInfo[])
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
      setError('');
      setLastUpdate(new Date());
      setLoading(false);
    } catch (err: any) {
      setError(err.message || 'Failed to load services');
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
        s => s.status && (s.status.status === 'running' || s.status.status === 'degraded')
      ).length;

      let aggregateStatus: GroupAggregateStatus;
      if (totalCount === 0) {
        aggregateStatus = 'empty';
      } else if (healthyCount === totalCount) {
        aggregateStatus = 'healthy';
      } else if (healthyCount === 0) {
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
        totalCount,
      };
    });
  }, [services]);

  const statusConfig: Record<GroupAggregateStatus, {
    bg: string;
    border: string;
    badge: string;
    badgeText: string;
    icon: typeof CheckCircle;
    label: string;
  }> = {
    healthy: {
      bg: darkMode ? 'bg-green-900/20' : 'bg-green-50',
      border: darkMode ? 'border-green-700' : 'border-green-200',
      badge: darkMode ? 'bg-green-800 text-green-200' : 'bg-green-100 text-green-800',
      badgeText: 'Healthy',
      icon: CheckCircle,
      label: 'healthy',
    },
    degraded: {
      bg: darkMode ? 'bg-yellow-900/20' : 'bg-yellow-50',
      border: darkMode ? 'border-yellow-700' : 'border-yellow-200',
      badge: darkMode ? 'bg-yellow-800 text-yellow-200' : 'bg-yellow-100 text-yellow-800',
      badgeText: 'Degraded',
      icon: AlertTriangle,
      label: 'degraded',
    },
    unhealthy: {
      bg: darkMode ? 'bg-red-900/20' : 'bg-red-50',
      border: darkMode ? 'border-red-700' : 'border-red-200',
      badge: darkMode ? 'bg-red-800 text-red-200' : 'bg-red-100 text-red-800',
      badgeText: 'Unhealthy',
      icon: AlertCircle,
      label: 'unhealthy',
    },
    empty: {
      bg: darkMode ? 'bg-gray-800' : 'bg-gray-50',
      border: darkMode ? 'border-gray-700' : 'border-gray-200',
      badge: darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-600',
      badgeText: 'No Services',
      icon: AlertCircle,
      label: 'empty',
    },
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
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}>
        <div className="text-center">
          <div className="text-red-500 text-6xl mb-4">
            <Icon icon={AlertCircle} size="xl" className="mx-auto text-red-500" />
          </div>
          <h3 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Error Loading Groups
          </h3>
          <p className={`mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>{error}</p>
          <button
            onClick={loadServices}
            className="px-4 py-2 rounded-md font-medium transition-colors duration-200 bg-blue-600 hover:bg-blue-700 text-white"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header with Controls */}
      <div className={`rounded-lg shadow-md p-6 ${
        darkMode ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'
      }`}>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center space-y-4 sm:space-y-0">
          <div>
            <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Deployment Groups
            </h2>
            <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Services organized by deployment group ({groups.filter(g => g.totalCount > 0).length} active groups)
            </p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Auto-refresh Toggle */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center space-x-2 px-4 py-2 rounded-md font-medium transition-colors duration-200 ${
                autoRefresh
                  ? darkMode
                    ? 'bg-green-700 hover:bg-green-600 text-white'
                    : 'bg-green-100 hover:bg-green-200 text-green-700'
                  : darkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-white'
                    : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
              }`}
            >
              <span>{autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}</span>
            </button>

            {/* Manual Refresh */}
            <button
              onClick={loadServices}
              className="px-4 py-2 rounded-md font-medium transition-colors duration-200 bg-blue-600 hover:bg-blue-700 text-white"
            >
              Refresh Now
            </button>
          </div>
        </div>

        {/* Last Update Time */}
        <div className={`text-xs mt-4 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
          Last updated: {lastUpdate.toLocaleTimeString('en-US', {
            hour12: true,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
          })}
        </div>
      </div>

      {/* Group Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {groups.map(group => {
          const config = statusConfig[group.aggregateStatus];
          const isExpanded = expandedGroups.has(group.id);
          const StatusIcon = config.icon;

          return (
            <div
              key={group.id}
              className={`rounded-lg shadow-md border transition-all duration-200 ${
                darkMode ? 'bg-gray-800' : 'bg-white'
              } ${config.border}`}
            >
              {/* Group Header */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-lg font-semibold truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {group.label}
                    </h3>
                    <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {group.description}
                    </p>
                  </div>
                  <span className={`ml-3 flex-shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.badge}`}>
                    <Icon icon={StatusIcon} size="xs" />
                    {config.badgeText}
                  </span>
                </div>

                {/* Health Summary */}
                <div className="flex items-center justify-between">
                  <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    {group.totalCount === 0
                      ? 'No monitored services'
                      : `${group.healthyCount}/${group.totalCount} services healthy`
                    }
                  </span>

                  {group.totalCount > 0 && (
                    <button
                      onClick={() => toggleGroup(group.id)}
                      className={`flex items-center gap-1 text-sm font-medium transition-colors duration-150 ${
                        darkMode
                          ? 'text-blue-400 hover:text-blue-300'
                          : 'text-blue-600 hover:text-blue-700'
                      }`}
                      aria-expanded={isExpanded}
                      aria-label={`${isExpanded ? 'Collapse' : 'Expand'} ${group.label} services`}
                    >
                      <span>{isExpanded ? 'Hide' : 'Show'}</span>
                      <Icon icon={isExpanded ? ChevronDown : ChevronRight} size="sm" />
                    </button>
                  )}
                </div>

                {/* Progress Bar */}
                {group.totalCount > 0 && (
                  <div className={`mt-3 w-full rounded-full h-2 ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                    <div
                      className={`h-2 rounded-full transition-all duration-300 ${
                        group.aggregateStatus === 'healthy'
                          ? 'bg-green-500'
                          : group.aggregateStatus === 'degraded'
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${group.totalCount > 0 ? (group.healthyCount / group.totalCount) * 100 : 0}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Expanded Service List */}
              {isExpanded && group.services.length > 0 && (
                <div className={`border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                  <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                    {group.services.map(({ definition, status }) => {
                      const isRunning = status?.status === 'running';
                      const isDegraded = status?.status === 'degraded';
                      const isHealthy = isRunning || isDegraded;

                      return (
                        <li
                          key={definition.id}
                          className={`px-5 py-3 flex items-center justify-between ${
                            darkMode ? 'hover:bg-gray-750' : 'hover:bg-gray-50'
                          }`}
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <span className="text-lg flex-shrink-0">{definition.icon}</span>
                            <div className="min-w-0">
                              <p className={`text-sm font-medium truncate ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                                {definition.name}
                              </p>
                              {definition.port && (
                                <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                                  Port {definition.port}
                                </p>
                              )}
                            </div>
                          </div>
                          <span className={`flex-shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                            isHealthy
                              ? darkMode
                                ? 'bg-green-800 text-green-200'
                                : 'bg-green-100 text-green-800'
                              : darkMode
                                ? 'bg-red-800 text-red-200'
                                : 'bg-red-100 text-red-800'
                          }`}>
                            <span className={`w-1.5 h-1.5 rounded-full ${
                              isHealthy ? 'bg-green-500' : 'bg-red-500'
                            }`} />
                            {status ? (isDegraded ? 'Degraded' : isRunning ? 'Running' : status.status) : 'Unknown'}
                          </span>
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
