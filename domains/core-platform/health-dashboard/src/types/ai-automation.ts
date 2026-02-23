/**
 * TypeScript types for AI Automation Suggestion System
 */

export interface Pattern {
  id: number;
  pattern_type: 'time_of_day' | 'co_occurrence' | 'anomaly';
  device_id: string;
  pattern_metadata: {
    hour?: number;
    minute?: number;
    device1?: string;
    device2?: string;
    avg_time_delta_seconds?: number;
    window_minutes?: number;
    support?: number;
    [key: string]: any;
  };
  confidence: number;
  occurrences: number;
  created_at: string;
}

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

export interface AnalysisResult {
  success: boolean;
  message: string;
  data: {
    summary: {
      events_analyzed: number;
      patterns_detected: number;
      suggestions_generated: number;
      suggestions_failed: number;
    };
    patterns: {
      total: number;
      by_type: {
        time_of_day: number;
        co_occurrence: number;
      };
      top_confidence: number;
      avg_confidence: number;
    };
    suggestions: Array<{
      id: number;
      title: string;
      category: string;
      priority: string;
      confidence: number;
      pattern_type: string;
    }>;
    openai_usage: {
      total_tokens: number;
      input_tokens: number;
      output_tokens: number;
      estimated_cost_usd: number;
      model: string;
    };
    performance: {
      total_duration_seconds: number;
      phase1_fetch_seconds: number;
      phase2_detect_seconds: number;
      phase3_store_seconds: number;
      phase4_generate_seconds: number;
      avg_time_per_suggestion: number;
    };
    time_range: {
      start: string;
      end: string;
      days: number;
    };
  };
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
  patterns_stored?: number;
  suggestions_generated?: number;
  suggestions_failed?: number;
  openai_tokens?: number;
  openai_cost_usd?: number;
  error?: string;
}

export interface PatternStats {
  total_patterns: number;
  by_type: {
    [key: string]: number;
  };
  unique_devices: number;
  avg_confidence: number;
}

