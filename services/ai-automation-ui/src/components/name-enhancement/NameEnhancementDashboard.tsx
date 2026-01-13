/**
 * Name Enhancement Dashboard
 * 
 * Main dashboard for reviewing and managing device name suggestions.
 * Enhanced with skeleton loaders, statistics, error handling, and batch operation improvements.
 */

import React, { useEffect, useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { useAppStore } from '../../store';
import { NameSuggestionCard } from './NameSuggestionCard';
import { NameEnhancementSkeleton } from './NameEnhancementSkeleton';
import { BatchEnhanceConfirmDialog } from './BatchEnhanceConfirmDialog';
import { ErrorBanner } from '../ErrorBanner';
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

interface EnhancementStats {
  total_suggestions: number;
  by_status: Record<string, number>;
  by_confidence: {
    high: number;
    medium: number;
    low: number;
  };
}

export const NameEnhancementDashboard: React.FC = () => {
  const { darkMode } = useAppStore();
  const [devices, setDevices] = useState<DeviceSuggestion[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<EnhancementStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [batchEnhancing, setBatchEnhancing] = useState<boolean>(false);
  const [batchJobId, setBatchJobId] = useState<string | null>(null);
  const [showConfirmDialog, setShowConfirmDialog] = useState<boolean>(false);
  const [pendingBatchType, setPendingBatchType] = useState<boolean>(false); // false = Pattern, true = AI

  const loadPendingSuggestions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPendingNameSuggestions(100, 0);
      setDevices(data.devices || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load pending suggestions';
      setError(errorMessage);
      toast.error(errorMessage);
      setDevices([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      setStatsLoading(true);
      const statsData = await api.getEnhancementStatus();
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load enhancement stats:', err);
      // Don't show error for stats, just log it
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPendingSuggestions();
    loadStats();
  }, [loadPendingSuggestions, loadStats]);

  // Handle batch enhancement completion
  useEffect(() => {
    if (!batchJobId) return;

    // Reload after batch operation completes (5 second delay)
    // In a production system, you'd poll the job status endpoint
    const reloadTimer = setTimeout(() => {
      loadPendingSuggestions();
      loadStats();
      setBatchJobId(null);
      setBatchEnhancing(false);
    }, 5000);

    return () => clearTimeout(reloadTimer);
  }, [batchJobId, loadPendingSuggestions, loadStats]);

  const handleAccept = async (deviceId: string, suggestedName: string) => {
    try {
      await api.acceptNameSuggestion(deviceId, suggestedName, false);
      await loadPendingSuggestions();
      await loadStats(); // Refresh stats after accepting
    } catch (error) {
      toast.error(`Failed to accept suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleReject = async (deviceId: string, suggestedName: string) => {
    try {
      await api.rejectNameSuggestion(deviceId, suggestedName);
      await loadPendingSuggestions();
      await loadStats(); // Refresh stats after rejecting
    } catch (error) {
      toast.error(`Failed to reject suggestion: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleBatchEnhanceClick = (useAI: boolean = false) => {
    setPendingBatchType(useAI);
    setShowConfirmDialog(true);
  };

  const handleBatchEnhance = async (useAI: boolean = false) => {
    setShowConfirmDialog(false);
    try {
      setBatchEnhancing(true);
      setError(null);
      const result = await api.batchEnhanceNames(null, useAI, false);
      toast.success(`Batch enhancement started: ${result.job_id}`);
      setBatchJobId(result.job_id);
      // Reload handled by useEffect when batchJobId is set
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setError(`Failed to start batch enhancement: ${errorMessage}`);
      toast.error(errorMessage);
      setBatchEnhancing(false);
    }
  };

  const handleCancelBatchEnhance = () => {
    setShowConfirmDialog(false);
    setPendingBatchType(false);
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
              onClick={() => handleBatchEnhanceClick(false)}
              disabled={batchEnhancing}
              className={`px-4 py-2 rounded-xl font-medium transition-all flex items-center gap-2 ${
                batchEnhancing
                  ? 'bg-gray-400 cursor-not-allowed text-white'
                  : darkMode
                  ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                  : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
              }`}
            >
              {batchEnhancing ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <span>🔍</span>
                  Batch Enhance (Pattern)
                </>
              )}
            </button>
            <button
              onClick={() => handleBatchEnhanceClick(true)}
              disabled={batchEnhancing}
              className={`px-4 py-2 rounded-xl font-medium transition-all flex items-center gap-2 ${
                batchEnhancing
                  ? 'bg-gray-400 cursor-not-allowed text-white'
                  : darkMode
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg shadow-purple-500/30'
                  : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg shadow-purple-400/30'
              }`}
            >
              {batchEnhancing ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Processing...
                </>
              ) : (
                <>
                  <span>🤖</span>
                  Batch Enhance (AI)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Statistics Section */}
        {!statsLoading && stats && (
          <div className={`grid grid-cols-2 md:grid-cols-4 gap-4 mb-6`}>
            <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800' : 'bg-white'} shadow-lg`}>
              <div className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                {stats.total_suggestions || 0}
              </div>
              <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Total Suggestions
              </div>
            </div>
            <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800' : 'bg-white'} shadow-lg`}>
              <div className="text-2xl font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                {stats.by_confidence.high || 0}
              </div>
              <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                High Confidence
              </div>
            </div>
            <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800' : 'bg-white'} shadow-lg`}>
              <div className="text-2xl font-bold bg-gradient-to-r from-yellow-600 to-orange-600 bg-clip-text text-transparent">
                {stats.by_confidence.medium || 0}
              </div>
              <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Medium Confidence
              </div>
            </div>
            <div className={`p-4 rounded-xl ${darkMode ? 'bg-slate-800' : 'bg-white'} shadow-lg`}>
              <div className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                {stats.by_confidence.low || 0}
              </div>
              <div className={`text-sm mt-1 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Low Confidence
              </div>
            </div>
          </div>
        )}

        {/* Error Banner */}
        <ErrorBanner
          error={error}
          onRetry={loadPendingSuggestions}
          onDismiss={() => setError(null)}
          variant="banner"
        />

        {/* Loading State */}
        {loading ? (
          <NameEnhancementSkeleton count={3} darkMode={darkMode} />
        ) : devices.length === 0 ? (
          <div className={`${darkMode 
            ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm' 
            : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
          } rounded-xl p-8 text-center ${textColor}`}>
            <div className="text-6xl mb-4">✨</div>
            <h3 className={`text-xl font-bold mb-2 ${textColor}`}>
              No Pending Name Suggestions
            </h3>
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-600'} text-sm mb-2`}>
              All devices have been reviewed or no suggestions are available yet.
            </p>
            <p className={`${darkMode ? 'text-gray-500' : 'text-gray-500'} text-xs mb-6`}>
              Run a batch enhancement to generate new name suggestions for your devices.
            </p>
            {!batchEnhancing && (
              <div className="flex flex-col items-center gap-3 mt-6">
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={() => handleBatchEnhanceClick(false)}
                    className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2 ${
                      darkMode
                        ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white shadow-lg shadow-blue-500/30'
                        : 'bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white shadow-lg shadow-blue-400/30'
                    }`}
                  >
                    <span>🔍</span>
                    <span>Run Batch Enhance (Pattern)</span>
                  </button>
                  <button
                    onClick={() => handleBatchEnhanceClick(true)}
                    className={`px-5 py-2.5 rounded-xl font-medium transition-all flex items-center gap-2 ${
                      darkMode
                        ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white shadow-lg shadow-purple-500/30'
                        : 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white shadow-lg shadow-purple-400/30'
                    }`}
                  >
                    <span>🤖</span>
                    <span>Run Batch Enhance (AI)</span>
                  </button>
                </div>
                <p className={`${darkMode ? 'text-gray-500' : 'text-gray-400'} text-xs mt-2 max-w-md`}>
                  💡 Pattern matching is faster and uses rule-based logic. AI-powered analysis provides more sophisticated suggestions but takes longer.
                </p>
              </div>
            )}
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

        {/* Confirmation Dialog */}
        <BatchEnhanceConfirmDialog
          isOpen={showConfirmDialog}
          useAI={pendingBatchType}
          deviceCount={stats?.total_suggestions}
          onConfirm={() => handleBatchEnhance(pendingBatchType)}
          onCancel={handleCancelBatchEnhance}
          darkMode={darkMode}
        />
      </div>
    </div>
  );
};
