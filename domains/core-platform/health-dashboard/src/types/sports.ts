/**
 * Sports Data Types
 * 
 * Type definitions for NFL/NHL sports integration
 */

export interface Team {
  id: string;
  name: string;
  abbreviation: string;
  logo: string;
  colors: {
    primary: string;
    secondary: string;
  };
  record?: {
    wins: number;
    losses: number;
    ties?: number;
  };
}

export interface Game {
  id: string;
  league: 'NFL' | 'NHL';
  status: 'scheduled' | 'live' | 'final';
  startTime: string;
  homeTeam: Team;
  awayTeam: Team;
  score: {
    home: number;
    away: number;
  };
  period: {
    current: number;
    total: number;
    timeRemaining?: string;
  };
  isFavorite?: boolean;
}

export interface GameStats {
  [key: string]: {
    home: number;
    away: number;
  };
}

export interface StoredPreferences {
  nfl_teams: string[];
  nhl_teams: string[];
  setup_completed: boolean;
  last_updated: string;
  version: number;
}

export interface APIUsageInfo {
  daily_calls: number;
  within_free_tier: boolean;
  warning_level: 'safe' | 'caution' | 'danger';
  recommendation: string;
}

export type League = 'NFL' | 'NHL';

