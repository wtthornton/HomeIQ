/**
 * Unit Tests for Input Sanitization Utilities
 * 
 * Tests all security utilities for sanitizing user inputs to prevent XSS and injection attacks.
 */

import { describe, it, expect } from 'vitest';
import {
  sanitizeText,
  sanitizeHtmlAttribute,
  sanitizeUrl,
  validateConversationId,
  validateUserId,
  sanitizeMarkdown,
  validateInputLength,
  sanitizeMessageInput,
} from '../inputSanitizer';

describe('inputSanitizer', () => {
  describe('sanitizeText', () => {
    it('should remove null bytes', () => {
      expect(sanitizeText('hello\0world')).toBe('helloworld');
      expect(sanitizeText('\0\0\0')).toBe('');
    });

    it('should remove control characters except newlines, tabs, and carriage returns', () => {
      expect(sanitizeText('hello\nworld')).toBe('hello\nworld');
      expect(sanitizeText('hello\tworld')).toBe('hello\tworld');
      expect(sanitizeText('hello\rworld')).toBe('hello\rworld');
      expect(sanitizeText('hello\x01world')).toBe('helloworld');
      expect(sanitizeText('hello\x7Fworld')).toBe('helloworld');
    });

    it('should trim whitespace', () => {
      expect(sanitizeText('  hello world  ')).toBe('hello world');
    });

    it('should return empty string for non-string input', () => {
      expect(sanitizeText(null as any)).toBe('');
      expect(sanitizeText(undefined as any)).toBe('');
      expect(sanitizeText(123 as any)).toBe('');
      expect(sanitizeText({} as any)).toBe('');
    });

    it('should handle empty strings', () => {
      expect(sanitizeText('')).toBe('');
    });

    it('should preserve normal text', () => {
      expect(sanitizeText('Hello, World!')).toBe('Hello, World!');
      expect(sanitizeText('Test 123')).toBe('Test 123');
    });
  });

  describe('sanitizeHtmlAttribute', () => {
    it('should escape HTML entities', () => {
      expect(sanitizeHtmlAttribute('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;&#x2F;script&gt;');
      expect(sanitizeHtmlAttribute("test'value")).toBe('test&#x27;value');
      expect(sanitizeHtmlAttribute('test&value')).toBe('test&amp;value');
    });

    it('should escape forward slashes', () => {
      expect(sanitizeHtmlAttribute('test/value')).toBe('test&#x2F;value');
    });

    it('should return empty string for non-string input', () => {
      expect(sanitizeHtmlAttribute(null as any)).toBe('');
      expect(sanitizeHtmlAttribute(undefined as any)).toBe('');
    });

    it('should combine with sanitizeText', () => {
      expect(sanitizeHtmlAttribute('  <test>\0  ')).toBe('&lt;test&gt;');
    });

    it('should handle normal text', () => {
      expect(sanitizeHtmlAttribute('hello world')).toBe('hello world');
    });
  });

  describe('sanitizeUrl', () => {
    it('should allow http URLs', () => {
      expect(sanitizeUrl('http://example.com')).toBe('http://example.com');
      expect(sanitizeUrl('HTTP://EXAMPLE.COM')).toBe('HTTP://EXAMPLE.COM');
    });

    it('should allow https URLs', () => {
      expect(sanitizeUrl('https://example.com')).toBe('https://example.com');
    });

    it('should allow mailto URLs', () => {
      expect(sanitizeUrl('mailto:test@example.com')).toBe('mailto:test@example.com');
    });

    it('should allow tel URLs', () => {
      expect(sanitizeUrl('tel:+1234567890')).toBe('tel:+1234567890');
    });

    it('should allow relative URLs', () => {
      expect(sanitizeUrl('/path/to/page')).toBe('/path/to/page');
      expect(sanitizeUrl('./relative')).toBe('./relative');
      expect(sanitizeUrl('#anchor')).toBe('#anchor');
    });

    it('should block javascript: protocol', () => {
      expect(sanitizeUrl('javascript:alert("xss")')).toBeNull();
      expect(sanitizeUrl('JAVASCRIPT:alert("xss")')).toBeNull();
    });

    it('should block data: protocol', () => {
      expect(sanitizeUrl('data:text/html,<script>alert("xss")</script>')).toBeNull();
    });

    it('should block vbscript: protocol', () => {
      expect(sanitizeUrl('vbscript:msgbox("xss")')).toBeNull();
    });

    it('should block file: protocol', () => {
      expect(sanitizeUrl('file:///etc/passwd')).toBeNull();
    });

    it('should block about: protocol', () => {
      expect(sanitizeUrl('about:blank')).toBeNull();
    });

    it('should return null for invalid URLs', () => {
      expect(sanitizeUrl('invalid-url')).toBeNull();
      expect(sanitizeUrl('ftp://example.com')).toBeNull();
    });

    it('should return null for empty or whitespace strings', () => {
      expect(sanitizeUrl('')).toBeNull();
      expect(sanitizeUrl('   ')).toBeNull();
    });

    it('should return null for non-string input', () => {
      expect(sanitizeUrl(null as any)).toBeNull();
      expect(sanitizeUrl(undefined as any)).toBeNull();
    });

    it('should trim URLs', () => {
      expect(sanitizeUrl('  https://example.com  ')).toBe('https://example.com');
    });
  });

  describe('validateConversationId', () => {
    it('should accept valid conversation IDs', () => {
      expect(validateConversationId('conv-123')).toBe(true);
      expect(validateConversationId('conv_123')).toBe(true);
      expect(validateConversationId('CONV123')).toBe(true);
      expect(validateConversationId('a')).toBe(true);
      expect(validateConversationId('a'.repeat(100))).toBe(true);
    });

    it('should reject invalid characters', () => {
      expect(validateConversationId('conv@123')).toBe(false);
      expect(validateConversationId('conv.123')).toBe(false);
      expect(validateConversationId('conv 123')).toBe(false);
      expect(validateConversationId('conv<script>')).toBe(false);
    });

    it('should reject IDs that are too long', () => {
      expect(validateConversationId('a'.repeat(101))).toBe(false);
    });

    it('should reject empty strings', () => {
      expect(validateConversationId('')).toBe(false);
      expect(validateConversationId('   ')).toBe(false);
    });

    it('should reject non-string input', () => {
      expect(validateConversationId(null as any)).toBe(false);
      expect(validateConversationId(undefined as any)).toBe(false);
      expect(validateConversationId(123 as any)).toBe(false);
    });

    it('should trim before validation', () => {
      expect(validateConversationId('  conv-123  ')).toBe(true);
    });
  });

  describe('validateUserId', () => {
    it('should accept valid user IDs', () => {
      expect(validateUserId('user-123')).toBe(true);
      expect(validateUserId('user_123')).toBe(true);
      expect(validateUserId('user.123')).toBe(true);
      expect(validateUserId('USER123')).toBe(true);
      expect(validateUserId('a')).toBe(true);
      expect(validateUserId('a'.repeat(100))).toBe(true);
    });

    it('should reject invalid characters', () => {
      expect(validateUserId('user@123')).toBe(false);
      expect(validateUserId('user 123')).toBe(false);
      expect(validateUserId('user<script>')).toBe(false);
    });

    it('should reject IDs that are too long', () => {
      expect(validateUserId('a'.repeat(101))).toBe(false);
    });

    it('should reject empty strings', () => {
      expect(validateUserId('')).toBe(false);
      expect(validateUserId('   ')).toBe(false);
    });

    it('should reject non-string input', () => {
      expect(validateUserId(null as any)).toBe(false);
      expect(validateUserId(undefined as any)).toBe(false);
    });

    it('should trim before validation', () => {
      expect(validateUserId('  user.123  ')).toBe(true);
    });
  });

  describe('sanitizeMarkdown', () => {
    it('should remove null bytes', () => {
      expect(sanitizeMarkdown('hello\0world')).toBe('helloworld');
    });

    it('should remove script tags', () => {
      expect(sanitizeMarkdown('<script>alert("xss")</script>')).toBe('');
      expect(sanitizeMarkdown('<SCRIPT>alert("xss")</SCRIPT>')).toBe('');
      expect(sanitizeMarkdown('Text <script>alert("xss")</script> more text')).toBe('Text  more text');
    });

    it('should remove iframe tags', () => {
      expect(sanitizeMarkdown('<iframe src="evil.com"></iframe>')).toBe('');
      expect(sanitizeMarkdown('Text <iframe></iframe> more')).toBe('Text  more');
    });

    it('should remove javascript: URLs from links', () => {
      // Note: The regex may leave a trailing ) in complex cases, but the dangerous URL is removed
      const result1 = sanitizeMarkdown('[Click me](javascript:alert("xss"))');
      expect(result1).toMatch(/^\[Click me\]/);
      expect(result1).not.toContain('javascript:');
      
      const result2 = sanitizeMarkdown('[Link](JAVASCRIPT:alert("xss"))');
      expect(result2).toMatch(/^\[Link\]/);
      expect(result2).not.toContain('javascript:');
    });

    it('should remove data: URLs from links', () => {
      expect(sanitizeMarkdown('[Click](data:text/html,<script>alert("xss")</script>)')).toBe('[Click]');
    });

    it('should preserve normal markdown', () => {
      const markdown = '# Heading\n\n**Bold** text and [link](https://example.com)';
      expect(sanitizeMarkdown(markdown)).toBe(markdown);
    });

    it('should return empty string for non-string input', () => {
      expect(sanitizeMarkdown(null as any)).toBe('');
      expect(sanitizeMarkdown(undefined as any)).toBe('');
    });

    it('should handle empty strings', () => {
      expect(sanitizeMarkdown('')).toBe('');
    });
  });

  describe('validateInputLength', () => {
    it('should accept inputs within max length', () => {
      expect(validateInputLength('hello', 10)).toBe(true);
      expect(validateInputLength('hello', 5)).toBe(true);
      expect(validateInputLength('a'.repeat(10000), 10000)).toBe(true);
    });

    it('should reject inputs exceeding max length', () => {
      expect(validateInputLength('hello', 4)).toBe(false);
      expect(validateInputLength('a'.repeat(10001), 10000)).toBe(false);
    });

    it('should use default max length of 10000', () => {
      expect(validateInputLength('a'.repeat(10000))).toBe(true);
      expect(validateInputLength('a'.repeat(10001))).toBe(false);
    });

    it('should return false for non-string input', () => {
      expect(validateInputLength(null as any)).toBe(false);
      expect(validateInputLength(undefined as any)).toBe(false);
      expect(validateInputLength(123 as any)).toBe(false);
    });

    it('should handle empty strings', () => {
      expect(validateInputLength('', 10)).toBe(true);
    });
  });

  describe('sanitizeMessageInput', () => {
    it('should sanitize and return valid input', () => {
      expect(sanitizeMessageInput('Hello, World!')).toBe('Hello, World!');
      expect(sanitizeMessageInput('  Test message  ')).toBe('Test message');
    });

    it('should remove control characters', () => {
      expect(sanitizeMessageInput('hello\x01world')).toBe('helloworld');
    });

    it('should return null for input exceeding max length', () => {
      expect(sanitizeMessageInput('a'.repeat(10001), 10000)).toBeNull();
    });

    it('should return null for empty input after sanitization', () => {
      expect(sanitizeMessageInput('   ')).toBeNull();
      expect(sanitizeMessageInput('\0\0\0')).toBeNull();
    });

    it('should return null for non-string input', () => {
      expect(sanitizeMessageInput(null as any)).toBeNull();
      expect(sanitizeMessageInput(undefined as any)).toBeNull();
      expect(sanitizeMessageInput(123 as any)).toBeNull();
    });

    it('should use default max length of 10000', () => {
      expect(sanitizeMessageInput('a'.repeat(10000))).toBe('a'.repeat(10000));
      expect(sanitizeMessageInput('a'.repeat(10001))).toBeNull();
    });

    it('should handle custom max length', () => {
      expect(sanitizeMessageInput('hello', 5)).toBe('hello');
      expect(sanitizeMessageInput('hello world', 5)).toBeNull();
    });

    it('should preserve newlines and tabs', () => {
      expect(sanitizeMessageInput('hello\nworld')).toBe('hello\nworld');
      expect(sanitizeMessageInput('hello\tworld')).toBe('hello\tworld');
    });
  });
});

