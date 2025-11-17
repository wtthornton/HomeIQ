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

interface DebugPanelProps {
  debug?: DebugData;
  technicalPrompt?: TechnicalPrompt;
  deviceInfo?: DeviceInfo[]; // Device info from suggestion (friendly names and entity IDs)
  darkMode?: boolean;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({
  debug,
  technicalPrompt,
  deviceInfo,
  darkMode = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'devices' | 'prompts' | 'technical'>('devices');
  const [showFilteredPrompt, setShowFilteredPrompt] = useState(true);  // Default to filtered

  if (!debug && !technicalPrompt && (!deviceInfo || deviceInfo.length === 0)) {
    return null;
  }

  const bgColor = darkMode ? 'bg-gray-800' : 'bg-gray-50';
  const textColor = darkMode ? 'text-gray-100' : 'text-gray-900';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';
  const codeBg = darkMode ? 'bg-gray-900' : 'bg-gray-100';

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
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

