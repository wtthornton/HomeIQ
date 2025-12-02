/**
 * Icon Helpers Utility
 * 
 * Utilities for resolving entity icons with proper fallback logic.
 * Prioritizes user-customized icons over defaults.
 */

// Domain default icons (fallback when no icon is available)
const DOMAIN_DEFAULT_ICONS: Record<string, string> = {
  'light': '💡',
  'switch': '🔌',
  'sensor': '📡',
  'binary_sensor': '📊',
  'climate': '🌡️',
  'fan': '🌀',
  'cover': '🪟',
  'lock': '🔒',
  'media_player': '📺',
  'camera': '📷',
  'vacuum': '🤖',
  'automation': '⚙️',
  'script': '📜',
  'scene': '🎬',
  'input_boolean': '🔘',
  'input_number': '🔢',
  'input_select': '📋',
  'input_text': '✏️',
  'timer': '⏱️',
  'weather': '🌤️',
  'sun': '☀️',
  'person': '👤',
  'device_tracker': '📍',
  'zone': '🗺️',
  'group': '👥',
  'default': '🏠'
};

/**
 * Resolve the best icon to display for an entity
 * Priority: icon (user-customized) > original_icon > domain default > generic default
 */
export function resolveEntityIcon(
  icon?: string,
  originalIcon?: string,
  domain?: string
): string {
  // Priority 1: User-customized icon
  if (icon) {
    return icon;
  }

  // Priority 2: Original icon from integration
  if (originalIcon) {
    return originalIcon;
  }

  // Priority 3: Domain default icon
  if (domain && DOMAIN_DEFAULT_ICONS[domain]) {
    return DOMAIN_DEFAULT_ICONS[domain];
  }

  // Priority 4: Generic default
  return DOMAIN_DEFAULT_ICONS.default;
}

/**
 * Check if an icon is user-customized (different from original)
 */
export function isUserCustomized(
  icon?: string,
  originalIcon?: string
): boolean {
  // If no icon, not customized
  if (!icon) {
    return false;
  }

  // If no original icon, assume customized if icon exists
  if (!originalIcon) {
    return true;
  }

  // Compare icons (case-insensitive)
  return icon.toLowerCase() !== originalIcon.toLowerCase();
}

/**
 * Get tooltip text for an icon
 */
export function getIconTooltip(
  icon?: string,
  originalIcon?: string,
  domain?: string
): string {
  if (isUserCustomized(icon, originalIcon)) {
    return `Custom icon (Original: ${originalIcon || 'none'})`;
  }

  if (icon || originalIcon) {
    return 'Default icon';
  }

  if (domain) {
    return `Default ${domain} icon`;
  }

  return 'Default icon';
}

/**
 * Get domain default icon
 */
export function getDomainDefaultIcon(domain?: string): string {
  if (!domain) {
    return DOMAIN_DEFAULT_ICONS.default;
  }

  return DOMAIN_DEFAULT_ICONS[domain] || DOMAIN_DEFAULT_ICONS.default;
}

/**
 * Format Home Assistant MDI icon name for display
 * Converts "mdi:lightbulb" to "💡" or returns as-is if not MDI format
 */
export function formatMdiIcon(icon: string): string {
  // If it's an MDI icon (mdi:icon-name), we can't render it directly
  // Return as-is for now (would need icon library integration)
  if (icon.startsWith('mdi:')) {
    return icon;
  }

  // If it's an emoji or other format, return as-is
  return icon;
}

