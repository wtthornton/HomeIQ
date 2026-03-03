/**
 * Events Tab - Real-time + Historical Events
 * Story 21.3: Enhanced with historical queries and statistics
 */

import React, { useState, useEffect, useCallback } from 'react';
import { EventStreamViewer } from '../EventStreamViewer';
import { TabProps } from './types';
import { dataApi } from '../../services/api';

interface EventStats {
  total_events: number;
  event_types: Record<string, number>;
  top_entities: Array<{ entity_id: string; count: number }>;
}

export const EventsTab: React.FC<TabProps> = ({ darkMode }) => {
  const [timeRange, setTimeRange] = useState('1h');
  const [historicalEvents, setHistoricalEvents] = useState<any[]>([]);
  const [stats, setStats] = useState<EventStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistorical, setShowHistorical] = useState(false);

  // Fetch historical events - wrapped in useCallback for proper dependency tracking
  const fetchHistoricalEvents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const events = await dataApi.getEvents({ limit: 100 });
      setHistoricalEvents(events || []);
    } catch (err) {
      console.error('Error fetching historical events:', err);
      setError(err instanceof Error ? err.message : 'Failed to load events');
      setHistoricalEvents([]);
    } finally {
      setLoading(false);
    }
  }, []); // No dependencies - dataApi is stable

  // Fetch event statistics - wrapped in useCallback with timeRange dependency
  const fetchEventStats = useCallback(async () => {
    try {
      const statsData = await dataApi.getEventsStats(timeRange);
      setStats(statsData);
    } catch (err) {
      console.error('Error fetching event stats:', err);
    }
  }, [timeRange]); // Depends on timeRange

  // Fetch historical events when time range changes
  useEffect(() => {
    if (showHistorical) {
      fetchHistoricalEvents();
      fetchEventStats();
    }
  }, [timeRange, showHistorical, fetchHistoricalEvents, fetchEventStats]);

  return (
    <div className="space-y-6" data-testid="event-stream">
      {/* View Toggle */}
      <div className="flex justify-between items-center">
        <div className="flex gap-2">
          <button
            onClick={() => setShowHistorical(false)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              !showHistorical
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
            }`}
          >
            📡 Real-Time Stream
          </button>
          <button
            onClick={() => setShowHistorical(true)}
            className={`px-4 py-2 rounded-lg transition-colors ${
              showHistorical
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300' : 'bg-gray-200 text-gray-700'
            }`}
          >
            📊 Historical Events
          </button>
        </div>

        {showHistorical && (
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className={`px-4 py-2 rounded-lg border ${
              darkMode
                ? 'bg-gray-700 border-gray-600 text-white'
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          >
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>
        )}
      </div>

      {/* Event Statistics (when viewing historical) */}
      {showHistorical && stats && (
        <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h3 className={`text-lg font-semibold mb-3 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Event Statistics ({timeRange})
          </h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Total Events</div>
              <div className="text-2xl font-bold">{stats.total_events || 0}</div>
            </div>
            <div>
              <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Event Types</div>
              <div className="text-2xl font-bold">{Object.keys(stats.event_types || {}).length}</div>
            </div>
            <div>
              <div className={`text-sm ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>Top Entities</div>
              <div className="text-2xl font-bold">{(stats.top_entities || []).length}</div>
            </div>
          </div>
        </div>
      )}

      {/* Real-Time Stream View */}
      {!showHistorical && <EventStreamViewer darkMode={darkMode} />}

      {/* Error State */}
      {showHistorical && error && !loading && (
        <div className={`p-6 rounded-lg border ${
          darkMode ? 'bg-red-900/20 border-red-700' : 'bg-red-50 border-red-200'
        }`} role="alert">
          <div className="flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <p className={`font-semibold ${darkMode ? 'text-red-300' : 'text-red-800'}`}>
                Error loading events
              </p>
              <p className={`text-sm mt-1 ${darkMode ? 'text-red-400' : 'text-red-600'}`}>
                {error}
              </p>
            </div>
            <button
              onClick={fetchHistoricalEvents}
              className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white font-medium transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Historical Events View */}
      {showHistorical && !error && (
        <div className={`p-4 rounded-lg ${darkMode ? 'bg-gray-800' : 'bg-white'} border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <h3 className={`text-lg font-semibold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            Historical Events
          </h3>
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
              <p className="mt-4 text-gray-500">Loading events...</p>
            </div>
          ) : historicalEvents.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <div className="text-6xl mb-4">📭</div>
              <p>No historical events found for this time range</p>
            </div>
          ) : (
            <div className="space-y-2">
              {historicalEvents.map((event, idx) => (
                <div
                  key={event.id || idx}
                  className={`p-3 rounded border ${
                    darkMode ? 'bg-gray-750 border-gray-600' : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <code className={`text-sm font-mono ${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
                          {event.entity_id}
                        </code>
                        <span className={`text-xs px-2 py-0.5 rounded ${darkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
                          {event.event_type}
                        </span>
                      </div>
                      <div className={`text-xs mt-1 ${darkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                        {new Date(event.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

