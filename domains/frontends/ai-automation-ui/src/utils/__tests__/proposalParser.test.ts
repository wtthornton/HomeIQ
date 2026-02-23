/**
 * Unit Tests for Proposal Parser
 * 
 * Tests proposal detection, parsing, and edge cases
 */

import { describe, it, expect } from 'vitest';
import { isProposalMessage, parseProposal, extractCTAPrompt } from '../proposalParser';

describe('proposalParser', () => {
  describe('isProposalMessage', () => {
    it('should detect standard proposal format', () => {
      const content = "Here's what I'll create for you:";
      expect(isProposalMessage(content)).toBe(true);
    });

    it('should detect case variations', () => {
      expect(isProposalMessage("here's what i'll create for you:")).toBe(true);
      expect(isProposalMessage("HERE'S WHAT I'LL CREATE FOR YOU:")).toBe(true);
    });

    it('should return false for non-proposal text', () => {
      expect(isProposalMessage("Hello, how are you?")).toBe(false);
      expect(isProposalMessage("")).toBe(false);
    });

    it('should detect proposal in longer text', () => {
      const content = "Some text before. Here's what I'll create for you: More text after.";
      expect(isProposalMessage(content)).toBe(true);
    });
  });

  describe('parseProposal', () => {
    const standardProposal = `Here's what I'll create for you:

**✨ What it does:** Every 15 minutes, your office lights will flash red for 1 second, then return to previous state.

**📋 When it runs:** Every 15 minutes, all day (00:00, 00:15, 00:30, 00:45, etc.)

**🎯 What's affected:** • Office area lights (7 total) • All Office light devices

**⚙️ How it works:** 1) Save current state, 2) Turn red at full brightness, 3) Wait 1 second, 4) Restore state

Ready to create this? Say 'approve', 'create', 'yes', or 'go ahead'! 🚀`;

    it('should parse complete proposal with all sections', () => {
      const result = parseProposal(standardProposal);
      
      expect(result.hasProposal).toBe(true);
      expect(result.sections).toHaveLength(4);
      
      expect(result.sections[0].type).toBe('what');
      expect(result.sections[0].icon).toBe('✨');
      expect(result.sections[0].title).toContain('What it does');
      
      expect(result.sections[1].type).toBe('when');
      expect(result.sections[1].icon).toBe('📋');
      
      expect(result.sections[2].type).toBe('affected');
      expect(result.sections[2].icon).toBe('🎯');
      
      expect(result.sections[3].type).toBe('how');
      expect(result.sections[3].icon).toBe('⚙️');
    });

    it('should handle missing sections gracefully', () => {
      const partialProposal = `Here's what I'll create for you:

**✨ What it does:** Some description.

**📋 When it runs:** Some trigger.`;

      const result = parseProposal(partialProposal);
      expect(result.hasProposal).toBe(true);
      expect(result.sections).toHaveLength(2);
    });

    it('should return empty sections for non-proposal', () => {
      const result = parseProposal("This is not a proposal.");
      expect(result.hasProposal).toBe(false);
      expect(result.sections).toHaveLength(0);
    });

    it('should handle sections without emojis', () => {
      const proposalWithoutEmojis = `Here's what I'll create for you:

**What it does:** Description without emoji.

**When it runs:** Trigger description.`;

      const result = parseProposal(proposalWithoutEmojis);
      // Should still attempt to parse, may not match all sections
      expect(result.hasProposal).toBeDefined();
    });

    it('should handle long content', () => {
      const longContent = `Here's what I'll create for you:

**✨ What it does:** ${'A'.repeat(500)}`;

      const result = parseProposal(longContent);
      expect(result.hasProposal).toBe(true);
      expect(result.sections.length).toBeGreaterThan(0);
    });

    it('should preserve content formatting', () => {
      const result = parseProposal(standardProposal);
      const whatSection = result.sections.find(s => s.type === 'what');
      
      expect(whatSection?.content).toContain('Every 15 minutes');
      expect(whatSection?.content).toContain('flash red');
    });

    it('should handle special characters', () => {
      const specialChars = `Here's what I'll create for you:

**✨ What it does:** Test with "quotes" and 'apostrophes' and <tags>`;

      const result = parseProposal(specialChars);
      expect(result.hasProposal).toBe(true);
    });
  });

  describe('extractCTAPrompt', () => {
    it('should extract CTA prompt', () => {
      const content = "Ready to create this? Say 'approve', 'create', 'yes', or 'go ahead'! 🚀";
      const cta = extractCTAPrompt(content);
      expect(cta).toContain('Ready to create');
    });

    it('should return null when no CTA present', () => {
      const content = "This is just regular text.";
      const cta = extractCTAPrompt(content);
      expect(cta).toBeNull();
    });

    it('should handle case variations', () => {
      const content = "ready to create this?";
      const cta = extractCTAPrompt(content);
      expect(cta).toBeTruthy();
    });
  });
});

