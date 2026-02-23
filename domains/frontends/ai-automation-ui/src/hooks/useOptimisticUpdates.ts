/**
 * Optimistic Updates Hook
 * Provides optimistic UI updates with automatic rollback on error
 */

import { useState, useCallback } from 'react';
import type { Suggestion } from '../types';

interface OptimisticUpdateOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
  rollbackDelay?: number;
}

export const useOptimisticUpdates = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [processedCount, setProcessedCount] = useState(0);
  const [failedCount, setFailedCount] = useState(0);
  const [errors, setErrors] = useState<Array<{ id: number; error: string }>>([]);

  /**
   * Execute batch operation with optimistic updates
   */
  const executeBatchOperation = useCallback(async <T>(
    items: Suggestion[],
    operation: (id: number) => Promise<T>,
    optimisticUpdate: (items: Suggestion[]) => void,
    rollbackUpdate: (items: Suggestion[]) => void,
    options: OptimisticUpdateOptions<T> = {}
  ): Promise<{ success: boolean; processed: number; failed: number; errors: Array<{ id: number; error: string }> }> => {
    setIsProcessing(true);
    setProcessedCount(0);
    setFailedCount(0);
    setErrors([]);

    // Apply optimistic update
    optimisticUpdate(items);

    const results: Array<{ id: number; success: boolean; error?: string }> = [];
    let successCount = 0;
    let failCount = 0;
    const batchErrors: Array<{ id: number; error: string }> = [];

    // Process each item
    for (const item of items) {
      try {
        const result = await operation(item.id);
        results.push({ id: item.id, success: true });
        successCount++;
        setProcessedCount(prev => prev + 1);
        
        options.onSuccess?.(result);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        results.push({ id: item.id, success: false, error: errorMessage });
        batchErrors.push({ id: item.id, error: errorMessage });
        failCount++;
        setFailedCount(prev => prev + 1);
        
        options.onError?.(error instanceof Error ? error : new Error(errorMessage));
      }
    }

    setErrors(batchErrors);
    setIsProcessing(false);

    // Rollback if all operations failed
    if (failCount === items.length) {
      setTimeout(() => {
        rollbackUpdate(items);
      }, options.rollbackDelay || 1000);
    }

    return {
      success: failCount === 0,
      processed: successCount,
      failed: failCount,
      errors: batchErrors,
    };
  }, []);

  /**
   * Execute single operation with optimistic update
   */
  const executeSingleOperation = useCallback(async <T>(
    item: Suggestion,
    operation: (id: number) => Promise<T>,
    optimisticUpdate: (item: Suggestion) => void,
    rollbackUpdate: (item: Suggestion) => void,
    options: OptimisticUpdateOptions<T> = {}
  ): Promise<{ success: boolean; error?: string }> => {
    setIsProcessing(true);
    setErrors([]);

    // Apply optimistic update
    optimisticUpdate(item);

    try {
      const result = await operation(item.id);
      setIsProcessing(false);
      options.onSuccess?.(result);
      
      return { success: true };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setErrors([{ id: item.id, error: errorMessage }]);
      setIsProcessing(false);
      
      // Rollback on error
      setTimeout(() => {
        rollbackUpdate(item);
      }, options.rollbackDelay || 1000);
      
      options.onError?.(error instanceof Error ? error : new Error(errorMessage));
      
      return { success: false, error: errorMessage };
    }
  }, []);

  /**
   * Execute batch operation with retry logic
   */
  const executeBatchWithRetry = useCallback(async <T>(
    items: Suggestion[],
    operation: (id: number) => Promise<T>,
    optimisticUpdate: (items: Suggestion[]) => void,
    rollbackUpdate: (items: Suggestion[]) => void,
    maxRetries = 3,
    retryDelay = 1000,
    options: OptimisticUpdateOptions<T> = {}
  ): Promise<{ success: boolean; processed: number; failed: number; errors: Array<{ id: number; error: string }> }> => {
    setIsProcessing(true);
    setProcessedCount(0);
    setFailedCount(0);
    setErrors([]);

    // Apply optimistic update
    optimisticUpdate(items);

    const results: Array<{ id: number; success: boolean; error?: string; retries: number }> = [];
    let successCount = 0;
    let failCount = 0;
    const batchErrors: Array<{ id: number; error: string }> = [];

    // Process each item with retry logic
    for (const item of items) {
      let retries = 0;
      let success = false;
      let lastError: string = '';

      while (retries < maxRetries && !success) {
        try {
          const result = await operation(item.id);
          success = true;
          results.push({ id: item.id, success: true, retries });
          successCount++;
          setProcessedCount(prev => prev + 1);
          
          options.onSuccess?.(result);
        } catch (error) {
          lastError = error instanceof Error ? error.message : 'Unknown error';
          retries++;
          
          if (retries < maxRetries) {
            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, retryDelay * retries));
          } else {
            // Max retries reached
            results.push({ id: item.id, success: false, error: lastError, retries });
            batchErrors.push({ id: item.id, error: lastError });
            failCount++;
            setFailedCount(prev => prev + 1);
            
            options.onError?.(error instanceof Error ? error : new Error(lastError));
          }
        }
      }
    }

    setErrors(batchErrors);
    setIsProcessing(false);

    // Rollback if all operations failed
    if (failCount === items.length) {
      setTimeout(() => {
        rollbackUpdate(items);
      }, options.rollbackDelay || 1000);
    }

    return {
      success: failCount === 0,
      processed: successCount,
      failed: failCount,
      errors: batchErrors,
    };
  }, []);

  return {
    isProcessing,
    processedCount,
    failedCount,
    errors,
    executeBatchOperation,
    executeSingleOperation,
    executeBatchWithRetry,
  };
};

export default useOptimisticUpdates;
