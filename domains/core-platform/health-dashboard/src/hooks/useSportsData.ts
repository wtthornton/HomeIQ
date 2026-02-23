/**
 * useSportsData Hook
 * 
 * Fetches and manages sports game data from Home Assistant sensors
 * Reads from Team Tracker or hass-nhlapi HACS integrations
 * Following Context7 KB patterns for custom hooks
 */

import { useState, useEffect, useCallback } from 'react';
import { haClient } from '../services/haClient';
import type { Game, Team } from '../types/sports';

interface UseSportsDataProps {
  teamIds: string[];
  league?: 'NFL' | 'NHL' | 'all';
  pollInterval?: number;
}

export const useSportsData = ({
  teamIds,
  league = 'all',
  pollInterval = 30000
}: UseSportsDataProps) => {
  const [liveGames, setLiveGames] = useState<Game[]>([]);
  const [upcomingGames, setUpcomingGames] = useState<Game[]>([]);
  const [completedGames, setCompletedGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch games from HA sensors (memoized with useCallback from Context7 KB pattern)
  const fetchGames = useCallback(async () => {
    if (teamIds.length === 0) {
      setLiveGames([]);
      setUpcomingGames([]);
      setCompletedGames([]);
      setLoading(false);
      return;
    }

    try {
      setError(null);

      // Get sensors from Home Assistant
      const teamTrackerSensors = await haClient.getTeamTrackerSensors();
      const nhlSensors = await haClient.getNHLSensors();

      // Parse sensors into Game objects
      const parsedGames: Game[] = [];
      
      // Process Team Tracker sensors
      for (const sensor of teamTrackerSensors) {
        const game = parseTeamTrackerSensor(sensor);
        if (game && shouldIncludeGame(game, teamIds, league)) {
          parsedGames.push(game);
        }
      }

      // Process NHL sensors
      for (const sensor of nhlSensors) {
        const game = parseNHLSensor(sensor);
        if (game && shouldIncludeGame(game, teamIds, league)) {
          parsedGames.push(game);
        }
      }

      // Categorize games by status
      const live = parsedGames.filter(g => g.status === 'live');
      const upcoming = parsedGames.filter(g => g.status === 'scheduled');
      const completed = parsedGames.filter(g => g.status === 'final');

      setLiveGames(live);
      setUpcomingGames(upcoming);
      setCompletedGames(completed);
      setLastUpdate(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch sports data from HA');
      console.error('Sports data fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, [teamIds, league]);

  // Initial fetch and polling setup (Context7 KB useEffect pattern)
  useEffect(() => {
    fetchGames();

    // Set up polling for real-time updates
    const interval = setInterval(fetchGames, pollInterval);

    return () => clearInterval(interval);
  }, [fetchGames, pollInterval]);

  return {
    liveGames,
    upcomingGames,
    completedGames,
    loading,
    error,
    lastUpdate,
    refresh: fetchGames
  };
};

/**
 * Helper function to parse Team Tracker sensor into Game object
 */
function parseTeamTrackerSensor(sensor: any): Game | null {
  try {
    const attrs = sensor.attributes || {};
    // Create Team objects from attributes
    const homeTeam: Team = {
      id: attrs.home_team_id || attrs.team_id || '',
      name: attrs.home_team || attrs.team || '',
      abbreviation: attrs.home_team_abbr || attrs.team_abbr || '',
      logo: attrs.home_team_logo || attrs.team_logo || '',
      colors: {
        primary: attrs.home_team_color || '#000000',
        secondary: attrs.home_team_color_secondary || '#FFFFFF',
      },
      record: attrs.home_team_record ? {
        wins: attrs.home_team_record.wins || 0,
        losses: attrs.home_team_record.losses || 0,
        ties: attrs.home_team_record.ties,
      } : undefined,
    };
    
    const awayTeam: Team = {
      id: attrs.away_team_id || '',
      name: attrs.away_team || '',
      abbreviation: attrs.away_team_abbr || '',
      logo: attrs.away_team_logo || '',
      colors: {
        primary: attrs.away_team_color || '#000000',
        secondary: attrs.away_team_color_secondary || '#FFFFFF',
      },
      record: attrs.away_team_record ? {
        wins: attrs.away_team_record.wins || 0,
        losses: attrs.away_team_record.losses || 0,
        ties: attrs.away_team_record.ties,
      } : undefined,
    };
    
    return {
      id: sensor.entity_id,
      league: (attrs.league || 'NFL') as 'NFL' | 'NHL',
      status: mapStatus(sensor.state),
      startTime: attrs.start_time || new Date().toISOString(),
      homeTeam,
      awayTeam,
      score: {
        home: parseInt(attrs.home_score || '0'),
        away: parseInt(attrs.away_score || '0'),
      },
      period: {
        current: parseInt(attrs.period || attrs.quarter || '1'),
        total: attrs.total_periods || 4,
        timeRemaining: attrs.clock || undefined,
      },
      isFavorite: attrs.is_favorite || false,
    };
  } catch (error) {
    console.error('Error parsing Team Tracker sensor:', error);
    return null;
  }
}

/**
 * Helper function to parse NHL sensor into Game object
 */
function parseNHLSensor(sensor: any): Game | null {
  try {
    const attrs = sensor.attributes || {};
    // Create Team objects from attributes
    const homeTeam: Team = {
      id: attrs.home_team_id || '',
      name: attrs.home_team || '',
      abbreviation: attrs.home_team_abbr || '',
      logo: attrs.home_team_logo || '',
      colors: {
        primary: attrs.home_team_color || '#000000',
        secondary: attrs.home_team_color_secondary || '#FFFFFF',
      },
      record: attrs.home_team_record ? {
        wins: attrs.home_team_record.wins || 0,
        losses: attrs.home_team_record.losses || 0,
        ties: attrs.home_team_record.ties,
      } : undefined,
    };
    
    const awayTeam: Team = {
      id: attrs.away_team_id || '',
      name: attrs.away_team || '',
      abbreviation: attrs.away_team_abbr || '',
      logo: attrs.away_team_logo || '',
      colors: {
        primary: attrs.away_team_color || '#000000',
        secondary: attrs.away_team_color_secondary || '#FFFFFF',
      },
      record: attrs.away_team_record ? {
        wins: attrs.away_team_record.wins || 0,
        losses: attrs.away_team_record.losses || 0,
        ties: attrs.away_team_record.ties,
      } : undefined,
    };
    
    return {
      id: sensor.entity_id,
      league: 'NHL',
      status: mapStatus(sensor.state),
      startTime: attrs.start_time || new Date().toISOString(),
      homeTeam,
      awayTeam,
      score: {
        home: parseInt(attrs.home_score || '0'),
        away: parseInt(attrs.away_score || '0'),
      },
      period: {
        current: parseInt(attrs.period || '1'),
        total: attrs.total_periods || 3,
        timeRemaining: attrs.clock || undefined,
      },
      isFavorite: attrs.is_favorite || false,
    };
  } catch (error) {
    console.error('Error parsing NHL sensor:', error);
    return null;
  }
}

/**
 * Map sensor state to game status
 */
function mapStatus(state: string): 'scheduled' | 'live' | 'final' {
  const stateMap: Record<string, 'scheduled' | 'live' | 'final'> = {
    'LIVE': 'live',
    'CRIT': 'live',
    'IN_PROGRESS': 'live',
    'PRE': 'scheduled',
    'SCHEDULED': 'scheduled',
    'UPCOMING': 'scheduled',
    'FINAL': 'final',
    'OVER': 'final',
    'FIN': 'final',
    'COMPLETED': 'final',
  };
  return stateMap[state.toUpperCase()] || 'scheduled';
}

/**
 * Check if game should be included based on team and league filters
 */
function shouldIncludeGame(game: Game, teamIds: string[], league: string): boolean {
  if (league !== 'all' && game.league !== league) {
    return false;
  }
  
  const homeMatch = teamIds.some(id => 
    game.homeTeam.id.toLowerCase().includes(id.toLowerCase()) ||
    game.homeTeam.name.toLowerCase().includes(id.toLowerCase())
  );
  const awayMatch = teamIds.some(id => 
    game.awayTeam.id.toLowerCase().includes(id.toLowerCase()) ||
    game.awayTeam.name.toLowerCase().includes(id.toLowerCase())
  );
  
  return homeMatch || awayMatch;
}

