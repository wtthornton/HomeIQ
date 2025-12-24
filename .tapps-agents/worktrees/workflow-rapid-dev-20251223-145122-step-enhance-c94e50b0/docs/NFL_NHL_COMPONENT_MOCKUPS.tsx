/**
 * NFL & NHL Integration - Component Mockups
 * 
 * This file contains React component mockups demonstrating the UX/UI design
 * for the sports integration feature. These are visual prototypes showing
 * the intended look and feel.
 * 
 * Based on research from:
 * - Context7 KB: Recharts library for data visualization
 * - Web research: Sports dashboard best practices
 * - Existing codebase: Dashboard patterns and hooks
 */

import React, { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

interface Team {
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

interface Game {
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

interface GameStats {
  [key: string]: {
    home: number;
    away: number;
  };
}

// ============================================================================
// LIVE GAME CARD COMPONENT
// ============================================================================

export const LiveGameCard: React.FC<{ game: Game; darkMode?: boolean }> = ({ 
  game, 
  darkMode = false 
}) => {
  const [pulse, setPulse] = useState(false);
  const [scoreChanged, setScoreChanged] = useState(false);

  // Simulate score change animation
  const handleScoreChange = () => {
    setScoreChanged(true);
    setTimeout(() => setScoreChanged(false), 600);
  };

  // Pulse animation for live indicator
  useEffect(() => {
    if (game.status === 'live') {
      const interval = setInterval(() => setPulse(prev => !prev), 1000);
      return () => clearInterval(interval);
    }
  }, [game.status]);

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-300' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  return (
    <div className={`${cardBg} rounded-xl shadow-lg border ${borderColor} overflow-hidden transition-all duration-200 hover:shadow-xl hover:-translate-y-1`}>
      {/* Header */}
      <div className={`${game.status === 'live' ? 'bg-green-500' : 'bg-gray-500'} px-4 py-2 flex items-center justify-between`}>
        <div className="flex items-center space-x-2">
          {game.status === 'live' && (
            <div className={`w-3 h-3 bg-white rounded-full ${pulse ? 'animate-pulse' : ''}`} />
          )}
          <span className="text-white font-bold uppercase text-sm">
            {game.status === 'live' ? '🟢 LIVE' : game.status.toUpperCase()}
          </span>
        </div>
        <div className="flex items-center space-x-3 text-white text-sm">
          <span>{game.league === 'NFL' ? `Q${game.period.current}` : `P${game.period.current}`}</span>
          <span className="font-mono">{game.period.timeRemaining || '--:--'}</span>
          {game.isFavorite && <span className="text-yellow-300">⭐</span>}
        </div>
      </div>

      {/* Teams & Scores */}
      <div className="p-6">
        <div className="grid grid-cols-7 gap-4 items-center">
          {/* Away Team */}
          <div className="col-span-3 text-center">
            <div className="flex flex-col items-center space-y-2">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
                style={{ backgroundColor: `${game.awayTeam.colors.primary}20` }}
              >
                {game.league === 'NFL' ? '🏈' : '🏒'}
              </div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.awayTeam.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.awayTeam.record && 
                  `${game.awayTeam.record.wins}-${game.awayTeam.record.losses}${game.awayTeam.record.ties ? `-${game.awayTeam.record.ties}` : ''}`
                }
              </div>
              <div className={`text-4xl font-bold ${textPrimary} ${scoreChanged ? 'animate-bounce' : ''}`}>
                {game.score.away}
              </div>
            </div>
          </div>

          {/* VS Divider */}
          <div className="col-span-1 text-center">
            <div className={`text-2xl font-bold ${textSecondary}`}>vs</div>
          </div>

          {/* Home Team */}
          <div className="col-span-3 text-center">
            <div className="flex flex-col items-center space-y-2">
              <div 
                className="w-16 h-16 rounded-full flex items-center justify-center text-3xl"
                style={{ backgroundColor: `${game.homeTeam.colors.primary}20` }}
              >
                {game.league === 'NFL' ? '🏈' : '🏒'}
              </div>
              <div className={`font-semibold ${textPrimary}`}>
                {game.homeTeam.name}
              </div>
              <div className={`text-xs ${textSecondary}`}>
                {game.homeTeam.record && 
                  `${game.homeTeam.record.wins}-${game.homeTeam.record.losses}${game.homeTeam.record.ties ? `-${game.homeTeam.record.ties}` : ''}`
                }
              </div>
              <div className={`text-4xl font-bold ${textPrimary} ${scoreChanged ? 'animate-bounce' : ''}`}>
                {game.score.home}
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex gap-3">
          <button 
            className={`flex-1 py-2 px-4 rounded-lg ${darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'} text-white font-medium transition-colors`}
          >
            📊 Full Stats
          </button>
          <button 
            className={`flex-1 py-2 px-4 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textPrimary} font-medium transition-colors`}
          >
            📺 Watch
          </button>
          <button 
            className={`py-2 px-4 rounded-lg ${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'} ${textPrimary} transition-colors`}
          >
            🔔
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// STATS COMPARISON COMPONENT
// ============================================================================

export const StatsComparison: React.FC<{ stats: GameStats; darkMode?: boolean }> = ({ 
  stats, 
  darkMode = false 
}) => {
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  const renderStatBar = (label: string, homeValue: number, awayValue: number) => {
    const total = homeValue + awayValue;
    const homePercent = (homeValue / total) * 100;
    const awayPercent = (awayValue / total) * 100;

    return (
      <div className="mb-4">
        <div className="flex justify-between mb-1">
          <span className={`text-sm ${textSecondary}`}>{label}</span>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-sm font-bold ${textPrimary} w-16 text-right`}>
            {homeValue}
          </span>
          <div className="flex-1 h-6 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden flex">
            <div 
              className="bg-blue-500 h-full flex items-center justify-end pr-2 transition-all duration-300"
              style={{ width: `${homePercent}%` }}
            />
            <div 
              className="bg-red-500 h-full flex items-center justify-start pl-2 transition-all duration-300"
              style={{ width: `${awayPercent}%` }}
            />
          </div>
          <span className={`text-sm font-bold ${textPrimary} w-16 text-left`}>
            {awayValue}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg`}>
      <h3 className={`text-xl font-bold ${textPrimary} mb-6`}>📊 Stats Comparison</h3>
      {Object.entries(stats).map(([key, value]) => (
        <div key={key}>
          {renderStatBar(
            key.replace(/([A-Z])/g, ' $1').trim(),
            value.home,
            value.away
          )}
        </div>
      ))}
    </div>
  );
};

// ============================================================================
// SCORE TIMELINE CHART
// ============================================================================

export const ScoreTimeline: React.FC<{ darkMode?: boolean }> = ({ darkMode = false }) => {
  // Sample data - in real implementation, this would come from API
  const data = [
    { time: '0:00', homeScore: 0, awayScore: 0 },
    { time: '15:00', homeScore: 7, awayScore: 0 },
    { time: '30:00', homeScore: 7, awayScore: 7 },
    { time: '45:00', homeScore: 14, awayScore: 10 },
    { time: '60:00', homeScore: 21, awayScore: 17 },
  ];

  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';

  return (
    <div className={`${darkMode ? 'bg-gray-800' : 'bg-white'} rounded-xl p-6 shadow-lg`}>
      <h3 className={`text-xl font-bold ${textPrimary} mb-6`}>📈 Score Timeline</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke={darkMode ? '#374151' : '#E5E7EB'} />
          <XAxis 
            dataKey="time" 
            label={{ value: 'Game Time', position: 'insideBottom', offset: -5 }}
            stroke={darkMode ? '#9CA3AF' : '#6B7280'}
          />
          <YAxis 
            label={{ value: 'Score', angle: -90, position: 'insideLeft' }}
            stroke={darkMode ? '#9CA3AF' : '#6B7280'}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: darkMode ? '#1F2937' : '#FFFFFF',
              border: `1px solid ${darkMode ? '#374151' : '#E5E7EB'}`,
              borderRadius: '0.5rem'
            }}
          />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="homeScore" 
            stroke="#3B82F6" 
            name="Home Team"
            strokeWidth={3}
            dot={{ fill: '#3B82F6', r: 5 }}
            activeDot={{ r: 8 }}
          />
          <Line 
            type="monotone" 
            dataKey="awayScore" 
            stroke="#EF4444" 
            name="Away Team"
            strokeWidth={3}
            dot={{ fill: '#EF4444', r: 5 }}
            activeDot={{ r: 8 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

// ============================================================================
// UPCOMING GAME CARD
// ============================================================================

export const UpcomingGameCard: React.FC<{ game: Game; darkMode?: boolean }> = ({ 
  game, 
  darkMode = false 
}) => {
  const [timeUntil, setTimeUntil] = useState('');

  useEffect(() => {
    const updateCountdown = () => {
      const now = new Date();
      const start = new Date(game.startTime);
      const diff = start.getTime() - now.getTime();
      
      const hours = Math.floor(diff / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      
      setTimeUntil(`${hours}h ${minutes}m`);
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 60000);
    return () => clearInterval(interval);
  }, [game.startTime]);

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  return (
    <div className={`${cardBg} rounded-lg shadow p-4 border ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
      <div className="flex items-center justify-between mb-3">
        <span className={`text-sm font-semibold ${textSecondary}`}>
          {new Date(game.startTime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span className="text-sm font-semibold text-amber-500">
          ⏰ in {timeUntil}
        </span>
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{game.league === 'NFL' ? '🏈' : '🏒'}</span>
          <div>
            <div className={`font-semibold ${textPrimary}`}>
              {game.awayTeam.abbreviation} @ {game.homeTeam.abbreviation}
            </div>
            <div className={`text-xs ${textSecondary}`}>
              {game.awayTeam.name} at {game.homeTeam.name}
            </div>
          </div>
        </div>
        
        <button 
          className={`px-3 py-1 rounded ${darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'} text-white text-sm transition-colors`}
        >
          🔔 Notify
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// SPORTS TAB MAIN COMPONENT
// ============================================================================

export const SportsTab: React.FC<{ darkMode?: boolean }> = ({ darkMode = false }) => {
  const [selectedLeague, setSelectedLeague] = useState<'all' | 'NFL' | 'NHL'>('all');
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);

  // Sample data
  const sampleLiveGame: Game = {
    id: '1',
    league: 'NFL',
    status: 'live',
    startTime: new Date().toISOString(),
    homeTeam: {
      id: 'sf',
      name: 'San Francisco 49ers',
      abbreviation: 'SF',
      logo: '',
      colors: { primary: '#AA0000', secondary: '#B3995D' },
      record: { wins: 5, losses: 2, ties: 0 }
    },
    awayTeam: {
      id: 'sea',
      name: 'Seattle Seahawks',
      abbreviation: 'SEA',
      logo: '',
      colors: { primary: '#002244', secondary: '#69BE28' },
      record: { wins: 4, losses: 3, ties: 0 }
    },
    score: { home: 24, away: 17 },
    period: { current: 3, total: 4, timeRemaining: '12:45' },
    isFavorite: true
  };

  const sampleStats: GameStats = {
    'Total Yards': { home: 352, away: 287 },
    'First Downs': { home: 18, away: 15 },
    'Passing Yards': { home: 245, away: 198 },
    'Rushing Yards': { home: 107, away: 89 },
  };

  const bgPrimary = darkMode ? 'bg-gray-900' : 'bg-gray-50';
  const bgSecondary = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';

  return (
    <div className={`${bgPrimary} min-h-screen p-6`}>
      {/* Header */}
      <div className="max-w-7xl mx-auto mb-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className={`text-3xl font-bold ${textPrimary} mb-2`}>
              🏈 NFL & 🏒 NHL Sports Center
            </h1>
            <p className={textSecondary}>
              3 Live Games • 5 Upcoming Today • 12 Favorites Active
            </p>
          </div>
          
          <button 
            className={`px-4 py-2 rounded-lg ${darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'} text-white font-medium transition-colors`}
          >
            ⚙️ Configure
          </button>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setSelectedLeague('all')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              selectedLeague === 'all'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            All Sports
          </button>
          <button
            onClick={() => setSelectedLeague('NFL')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              selectedLeague === 'NFL'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            🏈 NFL
          </button>
          <button
            onClick={() => setSelectedLeague('NHL')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              selectedLeague === 'NHL'
                ? darkMode ? 'bg-blue-600 text-white' : 'bg-blue-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            🏒 NHL
          </button>
          <button
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              showFavoritesOnly
                ? 'bg-yellow-500 text-white'
                : darkMode ? 'bg-gray-700 text-gray-300 hover:bg-gray-600' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            ⭐ Favorites {showFavoritesOnly && '(ON)'}
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto">
        {/* Live Games Section */}
        <div className="mb-8">
          <h2 className={`text-2xl font-bold ${textPrimary} mb-4`}>
            📍 LIVE NOW (3 games)
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <LiveGameCard game={sampleLiveGame} darkMode={darkMode} />
            <LiveGameCard game={sampleLiveGame} darkMode={darkMode} />
          </div>
        </div>

        {/* Stats Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <StatsComparison stats={sampleStats} darkMode={darkMode} />
          <ScoreTimeline darkMode={darkMode} />
        </div>

        {/* Upcoming Games Section */}
        <div className="mb-8">
          <h2 className={`text-2xl font-bold ${textPrimary} mb-4`}>
            📅 UPCOMING TODAY (5 games)
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <UpcomingGameCard game={sampleLiveGame} darkMode={darkMode} />
            <UpcomingGameCard game={sampleLiveGame} darkMode={darkMode} />
            <UpcomingGameCard game={sampleLiveGame} darkMode={darkMode} />
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// CONFIGURATION COMPONENT
// ============================================================================

export const SportsConfiguration: React.FC<{ darkMode?: boolean }> = ({ darkMode = false }) => {
  const [apiProvider, setApiProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle');

  const cardBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const inputBg = darkMode ? 'bg-gray-700' : 'bg-gray-50';
  const borderColor = darkMode ? 'border-gray-600' : 'border-gray-300';

  return (
    <div className={`${cardBg} rounded-xl shadow-lg p-8 max-w-2xl mx-auto`}>
      <h2 className={`text-2xl font-bold ${textPrimary} mb-6`}>
        🏈🏒 Sports Data Configuration
      </h2>

      {/* API Provider Selection */}
      <div className="mb-6">
        <label className={`block text-sm font-semibold ${textPrimary} mb-3`}>
          Select API Provider
        </label>
        <div className="space-y-3">
          {['ESPN API', 'The Sports DB', 'SportsData.io'].map((provider) => (
            <div
              key={provider}
              onClick={() => setApiProvider(provider)}
              className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
                apiProvider === provider
                  ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                  : `${borderColor} hover:border-blue-300`
              }`}
            >
              <div className="flex items-start">
                <input
                  type="radio"
                  checked={apiProvider === provider}
                  onChange={() => setApiProvider(provider)}
                  className="mt-1 mr-3"
                />
                <div className="flex-1">
                  <div className={`font-semibold ${textPrimary}`}>{provider}</div>
                  <div className={`text-sm ${textSecondary} mt-1`}>
                    {provider === 'ESPN API' && 'Free tier: 100 calls/day • Real-time scores • Limited history'}
                    {provider === 'The Sports DB' && 'Free, rate-limited • Team info • Historical data • No real-time'}
                    {provider === 'SportsData.io' && 'Paid: from $19/mo • Real-time • Advanced stats • Unlimited'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* API Key Input */}
      {apiProvider && (
        <div className="mb-6">
          <label className={`block text-sm font-semibold ${textPrimary} mb-2`}>
            API Key
          </label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="Enter your API key"
            className={`w-full px-4 py-3 rounded-lg border ${borderColor} ${inputBg} ${textPrimary} focus:outline-none focus:ring-2 focus:ring-blue-500`}
          />
          <div className={`text-xs ${textSecondary} mt-2`}>
            ℹ️ How to get an API key: Visit the provider's website and sign up for an account
          </div>
        </div>
      )}

      {/* Test Connection */}
      {apiKey && (
        <div className="mb-6">
          <button
            onClick={() => {
              setTestStatus('testing');
              setTimeout(() => setTestStatus('success'), 2000);
            }}
            disabled={testStatus === 'testing'}
            className={`w-full py-3 rounded-lg font-medium transition-colors ${
              darkMode ? 'bg-green-600 hover:bg-green-700' : 'bg-green-500 hover:bg-green-600'
            } text-white ${testStatus === 'testing' ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {testStatus === 'testing' ? '🔄 Testing Connection...' : '🔌 Test Connection'}
          </button>
          
          {testStatus === 'success' && (
            <div className="mt-3 p-3 bg-green-100 dark:bg-green-900/30 rounded-lg text-green-800 dark:text-green-300 text-sm">
              ✅ Connected successfully! Rate Limit: 95 / 100 calls remaining
            </div>
          )}
          
          {testStatus === 'error' && (
            <div className="mt-3 p-3 bg-red-100 dark:bg-red-900/30 rounded-lg text-red-800 dark:text-red-300 text-sm">
              ❌ Connection failed. Please check your API key and try again.
            </div>
          )}
        </div>
      )}

      {/* Save Button */}
      <button
        className={`w-full py-3 rounded-lg font-medium transition-colors ${
          darkMode ? 'bg-blue-600 hover:bg-blue-700' : 'bg-blue-500 hover:bg-blue-600'
        } text-white`}
      >
        💾 Save Configuration
      </button>
    </div>
  );
};

export default SportsTab;

