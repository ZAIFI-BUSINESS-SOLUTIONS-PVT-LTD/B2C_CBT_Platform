/**
 * Google OAuth Callback Component
 * 
 * This component handles the Google OAuth redirect and processes the authentication.
 * It extracts the ID token from Google and sends it to the backend for verification.
 */

import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "@/hooks/use-toast";
import { API_BASE_URL } from "@/config/google-auth";

export default function GoogleAuthCallback() {
  const [, setLocation] = useLocation();
  const { setStudent } = useAuth();
  const [processing, setProcessing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleGoogleCallback = async () => {
      try {
        // Check if we have Google's credential response
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        const error = urlParams.get('error');

        if (error) {
          throw new Error(`Google authentication error: ${error}`);
        }

        // For Google Identity Services (GIS), the ID token is usually passed via postMessage
        // We'll listen for messages from Google
        const handleMessage = async (event: MessageEvent) => {
          if (event.origin !== window.location.origin) {
            return;
          }

          if (event.data?.type === 'GOOGLE_AUTH_SUCCESS' && event.data?.idToken) {
            try {
              await processGoogleToken(event.data.idToken);
            } catch (error) {
              console.error('Error processing Google token:', error);
              setError(error instanceof Error ? error.message : 'Authentication failed');
              setProcessing(false);
            }
          }
        };

        window.addEventListener('message', handleMessage);

        // Cleanup function
        return () => {
          window.removeEventListener('message', handleMessage);
        };

      } catch (error) {
        console.error('Google callback error:', error);
        setError(error instanceof Error ? error.message : 'Authentication failed');
        setProcessing(false);
      }
    };

    const processGoogleToken = async (idToken: string) => {
      try {
        // Use centralized API_BASE_URL that handles dev/prod switching
        const response = await fetch(`${API_BASE_URL}/auth/google/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ idToken }),
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || 'Authentication failed');
        }

        // Store tokens and user data  
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        localStorage.setItem('user', JSON.stringify(data.student));

        // Set authentication state directly
        setStudent(data.student);

        toast({
          title: "Welcome!",
          description: "Successfully signed in with Google.",
        });

        // Redirect to dashboard
        setLocation('/dashboard');

      } catch (error) {
        console.error('Token processing error:', error);
        throw error;
      }
    };

    handleGoogleCallback();
  }, [setStudent, setLocation]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Authentication Error
            </h2>
            <p className="mt-2 text-sm text-gray-600">{error}</p>
            <button
              onClick={() => setLocation('/')}
              className="mt-4 w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Return to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Completing Sign In
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Please wait while we verify your Google account...
          </p>
        </div>
      </div>
    </div>
  );
}
