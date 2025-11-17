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
    if (loading || !enhancedHealth || !statistics) {
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

