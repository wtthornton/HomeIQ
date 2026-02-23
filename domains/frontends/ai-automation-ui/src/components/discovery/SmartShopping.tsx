/**
 * Smart Shopping Component
 * 
 * Displays device purchase recommendations with ROI scores.
 * Uses Dependencies Tab pattern for interactive visualizations.
 * 
 * Epic AI-4, Story AI4.3
 * Memory: Dependencies Tab pattern ID 9810709
 */
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../../store';

interface DeviceRecommendation {
  device_type: string;
  automations_unlocked: number;
  example_use_cases: string[];
  cost_estimate_usd: [number, number];
  roi_score: number;
  compatible_integrations: string[];
  example_automations: Array<{
    title: string;
    quality_score: number;
    use_case: string;
  }>;
}

interface SmartShoppingProps {
  userDevices: string[];
}

export const SmartShopping: React.FC<SmartShoppingProps> = ({ userDevices }) => {
  const { darkMode } = useAppStore();
  const [recommendations, setRecommendations] = useState<DeviceRecommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);

  useEffect(() => {
    if (userDevices.length === 0) return;

    const fetchRecommendations = async () => {
      setLoading(true);
      
      try {
        const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';
        const userDevicesParam = userDevices.join(',');
        // Note: using proxied API endpoint for automation-miner
        const response = await fetch(
          `/api/automation-miner/devices/recommendations?user_devices=${userDevicesParam}&limit=10`,
          {
            headers: {
              'Authorization': `Bearer ${API_KEY}`,
              'X-HomeIQ-API-Key': API_KEY,
            },
          }
        );
        
        if (!response.ok) {
          throw new Error('Failed to fetch recommendations');
        }
        
        const data = await response.json();
        setRecommendations(data || []);
      } catch (error) {
        console.error('Error fetching recommendations:', error);
        setRecommendations([]);
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [userDevices]);

  const getDeviceIcon = (deviceType: string): string => {
    // Simple emoji icons (can be enhanced with icon library)
    const icons: Record<string, string> = {
      motion_sensor: '🚶',
      temperature_sensor: '🌡️',
      humidity_sensor: '💧',
      door_sensor: '🚪',
      window_sensor: '🪟',
      light: '💡',
      switch: '🔌',
      thermostat: '🌡️',
      lock: '🔒',
      camera: '📷',
      plug: '🔌'
    };
    
    return icons[deviceType] || '📦';
  };

  const getRoiColor = (roi: number): string => {
    if (roi >= 3.0) return 'bg-green-500';
    if (roi >= 1.5) return 'bg-yellow-500';
    return 'bg-gray-500';
  };

  const getRoiLabel = (roi: number): string => {
    if (roi >= 3.0) return 'Excellent Value';
    if (roi >= 1.5) return 'Good Value';
    return 'Niche Use Case';
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        <p className="mt-4 text-gray-600">Analyzing device recommendations...</p>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No device recommendations available yet.</p>
        <p className="text-sm mt-2">
          The corpus needs to be populated first. Run: <code className="bg-gray-100 px-2 py-1 rounded">python -m src.cli crawl</code>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* ROI Chart */}
      <div className={`border rounded-xl p-4 backdrop-blur-sm ${
        darkMode
          ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-xl shadow-blue-900/20'
          : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-md shadow-blue-100/50'
      }`}>
        <h3 className="text-lg font-semibold mb-4">ROI Comparison</h3>
        <div className="space-y-2">
          {recommendations.slice(0, 5).map((rec) => (
            <div key={rec.device_type} className="flex items-center gap-4">
              <div className="w-32 text-sm font-medium truncate">
                {rec.device_type.replace('_', ' ')}
              </div>
              <div className="flex-1">
                <div className="w-full bg-gray-200 rounded-full h-6 relative">
                  <div
                    className={`h-6 rounded-full ${getRoiColor(rec.roi_score)} transition-all duration-300`}
                    style={{ width: `${Math.min(100, (rec.roi_score / 5.0) * 100)}%` }}
                  >
                    <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                      ROI: {rec.roi_score.toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
              <div className="w-24 text-sm text-right text-gray-600">
                ${rec.cost_estimate_usd[0]}-${rec.cost_estimate_usd[1]}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Device Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {recommendations.map((rec, idx) => (
          <motion.div
            key={rec.device_type}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            whileHover={{ scale: 1.02 }}
            className={`
              border rounded-xl p-4 cursor-pointer transition-all duration-200 backdrop-blur-sm
              ${selectedDevice === rec.device_type 
                ? darkMode
                  ? 'ring-2 ring-blue-500/50 shadow-2xl shadow-blue-900/20 bg-gradient-to-br from-blue-900/40 to-purple-900/40'
                  : 'ring-2 ring-blue-500/50 shadow-xl shadow-blue-100/50 bg-gradient-to-br from-blue-50 to-purple-50'
                : darkMode
                ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border-blue-500/20 shadow-xl shadow-blue-900/20'
                : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border-blue-200/50 shadow-md shadow-blue-100/50'
              }
            `}
            onClick={() => setSelectedDevice(
              selectedDevice === rec.device_type ? null : rec.device_type
            )}
          >
            {/* Icon and Title */}
            <div className="flex items-center gap-3 mb-3">
              <div className="text-4xl">{getDeviceIcon(rec.device_type)}</div>
              <div>
                <h3 className="font-semibold capitalize">
                  {rec.device_type.replace('_', ' ')}
                </h3>
                <p className="text-sm text-gray-600">
                  {getRoiLabel(rec.roi_score)}
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Automations:</span>
                <span className="font-semibold">{rec.automations_unlocked}</span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">ROI Score:</span>
                <span className={`font-semibold ${rec.roi_score >= 3 ? 'text-green-600' : rec.roi_score >= 1.5 ? 'text-yellow-600' : 'text-gray-600'}`}>
                  {rec.roi_score.toFixed(2)}
                </span>
              </div>
              
              <div className="flex justify-between">
                <span className="text-gray-600">Cost:</span>
                <span className="font-semibold">
                  ${rec.cost_estimate_usd[0]}-${rec.cost_estimate_usd[1]}
                </span>
              </div>
              
              {/* Use Cases */}
              <div className="pt-2 border-t">
                <span className="text-gray-600 text-xs">Use cases:</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {rec.example_use_cases.map((uc) => (
                    <span
                      key={uc}
                      className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs capitalize"
                    >
                      {uc}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* Expanded Details */}
            {selectedDevice === rec.device_type && rec.example_automations.length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm font-medium mb-2">Example Automations:</p>
                <ul className="space-y-2">
                  {rec.example_automations.map((auto, idx) => (
                    <li key={idx} className="text-xs text-gray-700">
                      • {auto.title} <span className="text-gray-500">({(auto.quality_score * 100).toFixed(0)}% quality)</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Instructions */}
      <div className={`border rounded-xl p-4 text-sm backdrop-blur-sm ${
        darkMode
          ? 'bg-blue-900/40 border-blue-700/50'
          : 'bg-blue-50/80 border-blue-200/50'
      }`}>
        <p className="font-semibold text-blue-900 mb-2">How to interpret ROI scores:</p>
        <ul className="space-y-1 text-blue-800">
          <li>• <strong>ROI &gt; 3.0:</strong> Excellent purchase - many high-quality automations, low cost</li>
          <li>• <strong>ROI 1.5-3.0:</strong> Good purchase - decent automation potential</li>
          <li>• <strong>ROI &lt; 1.5:</strong> Niche use case - consider if you have a specific need</li>
        </ul>
      </div>
    </div>
  );
};

