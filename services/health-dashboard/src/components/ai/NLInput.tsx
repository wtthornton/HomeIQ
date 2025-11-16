/**
 * Natural Language Input Component
 * Story AI1.22: Simple Dashboard Integration
 * 
 * Allows users to create automations from natural language requests.
 */

import React, { useState } from 'react';
import { aiApi } from '../../services/api';

interface Props {
  darkMode: boolean;
  onSuccess: () => void;
}

export const NLInput: React.FC<Props> = ({ darkMode, onSuccess }) => {
  const [request, setRequest] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | '' }>({ text: '', type: '' });

  const examples = [
    'Turn on kitchen light at 7 AM on weekdays',
    'Turn off heater when window opens for 10 minutes',
    'Send notification when front door left open 5 minutes',
    'Close blinds at sunset'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (request.length < 10) {
      setMessage({ text: 'Request must be at least 10 characters', type: 'error' });
      return;
    }

    setLoading(true);
    setMessage({ text: '', type: '' });

    try {
      const data = await aiApi.generateNaturalLanguageAutomation(request);

      if (data.success) {
        setMessage({ 
          text: `✅ Automation created! "${data.automation.title}" - Review below to approve.`, 
          type: 'success' 
        });
        setRequest('');
        // Refresh parent suggestions list
        onSuccess();
      } else {
        setMessage({ 
          text: `❌ Failed to generate: ${data.error || 'Unknown error'}`, 
          type: 'error' 
        });
      }
    } catch (error) {
      console.error('NL generation error:', error);
      setMessage({ 
        text: `❌ Error: ${error instanceof Error ? error.message : 'Unknown error'}`, 
        type: 'error' 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`p-6 rounded-lg border ${
      darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-300'
    }`}>
      <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        ✨ Create Automation from Natural Language
      </h3>
      
      <p className={`text-sm mb-4 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
        Describe what you want your automation to do in plain English. AI will generate it for you!
      </p>

      <form onSubmit={handleSubmit} className="space-y-3">
        <textarea
          value={request}
          onChange={(e) => setRequest(e.target.value)}
          placeholder="E.g., Turn on living room lights when motion detected after sunset"
          className={`w-full px-4 py-3 rounded-lg border ${
            darkMode
              ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400'
              : 'bg-white border-gray-300 text-gray-900 placeholder-gray-500'
          } focus:outline-none focus:ring-2 focus:ring-blue-500`}
          rows={3}
          disabled={loading}
        />

        <div className="flex items-center justify-between">
          <span className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            {request.length} characters (min 10)
          </span>
          <button
            type="submit"
            disabled={loading || request.length < 10}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
          >
            {loading ? '⏳ Generating...' : '✨ Generate Automation'}
          </button>
        </div>
      </form>

      {/* Message Display */}
      {message.text && (
        <div className={`mt-3 p-3 rounded text-sm ${
          message.type === 'success'
            ? (darkMode ? 'bg-green-900/30 text-green-300 border border-green-700' : 'bg-green-100 text-green-700 border border-green-300')
            : (darkMode ? 'bg-red-900/30 text-red-300 border border-red-700' : 'bg-red-100 text-red-700 border border-red-300')
        }`}>
          {message.text}
        </div>
      )}

      {/* Example Requests */}
      <div className="mt-4">
        <h4 className={`text-sm font-medium mb-2 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Example requests:
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {examples.map((example, idx) => (
            <button
              key={idx}
              onClick={() => setRequest(example)}
              disabled={loading}
              className={`p-2 rounded text-left text-xs transition-colors ${
                darkMode
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              } disabled:opacity-50`}
            >
              {example}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

