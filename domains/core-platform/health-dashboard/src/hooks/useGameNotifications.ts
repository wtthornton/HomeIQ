/**
 * useGameNotifications Hook
 * 
 * Manages game notification preferences and browser notification permissions
 * Phase 2 Enhancement
 */

import { useState, useEffect, useCallback } from 'react';

const STORAGE_KEY = 'sports_game_notifications';
const PERMISSION_KEY = 'sports_notification_permission_requested';

interface NotificationPreferences {
  gameIds: string[]; // Game IDs that have notifications enabled
  permissionRequested: boolean;
}

const DEFAULT_PREFERENCES: NotificationPreferences = {
  gameIds: [],
  permissionRequested: false
};

export const useGameNotifications = () => {
  const [preferences, setPreferences] = useState<NotificationPreferences>(DEFAULT_PREFERENCES);
  const [permission, setPermission] = useState<NotificationPermission>('default');
  const [loading, setLoading] = useState(true);

  // Load preferences from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored) as NotificationPreferences;
        setPreferences(parsed);
      }

      // Check browser notification permission
      if ('Notification' in window) {
        setPermission(Notification.permission);
      }
    } catch (error) {
      console.error('Error loading notification preferences:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Check if notifications are enabled for a game
  const isNotificationEnabled = useCallback((gameId: string) => {
    return preferences.gameIds.includes(gameId);
  }, [preferences.gameIds]);

  // Request browser notification permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    if (!('Notification' in window)) {
      console.warn('Browser does not support notifications');
      return false;
    }

    if (Notification.permission === 'granted') {
      setPermission('granted');
      return true;
    }

    if (Notification.permission === 'denied') {
      setPermission('denied');
      return false;
    }

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      
      // Store that we've requested permission
      localStorage.setItem(PERMISSION_KEY, 'true');
      
      return result === 'granted';
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return false;
    }
  }, []);

  // Toggle notifications for a game
  const toggleNotification = useCallback(async (gameId: string): Promise<boolean> => {
    const isEnabled = isNotificationEnabled(gameId);
    
    // If enabling, request permission first
    if (!isEnabled) {
      const hasPermission = await requestPermission();
      if (!hasPermission) {
        return false; // User denied permission
      }
    }

    // Update preferences
    const newGameIds = isEnabled
      ? preferences.gameIds.filter(id => id !== gameId)
      : [...preferences.gameIds, gameId];

    const newPreferences: NotificationPreferences = {
      ...preferences,
      gameIds: newGameIds
    };

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newPreferences));
      setPreferences(newPreferences);
      return true;
    } catch (error) {
      console.error('Error saving notification preferences:', error);
      return false;
    }
  }, [preferences, isNotificationEnabled, requestPermission]);

  // Show a browser notification (if permission granted)
  const showNotification = useCallback((title: string, options?: NotificationOptions) => {
    if (!('Notification' in window) || Notification.permission !== 'granted') {
      return false;
    }

    try {
      new Notification(title, {
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        ...options
      });
      return true;
    } catch (error) {
      console.error('Error showing notification:', error);
      return false;
    }
  }, []);

  return {
    loading,
    permission,
    isNotificationEnabled,
    requestPermission,
    toggleNotification,
    showNotification,
    enabledGameIds: preferences.gameIds
  };
};
