/**
 * Error Boundary for Markdown Rendering
 * 
 * Catches errors when rendering malformed markdown content
 */

import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  content: string;
  darkMode: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class MarkdownErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Markdown rendering error:', error, errorInfo);
  }

  componentDidUpdate(prevProps: Props) {
    // Reset error state if content changes
    if (prevProps.content !== this.props.content && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError) {
      // Fallback to plain text rendering
      return (
        <div 
          className={`text-sm whitespace-pre-wrap break-words ${
            this.props.darkMode ? 'text-gray-300' : 'text-gray-700'
          }`}
          role="text"
          aria-label="Message content (fallback rendering)"
        >
          {this.props.content}
        </div>
      );
    }

    return this.props.children;
  }
}

