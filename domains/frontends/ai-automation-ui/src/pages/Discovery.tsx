/**
 * Discovery Page
 * 
 * Helps users discover what they can automate with existing devices
 * and provides data-driven device purchase recommendations.
 * 
 * Epic AI-4, Story AI4.3
 */
import React, { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { useAppStore } from '../store';
import { DeviceExplorer } from '../components/discovery/DeviceExplorer';
import { SmartShopping } from '../components/discovery/SmartShopping';

const DEMO_DEVICES = ['light', 'switch', 'sensor'];

interface DiscoveryPageProps {
  // Discovery page component props (currently none)
}

export const DiscoveryPage: React.FC<DiscoveryPageProps> = () => {
  const { darkMode } = useAppStore();
  const [userDevices, setUserDevices] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [demoMode, setDemoMode] = useState(false);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setDemoMode(false);
    try {
      const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';

      // Fetch entities to get unique domains (device types)
      // Note: using proxied API endpoint - data-api has /api/entities, not /api/data/entities
      const entitiesResponse = await fetch('/api/entities?limit=10000', {
        headers: {
          'Authorization': `Bearer ${API_KEY}`,
          'X-HomeIQ-API-Key': API_KEY,
        },
      });
      if (!entitiesResponse.ok) {
        throw new Error('Failed to fetch entities');
      }

      const entitiesData = await entitiesResponse.json();

      // Extract unique domains from entities
      const entities = entitiesData.data?.entities || entitiesData.entities || [];
      const uniqueDomains = Array.from(new Set(entities.map((e: any) => e.domain || e.entity_id?.split('.')[0]).filter(Boolean))) as string[];

      if (uniqueDomains.length > 0) {
        setUserDevices(uniqueDomains);
      } else {
        // Fallback: try to get from devices
        const devicesResponse = await fetch('/api/data/devices', {
          headers: {
            'Authorization': `Bearer ${API_KEY}`,
            'X-HomeIQ-API-Key': API_KEY,
          },
        });
        if (devicesResponse.ok) {
          const devicesData = await devicesResponse.json();
          const deviceDomains = devicesData.data?.devices || devicesData.devices || [];
          if (deviceDomains.length > 0) {
            setUserDevices(deviceDomains.map((d: any) => d.domain || d.type).filter(Boolean));
          } else {
            setUserDevices(DEMO_DEVICES);
            setDemoMode(true);
          }
        } else {
          throw new Error('Failed to fetch devices');
        }
      }
    } catch (err) {
      console.error('Error fetching devices:', err);
      setUserDevices(DEMO_DEVICES);
      setDemoMode(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevices();
  }, [fetchDevices]);

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`mb-8 p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex items-center gap-3 mb-1">
          <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Automation Discovery
          </h1>
        </div>
        <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Discover what you can automate and get smart device recommendations
        </p>
      </motion.div>

      {/* Demo mode banner */}
      {demoMode && !loading && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-xl p-4 mb-6 border ${darkMode ? 'bg-amber-900/30 border-amber-700/50 text-amber-200' : 'bg-amber-50 border-amber-200 text-amber-800'} backdrop-blur-sm`}
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold mb-1">Showing demo devices</p>
              <p className="text-sm">
                Could not connect to your home. Connect your Home Assistant instance to see your real devices.{' '}
                <Link
                  to="/settings"
                  className="underline font-medium hover:opacity-80"
                >
                  Go to Settings
                </Link>
              </p>
            </div>
            <button
              onClick={fetchDevices}
              className={`flex-shrink-0 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                darkMode
                  ? 'bg-amber-700/50 hover:bg-amber-700/70 text-amber-100'
                  : 'bg-amber-200 hover:bg-amber-300 text-amber-900'
              }`}
            >
              Retry
            </button>
          </div>
        </motion.div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-8">
          {[1, 2].map((i) => (
            <div
              key={i}
              className={`rounded-xl p-6 border ${
                darkMode
                  ? 'bg-slate-900/60 border-blue-500/20'
                  : 'bg-white border-blue-200/50'
              }`}
            >
              <div className={`h-6 w-48 rounded mb-4 animate-pulse ${darkMode ? 'bg-slate-700' : 'bg-gray-200'}`} />
              <div className={`h-4 w-72 rounded mb-6 animate-pulse ${darkMode ? 'bg-slate-700' : 'bg-gray-200'}`} />
              <div className={`h-10 w-1/2 rounded-xl animate-pulse ${darkMode ? 'bg-slate-700' : 'bg-gray-200'}`} />
            </div>
          ))}
        </div>
      )}

      {/* Main content */}
      {!loading && (
        <div className="space-y-8">
          {/* Device Explorer Section */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className={`rounded-xl shadow-lg p-6 ${
              darkMode
                ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
                : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
            }`}
          >
            <h2 className={`text-2xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Device Explorer
            </h2>
            <p className={`text-sm mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              See what you can automate with your existing devices
            </p>
            <DeviceExplorer devices={userDevices} demoMode={demoMode} />
          </motion.section>

          {/* Smart Shopping Section */}
          <motion.section
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className={`rounded-xl shadow-lg p-6 ${
              darkMode
                ? 'bg-gradient-to-br from-slate-900/95 via-blue-900/20 to-purple-900/20 border border-blue-500/20 shadow-2xl shadow-blue-900/20 backdrop-blur-sm'
                : 'bg-gradient-to-br from-white via-blue-50/50 to-purple-50/50 border border-blue-200/50 shadow-xl shadow-blue-100/50'
            }`}
          >
            <h2 className={`text-2xl font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              Smart Shopping Recommendations
            </h2>
            <p className={`text-sm mb-6 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              Data-driven device suggestions to unlock new automations
            </p>
            <SmartShopping userDevices={userDevices} />
          </motion.section>
        </div>
      )}
    </div>
  );
};

export default DiscoveryPage;

