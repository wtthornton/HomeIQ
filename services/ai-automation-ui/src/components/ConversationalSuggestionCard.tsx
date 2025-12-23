/**
 * Conversational Suggestion Card - Story AI1.23 Phase 5
 * 
 * Description-first UI with natural language editing.
 * No YAML shown until after approval!
 */

import React, { useState, useMemo, useCallback, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import { getButtonStyles } from '../utils/designSystem';
import { DeviceMappingModal } from './DeviceMappingModal';
import { DeployedBadge } from './DeployedBadge';
import { TagBadge } from './TagBadge';
import { AutomationMetadataBadge } from './AutomationMetadataBadge';
import { QuestionsAndAnswersSection } from './ask-ai/QuestionsAndAnswersSection';
import { resolveEntityIcon, isUserCustomized, getIconTooltip } from '../utils/iconHelpers';

interface DeviceInfo {
  friendly_name: string;
  entity_id: string;
  domain?: string;
  selected?: boolean; // Whether this device is selected for inclusion in automation
  // Epic AI-9: HA 2025 Enhancements
  labels?: string[];
  options?: Record<string, any>;
  icon?: string;
  original_icon?: string;
  aliases?: string[];
}

interface EnergySavings {
  daily_savings_kwh?: number;
  daily_savings_usd?: number;
  monthly_savings_usd?: number;
  currency?: string;
  device_power_watts?: number;
  cheapest_hours?: number[];
  optimization_potential?: 'high' | 'medium' | 'low';
}

interface SuggestionContext {
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

interface ConversationalSuggestion {
  id: number;
  description_only: string;
  title: string;
  category: string;
  confidence: number;
  status: 'draft' | 'refining' | 'yaml_generated' | 'deployed' | 'rejected' | 'pending' | 'approved';
  refinement_count: number;
  source_type?: 'pattern' | 'predictive' | 'cascade' | 'feature' | 'synergy'; // Phase 1 improvement
  energy_savings?: EnergySavings; // Phase 2 - Energy savings data
  estimated_monthly_savings?: number; // Phase 2 - Quick access
  context?: SuggestionContext; // Phase 2 - Full context data
  user_preference_match?: number; // Phase 3 - User preference score (0.0-1.0)
  user_preference_badge?: { score: number; label: string }; // Phase 3 - Badge data
  weighted_score?: number; // Phase 3 - Final weighted score
  metadata?: Record<string, any>; // Full metadata
  conversation_history: Array<{
    timestamp: string;
    user_input: string;
    updated_description: string;
    changes: string[];
    validation: { ok: boolean; error?: string };
  }>;
  device_capabilities?: {
    entity_id: string;
    friendly_name: string;
    domain: string;
    supported_features?: Record<string, boolean>;
    friendly_capabilities?: string[];
  };
  device_info?: DeviceInfo[]; // List of devices involved in the suggestion
  automation_yaml?: string | null;
  created_at: string;
  approve_response?: {
    automation_id?: string;
    status?: string;
    deployed_at?: string;
  };
  ha_automation_id?: string | null;
  questionsAndAnswers?: Array<{
    question: string;
    answer: string;
    selected_entities?: string[];
  }>;
  // Epic AI-9: HA 2025 Enhancements
  tags?: string[];
  mode?: string;
  initial_state?: boolean;
  max_exceeded?: string;
}

interface Props {
  suggestion: ConversationalSuggestion;
  onRefine: (id: number, userInput: string) => Promise<void>;
  onApprove: (id: number, customMappings?: Record<string, string>) => Promise<void>;
  onReject: (id: number) => Promise<void>;
  onTest?: (id: number) => Promise<void>;
  onRedeploy?: (id: number) => Promise<void>;
  onDeviceToggle?: (id: number, entityId: string, selected: boolean) => void; // Callback for device selection changes
  darkMode?: boolean;
  disabled?: boolean;
  tested?: boolean;
  previousConfidence?: number;
  confidenceDelta?: number;
  confidenceSummary?: string;
}

// PERFORMANCE: Memoize component to prevent unnecessary re-renders
export const ConversationalSuggestionCard: React.FC<Props> = memo(({
  suggestion,
  previousConfidence,
  confidenceDelta,
  confidenceSummary,
  onRefine,
  onApprove,
  onReject,
  onTest,
  onRedeploy,
  onDeviceToggle,
  darkMode = false,
  disabled = false,
  tested = false
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editInput, setEditInput] = useState('');
  const [isRefining, setIsRefining] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showCapabilities, setShowCapabilities] = useState(false);
  const [showYaml, setShowYaml] = useState(false);
  const [customMappings, setCustomMappings] = useState<Record<string, string>>({});
  const [editingMapping, setEditingMapping] = useState<{ friendlyName: string; currentEntityId: string; domain?: string } | null>(null);

  // PERFORMANCE: Memoize expensive computations
  const categoryColor = useMemo(() => {
    const colors = {
      energy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      comfort: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
      security: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
      convenience: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
    };
    return colors[suggestion.category as keyof typeof colors] || colors.convenience;
  }, [suggestion.category]);

  const categoryIcon = useMemo(() => {
    const icons = {
      energy: '🌱',
      comfort: '💙',
      security: '🔐',
      convenience: '✨',
    };
    return icons[suggestion.category as keyof typeof icons] || '✨';
  }, [suggestion.category]);

  const sourceTypeBadge = useMemo(() => {
    const sourceType = suggestion.source_type || 'pattern';
    const badges = {
      pattern: { icon: '🔍', label: 'Pattern', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
      predictive: { icon: '🔮', label: 'Predictive', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
      cascade: { icon: '⚡', label: 'Cascade', color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
      feature: { icon: '💎', label: 'Feature', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
      synergy: { icon: '🔗', label: 'Synergy', color: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200' },
    };
    return badges[sourceType] || badges.pattern;
  }, [suggestion.source_type]);

  // PERFORMANCE: Memoize callbacks to prevent unnecessary re-renders
  const handleRefine = useCallback(async () => {
    if (!editInput.trim()) {
      toast.error('Please enter your changes');
      return;
    }

    setIsRefining(true);
    try {
      await onRefine(suggestion.id, editInput);
      setEditInput('');
      toast.success('✅ Description updated!');
    } catch (error) {
      toast.error('❌ Failed to refine suggestion');
    } finally {
      setIsRefining(false);
    }
  }, [editInput, onRefine, suggestion.id]);

  const handleTest = useCallback(async () => {
    if (!onTest) return;
    
    try {
      await onTest(suggestion.id);
      toast.success('✅ Automation validated successfully!');
    } catch (error) {
      toast.error('❌ Validation failed');
    }
  }, [onTest, suggestion.id]);

  const handleApprove = useCallback(async () => {
    try {
      await onApprove(suggestion.id, Object.keys(customMappings).length > 0 ? customMappings : undefined);
      toast.success('✅ Automation created successfully!');
    } catch (error) {
      toast.error('❌ Failed to create automation');
    }
  }, [onApprove, suggestion.id, customMappings]);

  const handleMappingSave = useCallback((friendlyName: string, newEntityId: string) => {
    setCustomMappings(prev => ({
      ...prev,
      [friendlyName]: newEntityId
    }));
    setEditingMapping(null);
    toast.success(`✅ Mapping updated: ${friendlyName} → ${newEntityId}`);
  }, []);

  const handleMappingCancel = useCallback(() => {
    setEditingMapping(null);
  }, []);

  const handleEditMapping = useCallback((device: DeviceInfo) => {
    setEditingMapping({
      friendlyName: device.friendly_name,
      currentEntityId: device.entity_id,
      domain: device.domain
    });
  }, []);

  // PERFORMANCE: Memoize computed values
  const getEffectiveEntityId = useCallback((device: DeviceInfo): string => {
    return customMappings[device.friendly_name] || device.entity_id;
  }, [customMappings]);

  // PERFORMANCE: Memoize computed values
  const isApproved = useMemo(() => 
    suggestion.status === 'yaml_generated' || suggestion.status === 'deployed',
    [suggestion.status]
  );
  
  const automationId = useMemo(() => 
    suggestion.approve_response?.automation_id || suggestion.ha_automation_id,
    [suggestion.approve_response?.automation_id, suggestion.ha_automation_id]
  );
  
  const isDeployed = useMemo(() => 
    !!automationId && (suggestion.status === 'deployed' || !!suggestion.approve_response?.automation_id),
    [automationId, suggestion.status, suggestion.approve_response?.automation_id]
  );
  
  const deployedAt = useMemo(() => 
    suggestion.approve_response?.deployed_at || (isDeployed ? new Date().toISOString() : undefined),
    [suggestion.approve_response?.deployed_at, isDeployed]
  );

  return (
    <>
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-xl border overflow-hidden shadow-lg backdrop-blur-sm ${
        isDeployed
          ? darkMode
            ? 'bg-gradient-to-br from-green-900/40 to-emerald-900/40 border-green-500/50 shadow-2xl shadow-green-900/20'
            : 'bg-gradient-to-br from-green-50 to-emerald-50 border-green-400/50 shadow-xl shadow-green-100/50'
          : darkMode
          ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-2xl shadow-blue-900/20'
          : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-xl shadow-blue-100/50'
      }`}
    >
      {/* Header - Glassmorphism */}
      <div className={`p-4 border-b ${
        darkMode
          ? 'bg-slate-800/60 border-gray-700/50 backdrop-blur-sm'
          : 'bg-white/80 border-gray-200/50 backdrop-blur-sm'
      }`}>
        <div className="flex justify-between items-start mb-2">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1.5">
              <motion.span
                animate={{ rotate: [0, -10, 10, 0] }}
                transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
                className="text-lg"
              >
                💡
              </motion.span>
              <h3 className="ds-title-card" style={{ color: '#ffffff', fontSize: '0.95rem' }}>
                {suggestion.title.toUpperCase()}
              </h3>
            </div>
            
            {/* Status Badge */}
            <div className="flex gap-1.5 items-center flex-wrap">
              {/* Source Type Badge (NEW - Phase 1 improvement) */}
              {suggestion.source_type && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${sourceTypeBadge.color}`} title={`Suggestion source: ${sourceTypeBadge.label}`} aria-label={`Source type: ${sourceTypeBadge.label}`}>
                  {sourceTypeBadge.icon} {sourceTypeBadge.label}
                </span>
              )}
              
              {suggestion.category && (
                <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${categoryColor}`} aria-label={`Category: ${suggestion.category}`}>
                  {categoryIcon} {suggestion.category}
                </span>
              )}
              
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
                suggestion.status === 'draft' ? 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300' :
                suggestion.status === 'refining' ? 'bg-yellow-200 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' :
                suggestion.status === 'yaml_generated' ? 'bg-green-200 text-green-800 dark:bg-green-900 dark:text-green-200' :
                'bg-blue-200 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
              }`}>
                {suggestion.status === 'draft' && '📝 New'}
                {suggestion.status === 'refining' && `✏️ ${suggestion.refinement_count} edit${suggestion.refinement_count > 1 ? 's' : ''}`}
                {suggestion.status === 'yaml_generated' && '✅ Ready'}
                {suggestion.status === 'deployed' && '🚀 Deployed'}
              </span>
              
              <span className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
                suggestion.confidence >= 0.9 ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' :
                suggestion.confidence >= 0.7 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' :
                'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
              }`}>
                {Math.round(suggestion.confidence * 100)}% confident
              </span>
              
              {/* Confidence Improvement Indicator */}
              {(() => {
                const shouldShow = previousConfidence !== undefined && 
                                  previousConfidence > 0 && 
                                  confidenceDelta !== undefined && 
                                  confidenceDelta > 0;
                if (shouldShow) {
                  console.log('✅ Showing confidence improvement badge:', {
                    previousConfidence,
                    confidenceDelta,
                    confidenceSummary
                  });
                } else {
                  console.log('⚠️ NOT showing confidence improvement badge:', {
                    previousConfidence,
                    confidenceDelta,
                    hasPrevious: previousConfidence !== undefined,
                    hasDelta: confidenceDelta !== undefined
                  });
                }
                return shouldShow ? (
                  <span 
                    className="px-1.5 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      background: 'rgba(16, 185, 129, 0.2)',
                      border: '1px solid rgba(16, 185, 129, 0.4)',
                      color: '#6ee7b7'
                    }}
                    title={confidenceSummary || `Confidence improved from ${Math.round(previousConfidence * 100)}%`}
                  >
                    ✨ +{Math.round(confidenceDelta * 100)}%
                  </span>
                ) : null;
              })()}
              
              {/* Deployed Badge */}
              {isDeployed && automationId && (
                <DeployedBadge
                  automationId={automationId}
                  deployedAt={deployedAt}
                  status="active"
                  darkMode={darkMode}
                  onEdit={() => {
                    // TODO: Implement edit functionality
                    toast('Edit functionality coming soon', { icon: 'ℹ️' });
                  }}
                  onDisable={() => {
                    // TODO: Implement disable functionality
                    toast('Disable functionality coming soon', { icon: 'ℹ️' });
                  }}
                />
              )}
              
              {/* Energy Savings Badge (Phase 2) */}
              {suggestion.estimated_monthly_savings && suggestion.estimated_monthly_savings > 0 && (
                <span 
                  className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  title={`Estimated monthly savings: $${suggestion.estimated_monthly_savings.toFixed(2)}`}
                >
                  💰 Save ${suggestion.estimated_monthly_savings.toFixed(2)}/mo
                </span>
              )}
              
              {/* Historical Usage Context Badge (Phase 2) */}
              {suggestion.context?.historical && suggestion.context.historical.usage_frequency && (
                <span 
                  className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                  title={`Based on ${suggestion.context.historical.total_events || 0} events over 30 days`}
                >
                  📊 {suggestion.context.historical.usage_frequency.toFixed(1)}x/day avg
                </span>
              )}
              
              {/* Carbon-Aware Badge (Phase 2) */}
              {suggestion.context?.carbon && suggestion.context.carbon.is_low_carbon && (
                <span 
                  className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200"
                  title="Low carbon intensity period - eco-friendly timing"
                >
                  🌱 Low Carbon
                </span>
              )}
              
              {/* User Preference Badge (Phase 3) */}
              {suggestion.user_preference_badge && suggestion.user_preference_match && suggestion.user_preference_match > 0.7 && (
                <span 
                  className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200"
                  title={`${Math.round(suggestion.user_preference_match * 100)}% match with your preferences`}
                >
                  👤 {suggestion.user_preference_badge.label}
                </span>
              )}
              
              {/* Device Health Warning Badge (Phase 4.1) */}
              {suggestion.metadata?.health_warning && suggestion.metadata?.health_score !== undefined && (
                <span 
                  className={`px-1.5 py-0.5 rounded-full text-xs font-medium ${
                    suggestion.metadata.health_score < 60
                      ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                      : 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                  }`}
                  title={`Device health: ${suggestion.metadata.health_score}/100 (${suggestion.metadata.health_status || 'fair'}). This device may not be reliable for automation.`}
                >
                  ⚠️ Health: {suggestion.metadata.health_score}/100
                </span>
              )}
              
              {/* Device Health Info Badge (Phase 4.1 - Good Health) */}
              {!suggestion.metadata?.health_warning && suggestion.metadata?.health_score !== undefined && suggestion.metadata.health_score >= 70 && (
                <span 
                  className="px-1.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                  title={`Device health: ${suggestion.metadata.health_score}/100 (${suggestion.metadata.health_status || 'good'})`}
                >
                  💚 Health: {suggestion.metadata.health_score}/100
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Main Description (NO YAML!) */}
        <div className="ds-text-body text-sm leading-relaxed p-3 rounded-lg border mt-2" style={{
          background: 'rgba(30, 41, 59, 0.6)',
          border: '1px solid rgba(51, 65, 85, 0.5)',
          color: '#cbd5e1'
        }}>
          {suggestion.description_only || 'No description available'}
          
          {/* Epic AI-9: Automation Tags Display */}
          {suggestion.tags && suggestion.tags.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-600">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-gray-400 font-medium">Tags:</span>
                {suggestion.tags.map((tag) => (
                  <TagBadge key={tag} tag={tag} darkMode={darkMode} showTooltip={true} />
                ))}
              </div>
            </div>
          )}

          {/* Epic AI-9: Automation Metadata Display */}
          {(suggestion.mode || suggestion.initial_state !== undefined || suggestion.max_exceeded) && (
            <div className="mt-3 pt-3 border-t border-gray-600">
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-400 font-medium">Metadata:</span>
                <AutomationMetadataBadge
                  mode={suggestion.mode}
                  initialState={suggestion.initial_state}
                  maxExceeded={suggestion.max_exceeded}
                  darkMode={darkMode}
                />
              </div>
            </div>
          )}
          
          {/* Phase 2: Historical Usage Context */}
          {suggestion.context?.historical && (
            <div className="mt-2 pt-2 border-t border-gray-600 text-xs opacity-80">
              <span className="text-gray-400">
                📈 Based on your usage: {suggestion.context.historical.usage_frequency?.toFixed(1)} times/day average
                {suggestion.context.historical.most_common_hour !== undefined && (
                  <span>, most common at {suggestion.context.historical.most_common_hour}:00</span>
                )}
              </span>
            </div>
          )}
          
          {/* Phase 2: Energy Savings Info */}
          {suggestion.energy_savings && suggestion.energy_savings.monthly_savings_usd && suggestion.energy_savings.monthly_savings_usd > 0 && (
            <div className="mt-2 pt-2 border-t border-gray-600 text-xs">
              <span className="text-green-400 font-medium">
                💰 Potential savings: ${suggestion.energy_savings.monthly_savings_usd.toFixed(2)}/month
                {suggestion.energy_savings.cheapest_hours && suggestion.energy_savings.cheapest_hours.length > 0 && (
                  <span className="text-gray-400 ml-2">
                    (Best times: {suggestion.energy_savings.cheapest_hours.map((h: number) => `${h}:00`).join(', ')})
                  </span>
                )}
              </span>
            </div>
          )}
          
          {/* Phase 4.1: Device Health Warning */}
          {suggestion.metadata?.health_warning && suggestion.metadata?.health_score !== undefined && (
            <div className="mt-2 pt-2 border-t border-gray-600">
              <div className={`text-xs p-2 rounded-md ${
                suggestion.metadata.health_score < 60
                  ? 'bg-red-900/30 border border-red-700/50'
                  : 'bg-orange-900/30 border border-orange-700/50'
              }`}>
                <span className={`font-medium flex items-center gap-1.5 ${
                  suggestion.metadata.health_score < 60 ? 'text-red-300' : 'text-orange-300'
                }`}>
                  <span>⚠️</span>
                  <span>
                    Device Health Warning: This device has a health score of {suggestion.metadata.health_score}/100
                    {suggestion.metadata.health_status && (
                      <span> ({suggestion.metadata.health_status})</span>
                    )}
                    . The automation may not work reliably.
                  </span>
                </span>
              </div>
            </div>
          )}
        </div>
        
        {/* Device Information Buttons - Selectable */}
        {suggestion.device_info && suggestion.device_info.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5 items-center">
            <span className="text-xs opacity-70" style={{ color: '#94a3b8' }}>
              Devices:
            </span>
            {suggestion.device_info.map((device, idx) => {
              const isSelected = device.selected !== false; // Default to true if not specified
              const effectiveEntityId = getEffectiveEntityId(device);
              const hasCustomMapping = customMappings[device.friendly_name] !== undefined;
              // Generate Home Assistant entity URL using effective entity ID
              const haBaseUrl = import.meta.env.VITE_HA_URL || 'http://192.168.1.86:8123';
              const haUrl = `${haBaseUrl}/config/entities/${encodeURIComponent(effectiveEntityId)}`;
              
              return (
                <div key={idx} className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      if (onDeviceToggle) {
                        onDeviceToggle(suggestion.id, effectiveEntityId, !isSelected);
                      }
                    }}
                    onContextMenu={(e) => {
                      // Right-click opens HA page
                      e.preventDefault();
                      window.open(haUrl, '_blank', 'noopener,noreferrer');
                    }}
                    className="text-xs px-2 py-0.5 rounded-md font-medium transition-all cursor-pointer"
                    style={{
                      background: isSelected 
                        ? 'rgba(59, 130, 246, 0.4)' 
                        : 'rgba(59, 130, 246, 0.1)',
                      border: isSelected 
                        ? '1px solid rgba(59, 130, 246, 0.6)' 
                        : '1px solid rgba(59, 130, 246, 0.2)',
                      color: isSelected ? '#bfdbfe' : '#64748b',
                      textDecoration: 'none',
                      opacity: isSelected ? 1 : 0.6
                    }}
                    onMouseEnter={(e) => {
                      if (isSelected) {
                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.5)';
                        e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.7)';
                      } else {
                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)';
                        e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.4)';
                      }
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = isSelected 
                        ? 'rgba(59, 130, 246, 0.4)' 
                        : 'rgba(59, 130, 246, 0.1)';
                      e.currentTarget.style.borderColor = isSelected 
                        ? '1px solid rgba(59, 130, 246, 0.6)' 
                        : '1px solid rgba(59, 130, 246, 0.2)';
                    }}
                    title={`${isSelected ? 'Click to exclude' : 'Click to include'} ${device.friendly_name} in automation. Right-click to view details.${hasCustomMapping ? ` Custom mapping: ${effectiveEntityId}` : ''}${device.icon ? `\n${getIconTooltip(device.icon, device.original_icon, device.domain)}` : ''}`}
                    disabled={disabled || !onDeviceToggle}
                  >
                    <span className="flex items-center gap-1">
                      {/* Epic AI-9: Icon display with customization indicator */}
                      {device.icon && (
                        <span className="text-sm" title={getIconTooltip(device.icon, device.original_icon, device.domain)}>
                          {resolveEntityIcon(device.icon, device.original_icon, device.domain)}
                          {isUserCustomized(device.icon, device.original_icon) && (
                            <span className="text-xs ml-0.5">✨</span>
                          )}
                        </span>
                      )}
                      {isSelected ? (
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      )}
                      {device.friendly_name}
                      {hasCustomMapping && (
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <title>{`Custom mapping: ${device.entity_id} → ${effectiveEntityId}`}</title>
                          <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                        </svg>
                      )}
                      {/* Epic AI-9: Entity Labels Display */}
                      {device.labels && device.labels.length > 0 && (
                        <span className="ml-1 flex items-center gap-0.5">
                          {device.labels.slice(0, 2).map((label) => (
                            <span
                              key={label}
                              className="px-1 py-0.5 rounded text-xs"
                              style={{
                                background: 'rgba(168, 85, 247, 0.2)',
                                border: '1px solid rgba(168, 85, 247, 0.4)',
                                color: '#c084fc'
                              }}
                              title={`Label: ${label}`}
                            >
                              {label}
                            </span>
                          ))}
                          {device.labels.length > 2 && (
                            <span className="text-xs opacity-70" title={`Additional labels: ${device.labels.slice(2).join(', ')}`}>
                              +{device.labels.length - 2}
                            </span>
                          )}
                        </span>
                      )}
                    </span>
                  </button>
                  {!disabled && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        handleEditMapping(device);
                      }}
                      className="text-xs p-0.5 rounded hover:bg-opacity-20 transition-all"
                      style={{
                        color: '#94a3b8',
                        opacity: 0.7
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.opacity = '1';
                        e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.opacity = '0.7';
                        e.currentTarget.style.background = 'transparent';
                      }}
                      title={`Edit entity mapping for ${device.friendly_name}`}
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Epic AI-9: Entity Options Display (Preferences) */}
        {suggestion.device_info && suggestion.device_info.some(d => d.options && Object.keys(d.options).length > 0) && (
          <div className="mt-2 p-2 rounded-lg" style={{
            background: 'rgba(30, 41, 59, 0.4)',
            border: '1px solid rgba(51, 65, 85, 0.3)'
          }}>
            <div className="text-xs text-gray-400 font-medium mb-1.5">Device Preferences:</div>
            <div className="space-y-1">
              {suggestion.device_info.filter(d => d.options && Object.keys(d.options).length > 0).map((device, idx) => (
                <div key={idx} className="text-xs" style={{ color: '#cbd5e1' }}>
                  <span className="font-medium">{device.friendly_name}:</span>
                  {' '}
                  {Object.entries(device.options || {}).map(([key, value], optIdx) => {
                    // Format option value nicely
                    let displayValue = value;
                    if (key === 'brightness' && typeof value === 'number') {
                      displayValue = `${Math.round((value / 255) * 100)}%`;
                    } else if (key === 'color_temp' && typeof value === 'number') {
                      displayValue = `${value}K`;
                    } else if (typeof value === 'boolean') {
                      displayValue = value ? 'On' : 'Off';
                    }
                    return (
                      <span key={optIdx}>
                        {optIdx > 0 && ', '}
                        <span className="opacity-70">{key}:</span> {String(displayValue)}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
        
        {suggestion.conversation_history && suggestion.conversation_history.length > 0 && (
          <div className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
            Based on {suggestion.conversation_history.length} edit{suggestion.conversation_history.length > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Questions and Answers Section */}
        {suggestion.questionsAndAnswers && suggestion.questionsAndAnswers.length > 0 && (
          <QuestionsAndAnswersSection
            questionsAndAnswers={suggestion.questionsAndAnswers}
            darkMode={darkMode}
            title="How Your Questions Were Answered"
          />
        )}

        {/* Device Capabilities (Expandable) */}
        {suggestion.device_capabilities && suggestion.device_capabilities.friendly_capabilities && suggestion.device_capabilities.friendly_capabilities.length > 0 && (
          <div>
            <button
              onClick={() => setShowCapabilities(!showCapabilities)}
              className="w-full text-left px-3 py-1.5 rounded-xl font-medium transition-all text-sm"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
              }}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showCapabilities ? '▼' : '▶'}</span>
                  <span>💡 This device can also...</span>
                </span>
                <span className="text-xs opacity-70">
                  {suggestion.device_capabilities.friendly_capabilities.length} features
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showCapabilities && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-2 p-4 rounded-xl border backdrop-blur-sm"
                  style={{
                    background: 'rgba(30, 58, 138, 0.2)',
                    borderColor: 'rgba(59, 130, 246, 0.3)'
                  }}
                >
                  <ul className="space-y-2 text-sm">
                    {suggestion.device_capabilities.friendly_capabilities.map((cap, idx) => (
                      <li key={idx} className="flex items-start gap-2" style={{ color: '#93c5fd' }}>
                        <span style={{ color: '#60a5fa' }}>•</span>
                        <span>{cap}</span>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-3 text-xs italic" style={{ color: '#bfdbfe' }}>
                    Try saying: "Make it blue" or "Set to 75% brightness" or "Only on weekdays"
                  </p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Conversation History (Expandable) */}
        {suggestion.conversation_history && suggestion.conversation_history.length > 0 && (
          <div>
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="w-full text-left px-3 py-1.5 rounded-xl font-medium transition-all text-sm"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
              }}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showHistory ? '▼' : '▶'}</span>
                  <span>📝 Edit History</span>
                </span>
                <span className="text-xs opacity-70">
                  {suggestion.conversation_history.length} edit{suggestion.conversation_history.length > 1 ? 's' : ''}
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showHistory && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="mt-2 space-y-2"
                >
                  {suggestion.conversation_history.map((entry, idx) => (
                    <div
                      key={idx}
                      className={`p-3 rounded-xl ${darkMode ? 'bg-slate-800/60 backdrop-blur-sm' : 'bg-white/80 backdrop-blur-sm'} border ${darkMode ? 'border-gray-700/50' : 'border-gray-200/50'}`}
                    >
                      <div className="flex items-start gap-2 mb-1">
                        <span className="text-sm font-medium text-blue-500">You said:</span>
                        <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                          "{entry.user_input}"
                        </span>
                      </div>
                      {entry.changes && entry.changes.length > 0 && (
                        <div className="mt-2 text-xs space-y-1">
                          {entry.changes.map((change, changeIdx) => (
                            <div key={changeIdx} className={`flex items-start gap-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                              <span className="text-green-500">✓</span>
                              <span>{change}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {entry.validation && !entry.validation.ok && entry.validation.error && (
                        <div className="mt-2 text-xs text-yellow-600 dark:text-yellow-400">
                          ⚠️ {entry.validation.error}
                        </div>
                      )}
                    </div>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Natural Language Edit Mode */}
        {!isApproved && (
          <div>
            {isEditing ? (
              <div className="space-y-3">
                <textarea
                  value={editInput}
                  onChange={(e) => setEditInput(e.target.value)}
                  placeholder="Describe your changes... (e.g., 'Make it blue and only on weekdays')"
                  className="w-full p-3 rounded-xl border-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm backdrop-blur-sm"
                  style={{
                    background: 'rgba(30, 41, 59, 0.6)',
                    borderColor: 'rgba(51, 65, 85, 0.5)',
                    color: '#ffffff'
                  }}
                  onFocus={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
                    e.currentTarget.style.boxShadow = '0 0 0 3px rgba(59, 130, 246, 0.1)';
                  }}
                  onBlur={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                    e.currentTarget.style.boxShadow = 'none';
                  }}
                  onKeyDown={(e) => {
                    // ACCESSIBILITY: Allow Escape to cancel editing
                    if (e.key === 'Escape') {
                      setIsEditing(false);
                      setEditInput('');
                    }
                    // Allow Ctrl/Cmd+Enter to submit
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      e.preventDefault();
                      if (!isRefining && editInput.trim()) {
                        handleRefine();
                      }
                    }
                  }}
                  rows={3}
                  autoFocus
                  aria-label="Edit automation description"
                  aria-describedby="edit-description-help"
                />
                <p id="edit-description-help" className="text-xs text-gray-400 mt-1">
                  Press Escape to cancel, Ctrl+Enter to submit
                </p>
                <div className="flex gap-1.5">
                  <button
                    onClick={handleRefine}
                    disabled={isRefining || !editInput.trim()}
                    style={getButtonStyles(isRefining || !editInput.trim() ? 'secondary' : 'primary', { flex: 1 })}
                    className={isRefining || !editInput.trim() ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {isRefining ? (
                      <>
                        <svg className="animate-spin h-3 w-3" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        <span>UPDATING...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>UPDATE DESCRIPTION</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => setIsEditing(false)}
                    style={getButtonStyles('secondary')}
                  >
                    CANCEL
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-1.5 flex-wrap items-center">
                {/* Test Button */}
                {onTest && (
                  <button
                    onClick={handleTest}
                    disabled={disabled || tested}
                    style={getButtonStyles(disabled || tested ? 'secondary' : 'primary', {
                      background: disabled || tested ? undefined : 'linear-gradient(to right, #f59e0b, #d97706)',
                      boxShadow: disabled || tested ? undefined : '0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                    })}
                    className={disabled || tested ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {tested ? (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>TESTED</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span>TEST</span>
                      </>
                    )}
                  </button>
                )}

                {/* Approve Button - Shows DEPLOYED when automation is deployed */}
                {isDeployed ? (
                  <button
                    disabled
                    style={getButtonStyles('secondary', {
                      flex: 1,
                      minWidth: '120px',
                      maxWidth: '200px',
                      background: 'linear-gradient(to right, #10b981, #059669)',
                      opacity: 0.8
                    })}
                    className="opacity-80 cursor-default"
                    title="Automation is deployed and active"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>✅ DEPLOYED</span>
                  </button>
                ) : (
                  <button
                    onClick={handleApprove}
                    disabled={disabled}
                    style={getButtonStyles(disabled ? 'secondary' : 'primary', {
                      flex: 1,
                      minWidth: '120px',
                      maxWidth: '200px',
                      background: disabled ? undefined : 'linear-gradient(to right, #10b981, #059669)',
                      boxShadow: disabled ? undefined : '0 2px 4px -1px rgba(0, 0, 0, 0.2)'
                    })}
                    className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                  >
                    {disabled ? (
                      <>
                        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>PROCESSING...</span>
                      </>
                    ) : (
                      <>
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        <span>APPROVE & CREATE</span>
                      </>
                    )}
                  </button>
                )}

                {/* Edit Button */}
                <button
                  onClick={() => setIsEditing(true)}
                  disabled={disabled}
                  style={getButtonStyles(disabled ? 'secondary' : 'primary')}
                  className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>EDIT</span>
                </button>

                {/* Reject Button */}
                <button
                  onClick={() => onReject(suggestion.id)}
                  disabled={disabled}
                  style={getButtonStyles('secondary')}
                  className={disabled ? 'opacity-50 cursor-not-allowed' : ''}
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span>NOT INTERESTED</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* YAML Preview (Only shown after approval) */}
        {isApproved && suggestion.automation_yaml && (
          <div>
            <button
              onClick={() => setShowYaml(!showYaml)}
              className="w-full text-left px-3 py-1.5 rounded-xl font-medium transition-all text-sm"
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.5)',
                color: '#cbd5e1'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(51, 65, 85, 0.5)';
                e.currentTarget.style.borderColor = 'rgba(59, 130, 246, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(30, 41, 59, 0.6)';
                e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
              }}
            >
              <span className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <span>{showYaml ? '▼' : '▶'}</span>
                  <span>🔧 Home Assistant YAML</span>
                </span>
                <span className="text-xs opacity-70">
                  {showYaml ? 'Hide' : 'Show'} code
                </span>
              </span>
            </button>

            <AnimatePresence>
              {showYaml && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <pre className={`mt-2 p-4 rounded-xl text-xs overflow-x-auto overflow-y-auto max-h-96 font-mono border backdrop-blur-sm ${
                    darkMode ? 'bg-slate-900/60 border-slate-700/50' : 'bg-white/80 border-gray-200/50'
                  }`} style={{
                    background: 'rgba(15, 23, 42, 0.9)',
                    borderColor: 'rgba(51, 65, 85, 0.5)',
                    color: '#10b981'
                  }}>
                    {suggestion.automation_yaml}
                  </pre>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Deploy Button (after YAML generated) */}
        {suggestion.status === 'yaml_generated' && (
          <button
            className="w-full px-3 py-0.5 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-medium rounded-xl transition-all shadow-lg hover:shadow-xl flex items-center justify-center gap-1.5 text-xs"
          >
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Deploy to Home Assistant</span>
          </button>
        )}

        {/* Re-deploy Button (for deployed suggestions) */}
        {suggestion.status === 'deployed' && onRedeploy && (
          <button
            onClick={() => onRedeploy(suggestion.id)}
            disabled={disabled}
            className={`w-full px-3 py-0.5 font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow-md text-xs ${
              disabled
                ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                : 'bg-purple-600 hover:bg-purple-700 text-white hover:shadow-lg'
            }`}
          >
            {disabled ? (
              <>
                <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Re-deploying...</span>
              </>
            ) : (
              <>
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>RE-DEPLOY WITH UPDATED YAML</span>
              </>
            )}
          </button>
        )}

        {/* Metadata Footer */}
        <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-500'} pt-2 mt-2 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <div className="flex justify-between">
            <span>Created: {new Date(suggestion.created_at).toLocaleString()}</span>
            <span>ID: #{suggestion.id}</span>
          </div>
        </div>
      </div>
    </motion.div>

    {/* Device Mapping Modal */}
    {editingMapping && (
      <DeviceMappingModal
        isOpen={true}
        friendlyName={editingMapping.friendlyName}
        currentEntityId={editingMapping.currentEntityId}
        currentDomain={editingMapping.domain}
        onSave={handleMappingSave}
        onCancel={handleMappingCancel}
        darkMode={darkMode}
      />
    )}
  </>
  );
}, (prevProps, nextProps) => {
  // Custom comparison function for React.memo
  // Only re-render if these props change
  return (
    prevProps.suggestion.id === nextProps.suggestion.id &&
    prevProps.suggestion.status === nextProps.suggestion.status &&
    prevProps.suggestion.confidence === nextProps.suggestion.confidence &&
    prevProps.darkMode === nextProps.darkMode &&
    prevProps.disabled === nextProps.disabled &&
    prevProps.tested === nextProps.tested &&
    prevProps.previousConfidence === nextProps.previousConfidence &&
    prevProps.confidenceDelta === nextProps.confidenceDelta
  );
});

ConversationalSuggestionCard.displayName = 'ConversationalSuggestionCard';

