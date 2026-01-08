/**
 * Input Sanitization Utilities Tests
 * 
 * Comprehensive test suite for security utilities to prevent XSS and injection attacks.
 * Based on ai-automation-ui test patterns for consistency.
 */

import { describe, it, expect } from 'vitest';
import {
  sanitizeText,
  sanitizeHtmlAttribute,
  sanitizeUrl,
  validateEntityId,
  validateDeviceId,
  validateServiceName,
  sanitizeMarkdown,
  validateInputLength,
  sanitizeSearchQuery,
  sanitizeFilterValue,
  sanitizeJsonInput,
  validateNumericInput,
  validateTimeRange,
} from '../inputSanitizer';

describe('sanitizeText', () => {
  it('should return empty string for non-string input', () => {
    expect(sanitizeText(null as unknown as string)).toBe('');
    expect(sanitizeText(undefined as unknown as string)).toBe('');
    expect(sanitizeText(123 as unknown as string)).toBe('');
    expect(sanitizeText({} as unknown as string)).toBe('');
  });

  it('should trim whitespace', () => {
    expect(sanitizeText('  hello  ')).toBe('hello');
    expect(sanitizeText('\t\nhello\n\t')).toBe('hello');
  });

  it('should remove null bytes', () => {
    expect(sanitizeText('hello\0world')).toBe('helloworld');
    expect(sanitizeText('\0test\0')).toBe('test');
  });

  it('should remove control characters except newlines and tabs', () => {
    expect(sanitizeText('hello\x01world')).toBe('helloworld');
    expect(sanitizeText('hello\x1Fworld')).toBe('helloworld');
    expect(sanitizeText('hello\nworld')).toBe('hello\nworld');
    expect(sanitizeText('hello\tworld')).toBe('hello\tworld');
  });

  it('should preserve valid text', () => {
    expect(sanitizeText('Hello, World!')).toBe('Hello, World!');
    expect(sanitizeText('Test 123 @#$%')).toBe('Test 123 @#$%');
  });
});

describe('sanitizeHtmlAttribute', () => {
  it('should return empty string for non-string input', () => {
    expect(sanitizeHtmlAttribute(null as unknown as string)).toBe('');
    expect(sanitizeHtmlAttribute(undefined as unknown as string)).toBe('');
  });

  it('should escape HTML entities', () => {
    expect(sanitizeHtmlAttribute('<script>')).toBe('&lt;script&gt;');
    expect(sanitizeHtmlAttribute('"quoted"')).toBe('&quot;quoted&quot;');
    expect(sanitizeHtmlAttribute("'single'"
    )).toBe('&#x27;single&#x27;');
    expect(sanitizeHtmlAttribute('a & b')).toBe('a &amp; b');
    expect(sanitizeHtmlAttribute('path/to/file')).toBe('path&#x2F;to&#x2F;file');
  });

  it('should handle combined XSS attempts', () => {
    const xss = '<script>alert("XSS")</script>';
    const result = sanitizeHtmlAttribute(xss);
    expect(result).not.toContain('<');
    expect(result).not.toContain('>');
    expect(result).not.toContain('"');
  });
});

