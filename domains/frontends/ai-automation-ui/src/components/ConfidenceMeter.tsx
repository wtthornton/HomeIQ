/**
 * Enhanced Confidence Meter Component
 * Integrated visual indicator combining confidence level and percentage
 * Supports accessibility and reduced motion preferences
 */

import React from 'react';
import { motion } from 'framer-motion';

interface ConfidenceMeterProps {
  confidence: number;
  darkMode?: boolean;
  showLabel?: boolean;
  variant?: 'standard' | 'compact' | 'inline';
  accessibility?: boolean;
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({
  confidence,
  darkMode = false,
  showLabel = true,
  variant = 'standard',
  accessibility = true
}) => {
  // Backend sends confidence as percentage (0-100+), cap at 100% for display
  const percentage = Math.round(Math.min(confidence, 100));
  
  const getColor = () => {
    if (confidence >= 90) return 'from-green-500 to-green-600';
    if (confidence >= 70) return 'from-yellow-500 to-yellow-600';
    return 'from-red-500 to-red-600';
  };

  const getLabel = () => {
    if (confidence >= 90) return 'High';
    if (confidence >= 70) return 'Medium';
    return 'Low';
  };

  const getFullLabel = () => {
    if (confidence >= 90) return 'High Confidence';
    if (confidence >= 70) return 'Medium Confidence';
    return 'Low Confidence';
  };

  // Accessibility: Screen reader text
  const getAriaLabel = () => {
    if (accessibility) {
      return `${getFullLabel()}: ${percentage} percent`;
    }
    return undefined;
  };

  // Compact variant: Single line with integrated label and percentage
  if (variant === 'compact') {
    return (
      <div 
        className={`inline-flex items-center gap-2 px-3 py-1 rounded-xl text-sm font-medium backdrop-blur-sm ${
          darkMode ? 'bg-slate-800/60 border border-slate-700/50' : 'bg-white/80 border border-gray-200/50'
        }`}
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={getAriaLabel()}
      >
        <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${getColor()}`} />
        <span className={`${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
          {percentage}% {getLabel()}
        </span>
      </div>
    );
  }

  // Inline variant: Just text
  if (variant === 'inline') {
    return (
      <span 
        className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}
        aria-label={getAriaLabel()}
      >
        {percentage}% {getLabel()} Confidence
      </span>
    );
  }

  // Standard variant: Full meter with integrated display
  return (
    <div>
      {showLabel && (
        <div className="flex justify-between items-center mb-2">
          <span className={`text-sm font-medium ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
            {percentage}% {getLabel()} Confidence
          </span>
        </div>
      )}
      
      <div 
        className={`w-full h-3 rounded-full overflow-hidden backdrop-blur-sm ${
          darkMode ? 'bg-slate-800/60 border border-slate-700/50' : 'bg-white/80 border border-gray-200/50'
        }`}
        role="progressbar"
        aria-valuenow={percentage}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={getAriaLabel()}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ 
            duration: 0.8, 
            ease: 'easeOut',
            // Respect reduced motion preference
            ...(window.matchMedia('(prefers-reduced-motion: reduce)').matches && {
              duration: 0.1
            })
          }}
          className={`h-full bg-gradient-to-r ${getColor()} shadow-lg`}
        />
      </div>
    </div>
  );
};

