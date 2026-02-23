/**
 * Performance History Hook
 * Phase 2: Enhancements
 * 
 * Tracks performance metrics over time for sparkline visualization
 */

import { useState, useEffect, useRef } from 'react';

export interface PerformanceDataPoint {
  timestamp: Date;
  value: number;
}

interface UsePerformanceHistoryOptions {
  maxDataPoints?: number;
  sampleInterval?: number; // milliseconds
}

export const usePerformanceHistory = (
  currentValue: number,
  options: UsePerformanceHistoryOptions = {}
) => {
  const {
    maxDataPoints = 60, // Keep last 60 data points (e.g., 60 minutes)
    sampleInterval = 60000 // Sample every 60 seconds
  } = options;

  const [history, setHistory] = useState<PerformanceDataPoint[]>([]);
  const lastSampleTime = useRef<number>(0);

  useEffect(() => {
    const now = Date.now();
    
    // Only add a new data point if enough time has passed
    if (now - lastSampleTime.current >= sampleInterval) {
      setHistory(prev => {
        const newDataPoint: PerformanceDataPoint = {
          timestamp: new Date(),
          value: currentValue
        };

        // Add new point and keep only maxDataPoints
        const updated = [...prev, newDataPoint].slice(-maxDataPoints);
        return updated;
      });

      lastSampleTime.current = now;
    }
  }, [currentValue, maxDataPoints, sampleInterval]);

  // Calculate statistics with null safety
  const safeCurrentValue = currentValue ?? 0;
  const stats = {
    current: safeCurrentValue,
    peak: history.length > 0 
      ? Math.max(...history.map(d => d.value ?? 0).filter(v => !isNaN(v))) 
      : safeCurrentValue,
    average: history.length > 0 
      ? history.reduce((sum, d) => sum + (d.value ?? 0), 0) / history.length 
      : safeCurrentValue,
    previous: history.length > 1 ? (history[history.length - 2].value ?? safeCurrentValue) : safeCurrentValue
  };

  return {
    history,
    stats
  };
};

