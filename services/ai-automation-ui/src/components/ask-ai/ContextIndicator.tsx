/**
 * Context Indicator - Shows active conversation context
 * 
 * Displays:
 * - Mentioned devices
 * - Active suggestions count
 * - Total mentions in conversation
 */

import React from 'react';

interface ConversationContext {
  mentioned_devices: string[];
  mentioned_intents: string[];
  active_suggestions: string[];
  last_query: string;
  last_entities: any[];
}

interface ContextIndicatorProps {
  context: ConversationContext;
  darkMode: boolean;
}

export const ContextIndicator: React.FC<ContextIndicatorProps> = ({ context, darkMode }) => {
  // Don't show if no context
  if (context.mentioned_devices.length === 0 && context.active_suggestions.length === 0) {
    return null;
  }
  
  return (
    <div className={`border-t px-4 py-2 text-xs ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
      <div className="flex items-center gap-4 flex-wrap">
        <span className={`font-medium ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
          🎛️ Context:
        </span>
        
        {context.mentioned_devices.length > 0 && (
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Devices: {context.mentioned_devices.slice(0, 3).join(', ')}
            {context.mentioned_devices.length > 3 && ` +${context.mentioned_devices.length - 3}`}
          </span>
        )}
        
        {context.active_suggestions.length > 0 && (
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {context.active_suggestions.length} active suggestion{context.active_suggestions.length > 1 ? 's' : ''}
          </span>
        )}
        
        <span className={`${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
          {context.mentioned_devices.length} mention{context.mentioned_devices.length !== 1 ? 's' : ''} in this conversation
        </span>
      </div>
    </div>
  );
};
