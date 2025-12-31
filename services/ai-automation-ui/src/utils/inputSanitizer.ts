/**
 * Input Sanitization Utilities
 * 
 * Security utilities for sanitizing user inputs to prevent XSS and injection attacks.
 * All user inputs should be sanitized before rendering or processing.
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
 * Validates that a string is a valid conversation ID format
 * Prevents injection through ID manipulation
 */
export function validateConversationId(id: string): boolean {
  if (typeof id !== 'string' || !id.trim()) {
    return false;
  }
  
  // Allow alphanumeric, hyphens, and underscores
  // Max length to prevent DoS
  const validPattern = /^[a-zA-Z0-9_-]{1,100}$/;
  return validPattern.test(id.trim());
}

/**
 * Validates that a string is a valid user ID format
 */
export function validateUserId(id: string): boolean {
  if (typeof id !== 'string' || !id.trim()) {
    return false;
  }
  
  // Allow alphanumeric, hyphens, underscores, and dots
  // Max length to prevent DoS
  const validPattern = /^[a-zA-Z0-9._-]{1,100}$/;
  return validPattern.test(id.trim());
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
  
  // Remove javascript: and data: URLs from links (basic check)
  // Simple approach: remove the URL content, keeping only the link text
  // For complex nested parentheses, we'll do a two-pass approach
  sanitized = sanitized.replace(/\[([^\]]+)\]\(javascript:[^)]*\)/gi, '[$1]');
  sanitized = sanitized.replace(/\[([^\]]+)\]\(data:[^)]*\)/gi, '[$1]');
  
  // Second pass: handle any remaining cases with nested parentheses by removing the entire link
  // This catches cases where the first pass didn't match due to nested parens
  sanitized = sanitized.replace(/\[([^\]]+)\]\(javascript:.*?\)/gs, '[$1]');
  sanitized = sanitized.replace(/\[([^\]]+)\]\(data:.*?\)/gs, '[$1]');
  
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
 * Sanitizes and validates a message input before sending
 */
export function sanitizeMessageInput(input: string, maxLength: number = 10000): string | null {
  if (typeof input !== 'string') {
    return null;
  }
  
  // Check length first
  if (!validateInputLength(input, maxLength)) {
    return null;
  }
  
  // Sanitize text
  const sanitized = sanitizeText(input);
  
  // Ensure it's not empty after sanitization
  if (!sanitized.trim()) {
    return null;
  }
  
  return sanitized;
}

