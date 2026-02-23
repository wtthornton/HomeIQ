/**
 * Message Content Component
 * 
 * Renders markdown content with proper formatting
 * Supports bold, bullets, emojis, code blocks, and links
 */

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface MessageContentProps {
  content: string;
  darkMode: boolean;
}

export const MessageContent: React.FC<MessageContentProps> = ({
  content,
  darkMode,
}) => {
  return (
    <div 
      className={`prose prose-sm max-w-none ${darkMode ? 'prose-invert' : ''}`}
      role="article"
      aria-label="Message content"
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Customize paragraph styling
          p: ({ children }) => (
            <p className={`mb-2 last:mb-0 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {children}
            </p>
          ),
          // Customize list styling
          ul: ({ children }) => (
            <ul className={`ml-4 mb-2 list-disc ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className={`ml-4 mb-2 list-decimal ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              {children}
            </ol>
          ),
          // Customize code blocks
          code: ({ className, children, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className={`px-1 py-0.5 rounded text-sm ${
                    darkMode
                      ? 'bg-gray-800 text-gray-200'
                      : 'bg-gray-100 text-gray-800'
                  }`}
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          // Customize links
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className={`underline ${
                darkMode ? 'text-blue-400 hover:text-blue-300' : 'text-blue-600 hover:text-blue-700'
              }`}
            >
              {children}
            </a>
          ),
          // Customize headings
          h1: ({ children }) => (
            <h1 className={`text-xl font-bold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className={`text-lg font-semibold mb-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className={`text-base font-semibold mb-1 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
              {children}
            </h3>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

