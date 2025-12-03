/**
 * Automation Preview Component
 * Epic AI-20 Story AI20.10: Automation Preview & Creation
 * 
 * Displays automation YAML with syntax highlighting and allows creation/editing
 */

import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ToolCall } from '../../services/haAiAgentApi';
import { executeToolCall } from '../../services/haAiAgentApi';
import toast from 'react-hot-toast';

interface AutomationPreviewProps {
  automationYaml: string;
  alias?: string;
  toolCall?: ToolCall;
  darkMode: boolean;
  onClose: () => void;
  onEdit?: (yaml: string) => void;
  conversationId: string;
}

interface ParsedAutomation {
  alias?: string;
  description?: string;
  entities: string[];
  trigger?: Record<string, unknown>;
  action?: Record<string, unknown>;
}

export const AutomationPreview: React.FC<AutomationPreviewProps> = ({
  automationYaml,
  alias: providedAlias,
  toolCall,
  darkMode,
  onClose,
  onEdit,
  conversationId,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [createdAutomationId, setCreatedAutomationId] = useState<string | null>(null);

  // Parse automation YAML to extract metadata (using regex since YAML isn't JSON)
  const parsedAutomation = useMemo<ParsedAutomation>(() => {
    const cleanYaml = automationYaml.replace(/```yaml\n?/g, '').replace(/```\n?/g, '').trim();
    const entities: string[] = [];
    
    // Extract alias
    const aliasMatch = cleanYaml.match(/alias:\s*['"]?([^'\n"]+)['"]?/i);
    const alias = aliasMatch ? aliasMatch[1] : providedAlias;
    
    // Extract description
    const descMatch = cleanYaml.match(/description:\s*['"]?([^'\n"]+)['"]?/i);
    const description = descMatch ? descMatch[1] : undefined;
    
    // Extract entities from entity_id patterns
    const entityMatches = cleanYaml.matchAll(/entity_id:\s*['"]?([^'\n"]+)['"]?/gi);
    for (const match of entityMatches) {
      if (match[1]) {
        entities.push(match[1]);
      }
    }
    
    // Also check for target.entity_id patterns
    const targetEntityMatches = cleanYaml.matchAll(/target:\s*\n\s*entity_id:\s*['"]?([^'\n"]+)['"]?/gi);
    for (const match of targetEntityMatches) {
      if (match[1]) {
        entities.push(match[1]);
      }
    }

    return {
      alias,
      description,
      entities: [...new Set(entities)], // Remove duplicates
    };
  }, [automationYaml, providedAlias]);

  // Clean YAML for display (remove markdown code blocks)
  const cleanYaml = useMemo(() => {
    return automationYaml
      .replace(/```yaml\n?/g, '')
      .replace(/```\n?/g, '')
      .trim();
  }, [automationYaml]);

  const handleCreateAutomation = async () => {
    if (!parsedAutomation.alias) {
      toast.error('Automation alias is required');
      return;
    }

    setIsCreating(true);
    try {
      // Execute create_automation tool call
      const result = await executeToolCall({
        tool_name: 'create_automation',
        arguments: {
          automation_yaml: cleanYaml,
          alias: parsedAutomation.alias,
        },
      });

      if (result.success) {
        setCreatedAutomationId(result.automation_id || null);
        toast.success(`Automation "${parsedAutomation.alias}" created successfully!`, {
          icon: '✅',
        });
      } else {
        toast.error(result.error || 'Failed to create automation', {
          icon: '❌',
        });
      }
    } catch (error) {
      console.error('Failed to create automation:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to create automation';
      toast.error(errorMessage, {
        icon: '❌',
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleEdit = () => {
    if (onEdit) {
      onEdit(cleanYaml);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.9, opacity: 0, y: 20 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={`rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col ${
            darkMode ? 'bg-gray-800' : 'bg-white'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div
            className={`px-6 py-4 border-b flex items-center justify-between ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
          >
            <div>
              <h2 className={`text-xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                ⚙️ Automation Preview
              </h2>
              {parsedAutomation.alias && (
                <p className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {parsedAutomation.alias}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className={`p-2 rounded-md transition-colors ${
                darkMode ? 'text-gray-400 hover:bg-gray-700' : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              ✕
            </button>
          </div>

          {/* Metadata */}
          {parsedAutomation.description && (
            <div className={`px-6 py-3 border-b ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <span className="font-medium">Description:</span> {parsedAutomation.description}
              </p>
            </div>
          )}

          {parsedAutomation.entities.length > 0 && (
            <div className={`px-6 py-3 border-b ${darkMode ? 'border-gray-700 bg-gray-750' : 'border-gray-200 bg-gray-50'}`}>
              <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                <span className="font-medium">Entities:</span>{' '}
                {parsedAutomation.entities.join(', ')}
              </p>
            </div>
          )}

          {/* YAML Content */}
          <div className="flex-1 overflow-auto p-6">
            <div className="rounded-lg overflow-hidden border border-gray-300">
              <SyntaxHighlighter
                language="yaml"
                style={darkMode ? vscDarkPlus : vs}
                customStyle={{
                  margin: 0,
                  padding: '1rem',
                  fontSize: '0.875rem',
                  lineHeight: '1.5',
                }}
                showLineNumbers
              >
                {cleanYaml}
              </SyntaxHighlighter>
            </div>
          </div>

          {/* Footer Actions */}
          <div
            className={`px-6 py-4 border-t flex items-center justify-between gap-3 ${
              darkMode ? 'border-gray-700' : 'border-gray-200'
            }`}
          >
            <div className="flex gap-2">
              {onEdit && (
                <button
                  onClick={handleEdit}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    darkMode
                      ? 'bg-gray-700 text-white hover:bg-gray-600'
                      : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                  }`}
                >
                  Edit
                </button>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  darkMode
                    ? 'bg-gray-700 text-white hover:bg-gray-600'
                    : 'bg-gray-200 text-gray-900 hover:bg-gray-300'
                }`}
              >
                Cancel
              </button>
              {!createdAutomationId ? (
                <button
                  onClick={handleCreateAutomation}
                  disabled={isCreating || !parsedAutomation.alias}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    isCreating || !parsedAutomation.alias
                      ? 'bg-gray-400 cursor-not-allowed'
                      : darkMode
                      ? 'bg-blue-600 text-white hover:bg-blue-700'
                      : 'bg-blue-500 text-white hover:bg-blue-600'
                  }`}
                >
                  {isCreating ? 'Creating...' : 'Create Automation'}
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className={`text-sm ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                    ✅ Created
                  </span>
                  {createdAutomationId && (
                    <a
                      href={`/deployed#${createdAutomationId}`}
                      className={`text-sm underline ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}
                    >
                      View Automation
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

