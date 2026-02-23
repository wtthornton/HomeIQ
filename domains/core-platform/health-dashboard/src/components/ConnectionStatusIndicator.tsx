/**
 * ConnectionStatusIndicator Component
 * 
 * Displays WebSocket connection status with visual feedback
 * Epic 15.1: Real-Time WebSocket Integration
 */

import React from 'react';

interface ConnectionStatusIndicatorProps {
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error' | 'fallback';
  darkMode?: boolean;
  onReconnect?: () => void;
}

export const ConnectionStatusIndicator: React.FC<ConnectionStatusIndicatorProps> = ({
  connectionState,
  darkMode = false,
  onReconnect
}) => {
  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          icon: '🟢',
          text: 'Live',
          bgColor: darkMode ? 'bg-green-900/30' : 'bg-green-100',
          textColor: darkMode ? 'text-green-400' : 'text-green-700',
          borderColor: darkMode ? 'border-green-500/50' : 'border-green-300',
          pulse: true
        };
      case 'connecting':
        return {
          icon: '🟡',
          text: 'Connecting...',
          bgColor: darkMode ? 'bg-yellow-900/30' : 'bg-yellow-100',
          textColor: darkMode ? 'text-yellow-400' : 'text-yellow-700',
          borderColor: darkMode ? 'border-yellow-500/50' : 'border-yellow-300',
          pulse: true
        };
      case 'disconnected':
        return {
          icon: '⚪',
          text: 'Disconnected',
          bgColor: darkMode ? 'bg-gray-700' : 'bg-gray-100',
          textColor: darkMode ? 'text-gray-400' : 'text-gray-600',
          borderColor: darkMode ? 'border-gray-600' : 'border-gray-300',
          pulse: false
        };
      case 'error':
        return {
          icon: '🔴',
          text: 'Error',
          bgColor: darkMode ? 'bg-red-900/30' : 'bg-red-100',
          textColor: darkMode ? 'text-red-400' : 'text-red-700',
          borderColor: darkMode ? 'border-red-500/50' : 'border-red-300',
          pulse: false
        };
      case 'fallback':
        return {
          icon: '🔄',
          text: 'Polling',
          bgColor: darkMode ? 'bg-blue-900/30' : 'bg-blue-100',
          textColor: darkMode ? 'text-blue-400' : 'text-blue-700',
          borderColor: darkMode ? 'border-blue-500/50' : 'border-blue-300',
          pulse: false
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div 
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${config.bgColor} ${config.borderColor} ${config.textColor} transition-all duration-200`}
      title={`Connection status: ${connectionState}`}
      data-testid="websocket-status"
      data-connected={connectionState === 'connected'}
    >
      <span className={`text-sm ${config.pulse ? 'live-pulse-dot' : ''}`}>
        {config.icon}
      </span>
      <span className="text-xs font-medium hidden sm:inline">
        {config.text}
      </span>
      
      {/* Reconnect button for disconnected/error states */}
      {(connectionState === 'disconnected' || connectionState === 'error' || connectionState === 'fallback') && onReconnect && (
        <button
          onClick={onReconnect}
          className={`ml-1 text-xs px-2 py-0.5 rounded transition-colors duration-200 ${
            darkMode 
              ? 'bg-gray-600 hover:bg-gray-500 text-white' 
              : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
          }`}
          aria-label="Reconnect WebSocket"
        >
          Retry
        </button>
      )}
    </div>
  );
};

