/**
 * Device Explorer Component
 * 
 * Allows users to select a device and see what they can automate with it.
 * 
 * Epic AI-4, Story AI4.3
 */
import React, { useState } from 'react';
import { useAppStore } from '../../store';

interface DeviceExplorerProps {
  devices: string[];
}

interface Possibility {
  use_case: string;
  automation_count: number;
  required_devices: string[];
  optional_enhancements: string[];
  difficulty: string;
  avg_quality: number;
}

export const DeviceExplorer: React.FC<DeviceExplorerProps> = ({ devices }) => {
  const { darkMode } = useAppStore();
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [possibilities, setPossibilities] = useState<Possibility[]>([]);
  const [loading, setLoading] = useState(false);

  const handleDeviceSelect = async (device: string) => {
    setSelectedDevice(device);
    
    if (!device) {
      setPossibilities([]);
      return;
    }

    setLoading(true);
    
    try {
      const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';
      const userDevicesParam = devices.join(',');
      // Note: using proxied API endpoint for automation-miner
      const response = await fetch(
        `/api/automation-miner/devices/${device}/possibilities?user_devices=${userDevicesParam}`,
        {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'X-HomeIQ-API-Key': API_KEY,
          },
        }
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch possibilities');
      }
      
      const data = await response.json();
      setPossibilities(data.possibilities || []);
    } catch (error) {
      console.error('Error fetching possibilities:', error);
      setPossibilities([]);
    } finally {
      setLoading(false);
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'low': return 'bg-green-100 text-green-800';
      case 'medium': return 'bg-yellow-100 text-yellow-800';
      case 'high': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-4">
      {/* Device Selector */}
      <div>
        <label className="block text-sm font-medium mb-2">
          Select a device to explore:
        </label>
        <select
          value={selectedDevice}
          onChange={(e) => handleDeviceSelect(e.target.value)}
          className="w-full md:w-1/2 px-4 py-2 border rounded-xl backdrop-blur-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/80 dark:bg-slate-800/60 border-gray-300/50 dark:border-gray-700/50"
        >
          <option value="">-- Choose a device --</option>
          {devices.map((device) => (
            <option key={device} value={device}>
              {device.replace('_', ' ')}
            </option>
          ))}
        </select>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Searching community automations...</p>
        </div>
      )}

      {/* Possibilities */}
      {!loading && selectedDevice && possibilities.length > 0 && (
        <div className="grid gap-4 mt-6">
          <h3 className="text-lg font-semibold">
            What you can automate with {selectedDevice.replace('_', ' ')}:
          </h3>
          
          {possibilities.map((possibility, idx) => (
            <div key={idx} className={`border rounded-xl p-4 hover:shadow-lg transition-all backdrop-blur-sm ${
              darkMode
                ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-xl shadow-blue-900/20'
                : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-md shadow-blue-100/50'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-lg font-medium capitalize">{possibility.use_case}</h4>
                <span className={`px-3 py-1 rounded-full text-sm ${getDifficultyColor(possibility.difficulty)}`}>
                  {possibility.difficulty} difficulty
                </span>
              </div>
              
              <div className="text-sm text-gray-600 space-y-1">
                <p>
                  <strong>{possibility.automation_count}</strong> automations available
                  (avg quality: {(possibility.avg_quality * 100).toFixed(0)}%)
                </p>
                
                {possibility.required_devices.length > 0 && (
                  <p>
                    <strong>You have:</strong> {possibility.required_devices.join(', ')}
                    <span className="ml-2 text-green-600">✓ Can do now!</span>
                  </p>
                )}
                
                {possibility.optional_enhancements.length > 0 && (
                  <p>
                    <strong>Optional:</strong> {possibility.optional_enhancements.join(', ')}
                    <span className="ml-2 text-gray-500">(for enhanced features)</span>
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results */}
      {!loading && selectedDevice && possibilities.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No automations found for {selectedDevice}.</p>
          <p className="text-sm mt-2">Try running the corpus crawl to populate data.</p>
        </div>
      )}
    </div>
  );
};

