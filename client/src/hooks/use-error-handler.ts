/**
 * Error handling utilities for the frontend
 * 
 * Provides helper functions for handling API errors consistently across the application
 */

import React from "react";
import { useLocation } from "wouter";
import { useToast } from "@/hooks/use-toast";
import { APIError } from "@/lib/queryClient";

/**
 * Hook for handling API errors consistently
 */
export function useErrorHandler() {
  const [, setLocation] = useLocation();
  const { toast } = useToast();

  const handleError = (error: Error | APIError, options?: {
    showToast?: boolean;
    redirectToErrorPage?: boolean;
    customMessage?: string;
  }) => {
    const opts = {
      showToast: true,
      redirectToErrorPage: false,
      ...options
    };

    let message = opts.customMessage;
    let code: string | undefined;

    if (error instanceof APIError) {
      message = message || error.message;
      code = error.code;

      // Determine if we should redirect to error page
      if (error.status >= 500 || error.isAuthError()) {
        opts.redirectToErrorPage = true;
      }
    } else {
      message = message || error.message || 'An unexpected error occurred';
    }

    // Show toast notification for non-critical errors
    if (opts.showToast && !opts.redirectToErrorPage) {
      toast({
        variant: "destructive",
        title: "Error",
        description: code ? `${message} (${code})` : message,
      });
    }

    // Redirect to error page for critical errors
    if (opts.redirectToErrorPage) {
      const params = new URLSearchParams();
      if (code) params.set('code', code);
      if (message) params.set('message', message);
      if (error instanceof APIError && error.timestamp) {
        params.set('timestamp', error.timestamp);
      }
      
      setLocation(`/error?${params.toString()}`);
    }

    // Log error for debugging
    console.error('Error handled:', error);
  };

  return { handleError };
}

/**
 * Helper function to determine error handling strategy
 */
export function getErrorHandlingStrategy(error: Error | APIError): {
  showInline: boolean;
  showToast: boolean;
  redirectToErrorPage: boolean;
} {
  if (error instanceof APIError) {
    // Critical server errors -> redirect to error page
    if (error.status >= 500) {
      return {
        showInline: false,
        showToast: false,
        redirectToErrorPage: true
      };
    }

    // Auth errors -> redirect to error page
    if (error.isAuthError()) {
      return {
        showInline: false,
        showToast: false,
        redirectToErrorPage: true
      };
    }

    // Validation errors -> show inline
    if (error.isValidationError()) {
      return {
        showInline: true,
        showToast: false,
        redirectToErrorPage: false
      };
    }

    // Other client errors -> show toast
    return {
      showInline: false,
      showToast: true,
      redirectToErrorPage: false
    };
  }

  // JavaScript errors -> show toast (unless in error boundary)
  return {
    showInline: false,
    showToast: true,
    redirectToErrorPage: false
  };
}

/**
 * React Query error handler
 */
export function handleQueryError(error: Error | APIError) {
  const strategy = getErrorHandlingStrategy(error);
  
  if (strategy.redirectToErrorPage) {
    // Will be handled by error boundary or manual redirect
    return;
  }
  
  if (strategy.showToast) {
    // Show toast notification
    // Note: This should be called within a component with access to toast
    console.error('Query error:', error);
  }
}

/**
 * Mutation error handler
 */
export function handleMutationError(error: Error | APIError, onError?: (error: any) => void) {
  const strategy = getErrorHandlingStrategy(error);
  
  if (strategy.redirectToErrorPage) {
    // Critical error - will be handled by error boundary
    return;
  }
  
  // Call custom error handler if provided
  if (onError) {
    onError(error);
  }
}

/**
 * Form error extractor
 */
export function extractFormErrors(error: APIError): Record<string, string> {
  const formErrors: Record<string, string> = {};
  
  if (error.details && typeof error.details === 'object') {
    Object.keys(error.details).forEach(field => {
      const fieldError = error.details[field];
      if (Array.isArray(fieldError)) {
        formErrors[field] = fieldError[0]; // Take first error message
      } else if (typeof fieldError === 'string') {
        formErrors[field] = fieldError;
      }
    });
  }
  
  return formErrors;
}

/**
 * Higher-order component for error handling
 */
export function withErrorHandling<T extends object>(
  Component: React.ComponentType<T>,
  errorHandler?: (error: Error | APIError) => void
) {
  const WrappedComponent = (props: T) => {
    const { handleError } = useErrorHandler();
    
    const defaultErrorHandler = errorHandler || handleError;
    
    return <Component {...props} />;
  };

  WrappedComponent.displayName = `withErrorHandling(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
}
