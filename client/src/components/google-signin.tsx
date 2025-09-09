/**
 * Google Sign-In Button Component
 *
 * Provides a "Continue with Google" button and helper that triggers Google OAuth flow.
 * Uses Google Identity Services (GIS) for secure authentication.
 */

import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "@/hooks/use-toast";
import { GOOGLE_CLIENT_ID, GOOGLE_CONFIG, isGoogleConfigured, GOOGLE_ERRORS, API_BASE_URL } from "@/config/google-auth";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, config: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface GoogleSignInProps {
  onSuccess?: (response: any) => void;
  onError?: (error: string) => void;
  className?: string;
  disabled?: boolean;
}

export default function GoogleSignIn({ 
  onSuccess, 
  onError, 
  className = "", 
  disabled = false 
}: GoogleSignInProps) {
  const { loginWithGoogle, setAuthFromTokens } = useAuth();
  const [, setLocation] = useLocation();
  const [loading, setLoading] = useState(false);
  const [googleLoaded, setGoogleLoaded] = useState(false);

  useEffect(() => {
    if (!isGoogleConfigured()) {
      console.error("Google Client ID not found in environment variables");
      onError?.(GOOGLE_ERRORS.NOT_CONFIGURED);
      return;
    }

    // Load Google Identity Services script
    const loadGoogleScript = () => {
      if (window.google) {
        initializeGoogle();
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        initializeGoogle();
      };
      script.onerror = () => {
        console.error("Failed to load Google Identity Services");
        onError?.(GOOGLE_ERRORS.FAILED_TO_LOAD);
      };
      document.head.appendChild(script);
    };

    const initializeGoogle = () => {
      if (!window.google) return;
      
      try {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
          auto_select: false,
          cancel_on_tap_outside: true,
        });
        setGoogleLoaded(true);
      } catch (error) {
        console.error("Error initializing Google Identity Services:", error);
        onError?.(GOOGLE_ERRORS.FAILED_TO_INITIALIZE);
      }
    };

    loadGoogleScript();
  }, [onError]);

  const handleCredentialResponse = async (response: any) => {
    setLoading(true);
    
    try {
      if (!response.credential) {
        throw new Error(GOOGLE_ERRORS.NO_CREDENTIAL);
      }

      // Use the auth context's loginWithGoogle method
      const data = await loginWithGoogle(response.credential);

      toast({
        title: "Welcome!",
        description: `Successfully signed in as ${data.student.fullName}`,
      });

      // Call success callback if provided
      onSuccess?.(data);

      // Redirect to dashboard
      setLocation('/dashboard');

    } catch (error) {
      console.error('Google sign-in error:', error);
      const errorMessage = error instanceof Error ? error.message : GOOGLE_ERRORS.SIGN_IN_FAILED;
      
      toast({
        title: "Sign-in Failed",
        description: errorMessage,
        variant: "destructive",
      });

      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = () => {
    setLoading(true);
    
    // Create a Google OAuth popup URL
    const redirectUri = `${window.location.origin}/auth/google/callback`;
    const scope = 'email profile';
    const responseType = 'code';
    const state = Math.random().toString(36).substring(2, 15);
    
    const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
      `client_id=${GOOGLE_CLIENT_ID}&` +
      `redirect_uri=${encodeURIComponent(redirectUri)}&` +
      `scope=${encodeURIComponent(scope)}&` +
      `response_type=${responseType}&` +
      `state=${state}&` +
      `prompt=select_account`;

    // Open popup window
    const popup = window.open(
      googleAuthUrl,
      'google-signin',
      'width=500,height=600,scrollbars=yes,resizable=yes'
    );

    if (!popup) {
      setLoading(false);
      onError?.(GOOGLE_ERRORS.POPUP_BLOCKED);
      return;
    }

    // Listen for popup messages
    const checkClosed = setInterval(() => {
      if (popup.closed) {
        setLoading(false);
        clearInterval(checkClosed);
      }
    }, 1000);

    // Listen for messages from popup
    const messageHandler = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      
      if (event.data.type === 'GOOGLE_AUTH_SUCCESS') {
        clearInterval(checkClosed);
        popup.close();
        handleAuthSuccess(event.data.code, state);
      } else if (event.data.type === 'GOOGLE_AUTH_ERROR') {
        clearInterval(checkClosed);
        popup.close();
        setLoading(false);
        onError?.(event.data.error || GOOGLE_ERRORS.SIGN_IN_FAILED);
      }
    };

    window.addEventListener('message', messageHandler);
    
    // Cleanup
    setTimeout(() => {
      window.removeEventListener('message', messageHandler);
      if (!popup.closed) {
        popup.close();
        setLoading(false);
      }
    }, 300000); // 5 minutes timeout
  };

  const handleAuthSuccess = async (code: string, state: string) => {
    try {
      // Send the authorization code to your backend
      // Use centralized API_BASE_URL that handles dev/prod switching
      const backendEndpoint = `${API_BASE_URL}/auth/google/`;

      const backendResponse = await fetch(backendEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          code: code,
          state: state 
        }),
      });

      console.log('Backend response status:', backendResponse.status);
      console.log('Backend response headers:', backendResponse.headers);

      // Check if response is JSON
      const contentType = backendResponse.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        const textResponse = await backendResponse.text();
        console.error('Non-JSON response:', textResponse);
        throw new Error(`Server returned non-JSON response: ${textResponse}`);
      }

      const data = await backendResponse.json();
      console.log('Backend response data:', data);

      if (!backendResponse.ok) {
        throw new Error(data.detail || GOOGLE_ERRORS.SIGN_IN_FAILED);
      }

      // For authorization code flow, we already have tokens and student data
      // Use setAuthFromTokens instead of calling loginWithGoogle again
      setAuthFromTokens(
        { access: data.access, refresh: data.refresh },
        data.student
      );

      toast({
        title: "Welcome!",
        description: "Successfully signed in with Google",
      });

      // Call success callback if provided
      onSuccess?.(data);

      // Redirect to dashboard
      setLocation('/dashboard');

    } catch (error) {
      console.error("Google auth error:", error);
      onError?.(error instanceof Error ? error.message : GOOGLE_ERRORS.SIGN_IN_FAILED);
    } finally {
      setLoading(false);
    }
  };

  if (!isGoogleConfigured()) {
    return (
      <div className="text-red-500 text-sm">
        {GOOGLE_ERRORS.NOT_CONFIGURED}
      </div>
    );
  }

  return (
    <button
      onClick={handleGoogleSignIn}
      disabled={disabled || loading || !googleLoaded}
      className={`
        w-full flex items-center justify-center px-4 py-2 border border-gray-300 rounded-md shadow-sm 
        text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
        disabled:opacity-50 disabled:cursor-not-allowed
        transition-colors duration-200
        ${className}
      `}
    >
      {loading ? (
        <>
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
          Signing in...
        </>
      ) : (
        <>
          <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
            />
          </svg>
          Continue with Google
        </>
      )}
    </button>
  );
}
