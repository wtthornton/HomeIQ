/**
 * CTA Action Buttons Component
 * 
 * Displays an interactive "Create Automation" button
 * to replace text prompts for automation approval
 */

import React, { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import { executeToolCall, type ExecuteToolCallResponse } from '../../services/haAiAgentApi';

interface CTAActionButtonsProps {
  messageContent: string;
  automationYaml?: string;
  conversationId: string;
  originalUserPrompt?: string; // Optional: original user prompt from conversation
  onSuccess?: (automationId: string) => void;
  darkMode: boolean;
}

export const CTAActionButtons: React.FC<CTAActionButtonsProps> = ({
  messageContent,
  automationYaml,
  conversationId: _conversationId,
  originalUserPrompt,
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

  // Extract alias from YAML (similar to AutomationPreview)
  const extractAliasFromYaml = (yaml: string): string | null => {
    if (!yaml || !yaml.trim()) return null;
    
    const cleanYaml = yaml.replace(/```yaml\n?/g, '').replace(/```\n?/g, '').trim();
    
    // Try multiple patterns to extract alias
    // Pattern 1: alias: "value" or alias: 'value'
    let aliasMatch = cleanYaml.match(/alias:\s*['"]([^'"]+)['"]/i);
    if (aliasMatch) return aliasMatch[1].trim();
    
    // Pattern 2: alias: value (without quotes, but may have trailing colon or newline)
    aliasMatch = cleanYaml.match(/alias:\s*([^\n:]+?)(?:\s*$|\s*#|\s*\n)/i);
    if (aliasMatch) {
      const extracted = aliasMatch[1].trim();
      // Only return if it's not empty and doesn't look like a YAML structure
      if (extracted && !extracted.startsWith('{') && !extracted.startsWith('[')) {
        return extracted;
      }
    }
    
    // Pattern 3: alias: value (more permissive, captures until newline or comment)
    aliasMatch = cleanYaml.match(/alias:\s*([^\n#]+)/i);
    if (aliasMatch) {
      const extracted = aliasMatch[1].trim();
      if (extracted) return extracted;
    }
    
    return null;
  };

  // Extract description from YAML (for user_prompt fallback)
  const extractDescriptionFromYaml = (yaml: string): string | null => {
    if (!yaml || !yaml.trim()) return null;
    
    const cleanYaml = yaml.replace(/```yaml\n?/g, '').replace(/```\n?/g, '').trim();
    
    // Try multiple patterns to extract description
    // Pattern 1: description: "value" or description: 'value'
    let descMatch = cleanYaml.match(/description:\s*['"]([^'"]+)['"]/i);
    if (descMatch) return descMatch[1].trim();
    
    // Pattern 2: description: value (without quotes)
    descMatch = cleanYaml.match(/description:\s*([^\n:]+?)(?:\s*$|\s*#|\s*\n)/i);
    if (descMatch) {
      const extracted = descMatch[1].trim();
      if (extracted && !extracted.startsWith('{') && !extracted.startsWith('[')) {
        return extracted;
      }
    }
    
    // Pattern 3: description: value (more permissive)
    descMatch = cleanYaml.match(/description:\s*([^\n#]+)/i);
    if (descMatch) {
      const extracted = descMatch[1].trim();
      if (extracted) return extracted;
    }
    
    return null;
  };

  // Compute YAML availability at render time
  const yamlToUse = automationYaml || extractAutomationYaml(messageContent);
  const hasYaml = !!yamlToUse;

  // Memoize alias extraction to avoid repeated regex calls
  const extractedAlias = useMemo(() => {
    return yamlToUse ? extractAliasFromYaml(yamlToUse) : null;
  }, [yamlToUse]);

  const handleCreateAutomation = async () => {
    if (isCreating || createdAutomationId || !hasYaml || !yamlToUse) return;

    // Use memoized alias
    const alias = extractedAlias;
    
    // Extract description from YAML (only when needed)
    const description = extractDescriptionFromYaml(yamlToUse);
    
    // Determine user_prompt: use originalUserPrompt prop, or description from YAML, or alias as fallback
    const userPrompt = originalUserPrompt?.trim() || description?.trim() || alias?.trim() || 'Automation creation request';
    
    // Validate required fields with strict checks (not just truthy, but non-empty strings)
    if (!alias || !alias.trim()) {
      toast.error('Automation alias is required. Please ensure the YAML contains an "alias" field.');
      return;
    }

    if (!yamlToUse || !yamlToUse.trim()) {
      toast.error('Automation YAML is required. Please preview the automation first.');
      return;
    }

    if (!userPrompt || !userPrompt.trim()) {
      toast.error('User prompt is required.');
      return;
    }

    // Log for debugging (remove in production if needed)
    console.log('[CTAActionButtons] Creating automation with:', {
      alias: alias.trim(),
      userPrompt: userPrompt.trim(),
      yamlLength: yamlToUse.trim().length,
    });

    setIsCreating(true);

    try {
      // Execute create_automation_from_prompt tool call with all required fields
      // Ensure all values are trimmed and non-empty
      const result: ExecuteToolCallResponse = await executeToolCall({
        tool_name: 'create_automation_from_prompt',
        arguments: {
          user_prompt: userPrompt.trim(),
          automation_yaml: yamlToUse.trim(),
          alias: alias.trim(),
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
        disabled={isCreating || !hasYaml || !extractedAlias}
        className={`px-6 py-3 rounded-lg text-base font-medium transition-all ${
          darkMode
            ? hasYaml && extractedAlias
              ? 'bg-blue-700 text-white hover:bg-blue-600 disabled:bg-blue-800 disabled:opacity-50'
              : 'bg-gray-700 text-gray-400 cursor-not-allowed'
            : hasYaml && extractedAlias
            ? 'bg-blue-500 text-white hover:bg-blue-600 disabled:bg-blue-400 disabled:opacity-50'
            : 'bg-gray-300 text-gray-500 cursor-not-allowed'
        } ${isCreating || !hasYaml || !extractedAlias ? 'cursor-not-allowed' : 'cursor-pointer'} shadow-md hover:shadow-lg`}
        aria-label="Create automation"
        aria-busy={isCreating}
        aria-disabled={isCreating || createdAutomationId !== null || !hasYaml || !extractedAlias}
        title={!hasYaml ? 'Preview automation first to generate YAML' : !extractedAlias ? 'YAML must contain an "alias" field' : undefined}
      >
        <span className="mr-2" aria-hidden="true">🚀</span>
        {isCreating ? 'Creating Automation...' : !hasYaml ? 'Create Automation (Preview first)' : !extractedAlias ? 'Create Automation (Missing alias)' : 'Create Automation'}
      </button>
      {!hasYaml && (
        <p className={`mt-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
          ⚠️ Preview the automation first to generate YAML
        </p>
      )}
    </motion.div>
  );
};

