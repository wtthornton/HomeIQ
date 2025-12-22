/**
 * CTA Action Buttons Component
 * 
 * Displays an interactive "Create Automation" button
 * to replace text prompts for automation approval
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { executeToolCall, type ExecuteToolCallResponse } from '../../services/haAiAgentApi';

interface CTAActionButtonsProps {
  messageContent: string;
  automationYaml?: string;
  conversationId: string;
  onSuccess?: (automationId: string) => void;
  darkMode: boolean;
}

export const CTAActionButtons: React.FC<CTAActionButtonsProps> = ({
  messageContent,
  automationYaml,
  conversationId,
  onSuccess,
  darkMode,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [createdAutomationId, setCreatedAutomationId] = useState<string | null>(null);

  // Detect if message contains CTA prompt
  const hasCTAPrompt = /(?:say|type|enter|use)\s+['"](?:approve|create|yes|go ahead)['"]/i.test(messageContent) ||
    /ready to create/i.test(messageContent);

  // Extract automation YAML from message if not provided
  const extractAutomationYaml = (content: string): string | null => {
    // Use provided YAML if available
    if (automationYaml) {
      return automationYaml;
    }

    // Try to find YAML in code blocks
    const yamlBlockMatch = content.match(/```(?:yaml|yml)?\n([\s\S]*?)```/);
    if (yamlBlockMatch) {
      return yamlBlockMatch[1].trim();
    }

    return null;
  };

  const handleCreateAutomation = async () => {
    if (isCreating || createdAutomationId) return;

    setIsCreating(true);

    try {
      // Prioritize provided automationYaml prop, then try to extract from message
      let yamlToUse = automationYaml || extractAutomationYaml(messageContent);

      if (!yamlToUse) {
        // If we can't extract YAML, send the action as a message to the AI
        // The AI will handle it via the conversation flow
        toast.error('Could not extract automation YAML. Please use the Preview Automation button instead.');
        setIsCreating(false);
        return;
      }

      // Execute create_automation_from_prompt tool call
      const result: ExecuteToolCallResponse = await executeToolCall({
        tool_name: 'create_automation_from_prompt',
        arguments: {
          automation_yaml: yamlToUse,
          conversation_id: conversationId,
        },
      });

      if (result.success && result.automation_id) {
        setCreatedAutomationId(result.automation_id);
        toast.success(`✅ Automation created: ${result.automation_id}`);
        
        if (onSuccess) {
          onSuccess(result.automation_id);
        }
      } else {
        toast.error(result.error || 'Failed to create automation');
      }
    } catch (error) {
      console.error('Failed to create automation:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create automation';
      toast.error(errorMessage);
    } finally {
      setIsCreating(false);
    }
  };

  // Don't render if no CTA prompt detected
  if (!hasCTAPrompt) {
    return null;
  }

  // Don't render if automation already created
  if (createdAutomationId) {
    return (
      <div className={`mt-3 p-3 rounded-lg ${
        darkMode ? 'bg-green-900/30 border border-green-700' : 'bg-green-50 border border-green-200'
      }`}>
        <p className={`text-sm ${darkMode ? 'text-green-300' : 'text-green-700'}`}>
          ✅ Automation created: <code className="text-xs">{createdAutomationId}</code>
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-4"
    >
      <button
        onClick={handleCreateAutomation}
        disabled={isCreating}
        className={`px-6 py-3 rounded-lg text-base font-medium transition-all ${
          darkMode
            ? 'bg-blue-700 text-white hover:bg-blue-600 disabled:bg-blue-800 disabled:opacity-50'
            : 'bg-blue-500 text-white hover:bg-blue-600 disabled:bg-blue-400 disabled:opacity-50'
        } ${isCreating ? 'cursor-not-allowed' : 'cursor-pointer'} shadow-md hover:shadow-lg`}
        aria-label="Create automation"
        aria-busy={isCreating}
        aria-disabled={isCreating || createdAutomationId !== null}
      >
        <span className="mr-2" aria-hidden="true">🚀</span>
        {isCreating ? 'Creating Automation...' : 'Create Automation'}
      </button>
    </motion.div>
  );
};

