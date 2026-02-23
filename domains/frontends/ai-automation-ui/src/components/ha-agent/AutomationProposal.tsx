/**
 * Automation Proposal Component
 * 
 * Displays structured automation proposals with visual sections
 * (What it does, When it runs, What's affected, How it works)
 */

import React from 'react';
import { motion } from 'framer-motion';
import { ProposalSection } from '../../utils/proposalParser';

interface AutomationProposalProps {
  sections: ProposalSection[];
  darkMode: boolean;
}

export const AutomationProposal: React.FC<AutomationProposalProps> = ({
  sections,
  darkMode,
}) => {
  const getSectionColor = (type: ProposalSection['type']) => {
    if (darkMode) {
      switch (type) {
        case 'what':
          return 'bg-blue-900/30 border-blue-700';
        case 'when':
          return 'bg-purple-900/30 border-purple-700';
        case 'affected':
          return 'bg-pink-900/30 border-pink-700';
        case 'how':
          return 'bg-green-900/30 border-green-700';
        default:
          return 'bg-gray-800 border-gray-700';
      }
    } else {
      switch (type) {
        case 'what':
          return 'bg-blue-50 border-blue-200';
        case 'when':
          return 'bg-purple-50 border-purple-200';
        case 'affected':
          return 'bg-pink-50 border-pink-200';
        case 'how':
          return 'bg-green-50 border-green-200';
        default:
          return 'bg-gray-50 border-gray-200';
      }
    }
  };

  const getSectionTitle = (type: ProposalSection['type']) => {
    switch (type) {
      case 'what':
        return 'What it does';
      case 'when':
        return 'When it runs';
      case 'affected':
        return "What's affected";
      case 'how':
        return 'How it works';
      default:
        return 'Section';
    }
  };

  return (
    <div className="space-y-3 mt-2" role="region" aria-label="Automation proposal details">
      {sections.map((section, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1 }}
          className={`p-4 rounded-lg border-2 ${getSectionColor(section.type)}`}
          role="article"
          aria-labelledby={`proposal-section-${index}-title`}
        >
          <div className="flex items-start gap-3">
            <span className="text-2xl flex-shrink-0" aria-hidden="true">{section.icon}</span>
            <div className="flex-1 min-w-0">
              <h3
                id={`proposal-section-${index}-title`}
                className={`font-semibold text-sm mb-2 ${
                  darkMode ? 'text-white' : 'text-gray-900'
                }`}
              >
                {getSectionTitle(section.type)}
              </h3>
              <div
                className={`text-sm whitespace-pre-wrap break-words ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}
                role="text"
                aria-label={`${getSectionTitle(section.type)}: ${section.content.substring(0, 100)}${section.content.length > 100 ? '...' : ''}`}
              >
                {section.content}
              </div>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  );
};

