/**
 * Tests for useTeamPreferences Hook
 * 
 * Following Vitest patterns from Context7 KB
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTeamPreferences } from '../hooks/useTeamPreferences';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};

  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('useTeamPreferences', () => {
  beforeEach(() => {
    // Clear localStorage before each test (Context7 KB pattern)
    localStorageMock.clear();
  });

  it('should initialize with empty preferences', () => {
    const { result } = renderHook(() => useTeamPreferences());

    expect(result.current.nflTeams).toEqual([]);
    expect(result.current.nhlTeams).toEqual([]);
    expect(result.current.setupCompleted).toBe(false);
  });

  it('should add NFL team', async () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.addTeam('NFL', 'sf');
    });

    expect(result.current.nflTeams).toContain('sf');
    expect(result.current.nhlTeams).toEqual([]);
  });

  it('should add NHL team', async () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.addTeam('NHL', 'bos');
    });

    expect(result.current.nhlTeams).toContain('bos');
    expect(result.current.nflTeams).toEqual([]);
  });

  it('should remove team', async () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.addTeam('NFL', 'sf');
      result.current.addTeam('NFL', 'dal');
    });

    expect(result.current.nflTeams).toHaveLength(2);

    act(() => {
      result.current.removeTeam('NFL', 'sf');
    });

    expect(result.current.nflTeams).toHaveLength(1);
    expect(result.current.nflTeams).not.toContain('sf');
    expect(result.current.nflTeams).toContain('dal');
  });

  it('should set multiple teams at once', async () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.setTeams(['sf', 'dal'], ['bos', 'wsh']);
    });

    expect(result.current.nflTeams).toEqual(['sf', 'dal']);
    expect(result.current.nhlTeams).toEqual(['bos', 'wsh']);
    expect(result.current.setupCompleted).toBe(true);
  });

  it('should save to localStorage', async () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.addTeam('NFL', 'sf');
    });

    // Wait for effect to run
    await vi.waitFor(() => {
      const stored = localStorage.getItem('sports_selected_teams');
      expect(stored).toBeTruthy();
      
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.nfl_teams).toContain('sf');
      }
    });
  });

  it('should load from localStorage on init', () => {
    // Pre-populate localStorage
    localStorage.setItem('sports_selected_teams', JSON.stringify({
      nfl_teams: ['gb', 'kc'],
      nhl_teams: ['pit'],
      setup_completed: true,
      last_updated: new Date().toISOString(),
      version: 1
    }));

    const { result } = renderHook(() => useTeamPreferences());

    expect(result.current.loading).toBe(false);
    expect(result.current.nflTeams).toEqual(['gb', 'kc']);
    expect(result.current.nhlTeams).toEqual(['pit']);
    expect(result.current.setupCompleted).toBe(true);
  });

  it('should prevent duplicate teams', () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.addTeam('NFL', 'sf');
      result.current.addTeam('NFL', 'sf'); // Duplicate
    });

    expect(result.current.nflTeams).toEqual(['sf']);
  });

  it('should calculate total team count correctly', () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.setTeams(['sf', 'dal'], ['bos']);
    });

    expect(result.current.getTotalTeamCount()).toBe(3);
  });

  it('should detect if any teams are selected', () => {
    const { result } = renderHook(() => useTeamPreferences());

    expect(result.current.hasAnyTeams()).toBe(false);

    act(() => {
      result.current.addTeam('NFL', 'sf');
    });

    expect(result.current.hasAnyTeams()).toBe(true);
  });

  it('should clear all teams', () => {
    const { result } = renderHook(() => useTeamPreferences());

    act(() => {
      result.current.setTeams(['sf', 'dal'], ['bos', 'wsh']);
    });

    expect(result.current.getTotalTeamCount()).toBe(4);

    act(() => {
      result.current.clearAll();
    });

    expect(result.current.getTotalTeamCount()).toBe(0);
    expect(result.current.setupCompleted).toBe(false);
  });
});

