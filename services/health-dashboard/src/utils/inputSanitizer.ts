/**
 * Input Sanitization Utilities
 * 
 * Security utilities for sanitizing user inputs to prevent XSS and injection attacks.
 * All user inputs should be sanitized before rendering or processing.
 * 
 * Based on ai-automation-ui implementation for consistency across HomeIQ UIs.
 */

/**
 * Sanitizes a string by removing potentially dangerous characters
 * Used for user inputs that will be displayed as text (not HTML)
 */
export function sanitizeText(input: string): string {
  if (typeof input !== 'string') {
    return '';
  }
  
  // Remove null bytes and control characters (except newlines, tabs, carriage returns)
  // eslint-disable-next-line no-control-regex
  return input
    .replace(/\0/g, '')
    .replace(/[\x01-\x08\x0B-\x0C\x0E-\x1F\x7F]/g, '')
    .trim();
}

/**
 * Sanitizes a string for use in HTML attributes
 * Escapes HTML entities to prevent XSS
 */
export function sanitizeHtmlAttribute(input: string): string {
  if (typeof input !== 'string') {
    return '';
  }
  
  const sanitized = sanitizeText(input);
  
  // Escape HTML entities
  return sanitized
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

/**
 * Validates and sanitizes a URL to prevent javascript: and data: protocol attacks
 * Returns null if URL is invalid or dangerous
 */
export function sanitizeUrl(url: string): string | null {
  if (typeof url !== 'string' || !url.trim()) {
    return null;
  }
  
  const trimmed = url.trim();
  
  // Block dangerous protocols
  const dangerousProtocols = ['javascript:', 'data:', 'vbscript:', 'file:', 'about:'];
  const lowerUrl = trimmed.toLowerCase();
  
  for (const protocol of dangerousProtocols) {
    if (lowerUrl.startsWith(protocol)) {
      return null;
    }
  }
  
  // Allow http, https, mailto, tel, and relative URLs
  const allowedPattern = /^(https?:\/\/|mailto:|tel:|\/|#|\.)/i;
  if (!allowedPattern.test(trimmed)) {
    return null;
  }
  
  return trimmed;
}

/**
 * Validates that a string is a valid entity ID format
 * Prevents injection through ID manipulation
 */
export function validateEntityId(id: string): boolean {
  if (typeof id !== 'string' || !id.trim()) {
    return false;
  }
  
  // Home Assistant entity IDs follow the pattern: domain.entity_name
  // Allow alphanumeric, underscores, and dots
  // Max length to prevent DoS
  const validPattern = /^[a-zA-Z0-9_]+\.[a-zA-Z0-9_]{1,200}$/;
  return validPattern.test(id.trim());
}

/**
 * Validates that a string is a valid device ID format
 */
export function validateDeviceId(id: string): boolean {
  if (typeof id !== 'string' || !id.trim()) {
    return false;
  }
  
  // Allow alphanumeric, hyphens, underscores, and colons (for MAC addresses)
  // Max length to prevent DoS
  const validPattern = /^[a-zA-Z0-9_:-]{1,100}$/;
  return validPattern.test(id.trim());
}

/**
 * Validates that a string is a valid service name format
 */
export function validateServiceName(name: string): boolean {
  if (typeof name !== 'string' || !name.trim()) {
    return false;
  }
  
  // Allow alphanumeric, hyphens, and underscores
  // Max length to prevent DoS
  const validPattern = /^[a-zA-Z0-9_-]{1,100}$/;
  return validPattern.test(name.trim());
}

/**
 * Sanitizes markdown content by removing potentially dangerous patterns
 * This is a basic sanitization - ReactMarkdown should handle the rest
 */
export function sanitizeMarkdown(content: string): string {
  if (typeof content !== 'string') {
    return '';
  }
  
  // Remove null bytes
  let sanitized = content.replace(/\0/g, '');
  
  // Remove script tags (shouldn't be in markdown, but just in case)
  sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  
  // Remove iframe tags
  sanitized = sanitized.replace(/<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>/gi, '');
  
  // Remove javascript: and data: URLs from links
  // Match markdown links with dangerous protocols and keep only the link text
  // Handle nested parentheses by matching balanced parens or non-paren chars
  sanitized = sanitized.replace(/\[([^\]]*)\]\(javascript:(?:[^()]*|\([^()]*\))*\)/gi, '[$1]');
  sanitized = sanitized.replace(/\[([^\]]*)\]\(data:(?:[^()]*|\([^()]*\))*\)/gi, '[$1]');
  
  return sanitized;
}

/**
 * Validates input length to prevent DoS attacks
 */
export function validateInputLength(input: string, maxLength: number = 10000): boolean {
  if (typeof input !== 'string') {
    return false;
  }
  
  return input.length <= maxLength;
}

/**
 * Sanitizes and validates search query input
 */
export function sanitizeSearchQuery(input: string, maxLength: number = 500): string | null {
  if (typeof input !== 'string') {
    return null;
  }
  
  // Check length first
  if (!validateInputLength(input, maxLength)) {
    return null;
  }
  
  // Sanitize text
  const sanitized = sanitizeText(input);
  
  // Allow empty search (to clear filter)
  return sanitized;
}

/**
 * Sanitizes filter/selector values
 */
export function sanitizeFilterValue(input: string, maxLength: number = 200): string | null {
  if (typeof input !== 'string') {
    return null;
  }
  
  // Check length first
  if (!validateInputLength(input, maxLength)) {
    return null;
  }
  
  // Sanitize text
  const sanitized = sanitizeText(input);
  
  // Ensure it's not empty after sanitization (unless empty is allowed)
  return sanitized;
}

/**
 * Sanitizes JSON string input before parsing
 * Returns null if input appears malicious
 */
export function sanitizeJsonInput(input: string, maxLength: number = 50000): string | null {
  if (typeof input !== 'string') {
    return null;
  }
  
  // Check length first
  if (!validateInputLength(input, maxLength)) {
    return null;
  }
  
  // Remove null bytes
  const sanitized = input.replace(/\0/g, '');
  
  return sanitized;
}

/**
 * Validates a numeric input within a range
 */
export function validateNumericInput(value: number, min: number, max: number): boolean {
  if (typeof value !== 'number' || isNaN(value)) {
    return false;
  }
  
  return value >= min && value <= max;
}

/**
 * Sanitizes and validates a time range parameter
 */
export function validateTimeRange(range: string): boolean {
  const validRanges = ['15m', '30m', '1h', '6h', '12h', '24h', '7d', '30d'];
  return validRanges.includes(range);
}
