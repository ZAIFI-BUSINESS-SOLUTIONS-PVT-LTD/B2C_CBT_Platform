/**
 * Error Page Component
 * 
 * A dedicated page for displaying critical errors that require user attention.
 * Shows error details including error code for support purposes.
 */

import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { AlertTriangle, Home, RefreshCw, Copy } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

interface ErrorInfo {
  code?: string;
  message?: string;
  timestamp?: string;
  details?: any;
}

interface ErrorPageProps {
  error?: ErrorInfo;
  onRetry?: () => void;
}

export default function ErrorPage(props?: ErrorPageProps) {
  const [, setLocation] = useLocation();
  const { toast } = useToast();
  const [error, setError] = useState<ErrorInfo | null>(props?.error || null);

  // Get error from URL params if not provided as prop
  useEffect(() => {
    if (!error) {
      const urlParams = new URLSearchParams(window.location.search);
      const errorCode = urlParams.get('code');
      const errorMessage = urlParams.get('message');
      const errorTimestamp = urlParams.get('timestamp');
      
      if (errorCode || errorMessage) {
        setError({
          code: errorCode || 'UNKNOWN_ERROR',
          message: errorMessage || 'An unexpected error occurred',
          timestamp: errorTimestamp || new Date().toISOString()
        });
      }
    }
  }, [error]);

  const handleCopyErrorCode = () => {
    if (error?.code) {
      navigator.clipboard.writeText(error.code);
      toast({
        title: "Error code copied",
        description: "Error code has been copied to clipboard",
      });
    }
  };

  const handleGoHome = () => {
    setLocation('/');
  };

  const handleRetry = () => {
    if (props?.onRetry) {
      props.onRetry();
    } else {
      // Default retry behavior - refresh the page
      window.location.reload();
    }
  };

  const displayError = error || {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
    timestamp: new Date().toISOString()
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
            <AlertTriangle className="w-8 h-8 text-red-600" />
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">
            Oops! Something went wrong
          </CardTitle>
          <CardDescription className="text-gray-600">
            We're sorry for the inconvenience. An error has occurred.
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {/* Error Message */}
          <div className="text-center">
            <p className="text-gray-800 font-medium mb-2">
              {displayError.message}
            </p>
            
            {/* Error Code */}
            {displayError.code && (
              <div className="flex items-center justify-center gap-2">
                <span className="text-sm text-gray-500">Error Code:</span>
                <code className="text-sm bg-gray-100 px-2 py-1 rounded font-mono text-gray-700">
                  {displayError.code}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyErrorCode}
                  className="h-6 w-6 p-0"
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            )}
            
            {/* Timestamp */}
            {displayError.timestamp && (
              <p className="text-xs text-gray-400 mt-2">
                {new Date(displayError.timestamp).toLocaleString()}
              </p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={handleRetry}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Try Again
            </Button>
            
            <Button
              onClick={handleGoHome}
              variant="outline"
              className="flex-1"
            >
              <Home className="w-4 h-4 mr-2" />
              Go Home
            </Button>
          </div>

          {/* Support Information */}
          <div className="text-center text-sm text-gray-500">
            <p>Need help? Contact support and provide the error code above.</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Export a component specifically for the error boundary
export function ErrorPageForBoundary({ error, onRetry }: ErrorPageProps) {
  return <ErrorPage error={error} onRetry={onRetry} />;
}
