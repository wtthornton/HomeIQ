/**
 * RAG Status Hook
 * 
 * Calculates and provides RAG status from health and statistics data
 */

import { useMemo } from 'react';
import { RAGStatus } from '../types/rag';
import { ServiceHealthResponse } from '../types/health';
import { Statistics } from '../types';
import { calculateRAGStatus } from '../utils/ragCalculations';

export interface UseRAGStatusProps {
  enhancedHealth: ServiceHealthResponse | null;
  statistics: Statistics | null;
  loading?: boolean;
}

export const useRAGStatus = ({
  enhancedHealth,
  statistics,
  loading = false
}: UseRAGStatusProps): {
  ragStatus: RAGStatus | null;
  loading: boolean;
} => {
  const ragStatus = useMemo(() => {
    // Allow calculation even if one of the data sources is missing
    // The calculation function handles null values gracefully
    if (loading) {
      return null;
    }

    // If both are null, return null (no data available)
    if (!enhancedHealth && !statistics) {
      return null;
    }

    try {
      return calculateRAGStatus(enhancedHealth, statistics);
    } catch (error) {
      console.error('Failed to calculate RAG status:', error);
      return null;
    }
  }, [enhancedHealth, statistics, loading]);

  return {
    ragStatus,
    loading
  };
};

