/**
 * Custom Toast Component with data-testid support
 * Wraps react-hot-toast for E2E testing
 */

import React from 'react';
import toast, { Toast, ToastBar, Toaster } from 'react-hot-toast';

interface CustomToasterProps {
  darkMode?: boolean;
}

/**
 * Custom Toaster with data-testid attributes for testing
 */
export const CustomToaster: React.FC<CustomToasterProps> = ({ darkMode = false }) => {
  return (
    <Toaster
      position="top-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: darkMode ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255, 255, 255, 0.95)',
          color: darkMode ? '#f3f4f6' : '#1f2937',
          border: `1px solid ${darkMode ? 'rgba(51, 65, 85, 0.5)' : 'rgba(203, 213, 225, 0.5)'}`,
          borderRadius: '16px', // Updated to rounded-xl (16px) for 2025 design
          backdropFilter: 'blur(12px)',
          WebkitBackdropFilter: 'blur(12px)',
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        },
        success: {
          iconTheme: {
            primary: '#10b981',
            secondary: '#fff',
          },
        },
        error: {
          iconTheme: {
            primary: '#ef4444',
            secondary: '#fff',
          },
        },
        loading: {
          iconTheme: {
            primary: '#3b82f6',
            secondary: '#fff',
          },
        },
      }}
    >
      {(t: Toast) => (
        <div data-testid={`toast-${t.type}`}>
          <ToastBar toast={t} />
        </div>
      )}
    </Toaster>
  );
};

/**
 * Helper functions to show toasts with proper data attributes
 */
export const showToast = {
  success: (message: string) => {
    return toast.success(message);
  },
  error: (message: string) => {
    return toast.error(message);
  },
  warning: (message: string) => {
    return toast(message, { icon: '⚠️' });
  },
  info: (message: string) => {
    return toast(message, { icon: 'ℹ️' });
  },
  loading: (message: string) => {
    return toast.loading(message);
  },
};

