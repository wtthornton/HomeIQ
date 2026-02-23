/**
 * EmptyState Component
 * 
 * Displays helpful message when no teams are selected
 */

import React from 'react';

interface EmptyStateProps {
  onAddTeam: () => void;
  darkMode?: boolean;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  onAddTeam,
  darkMode = false
}) => {
  const textPrimary = darkMode ? 'text-white' : 'text-gray-900';
  const textSecondary = darkMode ? 'text-gray-400' : 'text-gray-600';
  const bgCard = darkMode ? 'bg-gray-800' : 'bg-white';

  return (
    <div className="flex items-center justify-center min-h-[500px]">
      <div className={`${bgCard} rounded-xl shadow-lg p-12 text-center max-w-lg`}>
        {/* Icon */}
        <div className="text-8xl mb-6">
          🏈🏒
        </div>

        {/* Message */}
        <h2 className={`text-2xl font-bold ${textPrimary} mb-3`}>
          No Teams Selected Yet!
        </h2>
        <p className={`${textSecondary} mb-8`}>
          Start tracking your favorite teams to see live scores and updates.
        </p>

        {/* CTA Button */}
        <button
          onClick={onAddTeam}
          className={`px-8 py-4 rounded-lg font-semibold text-lg transition-all ${
            darkMode
              ? 'bg-blue-600 hover:bg-blue-700'
              : 'bg-blue-500 hover:bg-blue-600'
          } text-white shadow-lg hover:shadow-xl hover:scale-105`}
        >
          + Add Your First Team
        </button>

        {/* Suggestions */}
        <div className={`mt-8 pt-6 border-t ${darkMode ? 'border-gray-700' : 'border-gray-200'}`}>
          <p className={`text-sm font-semibold ${textPrimary} mb-3`}>
            💡 New here? Try adding:
          </p>
          <ul className={`text-sm ${textSecondary} space-y-2`}>
            <li>• Your local team</li>
            <li>• Your favorite team</li>
            <li>• Top teams this season</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

