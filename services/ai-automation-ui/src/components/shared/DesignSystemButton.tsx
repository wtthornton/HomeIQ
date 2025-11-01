/**
 * DesignSystemButton - Reusable button component with Modern & Manly design system styling
 * 
 * Standardized button component that applies consistent styling across the application.
 */

import React from 'react';
import { motion } from 'framer-motion';
import { getButtonStyles } from '../../utils/designSystem';

interface DesignSystemButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  children: React.ReactNode;
  animate?: boolean;
}

export const DesignSystemButton: React.FC<DesignSystemButtonProps> = ({
  variant = 'primary',
  children,
  animate = true,
  className = '',
  style = {},
  ...props
}) => {
  const buttonStyles = getButtonStyles(variant, style);

  const buttonContent = (
    <button
      style={buttonStyles}
      className={className}
      {...props}
      onMouseEnter={(e) => {
        if (variant !== 'secondary') {
          e.currentTarget.style.transform = 'translateY(-1px)';
        }
        props.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        props.onMouseLeave?.(e);
      }}
    >
      {children}
    </button>
  );

  if (animate) {
    return (
      <motion.div
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        {buttonContent}
      </motion.div>
    );
  }

  return buttonContent;
};

