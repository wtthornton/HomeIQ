/**
 * HACS Status Check Component
 * 
 * Displays HACS and Team Tracker installation status
 * Provides installation guidance if not installed
 */

import React, { useEffect, useState } from 'react';

interface HACSStatus {
  installed: boolean;
  hacs_entry?: any;
  hacs_entities_count?: number;
  team_tracker_installed?: boolean;
  error?: string;
  recommendation?: string;
}

interface HACSStatusCheckProps {
  darkMode?: boolean;
}

export const HACSStatusCheck: React.FC<HACSStatusCheckProps> = ({ darkMode = false }) => {
  const [status, setStatus] = useState<HACSStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);

  useEffect(() => {
    checkHACSStatus();
  }, []);

  const checkHACSStatus = async () => {
    try {
      setLoading(true);
      setError(null);

      // Check via HA API through admin-api service
      const response = await fetch('/api/v1/health/integrations');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Find HACS integration check result
      const hacsCheck = data.integrations?.find((i: any) => 
        i.integration_name === 'HACS'
      );

      if (hacsCheck) {
        setStatus({
          installed: hacsCheck.is_configured && hacsCheck.is_connected,
          team_tracker_installed: hacsCheck.check_details?.team_tracker_installed,
          recommendation: hacsCheck.check_details?.recommendation,
          error: hacsCheck.error_message,
          hacs_entities_count: hacsCheck.check_details?.hacs_entities_found ? 1 : 0
        });
      } else {
        setStatus({
          installed: false,
          error: 'HACS status check unavailable'
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to check HACS status');
      setStatus({
        installed: false,
        error: err instanceof Error ? err.message : 'Unknown error'
      });
    } finally {
      setLoading(false);
    }
  };

  const bgPrimary = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const bgCard = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  if (loading) {
    return (
      <div className={`rounded-lg shadow-md p-6 ${bgCard} ${textPrimary}`}>
        <div className="flex items-center space-x-3">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
          <span>Checking HACS status...</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg shadow-md p-6 ${bgCard} ${textPrimary}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-bold">HACS & Team Tracker Status</h3>
        <button
          onClick={checkHACSStatus}
          className={`px-3 py-1 rounded ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textPrimary} text-sm`}
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className={`mb-4 p-4 rounded-lg bg-red-500/10 border border-red-500/20 ${textPrimary}`}>
          <p className="text-red-500">Error: {error}</p>
        </div>
      )}

      {/* HACS Status */}
      <div className={`mb-4 p-4 rounded-lg border ${borderColor}`}>
        <div className="flex items-center space-x-3">
          {status?.installed ? (
            <>
              <div className="text-2xl">✅</div>
              <div className="flex-1">
                <h4 className="font-semibold text-green-500">HACS Installed</h4>
                <p className={`text-sm ${textSecondary}`}>
                  {status.hacs_entities_count && status.hacs_entities_count > 0 
                    ? `${status.hacs_entities_count} HACS entity found`
                    : 'HACS is configured and ready'}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="text-2xl">❌</div>
              <div className="flex-1">
                <h4 className="font-semibold text-red-500">HACS Not Installed</h4>
                <p className={`text-sm ${textSecondary}`}>
                  HACS is required for sports features to work
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Team Tracker Status */}
      <div className={`mb-4 p-4 rounded-lg border ${borderColor}`}>
        <div className="flex items-center space-x-3">
          {status?.team_tracker_installed ? (
            <>
              <div className="text-2xl">✅</div>
              <div className="flex-1">
                <h4 className="font-semibold text-green-500">Team Tracker Installed</h4>
                <p className={`text-sm ${textSecondary}`}>
                  Ready to use sports features
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="text-2xl">❌</div>
              <div className="flex-1">
                <h4 className="font-semibold text-red-500">Team Tracker Not Installed</h4>
                <p className={`text-sm ${textSecondary}`}>
                  Required for displaying live sports data
                </p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Recommendation */}
      {status?.recommendation && (
        <div className={`mb-4 p-4 rounded-lg border ${borderColor} bg-blue-500/10`}>
          <p className={`text-sm ${textPrimary}`}>
            <strong>💡 Recommendation:</strong> {status.recommendation}
          </p>
        </div>
      )}

      {/* Installation Instructions */}
      {!status?.installed && (
        <div className="space-y-4">
          <button
            onClick={() => setShowInstructions(!showInstructions)}
            className={`w-full p-3 rounded-lg ${darkMode ? 'bg-blue-700 hover:bg-blue-600' : 'bg-blue-600 hover:bg-blue-700'} text-white font-semibold transition-colors`}
          >
            {showInstructions ? 'Hide' : 'Show'} Installation Instructions
          </button>

          {showInstructions && (
            <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-gray-100'} ${textPrimary}`}>
              <h4 className="font-bold mb-3">HACS Installation Guide</h4>
              
              <div className="space-y-3 text-sm">
                <div>
                  <strong>STEP 1:</strong> Access Home Assistant Terminal
                  <ul className={`ml-4 mt-1 ${textSecondary} list-disc list-inside`}>
                    <li>Install 'Terminal & SSH' add-on in Home Assistant</li>
                    <li>Or use SSH to access your HA instance</li>
                  </ul>
                </div>

                <div>
                  <strong>STEP 2:</strong> Download and Install HACS
                  <pre className={`ml-4 mt-1 p-2 rounded ${darkMode ? 'bg-gray-900' : 'bg-gray-800'} text-green-400 text-xs overflow-x-auto`}>
                    cd /config{'\n'}wget -O - https://get.hacs.xyz | bash -
                  </pre>
                </div>

                <div>
                  <strong>STEP 3:</strong> Restart Home Assistant
                  <p className={`ml-4 mt-1 ${textSecondary}`}>
                    Settings → System → Restart Home Assistant
                  </p>
                </div>

                <div>
                  <strong>STEP 4:</strong> Configure HACS
                  <p className={`ml-4 mt-1 ${textSecondary}`}>
                    Settings → Devices & Services → Add Integration → Search 'HACS'
                  </p>
                </div>

                <div>
                  <strong>STEP 5:</strong> Install Team Tracker
                  <ul className={`ml-4 mt-1 ${textSecondary} list-disc list-inside`}>
                    <li>Open HACS in Home Assistant sidebar</li>
                    <li>Click 'Integrations' → '+ Explore & Download Repositories'</li>
                    <li>Search 'Team Tracker' and download</li>
                    <li>Restart HA and add integration</li>
                  </ul>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-700">
                <p className={`text-xs ${textSecondary}`}>
                  <strong>Documentation:</strong><br/>
                  HACS: <a href="https://hacs.xyz/docs/setup/download" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">https://hacs.xyz/docs/setup/download</a><br/>
                  Team Tracker: <a href="https://github.com/vasquatch2/team_tracker" target="_blank" rel="noreferrer" className="text-blue-400 hover:underline">https://github.com/vasquatch2/team_tracker</a>
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

