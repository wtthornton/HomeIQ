/**
 * Keyboard Shortcuts Hook
 * Provides keyboard shortcuts for batch operations and navigation
 */

import { useEffect, useCallback } from 'react';
import { useSelection } from '../context/SelectionContext';

interface KeyboardShortcutsOptions {
  availableIds?: number[];
  onBatchApprove?: (ids: number[]) => void;
  onBatchReject?: (ids: number[]) => void;
  onBatchDelete?: (ids: number[]) => void;
  onSelectAll?: () => void;
}

export const useKeyboardShortcuts = (options: KeyboardShortcutsOptions = {}) => {
  const {
    availableIds = [],
    onBatchApprove,
    onBatchReject,
    onBatchDelete,
    onSelectAll,
  } = options;

  const {
    selectedCount,
    selectAll,
    clearSelection,
    getSelectedIds,
    hasSelection,
  } = useSelection();

  // Handle Select All Request
  const handleSelectAll = useCallback(() => {
    if (availableIds.length > 0) {
      selectAll(availableIds);
      onSelectAll?.();
    }
  }, [availableIds, selectAll, onSelectAll]);

  // Handle Batch Delete Request
  const handleBatchDelete = useCallback(() => {
    const selected = getSelectedIds();
    if (selected.length > 0 && onBatchDelete) {
      onBatchDelete(selected);
    }
  }, [getSelectedIds, onBatchDelete]);

  // Handle Batch Approve (Enter key)
  const handleBatchApprove = useCallback(() => {
    const selected = getSelectedIds();
    if (selected.length > 0 && onBatchApprove) {
      onBatchApprove(selected);
    }
  }, [getSelectedIds, onBatchApprove]);

  // Handle Batch Reject (Delete key)
  const handleBatchReject = useCallback(() => {
    const selected = getSelectedIds();
    if (selected.length > 0 && onBatchReject) {
      onBatchReject(selected);
    }
  }, [getSelectedIds, onBatchReject]);

  // Keyboard Event Handler
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    // Only handle keyboard shortcuts when not in input/textarea
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      event.target instanceof HTMLSelectElement
    ) {
      return;
    }

    // Handle specific keyboard shortcuts
    switch (event.key) {
      case 'Enter':
        if (hasSelection()) {
          event.preventDefault();
          handleBatchApprove();
        }
        break;
        
      case 'Delete':
      case 'Backspace':
        if (hasSelection()) {
          event.preventDefault();
          handleBatchReject();
        }
        break;
        
      case 'Escape':
        if (hasSelection()) {
          event.preventDefault();
          clearSelection();
        }
        break;
    }
  }, [hasSelection, handleBatchApprove, handleBatchReject, clearSelection]);

  // Add Event Listeners
  useEffect(() => {
    // Add keyboard event listener
    document.addEventListener('keydown', handleKeyDown);
    
    // Add custom event listeners for cross-component communication
    const handleSelectAllRequested = () => handleSelectAll();
    const handleBatchDeleteRequested = () => handleBatchDelete();
    
    window.addEventListener('select-all-requested', handleSelectAllRequested);
    window.addEventListener('batch-delete-requested', handleBatchDeleteRequested);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('select-all-requested', handleSelectAllRequested);
      window.removeEventListener('batch-delete-requested', handleBatchDeleteRequested);
    };
  }, [handleKeyDown, handleSelectAll, handleBatchDelete]);

  // Return keyboard shortcut info for UI display
  return {
    shortcuts: {
      selectAll: 'Ctrl+A',
      approve: 'Enter',
      reject: 'Delete',
      clear: 'Escape',
    },
    selectedCount,
    hasSelection: hasSelection(),
    availableCount: availableIds.length,
  };
};
