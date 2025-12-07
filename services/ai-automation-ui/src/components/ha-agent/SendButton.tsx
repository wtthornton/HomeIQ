/**
 * SendButton Component - Optimized for 2025 Best Practices
 * 
 * A modern, accessible send button with enhanced visual states,
 * micro-interactions, and comprehensive accessibility support.
 * 
 * Features:
 * - Icon + text design with smooth animations
 * - Enhanced hover/active states
 * - Comprehensive ARIA labels
 * - Loading state with improved indicator
 * - Error state support
 * - Keyboard navigation support
 * - Reduced motion support
 */

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';

interface SendButtonProps {
  /** Whether the button is in loading state */
  isLoading?: boolean;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Whether there's an error state */
  hasError?: boolean;
  /** Click handler */
  onClick: () => void;
  /** Dark mode support */
  darkMode?: boolean;
  /** Optional custom label */
  label?: string;
  /** Optional loading text */
  loadingText?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show icon only (for compact layouts) */
  iconOnly?: boolean;
  /** Optional retry handler for error state */
  onRetry?: () => void;
}

export const SendButton: React.FC<SendButtonProps> = ({
  isLoading = false,
  disabled = false,
  hasError = false,
  onClick,
  darkMode = false,
  label = 'Send',
  loadingText = 'Sending...',
  size = 'md',
  iconOnly = false,
  onRetry,
}) => {
  const shouldReduceMotion = useReducedMotion();

  // Size configurations
  const sizeConfig = {
    sm: {
      height: 'h-10',
      padding: 'px-4',
      iconSize: 'w-4 h-4',
      textSize: 'text-sm',
    },
    md: {
      height: 'h-11',
      padding: 'px-6',
      iconSize: 'w-5 h-5',
      textSize: 'text-base',
    },
    lg: {
      height: 'h-12',
      padding: 'px-8',
      iconSize: 'w-6 h-6',
      textSize: 'text-lg',
    },
  };

  const config = sizeConfig[size];

  // Determine button state
  const isInteractive = !disabled && !isLoading && !hasError;
  const isDisabled = disabled || isLoading;

  // Base styles
  const baseStyles = `${config.height} ${config.padding} rounded-lg font-medium transition-all duration-200 min-h-[44px] flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2`;

  // State-specific styles
  const getStateStyles = () => {
    if (hasError) {
      return darkMode
        ? 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500'
        : 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-400';
    }

    if (isDisabled) {
      return darkMode
        ? 'bg-gray-700 text-gray-500 cursor-not-allowed opacity-60'
        : 'bg-gray-200 text-gray-400 cursor-not-allowed opacity-60';
    }

    return darkMode
      ? 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 focus:ring-blue-500'
      : 'bg-blue-500 text-white hover:bg-blue-600 active:bg-blue-700 focus:ring-blue-400';
  };

  // Animation variants (respect reduced motion)
  const buttonVariants = {
    hover: shouldReduceMotion
      ? {}
      : {
          scale: 1.02,
          transition: { duration: 0.2, ease: 'easeOut' },
        },
    tap: shouldReduceMotion
      ? {}
      : {
          scale: 0.98,
          transition: { duration: 0.1, ease: 'easeIn' },
        },
  };

  const iconVariants = {
    hover: shouldReduceMotion
      ? {}
      : {
          x: 2,
          transition: { duration: 0.2, ease: 'easeOut' },
        },
    tap: shouldReduceMotion
      ? {}
      : {
          scale: 0.9,
          transition: { duration: 0.1, ease: 'easeIn' },
        },
  };

  // Send icon SVG
  const SendIcon = ({ className }: { className?: string }) => (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
      />
    </svg>
  );

  // Error/Retry icon
  const RetryIcon = ({ className }: { className?: string }) => (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      />
    </svg>
  );

  // Loading spinner
  const LoadingSpinner = () => (
    <motion.div
      className={`${config.iconSize} border-2 border-white border-t-transparent rounded-full`}
      animate={{ rotate: 360 }}
      transition={{
        duration: 0.8,
        repeat: Infinity,
        ease: 'linear',
      }}
      aria-hidden="true"
    />
  );

  // Determine button content
  const getButtonContent = () => {
    if (hasError) {
      return (
        <>
          <motion.div variants={iconVariants}>
            <RetryIcon className={config.iconSize} />
          </motion.div>
          {!iconOnly && <span className={config.textSize}>Retry</span>}
        </>
      );
    }

    if (isLoading) {
      return (
        <>
          <LoadingSpinner />
          {!iconOnly && <span className={config.textSize}>{loadingText}</span>}
        </>
      );
    }

    return (
      <>
        <motion.div variants={iconVariants}>
          <SendIcon className={config.iconSize} />
        </motion.div>
        {!iconOnly && <span className={config.textSize}>{label}</span>}
      </>
    );
  };

  // ARIA label for accessibility
  const getAriaLabel = () => {
    if (hasError) {
      return iconOnly ? 'Retry sending message' : 'Retry';
    }
    if (isLoading) {
      return iconOnly ? 'Sending message' : loadingText;
    }
    if (isDisabled) {
      return iconOnly ? 'Send message (disabled)' : `${label} (disabled)`;
    }
    return iconOnly ? 'Send message' : label;
  };

  // Handle click
  const handleClick = () => {
    if (isDisabled) return;
    if (hasError && onRetry) {
      onRetry();
    } else {
      onClick();
    }
  };

  // Keyboard handler
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  };

  return (
    <motion.button
      type="button"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      disabled={isDisabled && !hasError}
      className={`${baseStyles} ${getStateStyles()}`}
      variants={buttonVariants}
      whileHover={isInteractive ? 'hover' : undefined}
      whileTap={isInteractive ? 'tap' : undefined}
      aria-label={getAriaLabel()}
      aria-busy={isLoading}
      aria-disabled={isDisabled && !hasError}
      aria-live="polite"
      title={isDisabled && !hasError ? 'Type a message to send' : undefined}
    >
      {getButtonContent()}
    </motion.button>
  );
};

