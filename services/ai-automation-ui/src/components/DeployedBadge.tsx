/**
 * DeployedBadge Component
 * 
 * Interactive badge that shows deployment status for automations.
 * Features:
 * - Pulse animation to draw attention
 * - Expandable deployment details
 * - Hover tooltip
 * - Accessibility support
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DeployedBadgeProps {
  automationId: string;
  deployedAt?: string;
  status?: 'active' | 'disabled';
  darkMode?: boolean;
  onEdit?: () => void;
  onDisable?: () => void;
}

export const DeployedBadge: React.FC<DeployedBadgeProps> = ({
  automationId,
  deployedAt,
  status = 'active',
  darkMode = false,
  onEdit,
  onDisable
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
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

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Just now';
    try {
      const date = new Date(dateString);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    } catch {
      return 'Just now';
    }
  };

  const badgeVariants = {
    pulse: prefersReducedMotion ? {} : {
      scale: [1, 1.05, 1],
      transition: {
        duration: 2,
        repeat: Infinity,
        repeatDelay: 3
      }
    }
  };

  return (
    <div className="relative">
      {/* Main Badge */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium cursor-pointer transition-all"
        style={{
          background: status === 'active' 
            ? 'rgba(16, 185, 129, 0.2)' 
            : 'rgba(107, 114, 128, 0.2)',
          border: `1px solid ${status === 'active' ? 'rgba(16, 185, 129, 0.5)' : 'rgba(107, 114, 128, 0.5)'}`,
          color: status === 'active' ? '#6ee7b7' : '#9ca3af'
        }}
        variants={badgeVariants}
        animate={status === 'active' && !isExpanded ? 'pulse' : {}}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        aria-label={`Deployed automation ${automationId}. Click to ${isExpanded ? 'collapse' : 'expand'} details`}
        aria-expanded={isExpanded}
      >
        <span className="text-sm">
          {status === 'active' ? '🟢' : '⏸️'}
        </span>
        <span>Active Automation</span>
        <span className="text-xs opacity-70">
          {isExpanded ? '▼' : '▶'}
        </span>
      </motion.button>

      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0, y: -10 }}
            animate={{ opacity: 1, height: 'auto', y: 0 }}
            exit={{ opacity: 0, height: 0, y: -10 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.2 }}
            className="absolute top-full left-0 mt-2 z-10 rounded-lg border shadow-lg overflow-hidden"
            style={{
              background: darkMode ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
              border: darkMode ? '1px solid rgba(51, 65, 85, 0.8)' : '1px solid rgba(203, 213, 225, 0.8)',
              minWidth: '280px',
              backdropFilter: 'blur(10px)'
            }}
          >
            <div className="p-3 space-y-2">
              {/* Automation ID */}
              <div>
                <div className="text-xs font-semibold mb-1" style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>
                  Automation ID
                </div>
                <div className="text-sm font-mono" style={{ color: darkMode ? '#cbd5e1' : '#1e293b' }}>
                  {automationId}
                </div>
              </div>

              {/* Deployment Time */}
              {deployedAt && (
                <div>
                  <div className="text-xs font-semibold mb-1" style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>
                    Deployed
                  </div>
                  <div className="text-sm" style={{ color: darkMode ? '#cbd5e1' : '#1e293b' }}>
                    {formatDate(deployedAt)}
                  </div>
                </div>
              )}

              {/* Status */}
              <div>
                <div className="text-xs font-semibold mb-1" style={{ color: darkMode ? '#94a3b8' : '#64748b' }}>
                  Status
                </div>
                <div className="text-sm" style={{ color: status === 'active' ? '#10b981' : '#9ca3af' }}>
                  {status === 'active' ? '🟢 Active' : '⏸️ Disabled'}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2 border-t" style={{ borderColor: darkMode ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)' }}>
                {onEdit && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onEdit();
                    }}
                    className="flex-1 px-2 py-1 text-xs rounded font-medium transition-all"
                    style={{
                      background: 'rgba(59, 130, 246, 0.2)',
                      border: '1px solid rgba(59, 130, 246, 0.4)',
                      color: '#93c5fd'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(59, 130, 246, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(59, 130, 246, 0.2)';
                    }}
                  >
                    Edit
                  </button>
                )}
                {onDisable && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDisable();
                    }}
                    className="flex-1 px-2 py-1 text-xs rounded font-medium transition-all"
                    style={{
                      background: 'rgba(239, 68, 68, 0.2)',
                      border: '1px solid rgba(239, 68, 68, 0.4)',
                      color: '#fca5a5'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(239, 68, 68, 0.3)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)';
                    }}
                  >
                    {status === 'active' ? 'Disable' : 'Enable'}
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

