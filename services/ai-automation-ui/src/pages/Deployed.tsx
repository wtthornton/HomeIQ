/**
 * Deployed Automations Page
 * Manage deployed automations from Home Assistant
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { useAppStore } from '../store';
import api from '../services/api';

interface Automation {
  entity_id: string;
  state: string;
  attributes: {
    friendly_name?: string;
    last_triggered?: string;
    mode?: string;
  };
}

export const Deployed: React.FC = () => {
  const { darkMode } = useAppStore();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedCode, setExpandedCode] = useState<Set<string>>(new Set());
  const [yamlCache, setYamlCache] = useState<Map<string, string>>(new Map());

  useEffect(() => {
    loadAutomations();
  }, []);

  const loadAutomations = async () => {
    try {
      setLoading(true);
      const result = await api.listDeployedAutomations();
      setAutomations(result.data || []);
    } catch (error) {
      console.error('Failed to load automations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (automationId: string, currentState: string) => {
    try {
      if (currentState === 'on') {
        await api.disableAutomation(automationId);
        toast.success(`✅ Disabled ${automationId}`);
      } else {
        await api.enableAutomation(automationId);
        toast.success(`✅ Enabled ${automationId}`);
      }
      await loadAutomations(); // Refresh
    } catch (error) {
      toast.error(`❌ Failed to toggle automation: ${error}`);
    }
  };

  const handleTrigger = async (automationId: string) => {
    try {
      await api.triggerAutomation(automationId);
      toast.success(`✅ Triggered ${automationId}`);
    } catch (error) {
      toast.error(`❌ Failed to trigger automation: ${error}`);
    }
  };

  const handleRedeploy = async (automationId: string) => {
    try {
      toast.loading('🔄 Finding suggestion and regenerating YAML...', { id: `redeploy-${automationId}` });
      
      // Step 1: Find the suggestion by automation_id
      const suggestion = await api.getSuggestionByAutomationId(automationId);
      
      if (!suggestion || !suggestion.id) {
        throw new Error('Suggestion not found for this automation');
      }
      
      toast.loading('🔄 Regenerating YAML with latest improvements...', { id: `redeploy-${automationId}` });
      
      // Step 2: Re-deploy (regenerate YAML and deploy)
      // redeploySuggestion expects numeric ID, suggestion.id is already numeric from getSuggestionByAutomationId
      const result = await api.redeploySuggestion(suggestion.id);
      
      toast.success(
        `✅ Re-deployed successfully!\nNew YAML generated with latest improvements.\nSafety score: ${result.yaml_validation.safety_score}/100`,
        { id: `redeploy-${automationId}`, duration: 6000 }
      );
      
      // Refresh the list
      await loadAutomations();
    } catch (error: any) {
      console.error('Failed to re-deploy:', error);
      toast.error(
        `❌ Re-deploy failed: ${error?.message || 'Unknown error'}`,
        { id: `redeploy-${automationId}`, duration: 5000 }
      );
    }
  };

  const handleShowCode = async (automationId: string) => {
    const newExpanded = new Set(expandedCode);
    
    if (expandedCode.has(automationId)) {
      // Hide code
      newExpanded.delete(automationId);
    } else {
      // Show code - fetch if not cached
      newExpanded.add(automationId);
      
      if (!yamlCache.has(automationId)) {
        try {
          const suggestion = await api.getSuggestionByAutomationId(automationId);
          if (suggestion && suggestion.automation_yaml) {
            const newCache = new Map(yamlCache);
            newCache.set(automationId, suggestion.automation_yaml);
            setYamlCache(newCache);
          } else {
            toast.error('YAML not found for this automation');
            newExpanded.delete(automationId);
          }
        } catch (error: any) {
          toast.error(`Failed to load YAML: ${error.message}`);
          newExpanded.delete(automationId);
        }
      }
    }
    
    setExpandedCode(newExpanded);
  };

  const handleSelfCorrect = async (automationId: string) => {
    try {
      toast.loading('🔄 Loading YAML and original prompt...', { id: `self-correct-${automationId}` });
      
      // Step 1: Find the suggestion by automation_id to get YAML and original prompt
      const suggestion = await api.getSuggestionByAutomationId(automationId);
      
      if (!suggestion || !suggestion.automation_yaml) {
        throw new Error('YAML not found for this automation');
      }
      
      // Get original prompt from suggestion description
      const originalPrompt = suggestion.description_only || suggestion.title || '';
      
      if (!originalPrompt) {
        throw new Error('Original prompt not found');
      }
      
      toast.loading('🔄 Reverse engineering and self-correcting YAML...', { id: `self-correct-${automationId}` });
      
      // Step 2: Run self-correction
      const response = await api.reverseEngineerYAML({
        yaml: suggestion.automation_yaml,
        original_prompt: originalPrompt,
        context: {
          entities: suggestion.device_capabilities || {},
          conversation_history: suggestion.conversation_history || []
        }
      });
      
      toast.dismiss(`self-correct-${automationId}`);
      
      // Display results
      toast.success(
        `✅ Self-correction complete!\n` +
        `Similarity: ${(response.final_similarity * 100).toFixed(1)}%\n` +
        `Iterations: ${response.iterations_completed}/${response.max_iterations}\n` +
        `Converged: ${response.convergence_achieved ? 'Yes' : 'No'}`,
        { duration: 10000 }
      );
      
      // Show iteration history in console for debugging
      console.log('Iteration History:', response.iteration_history);
      
      // Show warnings if similarity is low
      if (response.final_similarity < 0.80) {
        toast(
          `⚠️ Similarity is ${(response.final_similarity * 100).toFixed(1)}% - may need manual review`,
          { icon: '⚠️', duration: 8000 }
        );
      }
      
    } catch (error: any) {
      toast.dismiss(`self-correct-${automationId}`);
      toast.error(`Self-correction failed: ${error.message}`);
    }
  };

  return (
    <div className="space-y-6" data-testid="deployed-container">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className={`text-3xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          🚀 Deployed Automations
        </h1>
        <p className={darkMode ? 'text-gray-400' : 'text-gray-600'}>
          Manage automations deployed to Home Assistant
        </p>
      </motion.div>

      {/* Automations List */}
      {loading ? (
        <div className={`text-center py-12 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          Loading deployed automations...
        </div>
      ) : automations.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-2xl shadow-xl p-8 text-center ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}
        >
          <div className="text-6xl mb-4">🚀</div>
          <h2 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            No Deployed Automations Yet
          </h2>
          <p className={`text-lg mb-6 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Approve suggestions and deploy them to see them here!
          </p>
        </motion.div>
      ) : (
        <div className="space-y-4">
          {automations.map((automation, index) => (
            <motion.div
              key={automation.entity_id}
              data-testid="deployed-automation"
              data-id={automation.entity_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              className={`rounded-xl shadow-lg p-6 ${
                darkMode ? 'bg-gray-800' : 'bg-white'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className={`text-lg font-bold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {automation.attributes.friendly_name || automation.entity_id}
                  </h3>
                  <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    {automation.entity_id}
                  </p>
                  {automation.attributes.last_triggered && (
                    <p className={`text-xs mt-2 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                      Last triggered: {new Date(automation.attributes.last_triggered).toLocaleString()}
                    </p>
                  )}
                </div>
                
                <div className="flex gap-3 items-center">
                  {/* Status Badge */}
                  <div className={`px-3 py-1 rounded-full text-sm font-medium ${
                    automation.state === 'on'
                      ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200'
                  }`}>
                    {automation.state === 'on' ? '✅ Enabled' : '⏸️ Disabled'}
                  </div>
                  
                  {/* Toggle Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleToggle(automation.entity_id, automation.state)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      automation.state === 'on'
                        ? darkMode
                          ? 'bg-gray-700 hover:bg-gray-600 text-white'
                          : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    }`}
                  >
                    {automation.state === 'on' ? 'Disable' : 'Enable'}
                  </motion.button>
                  
                  {/* Trigger Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleTrigger(automation.entity_id)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-500 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    }`}
                  >
                    ▶️ Trigger
                  </motion.button>
                  
                  {/* Re-deploy Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleRedeploy(automation.entity_id)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      darkMode
                        ? 'bg-purple-600 hover:bg-purple-500 text-white'
                        : 'bg-purple-500 hover:bg-purple-600 text-white'
                    }`}
                    title="Re-generate YAML with latest improvements and re-deploy"
                  >
                    🔄 Re-deploy
                  </motion.button>
                  
                  {/* Show Code Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleShowCode(automation.entity_id)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      darkMode
                        ? 'bg-gray-600 hover:bg-gray-500 text-white'
                        : 'bg-gray-500 hover:bg-gray-600 text-white'
                    }`}
                    title={expandedCode.has(automation.entity_id) ? "Hide YAML code" : "Show YAML code"}
                  >
                    {expandedCode.has(automation.entity_id) ? '👁️ Hide Code' : '👁️ Show Code'}
                  </motion.button>
                  
                  {/* Self-Correct Button */}
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => handleSelfCorrect(automation.entity_id)}
                    className={`px-4 py-2 rounded-lg font-medium ${
                      darkMode
                        ? 'bg-green-600 hover:bg-green-500 text-white'
                        : 'bg-green-500 hover:bg-green-600 text-white'
                    }`}
                    title="Reverse engineer and self-correct YAML to match original prompt"
                  >
                    🔄 Self-Correct
                  </motion.button>
                </div>
              </div>
              
              {/* Expandable Code Display */}
              {expandedCode.has(automation.entity_id) && yamlCache.has(automation.entity_id) && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className={`mt-4 rounded-lg overflow-hidden ${darkMode ? 'bg-gray-900' : 'bg-gray-50'}`}
                >
                  <pre className={`p-4 overflow-x-auto overflow-y-auto max-h-96 text-xs font-mono ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                    <code>{yamlCache.get(automation.entity_id)}</code>
                  </pre>
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Refresh Button */}
      <motion.button
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        onClick={loadAutomations}
        className={`w-full px-6 py-3 rounded-xl font-semibold shadow-lg transition-all ${
          darkMode
            ? 'bg-gray-700 hover:bg-gray-600 text-white'
            : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
        }`}
      >
        🔄 Refresh List
      </motion.button>
    </div>
  );
};
