import React, { useState, useEffect } from 'react';
import { dataApi } from '../../services/api';

interface EnergyCorrelation {
  timestamp: string;
  entity_id: string;
  domain: string;
  state: string;
  previous_state: string;
  power_before_w: number;
  power_after_w: number;
  power_delta_w: number;
  power_delta_pct: number;
}

interface EnergyStatistics {
  current_power_w: number;
  daily_kwh: number;
  peak_power_w: number;
  peak_time: string | null;
  average_power_w: number;
  total_correlations: number;
}

interface DeviceImpact {
  entity_id: string;
  domain: string;
  average_power_on_w: number;
  average_power_off_w: number;
  total_state_changes: number;
  estimated_daily_kwh: number;
  estimated_monthly_cost: number;
}

interface EnergyTabProps {
  darkMode: boolean;
}

export const EnergyTab: React.FC<EnergyTabProps> = ({ darkMode }) => {
  const [statistics, setStatistics] = useState<EnergyStatistics | null>(null);
  const [correlations, setCorrelations] = useState<EnergyCorrelation[]>([]);
  const [topConsumers, setTopConsumers] = useState<DeviceImpact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEnergyData();
    const interval = setInterval(fetchEnergyData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchEnergyData = async () => {
    try {
      const [statsData, corrData, consumersData] = await Promise.all([
        dataApi.getEnergyStatistics(24),
        dataApi.getEnergyCorrelations(24, undefined, undefined, 50, 20),
        dataApi.getTopEnergyConsumers(7, 5)
      ]);

      setStatistics(statsData);
      setCorrelations(corrData);
      setTopConsumers(consumersData);
      setError(null);
    } catch (err) {
      console.error('Error fetching energy data:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch energy data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg">Loading energy data...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-100 dark:bg-red-900 rounded-lg">
        <p className="text-red-800 dark:text-red-200">Error: {error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className={`text-2xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Energy Monitoring & Correlations
        </h2>
        <button
          onClick={fetchEnergyData}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {/* Current Power Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className={`p-4 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Current Power
              </p>
              <p className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics?.current_power_w.toFixed(0) || 0}W
              </p>
            </div>
            <div className="text-4xl">⚡</div>
          </div>
        </div>

        <div className={`p-4 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Daily Energy
              </p>
              <p className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics?.daily_kwh.toFixed(1) || 0} kWh
              </p>
            </div>
            <div className="text-4xl">📊</div>
          </div>
        </div>

        <div className={`p-4 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Peak Power (24h)
              </p>
              <p className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics?.peak_power_w.toFixed(0) || 0}W
              </p>
            </div>
            <div className="text-4xl">📈</div>
          </div>
        </div>

        <div className={`p-4 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                Correlations Found
              </p>
              <p className={`text-3xl font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                {statistics?.total_correlations || 0}
              </p>
            </div>
            <div className="text-4xl">🔗</div>
          </div>
        </div>
      </div>

      {/* Top Energy Consumers */}
      {topConsumers.length > 0 && (
        <div className={`p-6 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
          <h3 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Top Energy Consumers (Last 7 Days)
          </h3>
          <div className="space-y-3">
            {topConsumers.map((device, idx) => (
              <div
                key={device.entity_id}
                className={`p-4 rounded-lg ${darkMode ? 'bg-gray-700' : 'bg-gray-50'}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className={`font-semibold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      #{idx + 1}. {device.entity_id}
                    </p>
                    <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      {device.domain}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold ${darkMode ? 'text-white' : 'text-gray-900'}`}>
                      {device.average_power_on_w.toFixed(0)}W
                    </p>
                    <p className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                      ${device.estimated_monthly_cost.toFixed(2)}/month
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Correlations */}
      <div className={`p-6 rounded-lg shadow ${darkMode ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
          Recent Power Changes (Last 24 Hours)
        </h3>
        
        {correlations.length === 0 ? (
          <p className={`text-center py-8 ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            No correlations found. Waiting for Home Assistant events and power data...
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead>
                <tr>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Time
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Device
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase tracking-wider ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    State Change
                  </th>
                  <th className={`px-4 py-3 text-right text-xs font-medium uppercase tracking-wider ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                    Power Change
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${darkMode ? 'divide-gray-700' : 'divide-gray-200'}`}>
                {correlations.map((corr, idx) => (
                  <tr key={idx} className={darkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm ${darkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                      {new Date(corr.timestamp).toLocaleString()}
                    </td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm ${darkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                      <div>
                        <div className="font-medium">{corr.entity_id}</div>
                        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-600'}`}>
                          {corr.domain}
                        </div>
                      </div>
                    </td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm ${darkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                      <span className={`px-2 py-1 rounded ${darkMode ? 'bg-gray-600' : 'bg-gray-200'}`}>
                        {corr.previous_state} → {corr.state}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <div>
                        <div className={`text-sm font-bold ${corr.power_delta_w > 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {corr.power_delta_w > 0 ? '+' : ''}{corr.power_delta_w.toFixed(0)}W
                        </div>
                        <div className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-600'}`}>
                          ({corr.power_delta_pct > 0 ? '+' : ''}{corr.power_delta_pct.toFixed(1)}%)
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className={`p-6 rounded-lg shadow ${darkMode ? 'bg-blue-900/20 border border-blue-800' : 'bg-blue-50 border border-blue-200'}`}>
        <div className="flex items-start">
          <div className="text-3xl mr-4">ℹ️</div>
          <div>
            <h4 className={`font-bold mb-2 ${darkMode ? 'text-blue-300' : 'text-blue-900'}`}>
              About Energy Correlations
            </h4>
            <p className={`text-sm ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
              This tab shows which Home Assistant devices (switches, lights, HVAC, etc.) cause measurable changes in power consumption. 
              The Energy Correlator service analyzes events every 60 seconds and matches them with power readings from the Smart Meter service.
            </p>
            <p className={`text-sm mt-2 ${darkMode ? 'text-blue-200' : 'text-blue-800'}`}>
              <strong>Note:</strong> You need energy monitoring configured in Home Assistant for real data. 
              Currently showing: {statistics?.total_correlations || 0} correlations from the last 24 hours.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

