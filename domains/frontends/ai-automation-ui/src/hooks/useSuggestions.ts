/**
 * useSuggestions Hook
 * React Query-based data fetching for automation suggestions.
 * Replaces raw useState+useEffect+setInterval in ConversationalDashboard.
 */

import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import type { Suggestion } from '../types';

function mapSuggestion(suggestion: any): Suggestion {
  const deviceHashMatch = suggestion.title.match(/AI Suggested: ([a-f0-9]{32})/);
  let friendlyTitle = suggestion.title;
  const originalDescription = suggestion.description_only || suggestion.description || '';
  let friendlyDescription = originalDescription;

  if (deviceHashMatch) {
    const deviceHash = deviceHashMatch[1];
    const deviceNameMap: Record<string, string> = {
      '1ba44a8f25eab1397cb48dd7b743edcd': 'Sun',
      '71d5add6cf1f844d6f9bb34a3b58a09d': 'Living Room Light',
      'eca71f35d1ff44a1149dedc519f0d27a': 'Kitchen Light',
      '61234ae84aba13edf830eb7c5a7e3ae8': 'Bedroom Light',
      '603c07b7a7096b280ac6316c78dd1c1f': 'Office Light'
    };
    const friendlyName = deviceNameMap[deviceHash] || `Device ${deviceHash.substring(0, 8)}...`;
    friendlyTitle = suggestion.title.replace(deviceHash, friendlyName);
    friendlyDescription = suggestion.description.replace(deviceHash, friendlyName);
  }

  const deviceCapabilities = suggestion.device_capabilities || {};
  const deviceInfoFromCapabilities = Array.isArray(deviceCapabilities?.devices)
    ? deviceCapabilities.devices
    : undefined;

  return {
    ...suggestion,
    title: friendlyTitle,
    description: friendlyDescription,
    description_only: friendlyDescription,
    status: suggestion.status || 'draft',
    refinement_count: suggestion.refinement_count ?? 0,
    conversation_history: Array.isArray(suggestion.conversation_history)
      ? suggestion.conversation_history
      : [],
    device_capabilities: deviceCapabilities,
    device_info: suggestion.device_info || deviceInfoFromCapabilities || [],
    ha_automation_id: suggestion.ha_automation_id || null,
    yaml_generated_at: suggestion.yaml_generated_at || null
  };
}

export function useSuggestions() {
  return useQuery<Suggestion[]>({
    queryKey: ['suggestions'],
    queryFn: async () => {
      const response = await api.getSuggestions();
      const suggestionsArray = response.data?.suggestions || [];
      return suggestionsArray.map(mapSuggestion);
    },
    refetchInterval: 30_000,
  });
}

export function useRefreshStatus() {
  return useQuery({
    queryKey: ['refreshStatus'],
    queryFn: async () => {
      const status = await api.getRefreshStatus();
      return {
        allowed: status.allowed as boolean,
        nextAllowedAt: status.next_allowed_at as string | null,
      };
    },
    refetchInterval: 30_000,
  });
}

export function useAnalysisStatus() {
  return useQuery({
    queryKey: ['analysisStatus'],
    queryFn: async () => {
      const status = await api.getAnalysisStatus();
      return (status.analysis_run ?? null) as {
        status: string;
        started_at: string;
        finished_at?: string | null;
        duration_seconds?: number | null;
      } | null;
    },
    refetchInterval: 30_000,
  });
}
