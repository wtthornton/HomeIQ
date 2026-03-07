/**
 * usePatternData Hook
 * Encapsulates pattern data fetching, analysis, filtering, and state management.
 * Extracted from Patterns.tsx to reduce component size.
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import toast from 'react-hot-toast';
import api from '../services/api';
import type { Pattern } from '../types';
import { deviceNameCache } from '../utils/deviceNameCache';

export function usePatternData() {
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [deviceNames, setDeviceNames] = useState<Record<string, string>>({});
  const [analysisRunning, setAnalysisRunning] = useState(false);
  const [scheduleInfo, setScheduleInfo] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDatabaseCorrupted, setIsDatabaseCorrupted] = useState(false);
  const [repairing, setRepairing] = useState(false);
  const [selectedPattern, setSelectedPattern] = useState<Pattern | null>(null);
  const [selectedPatternIds, setSelectedPatternIds] = useState<Set<number>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'confidence' | 'occurrences' | 'recent'>('confidence');

  const loadPatterns = useCallback(async () => {
    try {
      setError(null);
      setLoading(true);
      const [patternsRes, statsRes] = await Promise.all([
        api.getPatterns(undefined, 0.7),
        api.getPatternStats().catch((err: any) => {
          if (err.isCorruption || err.repair_available) {
            setIsDatabaseCorrupted(true);
            throw err;
          }
          throw err;
        })
      ]);

      const patternsData = patternsRes.data?.patterns || [];
      setPatterns(patternsData);
      setStats(statsRes);

      if (patternsData.length > 0) {
        const uniqueDeviceIds = [...new Set(patternsData.map(p => p.device_id))];
        try {
          const names = await api.getDeviceNames(uniqueDeviceIds);
          setDeviceNames(names);
        } catch (nameError: any) {
          console.warn('Failed to load device names (non-critical):', nameError);
        }
      }
    } catch (err: any) {
      console.error('Failed to load patterns:', err);

      const errorStr = err.message || err.toString() || '';
      const isCorruption = errorStr.toLowerCase().includes('database') &&
        (errorStr.toLowerCase().includes('corrupt') ||
          errorStr.toLowerCase().includes('malformed') ||
          errorStr.toLowerCase().includes('repair'));

      setIsDatabaseCorrupted(isCorruption);

      let errorMessage = 'Failed to load patterns';
      if (err instanceof TypeError && err.message.includes('fetch')) {
        errorMessage = 'Network error: Unable to connect to the server. Please check your connection.';
      } else if (err.message) {
        errorMessage = err.message;
      } else if (err.toString && err.toString() !== '[object Object]') {
        errorMessage = err.toString();
      }

      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRepairDatabase = useCallback(async () => {
    try {
      setRepairing(true);
      setError(null);

      const result = await api.repairDatabase();

      if (result.success) {
        toast.success(result.message || 'Database repair completed successfully!');
        setIsDatabaseCorrupted(false);
        await loadPatterns();
      } else {
        toast.error(result.message || 'Database repair failed. Please try again or contact support.');
        setError(result.error || 'Repair failed');
      }
    } catch (err: any) {
      console.error('Failed to repair database:', err);
      const errorMessage = err.message || 'Failed to repair database. Please try again.';
      toast.error(errorMessage);
      setError(errorMessage);
    } finally {
      setRepairing(false);
    }
  }, [loadPatterns]);

  const loadAnalysisStatus = useCallback(async () => {
    try {
      const [, schedule] = await Promise.all([
        api.getAnalysisStatus(),
        api.getScheduleInfo()
      ]);
      setScheduleInfo(schedule);
    } catch (err) {
      console.error('Failed to load analysis status:', err);
    }
  }, []);

  useEffect(() => {
    loadPatterns();
    loadAnalysisStatus();

    let interval: ReturnType<typeof setInterval> | null = null;
    if (analysisRunning) {
      interval = setInterval(() => {
        loadPatterns();
        loadAnalysisStatus();
      }, 10000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [analysisRunning, loadPatterns, loadAnalysisStatus]);

  const handleRunAnalysis = useCallback(async () => {
    try {
      setAnalysisRunning(true);
      setError(null);

      toast.loading('Starting pattern analysis...', { id: 'analysis-start' });
      await api.triggerManualJob();
      toast.loading('Analysis in progress. This may take 1-3 minutes...', {
        id: 'analysis-start',
        duration: 10000
      });

      const initialPatternCount = patterns.length;

      const pollInterval = setInterval(async () => {
        try {
          const [patternsRes] = await Promise.all([
            api.getPatterns(undefined, 0.7),
            loadAnalysisStatus()
          ]);

          const newPatterns = patternsRes.data?.patterns || [];
          const newPatternCount = newPatterns.length;
          setPatterns(newPatterns);

          const status = await api.getAnalysisStatus();
          if (status.status === 'ready') {
            clearInterval(pollInterval);
            setAnalysisRunning(false);

            const patternDiff = newPatternCount - initialPatternCount;
            toast.dismiss('analysis-start');
            if (patternDiff > 0) {
              toast.success(
                `Analysis complete! Found ${patternDiff} new pattern${patternDiff !== 1 ? 's' : ''}. Total: ${newPatternCount} patterns.`,
                { duration: 5000 }
              );
            } else {
              toast.success(
                `Analysis complete! ${newPatternCount} pattern${newPatternCount !== 1 ? 's' : ''} detected.`,
                { duration: 5000 }
              );
            }
          }
        } catch (err) {
          console.error('Failed to poll analysis status:', err);
        }
      }, 5000);

      setTimeout(() => {
        clearInterval(pollInterval);
        setAnalysisRunning(false);
        toast.dismiss('analysis-start');
        toast.error('Analysis timed out after 5 minutes. Please try again.', { duration: 6000 });
      }, 300000);
    } catch (err: any) {
      console.error('Failed to trigger analysis:', err);
      toast.dismiss('analysis-start');
      const errorMessage = err.message || 'Failed to start analysis';
      setError(errorMessage);
      setAnalysisRunning(false);
      toast.error(errorMessage, { duration: 8000 });
    }
  }, [patterns.length, loadAnalysisStatus]);

  const getFallbackName = useCallback((deviceId: string) => {
    const cachedName = deviceNameCache.getFallbackName(deviceId);
    if (cachedName !== deviceId) return cachedName;

    if (deviceId.includes('+')) {
      const parts = deviceId.split('+');
      if (parts.length === 2) {
        return `Co-occurrence (${parts[0].substring(0, 8)}... + ${parts[1].substring(0, 8)}...)`;
      }
    }

    if (deviceId.length === 32) {
      return `Device ${deviceId.substring(0, 8)}...`;
    }

    return deviceId.length > 20 ? `${deviceId.substring(0, 20)}...` : deviceId;
  }, []);

  const filteredAndSortedPatterns = useMemo(() => {
    let filtered = [...patterns];

    if (filterType !== 'all') {
      filtered = filtered.filter(p => p.pattern_type === filterType);
    }

    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(p => {
        const deviceName = (deviceNames[p.device_id] || getFallbackName(p.device_id)).toLowerCase();
        const patternInfo = getPatternTypeInfo(p.pattern_type);
        return deviceName.includes(query) ||
          patternInfo.name.toLowerCase().includes(query) ||
          patternInfo.description.toLowerCase().includes(query);
      });
    }

    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'confidence':
          return b.confidence - a.confidence;
        case 'occurrences':
          return b.occurrences - a.occurrences;
        case 'recent':
          return (b as any).detected_at ?
            new Date((b as any).detected_at).getTime() - new Date((a as any).detected_at).getTime() :
            b.confidence - a.confidence;
        default:
          return 0;
      }
    });

    return filtered;
  }, [patterns, filterType, searchQuery, sortBy, deviceNames, getFallbackName]);

  const availablePatternTypes = useMemo(() => {
    const types = new Set(patterns.map(p => p.pattern_type));
    return Array.from(types).sort();
  }, [patterns]);

  return {
    patterns,
    stats,
    loading,
    deviceNames,
    analysisRunning,
    scheduleInfo,
    error,
    isDatabaseCorrupted,
    repairing,
    selectedPattern,
    setSelectedPattern,
    selectedPatternIds,
    setSelectedPatternIds,
    searchQuery,
    setSearchQuery,
    filterType,
    setFilterType,
    sortBy,
    setSortBy,
    loadPatterns,
    handleRepairDatabase,
    handleRunAnalysis,
    getFallbackName,
    filteredAndSortedPatterns,
    availablePatternTypes,
    setError,
    setIsDatabaseCorrupted,
  };
}

// --- Utility functions (shared between hook and components) ---

export function getPatternIcon(type: string): string {
  const icons: Record<string, string> = {
    time_of_day: '\u23F0',
    co_occurrence: '\uD83D\uDD17',
    multi_factor: '\uD83D\uDD00',
    sequence: '\u27A1\uFE0F',
    contextual: '\uD83C\uDF0D',
    room_based: '\uD83C\uDFE0',
    session: '\uD83D\uDC64',
    duration: '\u23F1\uFE0F',
    day_type: '\uD83D\uDCC5',
    seasonal: '\uD83C\uDF42',
    anomaly: '\u26A0\uFE0F',
    frequency: '\uD83D\uDCC8',
  };
  return icons[type] || '\uD83D\uDCCA';
}

export function getPatternStatus(type: string): 'active' | 'coming-soon' {
  const activeTypes = [
    'time_of_day', 'co_occurrence', 'multi_factor',
    'sequence', 'duration', 'anomaly', 'room_based',
    'day_type', 'frequency', 'seasonal', 'contextual',
  ];
  return activeTypes.includes(type) ? 'active' : 'coming-soon';
}

export function getPatternTypeInfo(type: string): { name: string; description: string; importance: string; example: string } {
  const info: Record<string, { name: string; description: string; importance: string; example: string }> = {
    time_of_day: {
      name: 'Time-of-Day Patterns',
      description: 'Detects when devices are consistently used at specific times throughout the day.',
      importance: 'These patterns reveal your daily routines and help create time-based automations that match your natural behavior.',
      example: 'Bedroom light turns on at 7:00 AM every morning, or thermostat adjusts at 6:00 PM in the evening.'
    },
    co_occurrence: {
      name: 'Co-Occurrence Patterns',
      description: 'Identifies devices that are used together within a short time window (typically 5-30 minutes).',
      importance: 'Shows device relationships and enables coordinated automations. When one device activates, related devices can automatically respond.',
      example: 'Motion sensor triggers \u2192 Light turns on (within 30 seconds), or Door opens \u2192 Alarm activates (within 2 minutes).'
    },
    multi_factor: {
      name: 'Multi-Factor Patterns',
      description: 'Detects complex patterns involving multiple factors such as time, location, device state, and external conditions working together.',
      importance: 'Identifies sophisticated behaviors that depend on multiple conditions. Enables advanced automations that respond to complex scenarios.',
      example: 'Lights turn on when motion detected AND it\'s after sunset AND temperature is below 68\u00B0F.'
    },
    sequence: {
      name: 'Sequence Patterns',
      description: 'Detects multi-step behaviors where devices activate in a specific order over time.',
      importance: 'Captures complex routines that involve multiple devices. Perfect for creating automation chains that replicate your natural behavior.',
      example: 'Coffee maker starts \u2192 Kitchen light turns on \u2192 Music plays (all within 10 minutes).'
    },
    contextual: {
      name: 'Contextual Patterns',
      description: 'Identifies behaviors that depend on external factors like weather, presence, or time context.',
      importance: 'Enables smart, adaptive automations that respond to your environment. Makes your home truly intelligent and context-aware.',
      example: 'Lights turn on at 6 PM when it\'s cloudy, or thermostat adjusts when you arrive home.'
    },
    room_based: {
      name: 'Room-Based Patterns',
      description: 'Detects device interactions within specific rooms or areas of your home.',
      importance: 'Helps create room-specific automations and understand spatial relationships between devices.',
      example: 'Living room motion sensor \u2192 Living room lights, or Bedroom door opens \u2192 Bedroom lights activate.'
    },
    session: {
      name: 'Session Patterns',
      description: 'Identifies user routine patterns that occur during specific activity sessions.',
      importance: 'Captures your personal routines and habits, enabling automations that adapt to your lifestyle.',
      example: 'Morning routine: Coffee \u2192 News \u2192 Lights, or Evening routine: Dim lights \u2192 Music \u2192 Thermostat.'
    },
    duration: {
      name: 'Duration Patterns',
      description: 'Detects how long devices typically stay in a certain state or how long activities last.',
      importance: 'Helps optimize device usage and create auto-off timers that match your actual usage patterns.',
      example: 'Lights typically stay on for 30 minutes after motion, or TV is watched for 2 hours in the evening.'
    },
    day_type: {
      name: 'Day-Type Patterns',
      description: 'Identifies differences between weekday and weekend behaviors.',
      importance: 'Enables different automation schedules for workdays vs. weekends, making your home adapt to your schedule.',
      example: 'Weekday: Alarm at 7 AM, Weekend: No alarm, or Weekday: Lights off at 10 PM, Weekend: Lights off at midnight.'
    },
    seasonal: {
      name: 'Seasonal Patterns',
      description: 'Detects behavior changes across seasons (summer vs. winter, daylight changes).',
      importance: 'Allows automations to adapt to seasonal changes automatically, maintaining comfort year-round.',
      example: 'Lights turn on earlier in winter (5 PM) vs. summer (8 PM), or thermostat settings change with seasons.'
    },
    anomaly: {
      name: 'Anomaly Patterns',
      description: 'Identifies unusual behaviors that deviate from normal patterns.',
      importance: 'Helps detect potential issues, security concerns, or opportunities to optimize unusual device usage.',
      example: 'Device activated at unusual time, or device left on longer than normal, or unexpected device combination.'
    },
    frequency: {
      name: 'Frequency Patterns',
      description: 'Tracks daily activation counts and detects significant changes in device usage frequency.',
      importance: 'Reveals usage trends and alerts to sudden changes that may indicate equipment issues or behavior shifts.',
      example: 'Furnace cycling 20x/day jumps to 40x/day (equipment issue), or garage door averaging 4 opens/day consistently.'
    }
  };
  return info[type] || {
    name: type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
    description: 'Pattern detected in your smart home usage.',
    importance: 'Helps create intelligent automations based on your behavior.',
    example: 'Device usage pattern detected.'
  };
}

export function formatLastRun(timestamp: string | null): string {
  if (!timestamp) return 'Never';
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  } catch {
    return 'Unknown';
  }
}
