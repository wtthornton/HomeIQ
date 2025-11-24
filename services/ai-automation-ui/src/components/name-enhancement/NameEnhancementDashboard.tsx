/**
 * Name Enhancement Dashboard
 * 
 * Main dashboard for reviewing and managing device name suggestions.
 */

import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
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
  const [processing, setProcessing] = useState<Set<string>>(new Set());

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
    setProcessing(prev => new Set(prev).add(deviceId));
    try {
      await api.acceptNameSuggestion(deviceId, suggestedName, false);
      // Reload suggestions
      await loadPendingSuggestions();
    } finally {
      setProcessing(prev => {
        const next = new Set(prev);
        next.delete(deviceId);
        return next;
      });
    }
  };

  const handleReject = async (deviceId: string, suggestedName: string) => {
    setProcessing(prev => new Set(prev).add(deviceId));
    try {
      await api.rejectNameSuggestion(deviceId, suggestedName);
      // Reload suggestions
      await loadPendingSuggestions();
    } finally {
      setProcessing(prev => {
        const next = new Set(prev);
        next.delete(deviceId);
        return next;
      });
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
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-blue-600 hover:bg-blue-700 text-white'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              Batch Enhance (Pattern)
            </button>
            <button
              onClick={() => handleBatchEnhance(true)}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                darkMode
                  ? 'bg-purple-600 hover:bg-purple-700 text-white'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              Batch Enhance (AI)
            </button>
          </div>
        </div>

        {loading ? (
          <div className={`${textColor} text-center py-12`}>Loading suggestions...</div>
        ) : devices.length === 0 ? (
          <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg p-8 text-center ${textColor}`}>
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

