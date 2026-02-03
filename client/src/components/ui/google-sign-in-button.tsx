/**
 * Google Sign-In Button Component
 * 
 * This component provides a "Continue with Goo      // Send ID token to backend using centralized API_BASE_URL
      const backendResponse = await fetch(`${API_BASE_URL}/auth/google/`, {utton that initiates
 * the Google OAuth flow using Google Identity Services (GIS).
 */

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { toast } from "@/hooks/use-toast";
import { useAuth } from "@/contexts/AuthContext";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          prompt: () => void;
          renderButton: (element: HTMLElement, config: any) => void;
        };
      };
    };
  }
}

interface GoogleSignInButtonProps {
  className?: string;
  variant?: "default" | "outline" | "secondary" | "ghost";
  size?: "default" | "sm" | "lg";
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export function GoogleSignInButton({ 
  className, 
  variant = "outline", 
  size = "default",
  onSuccess,
  onError 
}: GoogleSignInButtonProps) {
  const [, setLocation] = useLocation();
  const { loginWithGoogle } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [googleLoaded, setGoogleLoaded] = useState(false);

  useEffect(() => {
    // Load Google Identity Services script
    const loadGoogleScript = () => {
      if (window.google) {
        setGoogleLoaded(true);
        return;
      }

      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setGoogleLoaded(true);
        initializeGoogleSignIn();
      };
      script.onerror = () => {
        console.error('Failed to load Google Identity Services');
        onError?.('Failed to load Google services');
      };
      
      document.head.appendChild(script);
    };

    const initializeGoogleSignIn = () => {
      if (!window.google) return;

      window.google.accounts.id.initialize({
        client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
        callback: handleCredentialResponse,
        auto_select: false,
        cancel_on_tap_outside: true,
      });
    };

    loadGoogleScript();
  }, []);

  const handleCredentialResponse = async (response: { credential: string }) => {
    setIsLoading(true);
    
    try {
      const idToken = response.credential;
      
      // Use centralized loginWithGoogle from AuthContext
      // This handles token storage with correct keys (accessToken/refreshToken)
      // and automatically redirects to /get-number if phone is missing
      const data = await loginWithGoogle(idToken);

      toast({
        title: "Welcome!",
        description: `Successfully signed in as ${data.student.fullName || data.student.email}`,
      });

      onSuccess?.();
      
      // AuthContext handles redirect based on phone number presence
      // No need for manual redirect here

    } catch (error) {
      console.error('Google sign-in error:', error);
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
      
      toast({
        title: "Sign-in Failed",
        description: errorMessage,
        variant: "destructive",
      });

      onError?.(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignIn = () => {
    if (!googleLoaded || !window.google) {
      toast({
        title: "Google Services Loading",
        description: "Please wait for Google services to load and try again.",
        variant: "destructive",
      });
      return;
    }

    try {
      window.google.accounts.id.prompt();
    } catch (error) {
      console.error('Error triggering Google sign-in:', error);
      toast({
        title: "Sign-in Error",
        description: "Failed to start Google sign-in process.",
        variant: "destructive",
      });
    }
  };

  return (
    <Button
      variant={variant}
      size={size}
      className={className}
      onClick={handleGoogleSignIn}
      disabled={isLoading || !googleLoaded}
    >
      {isLoading ? (
        <div className="flex items-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2"></div>
          Signing in...
        </div>
      ) : (
        <div className="flex items-center">
          <svg
            className="w-5 h-5 mr-2"
            viewBox="0 0 24 24"
            fill="currentColor"
          >
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </div>
      )}
    </Button>
  );
}
