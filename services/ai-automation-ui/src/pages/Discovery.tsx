/**
 * Discovery Page
 * 
 * Helps users discover what they can automate with existing devices
 * and provides data-driven device purchase recommendations.
 * 
 * Epic AI-4, Story AI4.3
 */
import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { useAppStore } from '../store';
import { DeviceExplorer } from '../components/discovery/DeviceExplorer';
import { SmartShopping } from '../components/discovery/SmartShopping';

interface DiscoveryPageProps {}

export const DiscoveryPage: React.FC<DiscoveryPageProps> = () => {
  const { darkMode } = useAppStore();
  const [userDevices, setUserDevices] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch user's device types from entities (domains)
    const fetchDevices = async () => {
      try {
        const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';
        
        // Fetch entities to get unique domains (device types)
        // Note: using proxied API endpoint
        const entitiesResponse = await fetch('/api/data/entities?limit=10000', {
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
          setLoading(false);
        } else {
          // Fallback: try to get from devices
          const devicesResponse = await fetch('/api/data/devices', {
            headers: {
              'Authorization': `Bearer ${API_KEY}`,
              'X-HomeIQ-API-Key': API_KEY,
            },
          });
          if (devicesResponse.ok) {
            // Use demo devices as fallback if no entities found
            setUserDevices(['light', 'switch', 'sensor']);
            setError('No device types found. Using demo mode.');
          } else {
            throw new Error('Failed to fetch devices');
          }
          setLoading(false);
        }
      } catch (err) {
        console.error('Error fetching devices:', err);
        setError('Failed to load devices. Using demo mode.');
        setUserDevices(['light', 'switch', 'sensor']);  // Demo devices
        setLoading(false);
      }
    };

    fetchDevices();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading discovery features...</div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header - Modern 2025 Design */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={`mb-8 p-4 rounded-xl ${darkMode ? 'bg-gradient-to-br from-purple-900/30 to-pink-900/30 border border-purple-700/50' : 'bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200'} shadow-lg`}
      >
        <div className="flex items-center gap-3 mb-1">
          <h1 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            🔍 Automation Discovery
          </h1>
        </div>
        <p className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          Discover what you can automate and get smart device recommendations
        </p>
      </motion.div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`rounded-xl p-4 mb-6 border ${darkMode ? 'bg-yellow-900/30 border-yellow-700/50 text-yellow-200' : 'bg-yellow-50 border-yellow-200 text-yellow-800'} backdrop-blur-sm`}
        >
          <p className="font-bold mb-1">Note</p>
          <p className="text-sm">{error}</p>
        </motion.div>
      )}

      <div className="space-y-8">
        {/* Device Explorer Section - Glassmorphism */}
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
          <DeviceExplorer devices={userDevices} />
        </motion.section>

        {/* Smart Shopping Section - Glassmorphism */}
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
    </div>
  );
};

export default DiscoveryPage;

