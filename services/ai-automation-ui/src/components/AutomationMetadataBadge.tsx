/**
 * AutomationMetadataBadge Component
 * 
 * Displays automation metadata (mode, initial_state, max_exceeded).
 * Features:
 * - Icon for each mode type
 * - Hover tooltip with explanation
 * - Compact display
 * - Expandable details
 * - Accessibility support
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface AutomationMetadataBadgeProps {
  mode?: string;
  initialState?: boolean;
  maxExceeded?: string;
  darkMode?: boolean;
}

// Mode icons and explanations
const MODE_INFO: Record<string, { icon: string; label: string; explanation: string; color: string }> = {
  'single': {
    icon: '⚡',
    label: 'Single',
    explanation: 'Runs once per trigger, waits for completion before next run',
    color: 'rgba(245, 158, 11, 0.2)'
  },
  'restart': {
    icon: '🔄',
    label: 'Restart',
    explanation: 'Cancels previous run and restarts when triggered again',
    color: 'rgba(59, 130, 246, 0.2)'
  },
  'queued': {
    icon: '📋',
    label: 'Queued',
    explanation: 'Queues triggers and runs them sequentially',
    color: 'rgba(168, 85, 247, 0.2)'
  },
  'parallel': {
    icon: '⚡⚡',
    label: 'Parallel',
    explanation: 'Runs multiple instances simultaneously',
    color: 'rgba(16, 185, 129, 0.2)'
  }
};

// Max exceeded info
const MAX_EXCEEDED_INFO: Record<string, { icon: string; label: string; explanation: string }> = {
  'silent': {
    icon: '🔇',
    label: 'Silent',
    explanation: 'Silently skips runs when max exceeded (prevents queue buildup)'
  },
  'warning': {
    icon: '⚠️',
    label: 'Warning',
    explanation: 'Logs a warning when max runs exceeded (important for safety-critical automations)'
  }
};

export const AutomationMetadataBadge: React.FC<AutomationMetadataBadgeProps> = ({
  mode,
  initialState,
  maxExceeded,
  darkMode = false
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  // Check for reduced motion preference
  React.useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);
    
    const handleChange = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };
    
    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, []);

  // If no metadata, don't render
  if (!mode && initialState === undefined && !maxExceeded) {
    return null;
  }

  const modeInfo = mode ? MODE_INFO[mode] : null;
  const maxExceededInfo = maxExceeded ? MAX_EXCEEDED_INFO[maxExceeded] : null;

  const badgeVariants = {
    initial: { scale: 1, opacity: 1 },
    hover: prefersReducedMotion ? {} : { scale: 1.02 }
  };

  const tooltipVariants = {
    hidden: { opacity: 0, y: -5, scale: 0.95 },
    visible: prefersReducedMotion ? { opacity: 1, y: 0, scale: 1 } : {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 20
      }
    }
  };

  return (
    <div className="relative inline-block">
      {/* Main Badge */}
      <motion.div
        className="flex items-center gap-2 px-2.5 py-1 rounded-xl text-xs font-medium backdrop-blur-sm"
        style={{
          background: darkMode ? 'rgba(30, 41, 59, 0.6)' : 'rgba(255, 255, 255, 0.8)',
          border: darkMode ? '1px solid rgba(51, 65, 85, 0.5)' : '1px solid rgba(203, 213, 225, 0.5)',
          color: darkMode ? '#cbd5e1' : '#1e293b'
        }}
        variants={badgeVariants}
        initial="initial"
        whileHover="hover"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        aria-label={`Automation metadata${mode ? `: Mode ${mode}` : ''}${initialState ? ', Auto-enabled' : ''}${maxExceeded ? `, Max exceeded: ${maxExceeded}` : ''}`}
      >
        {/* Mode */}
        {modeInfo && (
          <div className="flex items-center gap-1">
            <span className="text-sm">{modeInfo.icon}</span>
            <span>{modeInfo.label}</span>
          </div>
        )}

        {/* Initial State */}
        {initialState && (
          <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-lg" style={{
            background: 'rgba(16, 185, 129, 0.2)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: '#6ee7b7'
          }}>
            <span className="text-xs">✓</span>
            <span>Auto-enabled</span>
          </div>
        )}

        {/* Max Exceeded */}
        {maxExceededInfo && (
          <div className="flex items-center gap-1">
            <span className="text-sm">{maxExceededInfo.icon}</span>
            <span>{maxExceededInfo.label}</span>
          </div>
        )}
      </motion.div>

      {/* Tooltip */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            className="absolute bottom-full left-0 mb-2 z-50 px-3 py-2 rounded-xl text-xs backdrop-blur-sm"
            style={{
              background: darkMode ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              border: darkMode ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(203, 213, 225, 0.8)',
              color: darkMode ? '#cbd5e1' : '#1e293b',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.3)',
              minWidth: '280px',
              maxWidth: '320px'
            }}
            variants={tooltipVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
          >
            <div className="space-y-2">
              {/* Mode explanation */}
              {modeInfo && (
                <div>
                  <div className="font-semibold mb-1">{modeInfo.icon} {modeInfo.label} Mode</div>
                  <div className="opacity-90">{modeInfo.explanation}</div>
                </div>
              )}

              {/* Initial state explanation */}
              {initialState && (
                <div>
                  <div className="font-semibold mb-1">✓ Auto-enabled</div>
                  <div className="opacity-90">This automation will be enabled by default when created</div>
                </div>
              )}

              {/* Max exceeded explanation */}
              {maxExceededInfo && (
                <div>
                  <div className="font-semibold mb-1">{maxExceededInfo.icon} Max Exceeded: {maxExceededInfo.label}</div>
                  <div className="opacity-90">{maxExceededInfo.explanation}</div>
                </div>
              )}
            </div>

            {/* Tooltip arrow */}
            <div
              className="absolute top-full left-4 -mt-1"
              style={{
                width: 0,
                height: 0,
                borderLeft: '4px solid transparent',
                borderRight: '4px solid transparent',
                borderTop: `4px solid ${darkMode ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)'}`
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

