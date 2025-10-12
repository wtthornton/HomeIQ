/**
 * EventStreamViewer Component
 * 
 * Real-time event stream with filtering, auto-scroll, and copy functionality
 * Epic 15.2: Live Event Stream & Log Viewer
 */

import React, { useState, useEffect, useRef } from 'react';
import { useRealtimeMetrics } from '../hooks/useRealtimeMetrics';

interface Event {
  id: string;
  timestamp: string;
  service: string;
  type: string;
  severity: 'info' | 'warning' | 'error' | 'debug';
  message: string;
  details?: any;
}

interface EventStreamViewerProps {
  darkMode: boolean;
}

export const EventStreamViewer: React.FC<EventStreamViewerProps> = ({ darkMode }) => {
  const [events, setEvents] = useState<Event[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedService, setSelectedService] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedEvent, setExpandedEvent] = useState<string | null>(null);
  
  const eventsEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  
  const { metrics } = useRealtimeMetrics({ enabled: true });

  // Update events from WebSocket
  useEffect(() => {
    if (metrics?.events && !isPaused) {
      setEvents(prev => {
        const newEvents = metrics.events.map((e: any, idx: number) => ({
          id: e.id || `event-${Date.now()}-${idx}`,
          timestamp: e.timestamp || new Date().toISOString(),
          service: e.service || 'unknown',
          type: e.event_type || e.type || 'event',
          severity: e.severity || 'info',
          message: e.message || JSON.stringify(e),
          details: e.details || e
        }));
        
        // Combine and limit to 1000 events (buffer management)
        const combined = [...newEvents, ...prev].slice(0, 1000);
        return combined;
      });
    }
  }, [metrics, isPaused]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, autoScroll]);

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
  const copyToClipboard = (event: Event) => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
  };

  // Clear all events
  const clearEvents = () => {
    setEvents([]);
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className={`card-base p-4`}>
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
        <div className="flex gap-4 mt-3 text-sm">
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Total: <span className="font-semibold">{events.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Filtered: <span className="font-semibold">{filteredEvents.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Status: <span className="font-semibold">{isPaused ? 'Paused' : 'Live'}</span>
          </span>
        </div>
      </div>
      
      {/* Event List */}
      <div 
        ref={containerRef}
        className={`card-base p-4 max-h-[600px] overflow-y-auto`}
      >
        {filteredEvents.length === 0 ? (
          <div className="text-center py-12">
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {isPaused ? '⏸️ Stream paused' : '⏳ Waiting for events...'}
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
                      onClick={() => setExpandedEvent(expandedEvent === event.id ? null : event.id)}
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
                    <pre>{JSON.stringify(event.details || event, null, 2)}</pre>
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

