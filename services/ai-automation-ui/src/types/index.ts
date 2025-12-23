/**
 * AI Automation UI - Core Types
 */

export interface SuggestionDeviceInfo {
  friendly_name: string;
  entity_id: string;
  domain?: string;
  area?: string;
  selected?: boolean;
  // Epic AI-9: HA 2025 Enhancements
  labels?: string[]; // Entity labels (outdoor, security, etc.)
  options?: Record<string, any>; // Entity options (default brightness, etc.)
  icon?: string; // Current icon (user-customized)
  original_icon?: string; // Original icon from integration
  aliases?: string[]; // Entity aliases
}

export interface SuggestionConversationEntry {
  timestamp: string;
  user_input: string;
  updated_description: string;
  changes?: string[];
  validation?: Record<string, any> | null;
}

export interface EnergySavings {
  daily_savings_kwh?: number;
  daily_savings_usd?: number;
  monthly_savings_usd?: number;
  currency?: string;
  device_power_watts?: number;
  cheapest_hours?: number[];
  optimization_potential?: 'high' | 'medium' | 'low';
}

export interface SuggestionContext {
  energy?: {
    current_price?: number;
    currency?: string;
    peak_period?: boolean;
    cheapest_hours?: number[];
  };
  historical?: {
    total_events?: number;
    usage_frequency?: number;
    avg_daily_usage?: number;
    most_common_hour?: number;
    most_common_day?: string;
    avg_duration_minutes?: number;
    usage_trend?: 'increasing' | 'decreasing' | 'stable';
  };
  weather?: {
    temperature?: number;
    humidity?: number;
    condition?: string;
  };
  carbon?: {
    current_intensity?: number;
    is_low_carbon?: boolean;
  };
}

export interface Suggestion {
  id: number;
  pattern_id?: number | null;
  title: string;
  description: string;
  description_only?: string;
  automation_yaml?: string | null;
  status: 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected' | 'pending' | 'approved';
  confidence: number;
  category?: 'energy' | 'comfort' | 'security' | 'convenience';
  priority?: 'high' | 'medium' | 'low';
  source_type?: 'pattern' | 'predictive' | 'cascade' | 'feature' | 'synergy'; // Phase 1 improvement
  energy_savings?: EnergySavings; // Phase 2 - Energy savings data
  estimated_monthly_savings?: number; // Phase 2 - Quick access to monthly savings
  context?: SuggestionContext; // Phase 2 - Full context data
  user_preference_match?: number; // Phase 3 - User preference score (0.0-1.0)
  user_preference_badge?: { score: number; label: string }; // Phase 3 - Badge data
  weighted_score?: number; // Phase 3 - Final weighted score
  metadata?: Record<string, any>; // Full metadata for advanced features
  created_at?: string;
  updated_at?: string;
  deployed_at?: string | null;
  ha_automation_id?: string | null;
  yaml_generated_at?: string | null;
  refinement_count?: number;
  conversation_history?: SuggestionConversationEntry[];
  device_capabilities?: Record<string, any>;
  device_info?: SuggestionDeviceInfo[];
  // Epic AI-9: HA 2025 Enhancements
  tags?: string[]; // Automation tags (ai-generated, energy, security, etc.)
  mode?: string; // Automation mode (single, restart, queued, parallel)
  initial_state?: boolean; // Initial state (enabled by default)
  max_exceeded?: string; // Max exceeded behavior (silent, warning)
}

export interface Pattern {
  id: number;
  pattern_type: 'time_of_day' | 'co_occurrence' | 'multi_factor' | 'sequence' | 'contextual' | 'room_based' | 'session' | 'duration' | 'day_type' | 'seasonal' | 'anomaly';
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
  analysis_run?: {
    status: string;
    started_at: string;
    finished_at?: string | null;
    duration_seconds?: number | null;
  } | null;
}

export interface ClarificationQuestion {
  id: string;
  category: string;
  question_text: string;
  question_type: 'multiple_choice' | 'text' | 'entity_selection' | 'boolean';
  options?: string[];
  priority: number;
  related_entities?: string[];
}

export interface ClarificationAnswer {
  question_id: string;
  answer_text: string;
  selected_entities?: string[];
}

export interface ClarificationResponse {
  session_id: string;
  confidence: number;
  confidence_threshold: number;
  clarification_complete: boolean;
  message: string;
  suggestions?: Suggestion[];
  questions?: ClarificationQuestion[];
  previous_confidence?: number;
  confidence_delta?: number;
  confidence_summary?: string;
  enriched_prompt?: string;
  questions_and_answers?: Array<{
    question: string;
    answer: string;
    selected_entities?: string[];
  }>;
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
    event_context?: string;  // For event_context synergies
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
  // Epic AI-4: Multi-device chains
  synergy_depth?: number;  // Number of devices in chain (2, 3, or 4)
  chain_devices?: string[];  // Array of entity IDs in the automation chain
  chain_path?: string;  // Human-readable chain path (e.g., "entity1 → entity2 → entity3")
  // 2025 Enhancement: Explainable AI
  rationale?: string;  // Explanation of why this synergy was detected
  explanation?: {
    summary?: string;
    score_breakdown?: Record<string, number>;
  };
  explanation_breakdown?: Record<string, number>;  // Score breakdown for display
}

