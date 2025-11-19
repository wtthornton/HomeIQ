/**
 * Original Request Card - Timeline Component
 * 
 * Displays the user's original request in the conversational timeline.
 */

import React from 'react';
import { motion } from 'framer-motion';

interface OriginalRequestCardProps {
  originalRequest: string;
  darkMode?: boolean;
}

export const OriginalRequestCard: React.FC<OriginalRequestCardProps> = ({
  originalRequest,
  darkMode = false
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-lg p-3"
      style={{
        background: darkMode 
          ? 'rgba(59, 130, 246, 0.15)' 
          : 'rgba(59, 130, 246, 0.08)',
        border: `2px solid ${darkMode ? 'rgba(59, 130, 246, 0.4)' : 'rgba(59, 130, 246, 0.3)'}`,
        borderLeftWidth: '4px',
        borderLeftColor: darkMode ? 'rgba(59, 130, 246, 0.6)' : 'rgba(59, 130, 246, 0.5)'
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span className="text-lg">🗣️</span>
        <h4 
          className="font-semibold text-xs uppercase tracking-wider"
          style={{ color: darkMode ? '#93c5fd' : '#1e40af' }}
        >
          Original Request
        </h4>
      </div>
      <div 
        className="text-sm leading-relaxed whitespace-pre-wrap"
        style={{ color: darkMode ? '#cbd5e1' : '#1e293b' }}
      >
        {originalRequest}
      </div>
    </motion.div>
  );
};

