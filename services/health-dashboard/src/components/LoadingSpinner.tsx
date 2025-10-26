/**
 * Loading Spinner Component
 * Modern, animated loading spinner with multiple variants
 */

import React from 'react';

export interface LoadingSpinnerProps {
  variant?: 'pulse' | 'dots' | 'spinner' | 'bars';
  size?: 'sm' | 'md' | 'lg';
  color?: 'default' | 'blue' | 'green' | 'purple';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  variant = 'pulse', 
  size = 'md',
  color = 'default',
  className = ''
}) => {
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  };

  const colorClasses = {
    default: 'bg-gray-400 dark:bg-gray-500',
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    purple: 'bg-purple-500'
  };

  // Pulse variant - animated growing circle
  if (variant === 'pulse') {
    return (
      <div className={`inline-flex items-center justify-center ${className}`}>
        <div className={`${sizeClasses[size]} rounded-full ${colorClasses[color]} animate-pulse`}></div>
      </div>
    );
  }

  // Dots variant - three bouncing dots
  if (variant === 'dots') {
    return (
      <div className={`inline-flex items-center space-x-1 ${className}`}>
        <div className={`${sizeClasses[size]} ${colorClasses[color]} rounded-full animate-bounce`} style={{ animationDelay: '0ms' }}></div>
        <div className={`${sizeClasses[size]} ${colorClasses[color]} rounded-full animate-bounce`} style={{ animationDelay: '150ms' }}></div>
        <div className={`${sizeClasses[size]} ${colorClasses[color]} rounded-full animate-bounce`} style={{ animationDelay: '300ms' }}></div>
      </div>
    );
  }

  // Spinner variant - rotating circle
  if (variant === 'spinner') {
    return (
      <div className={`inline-flex items-center justify-center ${className}`}>
        <svg
          className={`animate-spin ${sizeClasses[size] === 'w-2 h-2' ? 'w-4 h-4' : sizeClasses[size] === 'w-3 h-3' ? 'w-6 h-6' : 'w-8 h-8'}`}
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
            style={{ color: color === 'default' ? '#9CA3AF' : color === 'blue' ? '#3B82F6' : color === 'green' ? '#10B981' : '#A855F7' }}
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      </div>
    );
  }

  // Bars variant - animated bars
  if (variant === 'bars') {
    return (
      <div className={`inline-flex items-end space-x-1 ${className}`}>
        <div className={`${colorClasses[color]} rounded-sm`} style={{ width: '3px', height: '8px', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '0ms' }}></div>
        <div className={`${colorClasses[color]} rounded-sm`} style={{ width: '3px', height: '12px', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '200ms' }}></div>
        <div className={`${colorClasses[color]} rounded-sm`} style={{ width: '3px', height: '10px', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '400ms' }}></div>
        <div className={`${colorClasses[color]} rounded-sm`} style={{ width: '3px', height: '8px', animation: 'pulse 1.5s ease-in-out infinite', animationDelay: '600ms' }}></div>
      </div>
    );
  }

  return null;
};

