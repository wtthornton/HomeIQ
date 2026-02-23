/**
 * GameDetailModal Component
 * 
 * Modal displaying comprehensive game details including statistics, team records, and timeline
 * Phase 2 Enhancement - High-Value Feature
 */

import React, { useState, useEffect, useRef } from 'react';
import { dataApi } from '../../services/api';
import { ScoreTimelineChart } from './charts/ScoreTimelineChart';
import type { Game } from '../../types/sports';

interface GameDetailModalProps {
  game: Game | null;
  isOpen: boolean;
  onClose: () => void;
  darkMode?: boolean;
}

interface TimelinePoint {
  timestamp: string;
  home_score: number;
  away_score: number;
  quarter_period: string;
  time_remaining: string;
}

export const GameDetailModal: React.FC<GameDetailModalProps> = ({
  game,
  isOpen,
  onClose,
  darkMode = false
}) => {
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const modalBg = darkMode ? 'bg-gray-800' : 'bg-white';
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const borderColor = darkMode ? 'border-gray-700' : 'border-gray-200';

  // Fetch game timeline when modal opens
  useEffect(() => {
    if (isOpen && game) {
      fetchGameTimeline();
    } else {
      setTimeline([]);
      setError(null);
    }
  }, [isOpen, game?.id]);

  const fetchGameTimeline = async () => {
    if (!game) return;

    try {
      setLoading(true);
      setError(null);
      
      const data = await dataApi.getGameTimeline(game.id, game.league);
      
      if (data && data.timeline) {
        setTimeline(data.timeline);
      } else {
        setTimeline([]);
      }
    } catch (err) {
      console.error('Error fetching game timeline:', err);
      setError(err instanceof Error ? err.message : 'Failed to load game timeline');
    } finally {
      setLoading(false);
    }
  };

  // Focus management for accessibility
  useEffect(() => {
    if (isOpen && closeButtonRef.current) {
      closeButtonRef.current.focus();
    }
  }, [isOpen]);

  // Keyboard navigation (ESC to close)
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  // Don't render if modal is not open
  if (!isOpen || !game) {
    return null;
  }

  const winner = game.score.home > game.score.away ? 'home' : game.score.away > game.score.home ? 'away' : 'tie';

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="game-detail-modal-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        ref={modalRef}
        className={`
          relative w-full max-w-4xl max-h-[90vh] overflow-y-auto
          rounded-xl shadow-2xl transform transition-all
          ${modalBg}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`
          sticky top-0 z-10 flex items-center justify-between p-6 border-b
          ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
        `}>
          <div>
            <h2 
              id="game-detail-modal-title"
              className={`text-2xl font-bold ${textPrimary} mb-1`}
            >
              Game Details
            </h2>
            <p className={`text-sm ${textSecondary}`}>
              {game.awayTeam.name} vs {game.homeTeam.name}
            </p>
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            className={`
              p-2 rounded-lg transition-colors
              ${darkMode 
                ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
                : 'hover:bg-gray-100 text-gray-500 hover:text-gray-900'
              }
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            `}
            aria-label="Close game details modal"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Game Score Header */}
          <div className={`
            rounded-xl p-6 border-2
            ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gradient-to-r from-blue-50 to-purple-50 border-gray-200'}
          `}>
            <div className="flex items-center justify-center gap-8">
              {/* Away Team */}
              <div className="text-center flex-1">
                <div className={`text-lg font-semibold ${textPrimary} mb-2`}>
                  {game.awayTeam.name}
                </div>
                <div className={`text-xs ${textSecondary} mb-2`}>
                  {game.awayTeam.abbreviation}
                </div>
                <div className={`
                  text-5xl font-bold 
                  ${winner === 'away' ? (darkMode ? 'text-green-400' : 'text-green-600') : textPrimary}
                `}>
                  {game.score.away}
                </div>
                {game.awayTeam.record && (
                  <div className={`text-xs ${textSecondary} mt-2`}>
                    {game.awayTeam.record.wins}-{game.awayTeam.record.losses}
                    {game.awayTeam.record.ties !== undefined && game.awayTeam.record.ties > 0 && `-${game.awayTeam.record.ties}`}
                  </div>
                )}
              </div>

              {/* VS Divider */}
              <div className={`
                text-2xl font-bold ${textSecondary}
                ${game.status === 'live' ? 'animate-pulse' : ''}
              `}>
                {game.status === 'live' ? 'LIVE' : 'VS'}
              </div>

              {/* Home Team */}
              <div className="text-center flex-1">
                <div className={`text-lg font-semibold ${textPrimary} mb-2`}>
                  {game.homeTeam.name}
                </div>
                <div className={`text-xs ${textSecondary} mb-2`}>
                  {game.homeTeam.abbreviation}
                </div>
                <div className={`
                  text-5xl font-bold
                  ${winner === 'home' ? (darkMode ? 'text-green-400' : 'text-green-600') : textPrimary}
                `}>
                  {game.score.home}
                </div>
                {game.homeTeam.record && (
                  <div className={`text-xs ${textSecondary} mt-2`}>
                    {game.homeTeam.record.wins}-{game.homeTeam.record.losses}
                    {game.homeTeam.record.ties !== undefined && game.homeTeam.record.ties > 0 && `-${game.homeTeam.record.ties}`}
                  </div>
                )}
              </div>
            </div>

            {/* Game Status Info */}
            <div className={`text-center mt-4 pt-4 border-t ${borderColor}`}>
              <div className={`text-sm ${textSecondary}`}>
                <time dateTime={game.startTime}>
                  {new Date(game.startTime).toLocaleString([], {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit'
                  })}
                </time>
              </div>
              {game.status === 'live' && (
                <div className={`text-sm font-semibold mt-2 ${darkMode ? 'text-green-400' : 'text-green-600'}`}>
                  {game.league === 'NFL' ? `Q${game.period.current}` : `P${game.period.current}`}
                  {game.period.timeRemaining && ` • ${game.period.timeRemaining}`}
                </div>
              )}
              {game.status === 'final' && (
                <div className={`text-sm font-semibold mt-2 ${textSecondary}`}>
                  Final
                </div>
              )}
            </div>
          </div>

          {/* Team Records Section */}
          {(game.awayTeam.record || game.homeTeam.record) && (
            <div>
              <h3 className={`text-lg font-semibold ${textPrimary} mb-4`}>
                Team Records
              </h3>
              <div className="grid grid-cols-2 gap-4">
                {game.awayTeam.record && (
                  <div className={`
                    p-4 rounded-lg border
                    ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
                  `}>
                    <div className={`font-semibold ${textPrimary} mb-2`}>
                      {game.awayTeam.name}
                    </div>
                    <div className={`text-sm ${textSecondary}`}>
                      <div>Wins: {game.awayTeam.record.wins}</div>
                      <div>Losses: {game.awayTeam.record.losses}</div>
                      {game.awayTeam.record.ties !== undefined && game.awayTeam.record.ties > 0 && (
                        <div>Ties: {game.awayTeam.record.ties}</div>
                      )}
                    </div>
                  </div>
                )}
                {game.homeTeam.record && (
                  <div className={`
                    p-4 rounded-lg border
                    ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
                  `}>
                    <div className={`font-semibold ${textPrimary} mb-2`}>
                      {game.homeTeam.name}
                    </div>
                    <div className={`text-sm ${textSecondary}`}>
                      <div>Wins: {game.homeTeam.record.wins}</div>
                      <div>Losses: {game.homeTeam.record.losses}</div>
                      {game.homeTeam.record.ties !== undefined && game.homeTeam.record.ties > 0 && (
                        <div>Ties: {game.homeTeam.record.ties}</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Timeline Section */}
          <div>
            <h3 className={`text-lg font-semibold ${textPrimary} mb-4`}>
              Score Timeline
            </h3>
            
            {loading && (
              <div className="text-center py-12">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" aria-hidden="true" />
                <p className={textSecondary}>Loading timeline...</p>
              </div>
            )}

            {error && (
              <div className={`
                text-center py-8 rounded-lg border
                ${darkMode ? 'bg-red-900/20 border-red-500/30' : 'bg-red-50 border-red-200'}
              `}>
                <p className={darkMode ? 'text-red-300' : 'text-red-600'}>
                  {error}
                </p>
              </div>
            )}

            {!loading && !error && timeline.length > 0 && (
              <div>
                <ScoreTimelineChart
                  data={timeline.map((point, index) => ({
                    time: point.time_remaining || point.quarter_period || `Point ${index + 1}`,
                    homeScore: point.home_score,
                    awayScore: point.away_score,
                    period: point.quarter_period || undefined
                  }))}
                  homeTeamName={game.homeTeam.name}
                  awayTeamName={game.awayTeam.name}
                  darkMode={darkMode}
                />
              </div>
            )}

            {!loading && !error && timeline.length === 0 && (
              <div className={`
                text-center py-8 rounded-lg border
                ${darkMode ? 'bg-gray-700/50 border-gray-600' : 'bg-gray-50 border-gray-200'}
              `}>
                <p className={textSecondary}>
                  Timeline data not available for this game
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className={`
          px-6 py-4 border-t flex justify-end
          ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}
        `}>
          <button
            onClick={onClose}
            className={`
              px-6 py-2 rounded-lg font-medium transition-colors
              ${darkMode
                ? 'bg-gray-700 hover:bg-gray-600 text-white'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-900'
              }
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
            `}
            aria-label="Close modal"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
