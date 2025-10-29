/**
 * useSportsData Hook
 * 
 * Fetches and manages sports game data from Home Assistant sensors
 * Reads from Team Tracker or hass-nhlapi HACS integrations
 * Following Context7 KB patterns for custom hooks
 */

import { useState, useEffect, useCallback } from 'react';
import { haClient } from '../services/haClient';
import type { Game } from '../types/sports';

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
      const live = parsedGames.filter(g => g.status === 'LIVE' || g.status === 'IN_PROGRESS');
      const upcoming = parsedGames.filter(g => g.status === 'SCHEDULED' || g.status === 'UPCOMING');
      const completed = parsedGames.filter(g => g.status === 'FINAL' || g.status === 'COMPLETED');

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
    return {
      id: sensor.entity_id,
      league: attrs.league || 'NFL',
      homeTeam: attrs.home_team || attrs.team || '',
      awayTeam: attrs.away_team || '',
      homeScore: parseInt(attrs.home_score || '0'),
      awayScore: parseInt(attrs.away_score || '0'),
      status: mapStatus(sensor.state),
      startTime: attrs.start_time || new Date().toISOString(),
      venue: attrs.venue || '',
      period: attrs.period || attrs.quarter || '',
      clock: attrs.clock || '',
      isLive: sensor.state === 'LIVE',
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
    return {
      id: sensor.entity_id,
      league: 'NHL',
      homeTeam: attrs.home_team || '',
      awayTeam: attrs.away_team || '',
      homeScore: parseInt(attrs.home_score || '0'),
      awayScore: parseInt(attrs.away_score || '0'),
      status: mapStatus(sensor.state),
      startTime: attrs.start_time || new Date().toISOString(),
      venue: attrs.venue || '',
      period: attrs.period || '',
      clock: attrs.clock || '',
      isLive: sensor.state === 'LIVE' || sensor.state === 'CRIT',
    };
  } catch (error) {
    console.error('Error parsing NHL sensor:', error);
    return null;
  }
}

/**
 * Map sensor state to game status
 */
function mapStatus(state: string): string {
  const stateMap: Record<string, string> = {
    'LIVE': 'LIVE',
    'CRIT': 'LIVE',
    'PRE': 'SCHEDULED',
    'FINAL': 'FINAL',
    'OVER': 'FINAL',
    'FIN': 'FINAL',
  };
  return stateMap[state] || state;
}

/**
 * Check if game should be included based on team and league filters
 */
function shouldIncludeGame(game: Game, teamIds: string[], league: string): boolean {
  if (league !== 'all' && game.league !== league) {
    return false;
  }
  
  const homeMatch = teamIds.some(id => game.homeTeam.toLowerCase().includes(id.toLowerCase()));
  const awayMatch = teamIds.some(id => game.awayTeam.toLowerCase().includes(id.toLowerCase()));
  
  return homeMatch || awayMatch;
}

