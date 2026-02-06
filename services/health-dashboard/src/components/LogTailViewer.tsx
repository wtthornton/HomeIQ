/**
 * LogTailViewer Component
 * 
 * Real-time log tail viewer with filtering and search
 * Epic 15.2: Live Event Stream & Log Viewer
 */

import React, { useState, useEffect, useRef } from 'react';

interface LogEntry {
  id?: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';
  service: string;
  message: string;
  correlation_id?: string;
  context?: {
    filename?: string;
    lineno?: number;
    function?: string;
    module?: string;
    pathname?: string;
  };
}

interface LogTailViewerProps {
  darkMode: boolean;
}

export const LogTailViewer: React.FC<LogTailViewerProps> = ({ darkMode }) => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [selectedLevel, setSelectedLevel] = useState<string>('all');
  const [selectedService, setSelectedService] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch logs from log aggregator service
  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    
    const fetchLogs = async () => {
      try {
        const params = new URLSearchParams();
        if (selectedService !== 'all') params.append('service', selectedService);
        if (selectedLevel !== 'all') params.append('level', selectedLevel);
        params.append('limit', '100');
        
        const response = await fetch(`/log-aggregator/api/v1/logs?${params}`, {
          headers: {
            'Content-Type': 'application/json',
            ...(sessionStorage.getItem('api_key') ? { 'X-API-Key': sessionStorage.getItem('api_key')! } : {}),
          },
        });
        if (response.ok) {
          const data = await response.json();
          setLogs(data.logs || []);
        } else {
          console.error('Failed to fetch logs:', response.statusText);
        }
      } catch (error) {
        console.error('Error fetching logs:', error);
      }
    };
    
    if (!isPaused) {
      // Fetch logs immediately
      fetchLogs();
      
      // Set up polling every 5 seconds
      intervalId = setInterval(fetchLogs, 5000);
    }
    
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [isPaused, selectedService, selectedLevel]);

  // Auto-scroll
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  // Search logs using log aggregator API
  const searchLogs = async (query: string) => {
    if (!query.trim()) return;
      
    try {
      const params = new URLSearchParams();
      const normalizedQuery = query.trim().slice(0, 200);
      if (!normalizedQuery) {
        return;
      }
      params.append('q', normalizedQuery);
      params.append('limit', '100');
        
      const response = await fetch(`/log-aggregator/api/v1/logs/search?${params}`, {
        headers: {
          'Content-Type': 'application/json',
          ...(sessionStorage.getItem('api_key') ? { 'X-API-Key': sessionStorage.getItem('api_key')! } : {}),
        },
      });
      if (response.ok) {
        const data = await response.json();
        setLogs(data.logs || []);
      } else {
        console.error('Failed to search logs:', response.statusText);
      }
    } catch (error) {
      console.error('Error searching logs:', error);
    }
  };

  // Filter logs (for local filtering when not searching)
  const filteredLogs = logs.filter(log => {
    if (selectedLevel !== 'all' && log.level !== selectedLevel) return false;
    if (selectedService !== 'all' && log.service !== selectedService) return false;
    return true;
  });

  // Get unique services
  const services = ['all', ...Array.from(new Set(logs.map(l => l.service)))];

  // Clear logs
  const clearLogs = () => {
    setLogs([]);
  };

  // Copy log to clipboard
  const copyLog = (log: LogEntry) => {
    const logText = `[${log.timestamp}] ${log.level} ${log.service}: ${log.message}`;
    navigator.clipboard.writeText(logText).then(() => {
      if (import.meta.env.MODE !== 'production') {
        console.log('Log copied to clipboard');
      }
    });
  };

  // Get log level color
  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'CRITICAL':
      case 'ERROR':
        return darkMode ? 'text-red-400 bg-red-900/30' : 'text-red-700 bg-red-50';
      case 'WARNING':
        return darkMode ? 'text-yellow-400 bg-yellow-900/30' : 'text-yellow-700 bg-yellow-50';
      case 'INFO':
        return darkMode ? 'text-blue-400 bg-blue-900/30' : 'text-blue-700 bg-blue-50';
      case 'DEBUG':
        return darkMode ? 'text-gray-400 bg-gray-700' : 'text-gray-600 bg-gray-100';
      default:
        return darkMode ? 'text-gray-300' : 'text-gray-700';
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className={'card-base p-4'}>
        <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
          <h2 className={`text-h2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
            📜 Live Log Viewer
          </h2>
          
          <div className="flex flex-wrap gap-2 w-full sm:w-auto">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`btn-${isPaused ? 'success' : 'secondary'} text-sm min-h-[44px]`}
            >
              {isPaused ? '▶️ Resume' : '⏸️ Pause'}
            </button>
            
            <button
              onClick={() => setAutoScroll(!autoScroll)}
              className={`btn-${autoScroll ? 'primary' : 'secondary'} text-sm min-h-[44px]`}
            >
              {autoScroll ? '⬇️ Auto-scroll' : '⬇️ Scroll: OFF'}
            </button>
            
            <button
              onClick={clearLogs}
              className="btn-danger text-sm min-h-[44px]"
            >
              🗑️ Clear
            </button>
          </div>
        </div>
        
        {/* Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
          <select
            value={selectedLevel}
            onChange={(e) => setSelectedLevel(e.target.value)}
            className="input-base min-h-[44px]"
          >
            <option value="all">All Levels</option>
            <option value="CRITICAL">Critical</option>
            <option value="ERROR">Error</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
            <option value="DEBUG">Debug</option>
          </select>
          
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="input-base min-h-[44px]"
          >
            {services.map(service => (
              <option key={service} value={service}>
                {service === 'all' ? 'All Services' : service}
              </option>
            ))}
          </select>
          
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search logs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  searchLogs(searchQuery);
                }
              }}
              className="input-base min-h-[44px] flex-1"
            />
            <button
              onClick={() => searchLogs(searchQuery)}
              className="btn-primary text-sm min-h-[44px] px-4"
            >
              🔍 Search
            </button>
          </div>
        </div>
        
        <div className="flex gap-4 mt-3 text-sm">
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Total: <span className="font-semibold">{logs.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Filtered: <span className="font-semibold">{filteredLogs.length}</span>
          </span>
          <span className={`${darkMode ? 'text-gray-400' : 'text-gray-600'}`}>
            Status: <span className="font-semibold">{isPaused ? 'Paused' : 'Live'}</span>
          </span>
        </div>
      </div>
      
      {/* Log List */}
      <div className={'card-base p-3 max-h-[600px] overflow-y-auto font-mono text-xs'}>
        {filteredLogs.length === 0 ? (
          <div className="text-center py-12">
            <p className={`${darkMode ? 'text-gray-400' : 'text-gray-500'}`}>
              {isPaused ? '⏸️ Log stream paused' : '⏳ Waiting for logs...'}
            </p>
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((log, index) => (
              <div
                key={log.id}
                style={{ animationDelay: `${Math.min(index * 0.01, 0.5)}s` }}
                className={'flex items-start gap-2 p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer transition-colors content-fade-in'}
                onClick={() => copyLog(log)}
                title="Click to copy"
              >
                <span className={`badge-base ${getLogLevelColor(log.level)} px-2 py-0.5 flex-shrink-0`}>
                  {log.level}
                </span>
                <span className={`${darkMode ? 'text-gray-400' : 'text-gray-500'} flex-shrink-0`}>
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`${darkMode ? 'text-gray-500' : 'text-gray-400'} flex-shrink-0`}>
                  [{log.service}]
                </span>
                <span className={`${darkMode ? 'text-gray-300' : 'text-gray-700'} break-all`}>
                  {log.message}
                </span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>
    </div>
  );
};