describe('sanitizeUrl', () => {
  it('should return null for non-string or empty input', () => {
    expect(sanitizeUrl(null as unknown as string)).toBeNull();
    expect(sanitizeUrl(undefined as unknown as string)).toBeNull();
    expect(sanitizeUrl('')).toBeNull();
    expect(sanitizeUrl('   ')).toBeNull();
  });

  it('should block dangerous protocols', () => {
    expect(sanitizeUrl('javascript:alert(1)')).toBeNull();
    expect(sanitizeUrl('JAVASCRIPT:alert(1)')).toBeNull();
    expect(sanitizeUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
    expect(sanitizeUrl('vbscript:alert(1)')).toBeNull();
    expect(sanitizeUrl('file:///etc/passwd')).toBeNull();
    expect(sanitizeUrl('about:blank')).toBeNull();
  });

  it('should allow safe protocols', () => {
    expect(sanitizeUrl('https://example.com')).toBe('https://example.com');
    expect(sanitizeUrl('http://example.com')).toBe('http://example.com');
    expect(sanitizeUrl('mailto:user@example.com')).toBe('mailto:user@example.com');
    expect(sanitizeUrl('tel:+1234567890')).toBe('tel:+1234567890');
  });

  it('should allow relative URLs', () => {
    expect(sanitizeUrl('/path/to/page')).toBe('/path/to/page');
    expect(sanitizeUrl('#section')).toBe('#section');
    expect(sanitizeUrl('./relative')).toBe('./relative');
  });

  it('should reject invalid URL schemes', () => {
    expect(sanitizeUrl('ftp://example.com')).toBeNull();
    expect(sanitizeUrl('invalid://example.com')).toBeNull();
  });
});

describe('validateEntityId', () => {
  it('should return false for non-string or empty input', () => {
    expect(validateEntityId(null as unknown as string)).toBe(false);
    expect(validateEntityId(undefined as unknown as string)).toBe(false);
    expect(validateEntityId('')).toBe(false);
    expect(validateEntityId('   ')).toBe(false);
  });

  it('should validate Home Assistant entity ID format', () => {
    expect(validateEntityId('light.living_room')).toBe(true);
    expect(validateEntityId('sensor.temperature_kitchen')).toBe(true);
    expect(validateEntityId('switch.bedroom_fan')).toBe(true);
    expect(validateEntityId('binary_sensor.motion_1')).toBe(true);
  });

  it('should reject invalid entity IDs', () => {
    expect(validateEntityId('no_dot')).toBe(false);
    expect(validateEntityId('.starts_with_dot')).toBe(false);
    expect(validateEntityId('ends_with.')).toBe(false);
    expect(validateEntityId('has spaces.entity')).toBe(false);
    expect(validateEntityId('has-dash.entity')).toBe(false);
    expect(validateEntityId('light.')).toBe(false);
  });
});

describe('validateDeviceId', () => {
  it('should return false for non-string or empty input', () => {
    expect(validateDeviceId(null as unknown as string)).toBe(false);
    expect(validateDeviceId(undefined as unknown as string)).toBe(false);
    expect(validateDeviceId('')).toBe(false);
  });

  it('should validate device ID format', () => {
    expect(validateDeviceId('abc123')).toBe(true);
    expect(validateDeviceId('device_123')).toBe(true);
    expect(validateDeviceId('device-456')).toBe(true);
    expect(validateDeviceId('00:11:22:33:44:55')).toBe(true); // MAC address
  });

  it('should reject invalid device IDs', () => {
    expect(validateDeviceId('has spaces')).toBe(false);
    expect(validateDeviceId('<script>')).toBe(false);
    expect(validateDeviceId('a'.repeat(101))).toBe(false); // Too long
  });
});

describe('validateServiceName', () => {
  it('should return false for non-string or empty input', () => {
    expect(validateServiceName(null as unknown as string)).toBe(false);
    expect(validateServiceName(undefined as unknown as string)).toBe(false);
    expect(validateServiceName('')).toBe(false);
  });

  it('should validate service name format', () => {
    expect(validateServiceName('websocket-ingestion')).toBe(true);
    expect(validateServiceName('data_api')).toBe(true);
    expect(validateServiceName('admin123')).toBe(true);
  });

  it('should reject invalid service names', () => {
    expect(validateServiceName('has spaces')).toBe(false);
    expect(validateServiceName('has.dot')).toBe(false);
    expect(validateServiceName('a'.repeat(101))).toBe(false);
  });
});

describe('sanitizeMarkdown', () => {
  it('should return empty string for non-string input', () => {
    expect(sanitizeMarkdown(null as unknown as string)).toBe('');
    expect(sanitizeMarkdown(undefined as unknown as string)).toBe('');
  });

  it('should remove null bytes', () => {
    expect(sanitizeMarkdown('hello\0world')).toBe('helloworld');
  });

  it('should remove script tags', () => {
    const input = 'Hello <script>alert(1)</script> World';
    expect(sanitizeMarkdown(input)).toBe('Hello  World');
  });

  it('should remove iframe tags', () => {
    const input = 'Hello <iframe src="evil.com"></iframe> World';
    expect(sanitizeMarkdown(input)).toBe('Hello  World');
  });

  it('should remove javascript: URLs from links', () => {
    const input = '[Click me](javascript:alert(1))';
    expect(sanitizeMarkdown(input)).toBe('[Click me]');
  });

  it('should remove data: URLs from links', () => {
    const input = '[Click me](data:text/html,<script>alert(1)</script>)';
    expect(sanitizeMarkdown(input)).toBe('[Click me]');
  });

  it('should preserve safe markdown', () => {
    const input = '# Title\n\n[Link](https://example.com)\n\n**bold**';
    expect(sanitizeMarkdown(input)).toBe(input);
  });
});

describe('validateInputLength', () => {
  it('should return false for non-string input', () => {
    expect(validateInputLength(null as unknown as string)).toBe(false);
    expect(validateInputLength(undefined as unknown as string)).toBe(false);
    expect(validateInputLength(123 as unknown as string)).toBe(false);
  });

  it('should validate within default max length', () => {
    expect(validateInputLength('short')).toBe(true);
    expect(validateInputLength('a'.repeat(10000))).toBe(true);
    expect(validateInputLength('a'.repeat(10001))).toBe(false);
  });

  it('should validate with custom max length', () => {
    expect(validateInputLength('hello', 10)).toBe(true);
    expect(validateInputLength('hello world', 10)).toBe(false);
  });
});

describe('sanitizeSearchQuery', () => {
  it('should return null for non-string input', () => {
    expect(sanitizeSearchQuery(null as unknown as string)).toBeNull();
    expect(sanitizeSearchQuery(undefined as unknown as string)).toBeNull();
  });

  it('should sanitize and return valid queries', () => {
    expect(sanitizeSearchQuery('hello')).toBe('hello');
    expect(sanitizeSearchQuery('  hello  ')).toBe('hello');
  });

  it('should allow empty string (for clearing filter)', () => {
    expect(sanitizeSearchQuery('')).toBe('');
  });

  it('should reject queries exceeding max length', () => {
    expect(sanitizeSearchQuery('a'.repeat(501))).toBeNull();
    expect(sanitizeSearchQuery('a'.repeat(50), 50)).toBe('a'.repeat(50));
    expect(sanitizeSearchQuery('a'.repeat(51), 50)).toBeNull();
  });
});

describe('sanitizeFilterValue', () => {
  it('should return null for non-string input', () => {
    expect(sanitizeFilterValue(null as unknown as string)).toBeNull();
    expect(sanitizeFilterValue(undefined as unknown as string)).toBeNull();
  });

  it('should sanitize and return valid values', () => {
    expect(sanitizeFilterValue('category')).toBe('category');
    expect(sanitizeFilterValue('  value  ')).toBe('value');
  });

  it('should respect max length', () => {
    expect(sanitizeFilterValue('a'.repeat(201))).toBeNull();
    expect(sanitizeFilterValue('a'.repeat(200))).toBe('a'.repeat(200));
  });
});

describe('sanitizeJsonInput', () => {
  it('should return null for non-string input', () => {
    expect(sanitizeJsonInput(null as unknown as string)).toBeNull();
    expect(sanitizeJsonInput(undefined as unknown as string)).toBeNull();
  });

  it('should remove null bytes from JSON', () => {
    expect(sanitizeJsonInput('{"key": "value\0"}')).toBe('{"key": "value"}');
  });

  it('should respect max length', () => {
    const longJson = '{"key": "' + 'a'.repeat(50000) + '"}';
    expect(sanitizeJsonInput(longJson)).toBeNull();
    expect(sanitizeJsonInput('{"key": "value"}')).toBe('{"key": "value"}');
  });
});

describe('validateNumericInput', () => {
  it('should return false for non-numeric input', () => {
    expect(validateNumericInput(NaN, 0, 100)).toBe(false);
    expect(validateNumericInput('5' as unknown as number, 0, 100)).toBe(false);
  });

  it('should validate within range', () => {
    expect(validateNumericInput(50, 0, 100)).toBe(true);
    expect(validateNumericInput(0, 0, 100)).toBe(true);
    expect(validateNumericInput(100, 0, 100)).toBe(true);
  });

  it('should reject values outside range', () => {
    expect(validateNumericInput(-1, 0, 100)).toBe(false);
    expect(validateNumericInput(101, 0, 100)).toBe(false);
  });
});

describe('validateTimeRange', () => {
  it('should validate known time ranges', () => {
    expect(validateTimeRange('15m')).toBe(true);
    expect(validateTimeRange('30m')).toBe(true);
    expect(validateTimeRange('1h')).toBe(true);
    expect(validateTimeRange('6h')).toBe(true);
    expect(validateTimeRange('12h')).toBe(true);
    expect(validateTimeRange('24h')).toBe(true);
    expect(validateTimeRange('7d')).toBe(true);
    expect(validateTimeRange('30d')).toBe(true);
  });

  it('should reject invalid time ranges', () => {
    expect(validateTimeRange('2h')).toBe(false);
    expect(validateTimeRange('1d')).toBe(false);
    expect(validateTimeRange('invalid')).toBe(false);
    expect(validateTimeRange('')).toBe(false);
  });
});
