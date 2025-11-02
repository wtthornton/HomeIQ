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

export const ContextIndicator: React.FC<ContextIndicatorProps> = ({ context, darkMode: _darkMode }) => {
  // Don't show if no context
  if (context.mentioned_devices.length === 0 && context.active_suggestions.length === 0) {
    return null;
  }
  
  return (
    <div className="border-t px-4 py-2 text-xs" style={{
      borderColor: 'rgba(51, 65, 85, 0.5)',
      background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.95) 100%)',
      backdropFilter: 'blur(12px)'
    }}>
      <div className="flex items-center gap-4 flex-wrap">
        <span className="font-medium" style={{ color: '#cbd5e1' }}>
          🎛️ CONTEXT:
        </span>
        
        {context.mentioned_devices.length > 0 && (
          <span style={{ color: '#94a3b8' }}>
            Devices: {context.mentioned_devices.slice(0, 3).join(', ')}
            {context.mentioned_devices.length > 3 && ` +${context.mentioned_devices.length - 3}`}
          </span>
        )}
        
        {context.active_suggestions.length > 0 && (
          <span style={{ color: '#94a3b8' }}>
            {context.active_suggestions.length} active suggestion{context.active_suggestions.length > 1 ? 's' : ''}
          </span>
        )}
        
        <span style={{ color: '#64748b' }}>
          {context.mentioned_devices.length} mention{context.mentioned_devices.length !== 1 ? 's' : ''} in this conversation
        </span>
      </div>
    </div>
  );
};
