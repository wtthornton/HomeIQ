/**
 * Tests for API Usage Calculator
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { calculateAPIUsage, getUsageColor, getProgressBarColor } from '../utils/apiUsageCalculator';

describe('calculateAPIUsage', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('calculates zero usage when no teams selected', () => {
    const result = calculateAPIUsage([], []);
    
    expect(result.daily_calls).toBe(0);
    expect(result.within_free_tier).toBe(true);
    expect(result.warning_level).toBe('safe');
  });

  it('calculates 36 daily calls for 3 NFL teams within safe limits', () => {
    const result = calculateAPIUsage(['sf', 'dal', 'gb'], []);
    
    expect(result.daily_calls).toBe(36); // 3 teams × 12 calls
    expect(result.within_free_tier).toBe(true);
    expect(result.warning_level).toBe('safe');
  });

  it('calculates 60 daily calls for 5 teams across both leagues', () => {
    const result = calculateAPIUsage(['sf', 'dal'], ['bos', 'wsh', 'pit']);
    
    expect(result.daily_calls).toBe(60); // 5 teams × 12 calls
    expect(result.within_free_tier).toBe(true);
    expect(result.warning_level).toBe('safe');
  });

  it('displays caution warning when reaching 80+ daily calls', () => {
    const result = calculateAPIUsage(
      ['sf', 'dal', 'gb', 'ne', 'kc', 'pit'],  // 6 teams
      ['bos']  // 1 team = 7 total × 12 = 84 calls
    );
    
    expect(result.daily_calls).toBe(84);
    expect(result.within_free_tier).toBe(true);
    expect(result.warning_level).toBe('caution');
    expect(result.recommendation).toContain('Approaching free tier limit');
  });

  it('displays danger warning when exceeding free tier at 95+ calls', () => {
    const result = calculateAPIUsage(
      ['sf', 'dal', 'gb', 'ne', 'kc'],  // 5 teams
      ['bos', 'wsh', 'pit', 'chi']  // 4 teams = 9 total × 12 = 108 calls
    );
    
    expect(result.daily_calls).toBe(108);
    expect(result.within_free_tier).toBe(false);
    expect(result.warning_level).toBe('danger');
    expect(result.recommendation).toContain('upgrading to paid tier');
  });

  it('provides recommendation showing available team slots', () => {
    const result = calculateAPIUsage(['sf'], []); // 12 calls
    
    expect(result.recommendation).toContain('can add');
    expect(result.recommendation).toContain('team');
  });
});

describe('getUsageColor', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('returns green color for safe usage level', () => {
    const color = getUsageColor('safe');
    expect(color).toContain('green');
  });

  it('returns yellow color for caution usage level', () => {
    const color = getUsageColor('caution');
    expect(color).toContain('yellow');
  });

  it('returns red color for danger usage level', () => {
    const color = getUsageColor('danger');
    expect(color).toContain('red');
  });
});

describe('getProgressBarColor', () => {
  afterEach(() => {
    // ✅ Context7 Best Practice: Cleanup after each test
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('returns correct Tailwind class for each warning level', () => {
    expect(getProgressBarColor('safe')).toBe('bg-green-500');
    expect(getProgressBarColor('caution')).toBe('bg-yellow-500');
    expect(getProgressBarColor('danger')).toBe('bg-red-500');
  });
});

