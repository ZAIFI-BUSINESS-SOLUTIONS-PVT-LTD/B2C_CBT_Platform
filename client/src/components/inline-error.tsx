/**
 * Inline Error Display Component
 * 
 * A reusable component for displaying validation and form errors inline
 * instead of redirecting to the error page.
 */

import { AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { APIError } from "@/lib/queryClient";

interface InlineErrorProps {
  error: Error | APIError | string;
  onDismiss?: () => void;
  className?: string;
  showCode?: boolean;
}

export function InlineError({ 
  error, 
  onDismiss, 
  className = "", 
  showCode = false 
}: InlineErrorProps) {
  // Extract error information
  let message: string;
  let code: string | undefined;
  
  if (typeof error === 'string') {
    message = error;
  } else if (error instanceof APIError) {
    message = error.message;
    code = error.code;
  } else {
    message = error.message || 'An error occurred';
  }

  return (
    <Alert variant="destructive" className={className}>
      <AlertCircle className="h-4 w-4" />
      <AlertDescription className="flex items-center justify-between">
        <div className="flex-1">
          <p>{message}</p>
          {showCode && code && (
            <p className="text-xs mt-1 opacity-75">
              Error Code: <code>{code}</code>
            </p>
          )}
        </div>
        {onDismiss && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            className="h-auto p-1 ml-2"
          >
            <X className="h-3 w-3" />
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}

/**
 * Field Error Component
 * 
 * Displays validation errors for specific form fields
 */
interface FieldErrorProps {
  error?: string | string[];
  className?: string;
}

export function FieldError({ error, className = "" }: FieldErrorProps) {
  if (!error) return null;
  
  const errors = Array.isArray(error) ? error : [error];
  
  return (
    <div className={`text-sm text-red-600 mt-1 ${className}`}>
      {errors.map((err, index) => (
        <p key={index}>{err}</p>
      ))}
    </div>
  );
}

/**
 * Error Helper Functions
 */

// Check if an error should be displayed inline vs redirecting to error page
export function shouldDisplayInline(error: Error | APIError): boolean {
  if (error instanceof APIError) {
    // Display inline for validation and client errors
    return error.status < 500 && !error.isAuthError();
  }
  
  // Display inline for basic JavaScript errors
  return true;
}

// Extract field-specific errors from API error
export function extractFieldErrors(error: APIError): Record<string, string[]> {
  const fieldErrors: Record<string, string[]> = {};
  
  if (error.details && typeof error.details === 'object') {
    Object.keys(error.details).forEach(field => {
      const fieldError = error.details[field];
      if (Array.isArray(fieldError)) {
        fieldErrors[field] = fieldError;
      } else if (typeof fieldError === 'string') {
        fieldErrors[field] = [fieldError];
      }
    });
  }
  
  return fieldErrors;
}

// Get user-friendly error message
export function getFriendlyErrorMessage(error: Error | APIError): string {
  if (error instanceof APIError) {
    // Map specific error codes to user-friendly messages
    switch (error.code) {
      case 'AUTH_REQUIRED':
        return 'Please log in to continue';
      case 'AUTH_TOKEN_EXPIRED':
        return 'Your session has expired. Please log in again';
      case 'AUTH_INVALID_CREDENTIALS':
        return 'Invalid username or password';
      case 'INVALID_INPUT':
        return 'Please check your input and try again';
      case 'NOT_FOUND':
        return 'The requested resource was not found';
      case 'RATE_LIMITED':
        return 'Too many requests. Please wait and try again';
      case 'SERVER_ERROR':
        return 'Something went wrong on our end. Please try again later';
      default:
        return error.message;
    }
  }
  
  return error.message || 'An unexpected error occurred';
}
