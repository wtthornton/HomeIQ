/**
 * Selection Context for Batch Operations
 * Manages selection state across the application with keyboard support
 */

import React, { createContext, useContext, useReducer, useEffect, useCallback } from 'react';

// Selection State
interface SelectionState {
  selectedIds: Set<number>;
  isSelectMode: boolean;
  lastSelectedId: number | null;
}

// Selection Actions
type SelectionAction =
  | { type: 'SELECT_ITEM'; id: number; multi?: boolean }
  | { type: 'DESELECT_ITEM'; id: number }
  | { type: 'SELECT_ALL'; ids: number[] }
  | { type: 'CLEAR_SELECTION' }
  | { type: 'ENTER_SELECT_MODE' }
  | { type: 'EXIT_SELECT_MODE' }
  | { type: 'TOGGLE_SELECT_MODE' };

// Initial State
const initialState: SelectionState = {
  selectedIds: new Set(),
  isSelectMode: false,
  lastSelectedId: null,
};

// Selection Reducer
const selectionReducer = (state: SelectionState, action: SelectionAction): SelectionState => {
  switch (action.type) {
    case 'SELECT_ITEM': {
      const newSelectedIds = new Set(state.selectedIds);
      
      if (action.multi && state.lastSelectedId !== null) {
        // Multi-select: select range from last selected to current
        const start = Math.min(state.lastSelectedId, action.id);
        const end = Math.max(state.lastSelectedId, action.id);
        
        for (let i = start; i <= end; i++) {
          newSelectedIds.add(i);
        }
      } else {
        newSelectedIds.add(action.id);
      }
      
      return {
        ...state,
        selectedIds: newSelectedIds,
        lastSelectedId: action.id,
        isSelectMode: true,
      };
    }
    
    case 'DESELECT_ITEM': {
      const newSelectedIds = new Set(state.selectedIds);
      newSelectedIds.delete(action.id);
      
      return {
        ...state,
        selectedIds: newSelectedIds,
        lastSelectedId: newSelectedIds.size > 0 ? Array.from(newSelectedIds).pop() || null : null,
        isSelectMode: newSelectedIds.size > 0,
      };
    }
    
    case 'SELECT_ALL': {
      return {
        ...state,
        selectedIds: new Set(action.ids),
        lastSelectedId: action.ids[action.ids.length - 1] || null,
        isSelectMode: true,
      };
    }
    
    case 'CLEAR_SELECTION': {
      return {
        ...state,
        selectedIds: new Set(),
        lastSelectedId: null,
        isSelectMode: false,
      };
    }
    
    case 'ENTER_SELECT_MODE': {
      return {
        ...state,
        isSelectMode: true,
      };
    }
    
    case 'EXIT_SELECT_MODE': {
      return {
        ...state,
        selectedIds: new Set(),
        lastSelectedId: null,
        isSelectMode: false,
      };
    }
    
    case 'TOGGLE_SELECT_MODE': {
      return {
        ...state,
        isSelectMode: !state.isSelectMode,
        selectedIds: state.isSelectMode ? new Set() : state.selectedIds,
        lastSelectedId: state.isSelectMode ? null : state.lastSelectedId,
      };
    }
    
    default:
      return state;
  }
};

// Context Type
interface SelectionContextType {
  // State
  selectedIds: Set<number>;
  isSelectMode: boolean;
  selectedCount: number;
  
  // Actions
  selectItem: (id: number, multi?: boolean) => void;
  deselectItem: (id: number) => void;
  toggleItem: (id: number, multi?: boolean) => void;
  selectAll: (ids: number[]) => void;
  clearSelection: () => void;
  enterSelectMode: () => void;
  exitSelectMode: () => void;
  toggleSelectMode: () => void;
  
  // Helpers
  isSelected: (id: number) => boolean;
  getSelectedIds: () => number[];
  hasSelection: () => boolean;
}

// Create Context
const SelectionContext = createContext<SelectionContextType | undefined>(undefined);

// Provider Props
interface SelectionProviderProps {
  children: React.ReactNode;
}

// Selection Provider Component
export const SelectionProvider: React.FC<SelectionProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(selectionReducer, initialState);

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

    switch (event.key) {
      case 'Escape':
        if (state.isSelectMode || state.selectedIds.size > 0) {
          event.preventDefault();
          dispatch({ type: 'CLEAR_SELECTION' });
        }
        break;
        
      case 'a':
        if (event.ctrlKey || event.metaKey) {
          event.preventDefault();
          // This will be handled by the component that knows the available IDs
          // We'll dispatch a custom event that components can listen to
          window.dispatchEvent(new CustomEvent('select-all-requested'));
        }
        break;
        
      case 'Delete':
      case 'Backspace':
        if (state.selectedIds.size > 0) {
          event.preventDefault();
          // This will be handled by the component that knows what to delete
          window.dispatchEvent(new CustomEvent('batch-delete-requested', {
            detail: { selectedIds: Array.from(state.selectedIds) }
          }));
        }
        break;
    }
  }, [state.isSelectMode, state.selectedIds]);

  // Add Keyboard Event Listeners
  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Context Value
  const contextValue: SelectionContextType = {
    // State
    selectedIds: state.selectedIds,
    isSelectMode: state.isSelectMode,
    selectedCount: state.selectedIds.size,
    
    // Actions
    selectItem: (id: number, multi?: boolean) => {
      dispatch({ type: 'SELECT_ITEM', id, multi });
    },
    
    deselectItem: (id: number) => {
      dispatch({ type: 'DESELECT_ITEM', id });
    },
    
    toggleItem: (id: number, multi?: boolean) => {
      if (state.selectedIds.has(id)) {
        dispatch({ type: 'DESELECT_ITEM', id });
      } else {
        dispatch({ type: 'SELECT_ITEM', id, multi });
      }
    },
    
    selectAll: (ids: number[]) => {
      dispatch({ type: 'SELECT_ALL', ids });
    },
    
    clearSelection: () => {
      dispatch({ type: 'CLEAR_SELECTION' });
    },
    
    enterSelectMode: () => {
      dispatch({ type: 'ENTER_SELECT_MODE' });
    },
    
    exitSelectMode: () => {
      dispatch({ type: 'EXIT_SELECT_MODE' });
    },
    
    toggleSelectMode: () => {
      dispatch({ type: 'TOGGLE_SELECT_MODE' });
    },
    
    // Helpers
    isSelected: (id: number) => state.selectedIds.has(id),
    
    getSelectedIds: () => Array.from(state.selectedIds),
    
    hasSelection: () => state.selectedIds.size > 0,
  };

  return (
    <SelectionContext.Provider value={contextValue}>
      {children}
    </SelectionContext.Provider>
  );
};

// Hook to use Selection Context
export const useSelection = (): SelectionContextType => {
  const context = useContext(SelectionContext);
  if (context === undefined) {
    throw new Error('useSelection must be used within a SelectionProvider');
  }
  return context;
};

// Export types for use in other components
export type { SelectionContextType, SelectionState };
