/**
 * Proposal Parser Utility
 * 
 * Parses AI-generated automation proposals from markdown format
 * into structured sections for visual rendering.
 * 
 * Format:
 * Here's what I'll create for you:
 * 
 * **✨ What it does:** [description]
 * **📋 When it runs:** [trigger description]
 * **🎯 What's affected:** [entities/devices]
 * **⚙️ How it works:** [step-by-step]
 */

export interface ProposalSection {
  type: 'what' | 'when' | 'affected' | 'how';
  icon: string;
  title: string;
  content: string;
}

export interface ParsedProposal {
  hasProposal: boolean;
  sections: ProposalSection[];
  rawContent: string;
}

/**
 * Detects if a message contains an automation proposal
 */
export function isProposalMessage(content: string): boolean {
  const proposalStartPattern = /here's what i'll create for you:/i;
  return proposalStartPattern.test(content);
}

/**
 * Parses a proposal message into structured sections
 */
export function parseProposal(content: string): ParsedProposal {
  if (!isProposalMessage(content)) {
    return {
      hasProposal: false,
      sections: [],
      rawContent: content,
    };
  }

  const sections: ProposalSection[] = [];

  // Pattern to match section headers: **✨ What it does:** or **📋 When it runs:**
  // Format: **✨ What it does:** [content]
  // Use a pattern that matches any emoji followed by text
  // The emoji characters need to be in a character class or matched individually
  const sectionHeaderPattern = /\*\*([^\*]+?):\*\*/g;
  
  // Find all potential section headers
  const allMatches: Array<{ fullMatch: string; icon: string; title: string; index: number }> = [];
  let match;
  while ((match = sectionHeaderPattern.exec(content)) !== null) {
    const headerText = match[1].trim();
    // Match any emoji (Unicode emoji range) or specific known emojis followed by text
    // Use a more flexible pattern that matches emoji characters
    // Also check for known section emojis: ✨ 📋 🎯 ⚙️
    const emojiMatch = headerText.match(/^(\p{Emoji}|\u{2728}|\u{1F4CB}|\u{1F3AF}|\u{2699})\s+(.+)$/u) ||
                      headerText.match(/^([✨📋🎯⚙️])\s+(.+)$/);
    if (emojiMatch) {
      allMatches.push({
        fullMatch: match[0],
        icon: emojiMatch[1],
        title: emojiMatch[2],
        index: match.index,
      });
    } else {
      // Fallback: if it looks like a section header (starts with common section words), accept it
      const titleLower = headerText.toLowerCase();
      if (titleLower.includes('what it does') || titleLower.includes('when it runs') || 
          titleLower.includes("what's affected") || titleLower.includes('how it works')) {
        // Extract emoji if present, otherwise use default
        const emojiExtract = headerText.match(/^([^\s]+)\s+(.+)$/);
        if (emojiExtract) {
          allMatches.push({
            fullMatch: match[0],
            icon: emojiExtract[1],
            title: emojiExtract[2],
            index: match.index,
          });
        }
      }
    }
  }
  
  // Convert to section headers format
  const sectionHeaders: Array<{ icon: string; title: string; index: number; headerLength: number }> = 
    allMatches.map(m => ({
      icon: m.icon,
      title: m.title,
      index: m.index,
      headerLength: m.fullMatch.length,
    }));

  // Parse each section
  for (let i = 0; i < sectionHeaders.length; i++) {
    const header = sectionHeaders[i];
    const startIndex = header.index + header.headerLength; // Start after the header
    const endIndex = i < sectionHeaders.length - 1 
      ? sectionHeaders[i + 1].index 
      : content.length;
    
    let sectionContent = content.substring(startIndex, endIndex).trim();
    
    // Clean up content - remove extra newlines and trim
    sectionContent = sectionContent.replace(/\n{3,}/g, '\n\n').trim();

    // Map title to section type
    let type: ProposalSection['type'];
    const titleLower = header.title.toLowerCase();
    if (titleLower.includes('what it does')) {
      type = 'what';
    } else if (titleLower.includes('when it runs')) {
      type = 'when';
    } else if (titleLower.includes("what's affected") || titleLower.includes('what is affected')) {
      type = 'affected';
    } else if (titleLower.includes('how it works')) {
      type = 'how';
    } else {
      // Skip unknown sections
      continue;
    }

    sections.push({
      type,
      icon: header.icon,
      title: header.title,
      content: sectionContent,
    });
  }

  // Fallback: Try alternative patterns if no sections found
  if (sections.length === 0) {
    // Try simpler pattern without emoji requirement
    const altPattern = /\*\*([^\*]+?):\*\*\s*([\s\S]*?)(?=\*\*[^\*]+?:\*\*|ready to create|$)/gi;
    let altMatch;
    const altMatches: Array<{ title: string; content: string; index: number }> = [];
    
    while ((altMatch = altPattern.exec(content)) !== null) {
      altMatches.push({
        title: altMatch[1].trim(),
        content: altMatch[2].trim(),
        index: altMatch.index,
      });
    }

    for (const altMatch of altMatches) {
      const titleLower = altMatch.title.toLowerCase();
      let type: ProposalSection['type'] | null = null;
      let icon = '✨';
      
      if (titleLower.includes('what it does')) {
        type = 'what';
        icon = '✨';
      } else if (titleLower.includes('when it runs')) {
        type = 'when';
        icon = '📋';
      } else if (titleLower.includes("what's affected") || titleLower.includes('what is affected')) {
        type = 'affected';
        icon = '🎯';
      } else if (titleLower.includes('how it works')) {
        type = 'how';
        icon = '⚙️';
      }

      if (type) {
        let sectionContent = altMatch.content.replace(/\n{3,}/g, '\n\n').trim();
        sections.push({
          type,
          icon,
          title: altMatch.title,
          content: sectionContent,
        });
      }
    }
  }

  return {
    hasProposal: sections.length > 0,
    sections,
    rawContent: content,
  };
}

/**
 * Extracts the CTA prompt from a proposal message
 */
export function extractCTAPrompt(content: string): string | null {
  const ctaPattern = /ready to create this\?[^\n]*/i;
  const match = content.match(ctaPattern);
  return match ? match[0] : null;
}

/**
 * Cleans markdown formatting from content while preserving structure
 */
export function cleanMarkdown(content: string): string {
  // Remove bold markers but keep content
  return content.replace(/\*\*([^\*]+?)\*\*/g, '$1');
}

