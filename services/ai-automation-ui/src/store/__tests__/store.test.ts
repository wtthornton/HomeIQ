/**
 * Unit Tests for Zustand Store
 * 
 * Tests the global state management store including:
 * - Suggestions management
 * - Schedule info management
 * - Analysis status management
 * - Dark mode toggle and localStorage integration
 * - Status selection
 * - Loading state
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAppStore } from '../../store';
import type { Suggestion, ScheduleInfo, AnalysisStatus } from '../../types';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

describe('useAppStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useAppStore.setState({
      suggestions: [],
      scheduleInfo: null,
      analysisStatus: null,
      darkMode: false,
      selectedStatus: 'pending',
      isLoading: false,
    });
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('Suggestions Management', () => {
    it('should initialize with empty suggestions array', () => {
      const { suggestions } = useAppStore.getState();
      expect(suggestions).toEqual([]);
    });

    it('should set suggestions', () => {
      const mockSuggestions: Suggestion[] = [
        {
          id: 1,
          title: 'Test Suggestion',
          description: 'Test Description',
          confidence: 0.8,
          status: 'pending',
        },
      ];

      useAppStore.getState().setSuggestions(mockSuggestions);
      const { suggestions } = useAppStore.getState();
      expect(suggestions).toEqual(mockSuggestions);
    });

    it('should replace existing suggestions', () => {
      const initialSuggestions: Suggestion[] = [
        { id: 1, title: 'Suggestion 1', description: 'Desc 1', confidence: 0.5, status: 'pending' },
      ];
      const newSuggestions: Suggestion[] = [
        { id: 2, title: 'Suggestion 2', description: 'Desc 2', confidence: 0.9, status: 'approved' },
      ];

      useAppStore.getState().setSuggestions(initialSuggestions);
      useAppStore.getState().setSuggestions(newSuggestions);
      const { suggestions } = useAppStore.getState();
      expect(suggestions).toEqual(newSuggestions);
      expect(suggestions).not.toContain(initialSuggestions[0]);
    });

    it('should handle empty suggestions array', () => {
      const mockSuggestions: Suggestion[] = [
        { id: 1, title: 'Test', description: 'Test', confidence: 0.5, status: 'pending' },
      ];
      useAppStore.getState().setSuggestions(mockSuggestions);
      useAppStore.getState().setSuggestions([]);
      const { suggestions } = useAppStore.getState();
      expect(suggestions).toEqual([]);
    });
  });

  describe('Schedule Info Management', () => {
    it('should initialize with null schedule info', () => {
      const { scheduleInfo } = useAppStore.getState();
      expect(scheduleInfo).toBeNull();
    });

    it('should set schedule info', () => {
      const mockScheduleInfo: ScheduleInfo = {
        schedule: 'daily',
        next_run: '2025-12-23T10:00:00Z',
        is_running: false,
        recent_jobs: [],
      };

      useAppStore.getState().setScheduleInfo(mockScheduleInfo);
      const { scheduleInfo } = useAppStore.getState();
      expect(scheduleInfo).toEqual(mockScheduleInfo);
    });

    it('should clear schedule info when set to null', () => {
      const mockScheduleInfo: ScheduleInfo = {
        schedule: 'daily',
        next_run: '2025-12-23T10:00:00Z',
        is_running: false,
        recent_jobs: [],
      };
      useAppStore.getState().setScheduleInfo(mockScheduleInfo);
      useAppStore.getState().setScheduleInfo(null);
      const { scheduleInfo } = useAppStore.getState();
      expect(scheduleInfo).toBeNull();
    });
  });

  describe('Analysis Status Management', () => {
    it('should initialize with null analysis status', () => {
      const { analysisStatus } = useAppStore.getState();
      expect(analysisStatus).toBeNull();
    });

    it('should set analysis status', () => {
      const mockStatus: AnalysisStatus = {
        status: 'running',
        patterns: {
          total_patterns: 0,
          by_type: {},
          unique_devices: 0,
          avg_confidence: 0,
        },
        suggestions: {
          pending_count: 0,
          recent: [],
        },
      };

      useAppStore.getState().setAnalysisStatus(mockStatus);
      const { analysisStatus } = useAppStore.getState();
      expect(analysisStatus).toEqual(mockStatus);
    });

    it('should clear analysis status when set to null', () => {
      const mockStatus: AnalysisStatus = {
        status: 'completed',
        patterns: {
          total_patterns: 0,
          by_type: {},
          unique_devices: 0,
          avg_confidence: 0,
        },
        suggestions: {
          pending_count: 0,
          recent: [],
        },
      };
      useAppStore.getState().setAnalysisStatus(mockStatus);
      useAppStore.getState().setAnalysisStatus(null);
      const { analysisStatus } = useAppStore.getState();
      expect(analysisStatus).toBeNull();
    });
  });

  describe('Dark Mode Management', () => {
    it('should initialize dark mode from localStorage', () => {
      localStorageMock.setItem('darkMode', 'true');
      // Note: Initial state is set at store creation, so we need to test initializeDarkMode
      useAppStore.getState().initializeDarkMode();
      expect(localStorageMock.getItem).toHaveBeenCalledWith('darkMode');
    });

    it('should default to light mode when localStorage is empty', () => {
      localStorageMock.clear();
      useAppStore.getState().initializeDarkMode();
      const { darkMode } = useAppStore.getState();
      expect(darkMode).toBe(false);
    });

    it('should toggle dark mode', () => {
      const { darkMode: initialDarkMode, toggleDarkMode } = useAppStore.getState();
      toggleDarkMode();
      const { darkMode: newDarkMode } = useAppStore.getState();
      expect(newDarkMode).toBe(!initialDarkMode);
    });

    it('should save dark mode to localStorage when toggled', () => {
      const { toggleDarkMode } = useAppStore.getState();
      toggleDarkMode();
      expect(localStorageMock.setItem).toHaveBeenCalledWith('darkMode', expect.any(String));
    });

    it('should handle localStorage errors gracefully', () => {
      // Mock localStorage.setItem to throw an error
      const originalSetItem = localStorageMock.setItem;
      localStorageMock.setItem = vi.fn(() => {
        throw new Error('localStorage quota exceeded');
      });

      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const { toggleDarkMode } = useAppStore.getState();
      
      // Should not throw
      expect(() => toggleDarkMode()).not.toThrow();
      
      // Should log warning
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to save darkMode to localStorage'),
        expect.any(Error)
      );

      // Restore
      localStorageMock.setItem = originalSetItem;
      consoleSpy.mockRestore();
    });

    it('should handle missing window object (SSR)', () => {
      const originalWindow = (globalThis as any).window;
      delete (globalThis as any).window;

      const { initializeDarkMode } = useAppStore.getState();
      expect(() => initializeDarkMode()).not.toThrow();

      const { darkMode } = useAppStore.getState();
      expect(darkMode).toBe(false);

      (globalThis as any).window = originalWindow;
    });
  });

  describe('Status Selection', () => {
    it('should initialize with pending status', () => {
      const { selectedStatus } = useAppStore.getState();
      expect(selectedStatus).toBe('pending');
    });

    it('should set selected status', () => {
      const statuses: Array<'pending' | 'approved' | 'rejected' | 'deployed'> = [
        'approved',
        'rejected',
        'deployed',
      ];

      statuses.forEach((status) => {
        useAppStore.getState().setSelectedStatus(status);
        const { selectedStatus } = useAppStore.getState();
        expect(selectedStatus).toBe(status);
      });
    });
  });

  describe('Loading State', () => {
    it('should initialize with loading false', () => {
      const { isLoading } = useAppStore.getState();
      expect(isLoading).toBe(false);
    });

    it('should set loading state', () => {
      useAppStore.getState().setIsLoading(true);
      const { isLoading } = useAppStore.getState();
      expect(isLoading).toBe(true);

      useAppStore.getState().setIsLoading(false);
      const { isLoading: isLoadingAfter } = useAppStore.getState();
      expect(isLoadingAfter).toBe(false);
    });
  });

  describe('Integration Tests', () => {
    it('should handle multiple state updates correctly', () => {
      const mockSuggestion: Suggestion = {
        id: 1,
        title: 'Test',
        description: 'Test',
        confidence: 0.8,
        status: 'pending',
      };
      const mockSchedule: ScheduleInfo = {
        schedule: 'daily',
        next_run: '2025-12-23T10:00:00Z',
        is_running: false,
        recent_jobs: [],
      };

      useAppStore.getState().setSuggestions([mockSuggestion]);
      useAppStore.getState().setScheduleInfo(mockSchedule);
      useAppStore.getState().setIsLoading(true);
      useAppStore.getState().toggleDarkMode();

      const state = useAppStore.getState();
      expect(state.suggestions).toEqual([mockSuggestion]);
      expect(state.scheduleInfo).toEqual(mockSchedule);
      expect(state.isLoading).toBe(true);
      expect(state.darkMode).toBe(true);
    });

    it('should maintain state consistency across multiple updates', () => {
      const { setSuggestions, setSelectedStatus, setIsLoading } = useAppStore.getState();
      
      setSuggestions([
        { id: 1, title: 'Test 1', description: 'Desc 1', confidence: 0.5, status: 'pending' },
        { id: 2, title: 'Test 2', description: 'Desc 2', confidence: 0.7, status: 'approved' },
      ]);
      setSelectedStatus('approved');
      setIsLoading(true);

      const state = useAppStore.getState();
      expect(state.suggestions).toHaveLength(2);
      expect(state.selectedStatus).toBe('approved');
      expect(state.isLoading).toBe(true);
    });
  });
});

