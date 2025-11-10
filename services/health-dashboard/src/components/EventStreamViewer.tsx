/**
 * EventStreamViewer Component
 * 
 * Real-time event stream with filtering, auto-scroll, and copy functionality
 * Epic 15.2: Live Event Stream & Log Viewer
 * 
 * Implementation: HTTP polling every 3 seconds for real-time updates
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { dataApi } from '../services/api';

interface Event {
  id: string;
  timestamp: string;
  service: string;
  type: string;
  severity: 'info' | 'warning' | 'error' | 'debug';
  message: string;
}

type DetailStatus =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'loaded'; data: any }
  | { status: 'error'; error: string };

interface EventStreamViewerProps {
  darkMode: boolean;
}

// Helper function to infer severity from event type
const inferSeverity = (eventType: string): 'info' | 'warning' | 'error' | 'debug' => {
  const type = eventType.toLowerCase();
  if (type.includes('error') || type.includes('fail')) return 'error';
  if (type.includes('warn')) return 'warning';
  if (type.includes('debug')) return 'debug';
  return 'info';
};

// Helper function to map API event to component format
const mapApiEvent = (apiEvent: any): Event => {
  const entityId = apiEvent.entity_id || 'unknown';
  const eventType = apiEvent.event_type || 'unknown';
  
  return {
    id: apiEvent.id || `event_${Date.now()}_${Math.random()}`,
    timestamp: apiEvent.timestamp || new Date().toISOString(),
    service: 'home-assistant',
    type: eventType,
    severity: inferSeverity(eventType),
    message: `${entityId}: ${eventType}`
  };
};

export const EventStreamViewer: React.FC<EventStreamViewerProps> = ({ darkMode }) => {
  // State management
  const [events, setEvents] = useState<Event[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedService, setSelectedService] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchTime, setLastFetchTime] = useState<Date | null>(null);
  const [detailState, setDetailState] = useState<Record<string, DetailStatus>>({});
  
  const eventsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // HTTP Polling for events - Following React best practices from Context7 KB
  useEffect(() => {
    if (isPaused) return; // Don't fetch when paused
    
    let ignore = false; // Race condition prevention (Context7 KB pattern)
    
    const fetchEvents = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch latest events from API
        const apiEvents = await dataApi.getEvents({ limit: 50 });
        
        if (ignore) return; // Prevent stale updates
        
        if (apiEvents && Array.isArray(apiEvents)) {
          // Map API events to component format
          const mappedEvents = apiEvents.map(mapApiEvent);
          
          // Filter out duplicates based on event ID
          setEvents(prevEvents => {
            const existingIds = new Set(prevEvents.map(e => e.id));
            const newEvents = mappedEvents.filter(e => !existingIds.has(e.id));
            
            // Prepend new events (newest first), limit to 500 total
            return [...newEvents, ...prevEvents].slice(0, 500);
          });
          
          setLastFetchTime(new Date());
        }
      } catch (err: any) {
        if (!ignore) {
          setError(err.message || 'Failed to fetch events');
          console.error('Event fetch error:', err);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };
    
    // Initial fetch
    fetchEvents();
    
    // Poll every 3 seconds (Context7 KB: setInterval with cleanup)
    const pollInterval = setInterval(fetchEvents, 3000);
    
    // Cleanup function - critical for preventing memory leaks (Context7 KB pattern)
    return () => {
      ignore = true;
      clearInterval(pollInterval);
    };
  }, [isPaused]); // Re-run when pause state changes

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

  // Clear events callback
  const clearEvents = useCallback(() => {
    setEvents([]);
    setError(null);
    setDetailState({});
    setExpandedEvent(null);
  }, []);

  const ensureEventDetails = useCallback(async (eventId: string) => {
    let shouldFetch = false;
    setDetailState(prev => {
      const current = prev[eventId];
      if (current && (current.status === 'loading' || current.status === 'loaded')) {
        return prev;
      }
      shouldFetch = true;
      return {
        ...prev,
        [eventId]: { status: 'loading' }
      };
    });

    if (!shouldFetch) {
      return;
    }

    try {
      const detail = await dataApi.getEventById(eventId);
      setDetailState(prev => ({
        ...prev,
        [eventId]: { status: 'loaded', data: detail }
      }));
    } catch (err: any) {
      const message = err?.message || 'Failed to load event details';
      setDetailState(prev => ({
        ...prev,
        [eventId]: { status: 'error', error: message }
      }));
    }
  }, []);

  // Filter events
  const filteredEvents = events.filter(event => {
    if (selectedService !== 'all' && event.service !== selectedService) return false;
    if (selectedSeverity !== 'all' && event.severity !== selectedSeverity) return false;
    if (searchQuery && !event.message.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  // Get unique services
  const services = ['all', ...Array.from(new Set(events.map(e => e.service)))];

  // Get severity color
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return darkMode ? 'text-red-400 bg-red-900/30' : 'text-red-700 bg-red-50';
      case 'warning':
        return darkMode ? 'text-yellow-400 bg-yellow-900/30' : 'text-yellow-700 bg-yellow-50';
      case 'info':
        return darkMode ? 'text-blue-400 bg-blue-900/30' : 'text-blue-700 bg-blue-50';
      case 'debug':
        return darkMode ? 'text-gray-400 bg-gray-700' : 'text-gray-600 bg-gray-100';
      default:
        return darkMode ? 'text-gray-300' : 'text-gray-700';
    }
  };

  // Copy event to clipboard
  const copyToClipboard = useCallback((event: Event) => {
    const detail = detailState[event.id];
    const payload = detail && detail.status === 'loaded' ? detail.data : event;
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
  }, [detailState]);

  const handleToggleDetails = useCallback((eventId: string) => {
    setExpandedEvent(prev => {
      const next = prev === eventId ? null : eventId;
      if (next === eventId) {
        void ensureEventDetails(eventId);
      }
      return next;
    });
  }, [ensureEventDetails]);

  const handleRetry = useCallback((eventId: string) => {
    setDetailState(prev => ({
      ...prev,
      [eventId]: { status: 'idle' }
    }));
    void ensureEventDetails(eventId);
  }, [ensureEventDetails]);

  return (
    <div className="space-y-4">
      {/* Error Banner */}
      {error && (
        <div className={`p-4 rounded-lg border ${
          darkMode 
            ? 'bg-red-900/30 border-red-700 text-red-400' 
            : 'bg-red-50 border-red-200 text-red-700'
        }`}>
          <div className="flex items-center gap-2">
            <span className="text-lg">⚠️</span>
            <div>
              <strong className="font-semibold">Error fetching events</strong>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Controls */}
      <div className={'card-base p-4'}>
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <h2 className={`text-h2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📡 Live Event Stream
          </h2>
          
          <div className="flex flex-wrap gap-2 w-full sm:w-auto">
            {/* Pause/Resume */}
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`btn-${isPaused ? 'success' : 'secondary'} text-sm min-h-[44px]`}
            >
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            
            {/* Auto-scroll */}
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`btn-${autoScroll ? 'primary' : 'secondary'} text-sm min-h-[44px]`}
            >
              {autoScroll ? '📜 Auto-scroll: ON' : '📜 Auto-scroll: OFF'}
            </button>
            
            {/* Clear */}
            <button
              onClick={clearEvents}
              className="btn-danger text-sm min-h-[44px]"
            >
              🗑️ Clear
            </button>
          </div>
        </div>
        
        {/* Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          {/* Service Filter */}
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="input-base min-h-[44px]"
            aria-label="Filter by service"
          >
            {services.map(service => (
              <option key={service} value={service}>
                {service === 'all' ? 'All Services' : service}
              </option>
            ))}
          </select>
          
          {/* Severity Filter */}
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="input-base min-h-[44px]"
            aria-label="Filter by severity"
          >
            <option value="all">All Severities</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
            <option value="debug">Debug</option>
          </select>
          
          {/* Search */}
          <input
            type="text"
            placeholder="Search events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-base min-h-[44px]"
            aria-label="Search events"
          />
        </div>
        
        {/* Stats */}
        <div className="flex flex-wrap gap-4 mt-3 text-sm">
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Total: <span className="font-semibold">{events.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Filtered: <span className="font-semibold">{filteredEvents.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Status: <span className="font-semibold">{isPaused ? 'Paused' : 'Live'}</span>
          </span>
          {loading && (
            <span className={`${darkMode ? 'text-blue-400' : 'text-blue-600'}`}>
              <span className="animate-pulse">🔄 Fetching...</span>
            </span>
          )}
          {lastFetchTime && !loading && (
            <span className={`${darkMode ? 'text-gray-500' : 'text-gray-500'} text-xs`}>
              Last update: {lastFetchTime.toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
      
      {/* Event List */}
      <div 
        ref={containerRef}
        className={'card-base p-4 max-h-[600px] overflow-y-auto'}
      >
        {loading && events.length === 0 ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-500">Loading events...</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="text-center py-12">
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {isPaused ? '⏸️ Stream paused' : events.length > 0 ? '🔍 No events match your filters' : '⏳ Waiting for events...'}
            </p>
          </div>
        ) : (
          <div className="space-y-2 stagger-in-list">
            {filteredEvents.map((event, index) => (
              <div
                key={event.id}
                style={{ animationDelay: `${Math.min(index * 0.02, 1)}s` }}
                className={`content-fade-in border rounded-lg p-3 transition-all duration-200 ${
                  expandedEvent === event.id ? 'ring-2 ring-blue-500' : ''
                } ${darkMode ? 'border-gray-700 hover:bg-gray-700/50' : 'border-gray-200 hover:bg-gray-50'}`}
              >
                {/* Event Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`badge-base ${getSeverityColor(event.severity)} text-xs`}>
                        {event.severity.toUpperCase()}
                      </span>
                      <span className={`text-xs font-mono ${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                      <span className={`text-xs ${darkMode ? 'text-gray-500' : 'text-gray-400'}`}>
                        {event.service}
                      </span>
                    </div>
                    <p className={`text-sm ${darkMode ? 'text-white' : 'text-gray-900'} break-words`}>
                      {event.message}
                    </p>
                  </div>
                  
                  <div className="flex gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleToggleDetails(event.id)}
                      className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      title="Toggle details"
                    >
                      {expandedEvent === event.id ? '🔼' : '🔽'}
                    </button>
                    <button
                      onClick={() => copyToClipboard(event)}
                      className="p-1.5 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                      title="Copy to clipboard"
                    >
                      📋
                    </button>
                  </div>
                </div>
                
                {/* Expanded Details */}
                {expandedEvent === event.id && (
                  <div className={`mt-3 p-3 rounded text-xs font-mono overflow-x-auto ${
                    darkMode ? 'bg-gray-900 text-gray-300' : 'bg-gray-100 text-gray-700'
                  }`}>
                    {(() => {
                      const detail = detailState[event.id];
                      if (!detail || detail.status === 'idle' || detail.status === 'loading') {
                        return (
                          <div className="flex items-center gap-2">
                            <span className="animate-spin">⏳</span>
                            <span>Loading event details…</span>
                          </div>
                        );
                      }
                      if (detail.status === 'error') {
                        return (
                          <div className="space-y-2">
                            <div className="text-red-400">
                              Failed to load details: {detail.error}
                            </div>
                            <button
                              onClick={() => handleRetry(event.id)}
                              className="btn-secondary text-xs"
                            >
                              Retry
                            </button>
                          </div>
                        );
                      }
                      return (
                        <pre>{JSON.stringify(detail.data, null, 2)}</pre>
                      );
                    })()}
                  </div>
                )}
              </div>
            ))}
            <div ref={eventsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

