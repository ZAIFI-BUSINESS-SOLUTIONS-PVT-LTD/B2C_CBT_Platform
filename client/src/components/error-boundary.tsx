/**
 * Error Boundary Component
 *
 * Catches JavaScript errors anywhere in the component tree and displays
 * a fallback UI instead of crashing the entire application.
 */

import { Component, ErrorInfo, ReactNode } from "react";
import { ErrorPageForBoundary } from "@/pages/error-page";
import reportError from "@/lib/errorReporting";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    // Generate a reportable error code and send to reporting backend/integration
    const report = reportError(error, errorInfo);

    // Update state with minimal error info and the report metadata
    this.setState({
      error,
      errorInfo,
    });

    // Also attach report metadata to the error object so it can be displayed in the UI
    try {
      (error as any).__report = report;
    } catch (e) {
      // ignore
    }

    // You can also log the error to an error reporting service here
    // Example: Sentry.captureException(error);
  }

  private handleRetry = () => {
    // Reset the error boundary state
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error page
      return (
        <ErrorPageForBoundary
          error={{
            code: 'JAVASCRIPT_ERROR',
            message: this.state.error?.message || 'A JavaScript error occurred',
            timestamp: new Date().toISOString(),
            details: process.env.NODE_ENV === 'development' ? {
              stack: this.state.error?.stack,
              componentStack: this.state.errorInfo?.componentStack,
            } : undefined,
          }}
          onRetry={this.handleRetry}
        />
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component for wrapping components with error boundary
 */
export function withErrorBoundary<T extends object>(
  Component: React.ComponentType<T>,
  fallback?: ReactNode
) {
  const WrappedComponent = (props: T) => (
    <ErrorBoundary fallback={fallback}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;

  return WrappedComponent;
}

/**
 * Hook for error boundary that can be used in functional components
 */
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    // Log the error
    console.error('Manual error handling:', error, errorInfo);

    // You can also report to error tracking service
    // Example: Sentry.captureException(error);

    // Throw the error to trigger error boundary
    throw error;
  };
}

