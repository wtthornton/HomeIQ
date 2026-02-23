/**
 * Tool Call Indicator Component
 * Epic AI-20 Story AI20.9: Tool Call Visualization
 * 
 * Displays tool calls made by the agent with expandable details
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ToolCall } from '../../services/haAiAgentApi';

interface ToolCallIndicatorProps {
  toolCalls: ToolCall[];
  responseTimeMs?: number;
  darkMode: boolean;
}

export const ToolCallIndicator: React.FC<ToolCallIndicatorProps> = ({
  toolCalls,
  responseTimeMs,
  darkMode,
}) => {
  const [expandedCall, setExpandedCall] = useState<string | null>(null);

  if (!toolCalls || toolCalls.length === 0) {
    return null;
  }

  const toggleExpand = (callId: string) => {
    setExpandedCall(expandedCall === callId ? null : callId);
  };

  // Get tool icon based on tool name
  const getToolIcon = (toolName: string): string => {
    const name = toolName.toLowerCase();
    if (name.includes('light') || name.includes('switch')) return '💡';
    if (name.includes('climate') || name.includes('temperature')) return '🌡️';
    if (name.includes('lock') || name.includes('door')) return '🔒';
    if (name.includes('camera')) return '📷';
    if (name.includes('media')) return '📺';
    if (name.includes('automation')) return '⚙️';
    if (name.includes('scene')) return '🎬';
    return '🔧';
  };

  // Format tool name for display
  const formatToolName = (toolName: string): string => {
    // Convert snake_case to Title Case
    return toolName
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  // Format arguments for display
  const formatArguments = (args: Record<string, any>): string => {
    try {
      return JSON.stringify(args, null, 2);
    } catch {
      return String(args);
    }
  };

  return (
    <div className="mt-2 space-y-2">
      {toolCalls.map((toolCall) => {
        const isExpanded = expandedCall === toolCall.id;
        const toolIcon = getToolIcon(toolCall.name);

        return (
          <motion.div
            key={toolCall.id}
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className={`rounded-lg border ${
              darkMode
                ? 'bg-gray-800 border-gray-700'
                : 'bg-blue-50 border-blue-200'
            }`}
          >
            {/* Tool Call Header */}
            <button
              onClick={() => toggleExpand(toolCall.id)}
              className={`w-full px-3 py-2 flex items-center justify-between text-left transition-colors ${
                darkMode ? 'hover:bg-gray-700' : 'hover:bg-blue-100'
              }`}
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-lg">{toolIcon}</span>
                <div className="flex-1 min-w-0">
                  <div className={`font-medium text-sm ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                    {formatToolName(toolCall.name)}
                  </div>
                  <div className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Tool executed
                    {responseTimeMs && (
                      <span className="ml-1">• {responseTimeMs}ms</span>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Success indicator */}
                <div
                  className={`w-2 h-2 rounded-full ${
                    darkMode ? 'bg-green-400' : 'bg-green-500'
                  }`}
                  title="Tool executed successfully"
                />
                <span className={`text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  {isExpanded ? '▼' : '▶'}
                </span>
              </div>
            </button>

            {/* Expanded Details */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                >
                  <div className={`px-3 pb-3 border-t ${darkMode ? 'border-gray-700' : 'border-blue-200'}`}>
                    <div className="mt-2">
                      <div className={`text-xs font-medium mb-1 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                        Arguments:
                      </div>
                      <pre
                        className={`text-xs p-2 rounded overflow-x-auto ${
                          darkMode
                            ? 'bg-gray-900 text-gray-300'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {formatArguments(toolCall.arguments)}
                      </pre>
                    </div>
                    {toolCall.id && (
                      <div className={`mt-2 text-xs ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                        Call ID: <code className="font-mono">{toolCall.id}</code>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        );
      })}
    </div>
  );
};

