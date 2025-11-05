/**
 * AI Automation UI - Core Types
 */

export interface Suggestion {
  id: number;
  pattern_id?: number;
  title: string;
  description: string;
  automation_yaml: string;
  status: 'pending' | 'approved' | 'deployed' | 'rejected';
  confidence: number;
  category?: 'energy' | 'comfort' | 'security' | 'convenience';
  priority?: 'high' | 'medium' | 'low';
  created_at: string;
  updated_at: string;
  deployed_at?: string;
  ha_automation_id?: string;
}

export interface Pattern {
  id: number;
  pattern_type: 'time_of_day' | 'co_occurrence' | 'anomaly';
  device_id: string;
  pattern_metadata: Record<string, any>;
  confidence: number;
  occurrences: number;
  created_at: string;
}

export interface ScheduleInfo {
  schedule: string;
  next_run: string | null;
  is_running: boolean;
  recent_jobs: JobHistory[];
}

export interface JobHistory {
  start_time: string;
  status: 'success' | 'failed' | 'no_data' | 'no_patterns';
  end_time?: string;
  duration_seconds?: number;
  events_count?: number;
  patterns_detected?: number;
  suggestions_generated?: number;
  openai_cost_usd?: number;
  error?: string;
}

export interface AnalysisStatus {
  status: string;
  patterns: {
    total_patterns: number;
    by_type: Record<string, number>;
    unique_devices: number;
    avg_confidence: number;
  };
  suggestions: {
    pending_count: number;
    recent: Array<{
      id: number;
      title: string;
      confidence: number;
      created_at: string;
    }>;
  };
}

export interface UsageStats {
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  model: string;
  budget_alert?: {
    alert_level: string;
    usage_percent: number;
  };
}

/**
 * Synergy Opportunity Type
 * Story AI3.8: Frontend Synergy Tab
 * Epic AI-3: Cross-Device Synergy & Contextual Opportunities
 * Phase 2: Pattern-Synergy Cross-Validation
 */
export interface SynergyOpportunity {
  id: number;
  synergy_id: string;
  synergy_type: 'device_pair' | 'weather_context' | 'energy_context' | 'event_context';
  device_ids: string;  // JSON array
  opportunity_metadata: {
    trigger_entity?: string;
    trigger_name?: string;
    action_entity?: string;
    action_name?: string;
    relationship?: string;
    rationale?: string;
    weather_condition?: string;
    suggested_action?: string;
    estimated_savings?: string;
  };
  impact_score: number;
  complexity: 'low' | 'medium' | 'high';
  confidence: number;
  area?: string;
  created_at: string;
  // Phase 2: Pattern-Synergy Cross-Validation
  pattern_support_score?: number;  // 0.0-1.0, how well patterns support this synergy
  validated_by_patterns?: boolean;  // true if patterns validate this synergy
  supporting_pattern_ids?: number[];  // IDs of patterns that support this synergy
}

