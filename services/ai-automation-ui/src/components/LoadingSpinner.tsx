/**
 * LoadingSpinner Component
 * Modern, accessible loading spinner following 2025 best practices
 * 
 * Supports multiple sizes and variants for different use cases
 */

import React from 'react';

export interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  label?: string;
  variant?: 'spinner' | 'dots' | 'pulse';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  className = '',
  label = 'Loading...',
  variant = 'spinner'
}) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8'
  };

  const borderWidth = {
    sm: 'border-2',
    md: 'border-2',
    lg: 'border-3'
  };

  // Spinner variant - rotating circle (most common)
  if (variant === 'spinner') {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`} role="status" aria-label={label}>
        <div
          className={`${sizeClasses[size]} ${borderWidth[size]} border-blue-500 border-t-transparent rounded-full animate-spin`}
          aria-hidden="true"
        />
        {label && (
          <span className="sr-only">{label}</span>
        )}
      </div>
    );
  }

  // Dots variant - three bouncing dots
  if (variant === 'dots') {
    return (
      <div className={`inline-flex items-center gap-1 ${className}`} role="status" aria-label={label}>
        <div className={`${sizeClasses[size]} bg-blue-500 rounded-full animate-bounce`} style={{ animationDelay: '0ms' }} aria-hidden="true" />
        <div className={`${sizeClasses[size]} bg-blue-500 rounded-full animate-bounce`} style={{ animationDelay: '150ms' }} aria-hidden="true" />
        <div className={`${sizeClasses[size]} bg-blue-500 rounded-full animate-bounce`} style={{ animationDelay: '300ms' }} aria-hidden="true" />
        {label && (
          <span className="sr-only">{label}</span>
        )}
      </div>
    );
  }

  // Pulse variant - pulsing circle
  if (variant === 'pulse') {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`} role="status" aria-label={label}>
        <div className={`${sizeClasses[size]} bg-blue-500 rounded-full animate-pulse`} aria-hidden="true" />
        {label && (
          <span className="sr-only">{label}</span>
        )}
      </div>
    );
  }

  return null;
};
