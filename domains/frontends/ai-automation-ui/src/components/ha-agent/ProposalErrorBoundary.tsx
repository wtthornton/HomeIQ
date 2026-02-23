/**
 * Error Boundary for Automation Proposal Component
 * 
 * Catches errors when parsing or rendering malformed proposals
 */

import { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ProposalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Proposal rendering error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="p-4 rounded-lg border-2 border-red-500 bg-red-50 dark:bg-red-900/30 dark:border-red-700" role="alert">
          <p className="text-sm text-red-800 dark:text-red-200 font-semibold mb-1">
            ⚠️ Unable to display automation proposal
          </p>
          <p className="text-xs text-red-600 dark:text-red-300">
            The proposal format could not be parsed. Please try refreshing or contact support if the issue persists.
          </p>
        </div>
      );
    }

    return this.props.children;
  }
}

