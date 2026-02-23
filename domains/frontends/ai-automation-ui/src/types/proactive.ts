/**
 * Proactive Suggestion Types
 * For proactive-agent-service integration (Epic AI-21)
 */

export type ProactiveContextType = 'weather' | 'sports' | 'energy' | 'historical';

export type ProactiveSuggestionStatus = 'pending' | 'sent' | 'approved' | 'rejected';

export interface ProactiveSuggestion {
  id: string;
  prompt: string;
  context_type: ProactiveContextType;
  status: ProactiveSuggestionStatus;
  quality_score: number;
  context_metadata: Record<string, unknown>;
  prompt_metadata: Record<string, unknown>;
  agent_response?: Record<string, unknown> | null;
  created_at: string;
  sent_at?: string | null;
  updated_at: string;
}

export interface ProactiveSuggestionStats {
  total: number;
  by_status: Partial<Record<ProactiveSuggestionStatus, number>>;
  by_context_type: Partial<Record<ProactiveContextType, number>>;
}

export interface ProactiveSuggestionFilters {
  status?: ProactiveSuggestionStatus | null;
  context_type?: ProactiveContextType | null;
  limit?: number;
  offset?: number;
}

export interface ProactiveSuggestionListResponse {
  suggestions: ProactiveSuggestion[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProactiveTriggerResponse {
  success: boolean;
  results: Record<string, unknown>;
}

// Context type display configuration
export const CONTEXT_TYPE_CONFIG: Record<ProactiveContextType, {
  icon: string;
  label: string;
  color: string;
  bgColor: string;
}> = {
  weather: {
    icon: '☁️',
    label: 'Weather',
    color: 'text-sky-400',
    bgColor: 'bg-sky-500/20',
  },
  sports: {
    icon: '🏈',
    label: 'Sports',
    color: 'text-orange-400',
    bgColor: 'bg-orange-500/20',
  },
  energy: {
    icon: '⚡',
    label: 'Energy',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
  },
  historical: {
    icon: '📊',
    label: 'Historical',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
  },
};

// Status display configuration
export const STATUS_CONFIG: Record<ProactiveSuggestionStatus, {
  label: string;
  color: string;
  bgColor: string;
}> = {
  pending: {
    label: 'Pending',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/20',
  },
  sent: {
    label: 'Sent',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/20',
  },
  approved: {
    label: 'Approved',
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
  },
  rejected: {
    label: 'Rejected',
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
  },
};
