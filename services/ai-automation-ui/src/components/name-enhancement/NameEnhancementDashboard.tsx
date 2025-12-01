/**
 * Name Enhancement Dashboard
 * 
 * Main dashboard for reviewing and managing device name suggestions.
 */

import React, { useEffect, useState } from 'react';
import toast from 'react-hot-toast';
import { useAppStore } from '../../store';
import { NameSuggestionCard } from './NameSuggestionCard';
import api from '../../services/api';

interface DeviceSuggestion {
  device_id: string;
  current_name: string;
  suggestions: Array<{
    name: string;
    confidence: number;
    source: string;
    reasoning: string | null;
  }>;
}

export const NameEnhancementDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  const [devices, setDevices] = useState<DeviceSuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPendingSuggestions();
  }, []);

  const loadPendingSuggestions = async () => {
    try {
      setLoading(true);
      // Get pending suggestions from bulk endpoint
      const DEVICE_INTELLIGENCE_API = import.meta.env.VITE_DEVICE_INTELLIGENCE_API || 'http://localhost:8019';
      const response = await fetch(`${DEVICE_INTELLIGENCE_API}/api/name-enhancement/devices/pending?limit=100`);
      
      if (!response.ok) {
        throw new Error('Failed to load pending suggestions');
      }
      
      const data = await response.json();
      setDevices(data.devices || []);
    } catch (error) {
      toast.error(`Failed to load suggestions: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAccept = async (deviceId: string, suggestedName: string) => {
    try {
      await api.acceptNameSuggestion(deviceId, suggestedName, false);
      // Reload suggestions
      await loadPendingSuggestions();
    } catch (error) {
      toast.error(`Failed to accept suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleReject = async (deviceId: string, suggestedName: string) => {
    try {
      await api.rejectNameSuggestion(deviceId, suggestedName);
      // Reload suggestions
      await loadPendingSuggestions();
    } catch (error) {
      toast.error(`Failed to reject suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleBatchEnhance = async (useAI: boolean = false) => {
    try {
      const result = await api.batchEnhanceNames(null, useAI, false);
      toast.success(`Batch enhancement started: ${result.job_id}`);
      
      // Reload after a delay
      setTimeout(() => {
        loadPendingSuggestions();
      }, 5000);
    } catch (error) {
      toast.error(`Failed to start batch enhancement: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const bgColor = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const textColor = darkMode ? 'text-gray-100' : 'text-gray-900';

  return (
    <div className={`min-h-screen ${bgColor} p-6`}>
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className={`${textColor} text-3xl font-bold mb-2`}>Device Name Enhancement</h1>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              Review and accept human-readable name suggestions for your devices
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => handleBatchEnhance(false)}
              className={`px-4 py-2 rounded-xl font-medium transition-all ${
                darkMode
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
              }`}
            >
              Batch Enhance (Pattern)
            </button>
            <button
              onClick={() => handleBatchEnhance(true)}
              className={`px-4 py-2 rounded-xl font-medium transition-all ${
                darkMode
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg shadow-purple-500/30'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg shadow-purple-400/30'
              }`}
            >
              Batch Enhance (AI)
            </button>
          </div>
        </div>

        {loading ? (
          <div className={`${textColor} text-center py-12`}>Loading suggestions...</div>
        ) : devices.length === 0 ? (
          <div className={`${darkMode 
            ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
            : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          } rounded-xl p-8 text-center ${textColor}`}>
            <p className="text-lg mb-2">No pending name suggestions</p>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'} text-sm`}>
              All devices have been reviewed or no suggestions are available yet.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {devices.map((device) => (
              <NameSuggestionCard
                key={device.device_id}
                deviceId={device.device_id}
                currentName={device.current_name}
                suggestions={device.suggestions}
                onAccept={handleAccept}
                onReject={handleReject}
                darkMode={darkMode}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

