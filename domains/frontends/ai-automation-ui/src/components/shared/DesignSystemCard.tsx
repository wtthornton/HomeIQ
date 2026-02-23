/**
 * DesignSystemCard - Reusable card component with Modern & Manly design system styling
 * 
 * A standardized card component that applies the design system aesthetic consistently
 * across all cards in the application.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { getCardStyles, getCornerAccentStyles } from '../../utils/designSystem';

interface DesignSystemCardProps {
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  onClick?: () => void;
  showCornerAccents?: boolean;
  animate?: boolean;
}

export const DesignSystemCard: React.FC<DesignSystemCardProps> = ({
  children,
  className = '',
  style = {},
  onClick,
  showCornerAccents = true,
  animate = true
}) => {
  const cardContent = (
    <div
      style={{ ...getCardStyles(), ...style }}
      className={className}
      onClick={onClick}
    >
      {/* Corner accents */}
      {showCornerAccents && (
        <>
          <div style={getCornerAccentStyles('top-left')} />
          <div style={getCornerAccentStyles('top-right')} />
          <div style={getCornerAccentStyles('bottom-left')} />
          <div style={getCornerAccentStyles('bottom-right')} />
        </>
      )}
      {children}
    </div>
  );

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {cardContent}
      </motion.div>
    );
  }

  return cardContent;
};

