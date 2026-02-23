/**
 * SessionTraceViewer — Full session trace viewer for evaluated sessions
 * E4.S7: Conversation timeline, tool calls, evaluation results
 */

import React, { useState } from 'react';

export interface TraceToolCall {
  tool_name: string;
  parameters: Record<string, any>;
  result: any;
  sequence_index: number;
  turn_index: number;
  latency_ms: number | null;
}

export interface TraceMessage {
  role: 'user' | 'agent';
  content: string;
  turn_index: number;
  timestamp?: string;
  tool_calls?: TraceToolCall[];
}

export interface TraceEvalResult {
  evaluator_name: string;
  level: string;
  score: number;
  label: string;
  explanation: string;
  passed: boolean;
}

export interface SessionTraceData {
  session_id: string;
  agent_name: string;
  timestamp: string;
  messages: TraceMessage[];
  evaluations: TraceEvalResult[];
}

interface SessionTraceViewerProps {
  trace: SessionTraceData | null;
  onClose?: () => void;
  darkMode: boolean;
}

const JsonBlock: React.FC<{ data: any; darkMode: boolean }> = ({ data, darkMode }) => {
  const [expanded, setExpanded] = useState(false);
  const json = JSON.stringify(data, null, 2);
  const preview = json.length > 80 ? json.slice(0, 80) + '...' : json;

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className={`text-xs font-mono px-2 py-1 rounded ${
          darkMode ? 'bg-gray-800 text-gray-400 hover:bg-gray-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        } transition-colors`}
      >
        {expanded ? 'Collapse' : 'Expand'} JSON
      </button>
      <pre className={`mt-1 text-xs font-mono overflow-x-auto p-2 rounded ${
        darkMode ? 'bg-gray-900 text-gray-300' : 'bg-gray-50 text-gray-700'
      }`}>
        {expanded ? json : preview}
      </pre>
    </div>
  );
};

export const SessionTraceViewer: React.FC<SessionTraceViewerProps> = ({
  trace,
  onClose,
  darkMode,
}) => {
  if (!trace) {
    return (
      <div className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
        Select a session to view its trace.
      </div>
    );
  }

  const copyTrace = () => {
    navigator.clipboard.writeText(JSON.stringify(trace, null, 2));
  };

  return (
    <div className={`rounded-lg border ${darkMode ? 'border-gray-700 bg-gray-800/50' : 'border-gray-200 bg-white'}`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${
        darkMode ? 'border-gray-700' : 'border-gray-200'
      }`}>
        <div>
          <h3 className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Session Trace
          </h3>
          <p className={`text-xs font-mono ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
            {trace.session_id}
          </p>
          <p className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
            {trace.agent_name} &middot; {new Date(trace.timestamp).toLocaleString()}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={copyTrace}
            className={`text-xs px-3 py-1.5 rounded ${
              darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            } transition-colors`}
          >
            Copy JSON
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className={`text-xs px-3 py-1.5 rounded ${
                darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              } transition-colors`}
            >
              Close
            </button>
          )}
        </div>
      </div>

      {/* Conversation Timeline */}
      <div className="p-4 space-y-4 max-h-[500px] overflow-y-auto">
        {trace.messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-lg p-3 ${
              msg.role === 'user'
                ? darkMode ? 'bg-blue-900/40 border border-blue-700/50' : 'bg-blue-50 border border-blue-200'
                : darkMode ? 'bg-gray-700/50 border border-gray-600/50' : 'bg-gray-50 border border-gray-200'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-xs font-medium ${
                  msg.role === 'user'
                    ? 'text-blue-400'
                    : darkMode ? 'text-green-400' : 'text-green-600'
                }`}>
                  {msg.role === 'user' ? 'User' : 'Agent'}
                </span>
                <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                  Turn {msg.turn_index}
                </span>
              </div>
              <p className={`text-sm whitespace-pre-wrap ${
                darkMode ? 'text-gray-200' : 'text-gray-800'
              }`}>
                {msg.content}
              </p>

              {/* Tool calls within this turn */}
              {msg.tool_calls && msg.tool_calls.length > 0 && (
                <div className="mt-3 space-y-2">
                  {msg.tool_calls.map((tc, j) => (
                    <div
                      key={j}
                      className={`rounded p-2 ${
                        darkMode ? 'bg-gray-800/80 border border-gray-600/30' : 'bg-white border border-gray-200'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className={`text-xs font-mono font-medium ${
                          darkMode ? 'text-purple-400' : 'text-purple-600'
                        }`}>
                          {tc.tool_name}
                        </span>
                        {tc.latency_ms !== null && (
                          <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                            {tc.latency_ms.toFixed(0)}ms
                          </span>
                        )}
                      </div>
                      <div className="space-y-1">
                        <div>
                          <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                            Parameters:
                          </span>
                          <JsonBlock data={tc.parameters} darkMode={darkMode} />
                        </div>
                        {tc.result !== null && tc.result !== undefined && (
                          <div>
                            <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                              Result:
                            </span>
                            <JsonBlock data={tc.result} darkMode={darkMode} />
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Evaluation Results */}
      {trace.evaluations.length > 0 && (
        <div className={`p-4 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h4 className={`text-sm font-semibold mb-3 ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>
            Evaluation Results
          </h4>
          <div className="space-y-2">
            {trace.evaluations.map((ev, i) => (
              <div
                key={i}
                className={`flex items-start gap-3 p-2 rounded ${
                  darkMode ? 'bg-gray-800/50' : 'bg-gray-50'
                }`}
              >
                <span className={`shrink-0 px-1.5 py-0.5 rounded text-xs font-medium ${
                  ev.passed
                    ? 'bg-green-500/20 text-green-500'
                    : 'bg-red-500/20 text-red-500'
                }`}>
                  {ev.passed ? 'PASS' : 'FAIL'}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-medium ${darkMode ? 'text-gray-200' : 'text-gray-800'}`}>
                      {ev.evaluator_name}
                    </span>
                    <span className={`text-xs font-mono ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                      {ev.level}
                    </span>
                    <span className={`text-sm font-bold ${
                      ev.passed ? 'text-green-500' : 'text-red-500'
                    }`}>
                      {(ev.score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {ev.explanation && (
                    <p className={`text-xs mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      {ev.explanation}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
