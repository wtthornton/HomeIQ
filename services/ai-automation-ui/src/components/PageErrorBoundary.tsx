/**
 * Error Boundary for Page Components
 * 
 * Catches errors in page components and displays a user-friendly error message.
 * Prevents the entire app from crashing when a single page encounters an error.
 */

import { Component, ErrorInfo, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

interface Props {
  children: ReactNode;
  pageName?: string;
  darkMode?: boolean;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class PageErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error for debugging
    console.error(`Page Error Boundary caught an error${this.props.pageName ? ` in ${this.props.pageName}` : ''}:`, error, errorInfo);
    
    // Update state with error info
    this.setState({ error, errorInfo });

    // TODO: Send error to error tracking service (e.g., Sentry)
    // if (window.Sentry) {
    //   window.Sentry.captureException(error, { contexts: { react: errorInfo } });
    // }
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      const { darkMode = false, pageName } = this.props;
      const { error } = this.state;

      return (
        <div className={`min-h-screen flex items-center justify-center p-4 ${
          darkMode ? 'bg-gray-900' : 'bg-gray-50'
        }`}>
          <div className={`max-w-md w-full rounded-lg p-6 border-2 ${
            darkMode 
              ? 'bg-gray-800 border-red-700 text-gray-100' 
              : 'bg-white border-red-300 text-gray-900'
          }`}>
            <div className="flex items-start gap-4">
              <div className="text-4xl">⚠️</div>
              <div className="flex-1">
                <h1 className={`text-xl font-bold mb-2 ${
                  darkMode ? 'text-red-300' : 'text-red-700'
                }`}>
                  Something went wrong
                </h1>
                {pageName && (
                  <p className={`text-sm mb-4 ${
                    darkMode ? 'text-gray-400' : 'text-gray-600'
                  }`}>
                    An error occurred while loading {pageName}.
                  </p>
                )}
                <p className={`text-sm mb-6 ${
                  darkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {error?.message || 'An unexpected error occurred. Please try refreshing the page.'}
                </p>
                
                {/* Error details in development */}
                {import.meta.env.DEV && error && (
                  <details className={`mb-4 p-3 rounded text-xs ${
                    darkMode ? 'bg-gray-900 text-gray-400' : 'bg-gray-100 text-gray-600'
                  }`}>
                    <summary className="cursor-pointer font-semibold mb-2">
                      Error Details (Development Only)
                    </summary>
                    <pre className="whitespace-pre-wrap overflow-auto max-h-40">
                      {error.stack || error.toString()}
                    </pre>
                  </details>
                )}

                <div className="flex gap-3">
                  <button
                    onClick={this.handleReload}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors ${
                      darkMode
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-blue-500 hover:bg-blue-600 text-white'
                    }`}
                  >
                    🔄 Reload Page
                  </button>
                  <button
                    onClick={this.handleGoHome}
                    className={`flex-1 px-4 py-2 rounded-lg font-medium transition-colors border ${
                      darkMode
                        ? 'border-gray-600 hover:bg-gray-700 text-gray-200'
                        : 'border-gray-300 hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    🏠 Go Home
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook-based wrapper for PageErrorBoundary that provides darkMode from store
 */
export const PageErrorBoundaryWrapper: React.FC<{ children: ReactNode; pageName?: string }> = ({ 
  children, 
  pageName 
}) => {
  // Note: We can't use hooks in error boundary, so we'll pass darkMode via props
  // For now, we'll detect it from the document or use a default
  const darkMode = typeof document !== 'undefined' 
    ? document.documentElement.classList.contains('dark')
    : false;

  return (
    <PageErrorBoundary pageName={pageName} darkMode={darkMode}>
      {children}
    </PageErrorBoundary>
  );
};

