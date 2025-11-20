/**
 * Debug Panel Component - Ask AI Enhancement
 * 
 * Displays debug information for suggestions including:
 * - Device selection reasoning
 * - OpenAI prompts and responses
 * - Technical prompt details
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DeviceDebugInfo {
  device_name: string;
  entity_id: string | null;
  selection_reason: string;
  entity_type: string | null;
  entities: Array<{ entity_id: string; friendly_name: string }>;
  capabilities: string[];
  actions_suggested: string[];
}

interface DebugData {
  device_selection?: DeviceDebugInfo[];
  system_prompt?: string;
  user_prompt?: string;
  filtered_user_prompt?: string;  // NEW: Filtered prompt with only entities used
  openai_response?: any;
  token_usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
  entity_context_stats?: {  // NEW: Entity context statistics
    total_entities_available?: number;
    entities_used_in_suggestion?: number;
    filtered_entity_context_json?: string;
  };
}

interface TechnicalPrompt {
  alias?: string;
  description?: string;
  trigger?: {
    entities?: Array<{
      entity_id: string;
      friendly_name: string;
      domain: string;
      platform: string;
      from?: string | null;
      to?: string | null;
    }>;
    platform?: string;
  };
  action?: {
    entities?: Array<{
      entity_id: string;
      friendly_name: string;
      domain: string;
      service_calls?: Array<{
        service: string;
        parameters?: Record<string, any>;
      }>;
    }>;
    service_calls?: Array<{
      service: string;
      parameters?: Record<string, any>;
    }>;
  };
  conditions?: any[];
  entity_capabilities?: Record<string, string[]>;
  metadata?: {
    query?: string;
    devices_involved?: string[];
    confidence?: number;
  };
}

interface DeviceInfo {
  friendly_name: string;
  entity_id: string;
  domain?: string;
  selected?: boolean;
}

interface FlowStep {
  id: string;
  name: string;
  status: 'completed' | 'pending' | 'in-progress' | 'error';
  timestamp?: string;
  duration?: number;
  details?: any;
  request?: any;
  response?: any;
  error?: string;
}

interface ApproveResponse {
  status?: string;
  automation_id?: string;
  automation_yaml?: string;
  message?: string;
  warnings?: string[];
  error_details?: any;
  safety_report?: any;
}

interface DebugPanelProps {
  debug?: DebugData;
  technicalPrompt?: TechnicalPrompt;
  deviceInfo?: DeviceInfo[]; // Device info from suggestion (friendly names and entity IDs)
  automation_yaml?: string | null;
  originalQuery?: string; // Original user query
  extractedEntities?: any[]; // Entities extracted from query
  approveResponse?: ApproveResponse; // Response from approve endpoint
  darkMode?: boolean;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({
  debug,
  technicalPrompt,
  deviceInfo,
  automation_yaml,
  originalQuery,
  extractedEntities,
  approveResponse,
  darkMode = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'devices' | 'prompts' | 'technical' | 'yaml' | 'flow'>('devices');
  const [showFilteredPrompt, setShowFilteredPrompt] = useState(true);  // Default to filtered
  const [flowViewMode, setFlowViewMode] = useState<'timeline' | 'diagram'>('timeline');
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  if (!debug && !technicalPrompt && (!deviceInfo || deviceInfo.length === 0) && !automation_yaml) {
    return null;
  }

  const bgColor = darkMode ? 'bg-gray-800' : 'bg-gray-50';
  const textColor = darkMode ? 'text-gray-100' : 'text-gray-900';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';
  const codeBg = darkMode ? 'bg-gray-900' : 'bg-gray-100';

  // Build flow steps from available data
  const buildFlowSteps = (): FlowStep[] => {
    const steps: FlowStep[] = [];

    // Step 1: User Prompt
    if (originalQuery) {
      steps.push({
        id: 'user-prompt',
        name: 'User Prompt',
        status: 'completed',
        details: { query: originalQuery }
      });
    }

    // Step 2: Entity Extraction
    if (extractedEntities && extractedEntities.length > 0) {
      steps.push({
        id: 'entity-extraction',
        name: 'Entity Extraction',
        status: 'completed',
        details: {
          entities: extractedEntities,
          count: extractedEntities.length
        },
        response: {
          method: 'POST',
          endpoint: '/api/conversation/process',
          entities_found: extractedEntities.length
        }
      });
    }

    // Step 3: Device Selection
    if (debug?.device_selection && debug.device_selection.length > 0) {
      steps.push({
        id: 'device-selection',
        name: 'Device Selection',
        status: 'completed',
        details: {
          devices: debug.device_selection,
          count: debug.device_selection.length
        }
      });
    } else if (deviceInfo && deviceInfo.length > 0) {
      steps.push({
        id: 'device-selection',
        name: 'Device Selection',
        status: 'completed',
        details: {
          devices: deviceInfo,
          count: deviceInfo.length
        }
      });
    }

    // Step 4: OpenAI Prompt Generation
    if (debug?.system_prompt || debug?.user_prompt) {
      steps.push({
        id: 'prompt-generation',
        name: 'OpenAI Prompt Generation',
        status: 'completed',
        details: {
          system_prompt: debug.system_prompt,
          user_prompt: debug.user_prompt,
          filtered_prompt: debug.filtered_user_prompt,
          token_usage: debug.token_usage
        }
      });
    } else {
      steps.push({
        id: 'prompt-generation',
        name: 'OpenAI Prompt Generation',
        status: 'pending',
        details: { message: 'Prompt generation data not available' }
      });
    }

    // Step 5: OpenAI API Call
    if (debug?.openai_response) {
      steps.push({
        id: 'openai-call',
        name: 'OpenAI API Call',
        status: 'completed',
        details: {
          response: debug.openai_response,
          token_usage: debug.token_usage
        },
        request: {
          model: 'gpt-4o-mini',
          messages: [
            { role: 'system', content: debug.system_prompt },
            { role: 'user', content: debug.user_prompt || debug.filtered_user_prompt }
          ]
        },
        response: debug.openai_response
      });
    } else {
      steps.push({
        id: 'openai-call',
        name: 'OpenAI API Call',
        status: 'pending',
        details: { message: 'OpenAI API call data not available' }
      });
    }

    // Step 6: Technical Prompt Creation
    if (technicalPrompt) {
      steps.push({
        id: 'technical-prompt',
        name: 'Technical Prompt Creation',
        status: 'completed',
        details: { technical_prompt: technicalPrompt }
      });
    } else {
      steps.push({
        id: 'technical-prompt',
        name: 'Technical Prompt Creation',
        status: 'pending',
        details: { message: 'Technical prompt will be created during suggestion generation' }
      });
    }

    // Step 7: YAML Generation
    if (automation_yaml) {
      steps.push({
        id: 'yaml-generation',
        name: 'YAML Generation',
        status: 'completed',
        details: { yaml: automation_yaml }
      });
    } else {
      steps.push({
        id: 'yaml-generation',
        name: 'YAML Generation',
        status: 'pending',
        details: { message: 'Click "Approve & Create" to generate YAML' }
      });
    }

    // Step 8: HA API Call (always show, even if no response yet)
    const hasError = approveResponse && (
      approveResponse.error_details || 
      approveResponse.status === 'error' || 
      approveResponse.status === 'blocked'
    );
    const hasSuccess = approveResponse && approveResponse.automation_id;
    
    steps.push({
      id: 'ha-api-call',
      name: 'Home Assistant API Call',
      status: hasSuccess ? 'completed' : 
              hasError ? 'error' : 
              approveResponse ? 'in-progress' : 'pending',
      details: approveResponse ? {
        endpoint: '/api/config/automation/config',
        method: 'POST',
        yaml: automation_yaml || approveResponse.automation_yaml,
        error: approveResponse.error_details?.message || 
               (hasError ? approveResponse.message : undefined)
      } : { message: 'Click "Approve & Create" to call Home Assistant API' },
      request: approveResponse ? {
        method: 'POST',
        endpoint: '/api/config/automation/config',
        body: automation_yaml || approveResponse.automation_yaml
      } : undefined,
      response: approveResponse,
      error: hasError ? (approveResponse.error_details?.message || approveResponse.message) : undefined
    });

    // Step 9: HA Response (always show, even if no response yet)
    steps.push({
      id: 'ha-response',
      name: 'Home Assistant Response',
      status: hasSuccess ? 'completed' : 
              hasError ? 'error' : 
              approveResponse ? 'in-progress' : 'pending',
      details: approveResponse ? {
        automation_id: approveResponse.automation_id,
        status: approveResponse.status,
        message: approveResponse.message,
        warnings: approveResponse.warnings,
        error: approveResponse.error_details?.message || 
               (hasError ? approveResponse.message : undefined),
        error_details: approveResponse.error_details
      } : { message: 'Waiting for Home Assistant API call' },
      response: approveResponse,
      error: hasError ? (approveResponse.error_details?.message || approveResponse.message) : undefined
    });

    return steps;
  };

  const flowSteps = buildFlowSteps();

  const toggleStepExpansion = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepId)) {
        newSet.delete(stepId);
      } else {
        newSet.add(stepId);
      }
      return newSet;
    });
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className={`mt-4 ${borderColor} border rounded-lg overflow-hidden`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-4 py-3 ${bgColor} ${textColor} flex items-center justify-between hover:opacity-80 transition-opacity`}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">🔍 Debug Panel</span>
          <span className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
            {isOpen ? 'Hide' : 'Show'}
          </span>
        </div>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className={`${bgColor} overflow-hidden`}
          >
            <div className="p-4">
              {/* Tabs */}
              <div className={`flex gap-2 mb-4 border-b ${borderColor}`}>
                {((deviceInfo && deviceInfo.length > 0) || (debug?.device_selection && debug.device_selection.length > 0)) && (
                  <button
                    onClick={() => setActiveTab('devices')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === 'devices'
                        ? `${textColor} border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`
                        : `${darkMode ? 'text-gray-400' : 'text-gray-600'} hover:${textColor}`
                    }`}
                  >
                    Device Selection
                  </button>
                )}
                {debug && (
                  <button
                    onClick={() => setActiveTab('prompts')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === 'prompts'
                        ? `${textColor} border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`
                        : `${darkMode ? 'text-gray-400' : 'text-gray-600'} hover:${textColor}`
                    }`}
                  >
                    OpenAI Prompts
                  </button>
                )}
                {technicalPrompt && (
                  <button
                    onClick={() => setActiveTab('technical')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === 'technical'
                        ? `${textColor} border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`
                        : `${darkMode ? 'text-gray-400' : 'text-gray-600'} hover:${textColor}`
                    }`}
                  >
                    Technical Prompt
                  </button>
                )}
                {automation_yaml && (
                  <button
                    onClick={() => setActiveTab('yaml')}
                    className={`px-4 py-2 text-sm font-medium transition-colors ${
                      activeTab === 'yaml'
                        ? `${textColor} border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`
                        : `${darkMode ? 'text-gray-400' : 'text-gray-600'} hover:${textColor}`
                    }`}
                  >
                    YAML Response
                  </button>
                )}
                <button
                  onClick={() => setActiveTab('flow')}
                  className={`px-4 py-2 text-sm font-medium transition-colors ${
                    activeTab === 'flow'
                      ? `${textColor} border-b-2 ${darkMode ? 'border-blue-400' : 'border-blue-600'}`
                      : `${darkMode ? 'text-gray-400' : 'text-gray-600'} hover:${textColor}`
                  }`}
                >
                  🔄 Execution Flow
                </button>
              </div>

              {/* Device Selection Tab */}
              {activeTab === 'devices' && (
                <div className="space-y-4">
                  {/* Device Info Section - Shows friendly names and entity IDs */}
                  {deviceInfo && deviceInfo.length > 0 && (
                    <div>
                      <h4 className={`font-semibold mb-3 ${textColor}`}>Selected Devices</h4>
                      <div className="space-y-2">
                        {deviceInfo.map((device, idx) => (
                          <div
                            key={idx}
                            className={`${codeBg} p-3 rounded-lg ${borderColor} border`}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <div className={`font-medium ${textColor} mb-1`}>
                                  {device.friendly_name}
                                </div>
                                <div className="text-xs">
                                  <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                    Entity ID:
                                  </span>
                                  <code className={`${codeBg} px-2 py-0.5 rounded ml-2 ${textColor} font-mono`}>
                                    {device.entity_id}
                                  </code>
                                </div>
                                {device.domain && (
                                  <div className="text-xs mt-1">
                                    <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                      Domain:
                                    </span>
                                    <span className={`ml-2 ${textColor}`}>{device.domain}</span>
                                  </div>
                                )}
                                <div className="text-xs mt-1">
                                  <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                    Status:
                                  </span>
                                  <span className={`ml-2 ${device.selected !== false ? 'text-green-500' : 'text-gray-500'}`}>
                                    {device.selected !== false ? 'Selected' : 'Excluded'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Debug Device Selection Section - Shows selection reasoning */}
                  {debug?.device_selection && debug.device_selection.length > 0 && (
                    <div>
                      <h4 className={`font-semibold mb-3 ${textColor}`}>Device Selection Reasoning</h4>
                      {debug.device_selection.map((device, idx) => (
                        <div
                          key={idx}
                          className={`${codeBg} p-4 rounded-lg ${borderColor} border mb-3`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <h4 className={`font-semibold ${textColor}`}>{device.device_name}</h4>
                            {device.entity_id && (
                              <span className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`}>
                                {device.entity_type || 'individual'}
                              </span>
                            )}
                          </div>
                          
                          <div className="space-y-2 text-sm">
                            <div>
                              <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                Why Selected:
                              </span>
                              <p className={`${textColor} mt-1`}>{device.selection_reason}</p>
                            </div>
                            
                            {device.entity_id && (
                              <div>
                                <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                  Entity ID:
                                </span>
                                <code className={`${codeBg} px-2 py-1 rounded text-xs ml-2 ${textColor}`}>
                                  {device.entity_id}
                                </code>
                              </div>
                            )}
                        
                        {device.entities.length > 0 && (
                          <div>
                            <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              Entities ({device.entities.length}):
                            </span>
                            <ul className="mt-1 space-y-1">
                              {device.entities.map((entity, eIdx) => (
                                <li key={eIdx} className={`${textColor} text-xs`}>
                                  <code className={`${codeBg} px-2 py-1 rounded`}>
                                    {entity.entity_id}
                                  </code>
                                  <span className="ml-2">{entity.friendly_name}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                        
                        {device.capabilities.length > 0 && (
                          <div>
                            <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              Capabilities:
                            </span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {device.capabilities.map((cap, cIdx) => (
                                <span
                                  key={cIdx}
                                  className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-blue-900' : 'bg-blue-100'} ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}
                                >
                                  {cap}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        
                        {device.actions_suggested.length > 0 && (
                          <div>
                            <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                              Actions Suggested:
                            </span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {device.actions_suggested.map((action, aIdx) => (
                                <span
                                  key={aIdx}
                                  className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-green-900' : 'bg-green-100'} ${darkMode ? 'text-green-200' : 'text-green-800'}`}
                                >
                                  {action}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* OpenAI Prompts Tab */}
              {activeTab === 'prompts' && debug && (
                <div className="space-y-4">
                  {/* Entity Context Statistics */}
                  {debug.entity_context_stats && (
                    <div className={`${codeBg} p-3 rounded-lg ${borderColor} border`}>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>Entity Context Statistics</h4>
                      <div className="text-sm space-y-1">
                        <div className={textColor}>
                          <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                            Total Entities Available:
                          </span>
                          <span className="ml-2">{debug.entity_context_stats.total_entities_available || 0}</span>
                        </div>
                        <div className={textColor}>
                          <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                            Entities Used in Suggestion:
                          </span>
                          <span className="ml-2 font-semibold text-green-600 dark:text-green-400">
                            {debug.entity_context_stats.entities_used_in_suggestion || 0}
                          </span>
                        </div>
                        {debug.entity_context_stats.total_entities_available && debug.entity_context_stats.entities_used_in_suggestion && (
                          <div className={`text-xs mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            💡 Filtered prompt shows only {debug.entity_context_stats.entities_used_in_suggestion} of {debug.entity_context_stats.total_entities_available} available entities to reduce token usage
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {debug.system_prompt && (
                    <div>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>System Prompt</h4>
                      <pre className={`${codeBg} p-4 rounded-lg overflow-x-auto text-xs ${textColor}`}>
                        {debug.system_prompt}
                      </pre>
                    </div>
                  )}
                  
                  {debug.user_prompt && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <h4 className={`font-semibold ${textColor}`}>User Prompt</h4>
                        {debug.filtered_user_prompt && (
                          <button
                            onClick={() => setShowFilteredPrompt(!showFilteredPrompt)}
                            className={`text-xs px-3 py-1 rounded ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textColor} transition-colors`}
                          >
                            {showFilteredPrompt ? 'Show Full Prompt' : 'Show Filtered Prompt'}
                          </button>
                        )}
                      </div>
                      <pre className={`${codeBg} p-4 rounded-lg overflow-x-auto text-xs ${textColor}`}>
                        {showFilteredPrompt && debug.filtered_user_prompt 
                          ? debug.filtered_user_prompt 
                          : debug.user_prompt}
                      </pre>
                      {debug.filtered_user_prompt && (
                        <div className={`text-xs mt-2 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          {showFilteredPrompt 
                            ? 'Showing filtered prompt (only entities used in suggestion)'
                            : 'Showing full prompt (all entities available during generation)'}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {debug.openai_response && (
                    <div>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>OpenAI Response</h4>
                      <pre className={`${codeBg} p-4 rounded-lg overflow-x-auto text-xs ${textColor}`}>
                        {JSON.stringify(debug.openai_response, null, 2)}
                      </pre>
                    </div>
                  )}
                  
                  {debug.token_usage && (
                    <div>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>Token Usage</h4>
                      <div className={`${codeBg} p-4 rounded-lg ${textColor} text-sm`}>
                        <div className="grid grid-cols-3 gap-4">
                          <div>
                            <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Prompt:</span>
                            <span className="ml-2 font-mono">{debug.token_usage.prompt_tokens || 0}</span>
                          </div>
                          <div>
                            <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Completion:</span>
                            <span className="ml-2 font-mono">{debug.token_usage.completion_tokens || 0}</span>
                          </div>
                          <div>
                            <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Total:</span>
                            <span className="ml-2 font-mono">{debug.token_usage.total_tokens || 0}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Technical Prompt Tab */}
              {activeTab === 'technical' && technicalPrompt && (
                <div className="space-y-4">
                  <div>
                    <h4 className={`font-semibold mb-2 ${textColor}`}>Technical Prompt</h4>
                    <pre className={`${codeBg} p-4 rounded-lg overflow-x-auto text-xs ${textColor}`}>
                      {JSON.stringify(technicalPrompt, null, 2)}
                    </pre>
                  </div>
                  
                  {technicalPrompt.trigger?.entities && technicalPrompt.trigger.entities.length > 0 && (
                    <div>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>Trigger Entities</h4>
                      <div className="space-y-2">
                        {technicalPrompt.trigger.entities.map((entity, idx) => (
                          <div key={idx} className={`${codeBg} p-3 rounded ${textColor} text-sm`}>
                            <div className="font-mono text-xs">{entity.entity_id}</div>
                            <div className="mt-1">{entity.friendly_name}</div>
                            {entity.to && (
                              <div className="mt-1 text-xs">
                                <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>State:</span>
                                <span className="ml-2">{entity.from || 'any'} → {entity.to}</span>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {technicalPrompt.action?.entities && technicalPrompt.action.entities.length > 0 && (
                    <div>
                      <h4 className={`font-semibold mb-2 ${textColor}`}>Action Entities</h4>
                      <div className="space-y-2">
                        {technicalPrompt.action.entities.map((entity, idx) => (
                          <div key={idx} className={`${codeBg} p-3 rounded ${textColor} text-sm`}>
                            <div className="font-mono text-xs">{entity.entity_id}</div>
                            <div className="mt-1">{entity.friendly_name}</div>
                            {entity.service_calls && entity.service_calls.length > 0 && (
                              <div className="mt-2 space-y-1">
                                {entity.service_calls.map((sc, scIdx) => (
                                  <div key={scIdx} className="text-xs">
                                    <span className={`font-medium ${darkMode ? 'text-blue-300' : 'text-blue-600'}`}>
                                      {sc.service}
                                    </span>
                                    {sc.parameters && Object.keys(sc.parameters).length > 0 && (
                                      <div className="ml-4 mt-1">
                                        {JSON.stringify(sc.parameters, null, 2)}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* YAML Response Tab */}
              {activeTab === 'yaml' && automation_yaml && (
                <div className="space-y-4">
                  <div>
                    <h4 className={`font-semibold mb-2 ${textColor}`}>YAML Response</h4>
                    <div className={`${codeBg} rounded-lg ${borderColor} border overflow-hidden`}>
                      <pre className={`p-4 overflow-x-auto text-xs ${textColor} font-mono max-h-96 overflow-y-auto`}>
                        {automation_yaml}
                      </pre>
                    </div>
                  </div>
                </div>
              )}

              {/* Flow Tab - Option 1: Timeline View */}
              {activeTab === 'flow' && (
                <div className="space-y-4">
                  {/* View Mode Toggle */}
                  <div className="flex items-center justify-between mb-4">
                    <h4 className={`font-semibold ${textColor}`}>Execution Flow</h4>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setFlowViewMode('timeline')}
                        className={`px-3 py-1.5 text-xs rounded transition-colors ${
                          flowViewMode === 'timeline'
                            ? `${darkMode ? 'bg-blue-600' : 'bg-blue-500'} text-white`
                            : `${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`
                        }`}
                      >
                        Timeline
                      </button>
                      <button
                        onClick={() => setFlowViewMode('diagram')}
                        className={`px-3 py-1.5 text-xs rounded transition-colors ${
                          flowViewMode === 'diagram'
                            ? `${darkMode ? 'bg-blue-600' : 'bg-blue-500'} text-white`
                            : `${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`
                        }`}
                      >
                        Flow Diagram
                      </button>
                    </div>
                  </div>

                  {flowViewMode === 'timeline' ? (
                    /* Timeline View */
                    <div className="space-y-3">
                      {flowSteps.map((step, idx) => {
                        const isExpanded = expandedSteps.has(step.id);
                        const statusIcon = 
                          step.status === 'completed' ? '✓' :
                          step.status === 'in-progress' ? '⟳' :
                          step.status === 'error' ? '✗' : '⏳';
                        const statusColor = 
                          step.status === 'completed' ? 'text-green-500' :
                          step.status === 'in-progress' ? 'text-blue-500' :
                          step.status === 'error' ? 'text-red-500' : 'text-gray-400';

                        return (
                          <div key={step.id} className="relative">
                            {/* Timeline Line */}
                            {idx < flowSteps.length - 1 && (
                              <div className={`absolute left-4 top-12 w-0.5 h-full ${darkMode ? 'bg-gray-700' : 'bg-gray-300'}`} />
                            )}
                            
                            {/* Step Card */}
                            <div className={`${codeBg} rounded-lg ${borderColor} border overflow-hidden`}>
                              <button
                                onClick={() => toggleStepExpansion(step.id)}
                                className="w-full px-4 py-3 flex items-start gap-3 hover:opacity-80 transition-opacity"
                              >
                                <div className={`text-2xl ${statusColor} flex-shrink-0`}>
                                  {statusIcon}
                                </div>
                                <div className="flex-1 text-left">
                                  <div className="flex items-center justify-between">
                                    <div>
                                      <span className={`font-semibold ${textColor}`}>
                                        {idx + 1}. {step.name}
                                      </span>
                                      <span className={`ml-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                        {step.status === 'completed' ? 'Completed' :
                                         step.status === 'in-progress' ? 'In Progress' :
                                         step.status === 'error' ? 'Error' : 'Pending'}
                                      </span>
                                    </div>
                                    {step.timestamp && (
                                      <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                        {new Date(step.timestamp).toLocaleTimeString()}
                                      </span>
                                    )}
                                  </div>
                                  
                                  {/* Step Preview */}
                                  {!isExpanded && (
                                    <div className={`mt-2 text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                                      {step.id === 'user-prompt' && step.details?.query && (
                                        <div className="truncate">"{step.details.query}"</div>
                                      )}
                                      {step.id === 'entity-extraction' && step.details?.count && (
                                        <div>{step.details.count} entities extracted</div>
                                      )}
                                      {step.id === 'device-selection' && step.details?.count && (
                                        <div>{step.details.count} devices selected</div>
                                      )}
                                      {step.id === 'prompt-generation' && step.details?.token_usage && (
                                        <div>
                                          {step.details.token_usage.prompt_tokens || 0} prompt tokens,{' '}
                                          {step.details.token_usage.completion_tokens || 0} completion tokens
                                        </div>
                                      )}
                                      {step.id === 'openai-call' && step.response && (
                                        <div>Response received</div>
                                      )}
                                      {step.id === 'technical-prompt' && (
                                        <div>JSON structure created</div>
                                      )}
                                      {step.id === 'yaml-generation' && step.details?.yaml && (
                                        <div className="truncate font-mono text-xs">
                                          {step.details.yaml.substring(0, 100)}...
                                        </div>
                                      )}
                                      {step.id === 'ha-api-call' && step.response?.automation_id && (
                                        <div>Automation created: {step.response.automation_id}</div>
                                      )}
                                      {step.id === 'ha-response' && step.response?.automation_id && (
                                        <div className="text-green-500">
                                          ✓ Success: {step.response.automation_id}
                                        </div>
                                      )}
                                      {step.error && (
                                        <div className="text-red-500">Error: {step.error}</div>
                                      )}
                                    </div>
                                  )}
                                </div>
                                <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                  {isExpanded ? '▼' : '▶'}
                                </div>
                              </button>

                              {/* Expanded Details */}
                              {isExpanded && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="px-4 pb-4 border-t border-gray-700"
                                >
                                  <div className="pt-4 space-y-4">
                                    {/* Request */}
                                    {step.request && (
                                      <div>
                                        <div className="flex items-center justify-between mb-2">
                                          <h5 className={`font-medium ${textColor}`}>Request</h5>
                                          {typeof step.request === 'object' && (
                                            <button
                                              onClick={() => copyToClipboard(JSON.stringify(step.request, null, 2))}
                                              className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`}
                                            >
                                              Copy
                                            </button>
                                          )}
                                        </div>
                                        <pre className={`${codeBg} p-3 rounded text-xs ${textColor} overflow-x-auto max-h-64 overflow-y-auto`}>
                                          {typeof step.request === 'object' 
                                            ? JSON.stringify(step.request, null, 2)
                                            : step.request}
                                        </pre>
                                      </div>
                                    )}

                                    {/* Response */}
                                    {step.response && (
                                      <div>
                                        <div className="flex items-center justify-between mb-2">
                                          <h5 className={`font-medium ${textColor}`}>Response</h5>
                                          {typeof step.response === 'object' && (
                                            <button
                                              onClick={() => copyToClipboard(JSON.stringify(step.response, null, 2))}
                                              className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`}
                                            >
                                              Copy
                                            </button>
                                          )}
                                        </div>
                                        <pre className={`${codeBg} p-3 rounded text-xs ${textColor} overflow-x-auto max-h-64 overflow-y-auto`}>
                                          {typeof step.response === 'object' 
                                            ? JSON.stringify(step.response, null, 2)
                                            : step.response}
                                        </pre>
                                      </div>
                                    )}

                                    {/* Details */}
                                    {step.details && (
                                      <div>
                                        <h5 className={`font-medium mb-2 ${textColor}`}>Details</h5>
                                        {step.details.query && (
                                          <div className={`${codeBg} p-3 rounded ${textColor} text-sm`}>
                                            {step.details.query}
                                          </div>
                                        )}
                                        {step.details.yaml && (
                                          <div className={`${codeBg} p-3 rounded ${textColor} text-xs font-mono max-h-64 overflow-y-auto`}>
                                            {step.details.yaml}
                                          </div>
                                        )}
                                        {step.details.entities && (
                                          <div className="space-y-2">
                                            {step.details.entities.map((entity: any, eIdx: number) => (
                                              <div key={eIdx} className={`${codeBg} p-2 rounded text-xs ${textColor}`}>
                                                {entity.entity_id || entity.id || JSON.stringify(entity)}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                        {step.details.devices && (
                                          <div className="space-y-2">
                                            {step.details.devices.map((device: any, dIdx: number) => (
                                              <div key={dIdx} className={`${codeBg} p-2 rounded text-xs ${textColor}`}>
                                                {device.device_name || device.friendly_name}: {device.entity_id || device.selection_reason}
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                        {step.details.message && (
                                          <div className={`${codeBg} p-3 rounded ${textColor} text-sm italic`}>
                                            {step.details.message}
                                          </div>
                                        )}
                                      </div>
                                    )}

                                    {/* Error */}
                                    {step.error && (
                                      <div className={`p-3 rounded ${darkMode ? 'bg-red-900' : 'bg-red-50'} ${darkMode ? 'text-red-200' : 'text-red-800'} text-sm`}>
                                        <strong>Error:</strong> {step.error}
                                      </div>
                                    )}
                                  </div>
                                </motion.div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    /* Flow Diagram View */
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 gap-4">
                        {flowSteps.map((step, idx) => {
                          const statusIcon = 
                            step.status === 'completed' ? '✓' :
                            step.status === 'in-progress' ? '⟳' :
                            step.status === 'error' ? '✗' : '⏳';
                          const statusColor = 
                            step.status === 'completed' ? 'border-green-500 bg-green-50 dark:bg-green-900/20' :
                            step.status === 'in-progress' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' :
                            step.status === 'error' ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : 
                            'border-gray-400 bg-gray-50 dark:bg-gray-700/20';

                          return (
                            <div key={step.id} className="relative">
                              {/* Arrow */}
                              {idx < flowSteps.length - 1 && (
                                <div className="absolute left-1/2 top-full transform -translate-x-1/2 w-0.5 h-4 bg-gray-400" />
                              )}
                              
                              {/* Node */}
                              <button
                                onClick={() => toggleStepExpansion(step.id)}
                                className={`w-full ${codeBg} rounded-lg border-2 ${statusColor} p-4 hover:opacity-80 transition-opacity`}
                              >
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-3">
                                    <div className={`text-2xl ${statusColor.includes('green') ? 'text-green-500' : statusColor.includes('red') ? 'text-red-500' : statusColor.includes('blue') ? 'text-blue-500' : 'text-gray-400'}`}>
                                      {statusIcon}
                                    </div>
                                    <div className="text-left">
                                      <div className={`font-semibold ${textColor}`}>
                                        {idx + 1}. {step.name}
                                      </div>
                                      <div className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                        {step.status === 'completed' ? 'Completed' :
                                         step.status === 'in-progress' ? 'In Progress' :
                                         step.status === 'error' ? 'Error' : 'Pending'}
                                      </div>
                                    </div>
                                  </div>
                                  <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                    {expandedSteps.has(step.id) ? '▼' : '▶'}
                                  </div>
                                </div>
                              </button>

                              {/* Expanded Details (same as timeline) */}
                              {expandedSteps.has(step.id) && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  className="mt-2"
                                >
                                  <div className={`${codeBg} rounded-lg ${borderColor} border p-4 space-y-4`}>
                                    {/* Same detail rendering as timeline view */}
                                    {step.request && (
                                      <div>
                                        <div className="flex items-center justify-between mb-2">
                                          <h5 className={`font-medium ${textColor}`}>Request</h5>
                                          {typeof step.request === 'object' && (
                                            <button
                                              onClick={() => copyToClipboard(JSON.stringify(step.request, null, 2))}
                                              className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`}
                                            >
                                              Copy
                                            </button>
                                          )}
                                        </div>
                                        <pre className={`${codeBg} p-3 rounded text-xs ${textColor} overflow-x-auto max-h-64 overflow-y-auto`}>
                                          {typeof step.request === 'object' 
                                            ? JSON.stringify(step.request, null, 2)
                                            : step.request}
                                        </pre>
                                      </div>
                                    )}
                                    {step.response && (
                                      <div>
                                        <div className="flex items-center justify-between mb-2">
                                          <h5 className={`font-medium ${textColor}`}>Response</h5>
                                          {typeof step.response === 'object' && (
                                            <button
                                              onClick={() => copyToClipboard(JSON.stringify(step.response, null, 2))}
                                              className={`text-xs px-2 py-1 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'} ${textColor}`}
                                            >
                                              Copy
                                            </button>
                                          )}
                                        </div>
                                        <pre className={`${codeBg} p-3 rounded text-xs ${textColor} overflow-x-auto max-h-64 overflow-y-auto`}>
                                          {typeof step.response === 'object' 
                                            ? JSON.stringify(step.response, null, 2)
                                            : step.response}
                                        </pre>
                                      </div>
                                    )}
                                    {step.error && (
                                      <div className={`p-3 rounded ${darkMode ? 'bg-red-900' : 'bg-red-50'} ${darkMode ? 'text-red-200' : 'text-red-800'} text-sm`}>
                                        <strong>Error:</strong> {step.error}
                                      </div>
                                    )}
                                  </div>
                                </motion.div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

