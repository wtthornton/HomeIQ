/**
 * API Usage Calculator
 * 
 * Calculates estimated API usage based on selected teams
 */

import type { APIUsageInfo } from '../types/sports';

const CALLS_PER_TEAM_PER_DAY = 12;
const FREE_TIER_LIMIT = 100;
const CAUTION_THRESHOLD = 80;
const DANGER_THRESHOLD = 95;

export function calculateAPIUsage(
  nflTeams: string[],
  nhlTeams: string[]
): APIUsageInfo {
  const totalTeams = nflTeams.length + nhlTeams.length;
  const dailyCalls = totalTeams * CALLS_PER_TEAM_PER_DAY;
  
  let warningLevel: 'safe' | 'caution' | 'danger' = 'safe';
  let recommendation = '';
  
  if (dailyCalls > DANGER_THRESHOLD) {
    warningLevel = 'danger';
    recommendation = '⚠️ Consider removing teams or upgrading to paid tier';
  } else if (dailyCalls > CAUTION_THRESHOLD) {
    warningLevel = 'caution';
    recommendation = '⚠️ Approaching free tier limit. Monitor usage carefully.';
  } else {
    const remaining = Math.floor((FREE_TIER_LIMIT - dailyCalls) / CALLS_PER_TEAM_PER_DAY);
    recommendation = `✅ You can add ${remaining} more team${remaining !== 1 ? 's' : ''}`;
  }
  
  return {
    daily_calls: dailyCalls,
    within_free_tier: dailyCalls <= FREE_TIER_LIMIT,
    warning_level: warningLevel,
    recommendation
  };
}

export function getUsageColor(warningLevel: 'safe' | 'caution' | 'danger'): string {
  switch (warningLevel) {
    case 'safe':
      return 'text-green-600 dark:text-green-400';
    case 'caution':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'danger':
      return 'text-red-600 dark:text-red-400';
  }
}

export function getProgressBarColor(warningLevel: 'safe' | 'caution' | 'danger'): string {
  switch (warningLevel) {
    case 'safe':
      return 'bg-green-500';
    case 'caution':
      return 'bg-yellow-500';
    case 'danger':
      return 'bg-red-500';
  }
}

