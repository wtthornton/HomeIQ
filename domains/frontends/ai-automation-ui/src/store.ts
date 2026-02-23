/**
 * Global State Management with Zustand
 */

import { create } from 'zustand';
import type { Suggestion, ScheduleInfo, AnalysisStatus } from './types';

interface AppState {
  // Suggestions
  suggestions: Suggestion[];
  setSuggestions: (suggestions: Suggestion[]) => void;
  
  // Schedule
  scheduleInfo: ScheduleInfo | null;
  setScheduleInfo: (info: ScheduleInfo | null) => void;
  
  // Analysis Status
  analysisStatus: AnalysisStatus | null;
  setAnalysisStatus: (status: AnalysisStatus | null) => void;
  
  // UI State
  darkMode: boolean;
  toggleDarkMode: () => void;
  
  // Initialize dark mode from localStorage safely
  initializeDarkMode: () => void;
  
  selectedStatus: 'pending' | 'approved' | 'rejected' | 'deployed';
  setSelectedStatus: (status: 'pending' | 'approved' | 'rejected' | 'deployed') => void;
  
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Suggestions
  suggestions: [],
  setSuggestions: (suggestions) => set({ suggestions }),
  
  // Schedule
  scheduleInfo: null,
  setScheduleInfo: (info) => set({ scheduleInfo: info }),
  
  // Analysis Status
  analysisStatus: null,
  setAnalysisStatus: (status) => set({ analysisStatus: status }),
  
  // UI State
  darkMode: (() => {
    // SECURITY: Safely read from localStorage with error handling
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return localStorage.getItem('darkMode') === 'true';
      }
    } catch (error) {
      console.warn('Failed to read darkMode from localStorage:', error);
    }
    return false; // Default to light mode
  })(),
  toggleDarkMode: () => set((state) => {
    const newDarkMode = !state.darkMode;
    // SECURITY: Safely write to localStorage with error handling
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        localStorage.setItem('darkMode', String(newDarkMode));
      }
    } catch (error) {
      console.warn('Failed to save darkMode to localStorage:', error);
    }
    return { darkMode: newDarkMode };
  }),
  initializeDarkMode: () => set(() => {
    // SECURITY: Safely initialize dark mode from localStorage
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem('darkMode');
        return { darkMode: stored === 'true' };
      }
    } catch (error) {
      console.warn('Failed to initialize darkMode from localStorage:', error);
    }
    return { darkMode: false };
  }),
  
  selectedStatus: 'pending',
  setSelectedStatus: (status) => set({ selectedStatus: status }),
  
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
}));

