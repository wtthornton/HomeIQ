/**
 * useTeamPreferences Hook
 * 
 * Manages team selection preferences in localStorage
 */

import { useState, useEffect } from 'react';
import type { StoredPreferences, League } from '../types/sports';

const STORAGE_KEY = 'sports_selected_teams';
const CURRENT_VERSION = 2;

const DEFAULT_PREFERENCES: StoredPreferences = {
  nfl_teams: [],
  nhl_teams: [],
  setup_completed: false,
  last_updated: new Date().toISOString(),
  version: CURRENT_VERSION
};

export const useTeamPreferences = () => {
  const [preferences, setPreferences] = useState<StoredPreferences>(DEFAULT_PREFERENCES);
  const [loading, setLoading] = useState(true);

  // Migration mapping: old ID -> new ID
  const migrationMap: Record<string, string> = {
    // NFL teams
    'dal': 'nfl-dal',    // Dallas Cowboys
    'car': 'nfl-car',    // Carolina Panthers
    'det': 'nfl-det',    // Detroit Lions
    'buf': 'nfl-buf',    // Buffalo Bills
    'phi': 'nfl-phi',    // Philadelphia Eagles
    'pit': 'nfl-pit',    // Pittsburgh Steelers
    'wsh': 'nfl-wsh',    // Washington Commanders
    'ari': 'nfl-ari',    // Arizona Cardinals
    'chi': 'nfl-chi',    // Chicago Bears
    'sea': 'nfl-sea',    // Seattle Seahawks
    'min': 'nfl-min',    // Minnesota Vikings
    // NHL teams
    'vgk': 'nhl-vgk',    // Vegas Golden Knights
    'bos': 'nhl-bos',    // Boston Bruins
    'fla': 'nhl-fla',    // Florida Panthers
    'mtl': 'nhl-mtl',    // Montreal Canadiens
    'ott': 'nhl-ott',    // Ottawa Senators
    'tbl': 'nhl-tbl',    // Tampa Bay Lightning
    'tor': 'nhl-tor',    // Toronto Maple Leafs
    'cbj': 'nhl-cbj',    // Columbus Blue Jackets
    'njd': 'nhl-njd',    // New Jersey Devils
    'nyi': 'nhl-nyi',    // New York Islanders
    'nyr': 'nhl-nyr',    // New York Rangers
    'col': 'nhl-col',    // Colorado Avalanche
    'ana': 'nhl-ana',    // Anaheim Ducks
    'cgy': 'nhl-cgy',    // Calgary Flames
    'edm': 'nhl-edm',    // Edmonton Oilers
    'lak': 'nhl-lak',    // Los Angeles Kings
    'sjs': 'nhl-sjs',    // San Jose Sharks
    'van': 'nhl-van',    // Vancouver Canucks
  };

  // Load from localStorage on mount with migration
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as StoredPreferences;
        
        // Check if migration is needed
        if (parsed.version < CURRENT_VERSION) {
          if (import.meta.env.MODE !== 'production') {
            console.log('🔄 Migrating team IDs to new format...');
          }
          
          // Migrate NFL teams
          const migratedNflTeams = parsed.nfl_teams.map(teamId => {
            const newId = migrationMap[teamId];
            if (newId) {
              if (import.meta.env.MODE !== 'production') {
                console.log(`✅ Migrated NFL: ${teamId} → ${newId}`);
              }
              return newId;
            }
            return teamId;
          });
          
          // Migrate NHL teams
          const migratedNhlTeams = parsed.nhl_teams.map(teamId => {
            const newId = migrationMap[teamId];
            if (newId) {
              if (import.meta.env.MODE !== 'production') {
                console.log(`✅ Migrated NHL: ${teamId} → ${newId}`);
              }
              return newId;
            }
            return teamId;
          });
          
          // Create migrated preferences
          const migratedPreferences: StoredPreferences = {
            ...parsed,
            nfl_teams: migratedNflTeams,
            nhl_teams: migratedNhlTeams,
            version: CURRENT_VERSION,
            last_updated: new Date().toISOString()
          };
          
          // Save migrated data
          localStorage.setItem(STORAGE_KEY, JSON.stringify(migratedPreferences));
          setPreferences(migratedPreferences);
          if (import.meta.env.MODE !== 'production') {
            console.log('🎉 Team ID migration complete!');
          }
        } else {
          setPreferences(parsed);
        }
      }
    } catch (error) {
      console.error('Error loading team preferences:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Save to localStorage whenever preferences change
  useEffect(() => {
    if (!loading) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
      } catch (error) {
        console.error('Error saving team preferences:', error);
      }
    }
  }, [preferences, loading]);

  // Listen for storage events from other tabs
  useEffect(() => {
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY && e.newValue) {
        try {
          const parsed = JSON.parse(e.newValue) as StoredPreferences;
          setPreferences(parsed);
        } catch (error) {
          console.error('Error syncing team preferences:', error);
        }
      }
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const addTeam = (league: League, teamId: string) => {
    setPreferences(prev => ({
      ...prev,
      nfl_teams: league === 'NFL' 
        ? [...new Set([...prev.nfl_teams, teamId])]
        : prev.nfl_teams,
      nhl_teams: league === 'NHL'
        ? [...new Set([...prev.nhl_teams, teamId])]
        : prev.nhl_teams,
      last_updated: new Date().toISOString()
    }));
  };

  const removeTeam = (league: League, teamId: string) => {
    setPreferences(prev => ({
      ...prev,
      nfl_teams: league === 'NFL'
        ? prev.nfl_teams.filter(id => id !== teamId)
        : prev.nfl_teams,
      nhl_teams: league === 'NHL'
        ? prev.nhl_teams.filter(id => id !== teamId)
        : prev.nhl_teams,
      last_updated: new Date().toISOString()
    }));
  };

  const setTeams = (nflTeams: string[], nhlTeams: string[]) => {
    setPreferences({
      nfl_teams: [...new Set(nflTeams)],
      nhl_teams: [...new Set(nhlTeams)],
      setup_completed: true,
      last_updated: new Date().toISOString(),
      version: CURRENT_VERSION
    });
  };

  const clearAll = () => {
    setPreferences(DEFAULT_PREFERENCES);
  };

  const hasAnyTeams = (): boolean => {
    return preferences.nfl_teams.length > 0 || preferences.nhl_teams.length > 0;
  };

  const getTotalTeamCount = (): number => {
    return preferences.nfl_teams.length + preferences.nhl_teams.length;
  };

  return {
    preferences,
    loading,
    addTeam,
    removeTeam,
    setTeams,
    clearAll,
    hasAnyTeams,
    getTotalTeamCount,
    nflTeams: preferences.nfl_teams,
    nhlTeams: preferences.nhl_teams,
    setupCompleted: preferences.setup_completed
  };
};

