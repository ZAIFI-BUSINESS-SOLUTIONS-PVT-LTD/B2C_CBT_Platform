import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { StudentProfile, LoginCredentials, LoginResponse } from "@/types/api";
import { 
  loginWithJWT, 
  getCurrentStudent, 
  getAccessToken, 
  getRefreshToken,
  refreshAccessToken,
  setTokens, 
  clearTokens,
  type JWTLoginResponse
} from "@/lib/auth";
import { API_BASE_URL } from "@/config/google-auth";
import { useLocation } from "wouter";

interface AuthContextType {
  student: StudentProfile | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  loginWithGoogle: (idToken: string) => Promise<any>;
  setAuthFromTokens: (tokens: { access: string; refresh: string }, student: StudentProfile) => void;
  logout: () => void;
  setStudent: (student: StudentProfile | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true); // Start with loading true to check for existing tokens
  const [error, setError] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const [, navigate] = useLocation();

  // Check for existing authentication on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      let token = getAccessToken();
      const refresh = getRefreshToken();
      
      // FIX #2: Proactive refresh if access missing but refresh exists
      if (!token && refresh) {
        console.log("🔄 No access token but refresh token exists, attempting proactive refresh...");
        try {
          token = await refreshAccessToken();
          if (token) {
            console.log("✅ Proactive refresh successful, session restored");
          }
        } catch (error) {
          console.warn("⚠️ Proactive refresh failed:", error);
        }
      }
      
      if (token) {
        // OFFLINE-AWARE: If user is offline, trust the token and load cached profile
        if (!navigator.onLine) {
          console.log("📴 User is offline, loading cached profile without API validation");
          
          // Try to load cached profile from localStorage
          const cachedProfile = localStorage.getItem('cachedStudentProfile');
          if (cachedProfile) {
            try {
              const studentData = JSON.parse(cachedProfile);
              setStudent(studentData);
              setIsAuthenticated(true);
              console.log("✅ Cached profile loaded successfully (offline mode)");
            } catch (error) {
              console.error("Failed to parse cached profile:", error);
            }
          } else {
            // No cached profile but token exists - still trust it offline
            setIsAuthenticated(true);
            console.log("⚠️ No cached profile, but trusting token (offline mode)");
          }
          setLoading(false);
          return;
        }
        
        // ONLINE: Validate token with API
        try {
          const studentData = await getCurrentStudent();
          setStudent(studentData);
          setIsAuthenticated(true);
          
          // Cache the profile for offline use
          localStorage.setItem('cachedStudentProfile', JSON.stringify(studentData));
          
          // Do NOT navigate here - let the page components handle navigation
          // based on their own logic (e.g., LoginPage redirects auth users, Home requires auth)
          console.log("AuthContext: Authentication state loaded from token");
        } catch (error: any) {
          console.error("Failed to verify existing authentication:", error);
          
          // OFFLINE-AWARE: Only clear tokens on 401, not on network errors
          if (error?.status === 401 || error?.message?.includes('401')) {
            console.log("❌ 401 Unauthorized - clearing tokens");
            clearTokens();
            localStorage.removeItem('cachedStudentProfile');
          } else if (!navigator.onLine) {
            // Network error while offline - keep session
            console.log("📴 Network error but offline - keeping session");
            const cachedProfile = localStorage.getItem('cachedStudentProfile');
            if (cachedProfile) {
              try {
                const studentData = JSON.parse(cachedProfile);
                setStudent(studentData);
                setIsAuthenticated(true);
                console.log("✅ Using cached profile due to offline network error");
              } catch (parseError) {
                console.error("Failed to parse cached profile:", parseError);
              }
            } else {
              setIsAuthenticated(true);
              console.log("⚠️ Network error offline, trusting token without profile");
            }
          } else {
            // Online but non-401 error (500, network issue) - keep session, retry later
            console.log("⚠️ API error but not 401 - keeping session for retry");
            const cachedProfile = localStorage.getItem('cachedStudentProfile');
            if (cachedProfile) {
              try {
                const studentData = JSON.parse(cachedProfile);
                setStudent(studentData);
                setIsAuthenticated(true);
                console.log("✅ Using cached profile due to API error");
              } catch (parseError) {
                console.error("Failed to parse cached profile:", parseError);
              }
            }
          }
        }
      }
      setLoading(false);
    };

    checkAuthStatus();
  }, [navigate]);

  const login = async (credentials: LoginCredentials): Promise<LoginResponse> => {
    setLoading(true);
    setError(null);
    console.log("AuthContext: Starting JWT login process");
    
    try {
      const response: JWTLoginResponse = await loginWithJWT(credentials.email, credentials.password);
      console.log("AuthContext: JWT login successful, setting tokens and state");
      
      // Store tokens
      setTokens({
        access: response.access,
        refresh: response.refresh
      });
      
      // Set student data and authentication state
      setStudent(response.student);
      setIsAuthenticated(true);
      setLoading(false);
      
      // Cache the profile for offline use
      localStorage.setItem('cachedStudentProfile', JSON.stringify(response.student));
      
      console.log("AuthContext: Authentication state updated with JWT");
      
      // Check if phone number is missing and redirect to get-number page
      if (!response.student.phoneNumber) {
        console.log("AuthContext: Phone number missing, redirecting to get-number");
        navigate("/get-number");
      } else {
        console.log("AuthContext: Phone number present, redirecting to dashboard");
        navigate("/dashboard");
      }
      
      // Return response in expected LoginResponse format
      return {
        access: response.access,
        refresh: response.refresh,
        student: response.student
      };
    } catch (err: any) {
      console.error("AuthContext: JWT login failed", err);
      setError(err.message || "Login failed");
      setIsAuthenticated(false);
      setStudent(null);
      setLoading(false);
      throw err;
    }
  };

  const loginWithGoogle = async (idToken: string) => {
    try {
      // Send the ID token to your backend using API_BASE_URL
      const response = await fetch(`${API_BASE_URL}/auth/google/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          idToken: idToken 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Google sign-in failed');
      }

      // Store tokens
      setTokens({
        access: data.access,
        refresh: data.refresh
      });
      
      // Set student data and authentication state
      setStudent(data.student);
      setIsAuthenticated(true);
      setError(null);
      
      // Cache the profile for offline use
      localStorage.setItem('cachedStudentProfile', JSON.stringify(data.student));
      
      console.log("AuthContext: Google authentication state updated");
      
      // Check if phone number is missing and redirect to get-number page
      if (!data.student.phoneNumber) {
        console.log("AuthContext: Phone number missing, redirecting to get-number");
        navigate("/get-number");
      } else {
        console.log("AuthContext: Phone number present, redirecting to dashboard");
        navigate("/dashboard");
      }
      
      return data;
    } catch (error) {
      setError('Google sign-in failed');
      console.error('Google sign-in error:', error);
      throw error;
    }
  };

  const setAuthFromTokens = (tokens: { access: string; refresh: string }, studentData: StudentProfile) => {
    // Store tokens
    setTokens(tokens);
    
    // Set student data and authentication state
    setStudent(studentData);
    setIsAuthenticated(true);
    setError(null);
    
    // Cache the profile for offline use
    localStorage.setItem('cachedStudentProfile', JSON.stringify(studentData));
    
    console.log("AuthContext: Authentication state updated with provided tokens");
  };

  const logout = async () => {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      
      // If we have a refresh token, try to blacklist it on the server
      if (refreshToken) {
        try {
          // Use dynamic API base URL instead of hardcoded production URL
          await fetch(`${API_BASE_URL}/auth/logout/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh: refreshToken }),
          });
        } catch (error) {
          console.warn('Failed to blacklist token on server:', error);
          // Continue with local logout even if server logout fails
        }
      }
    } catch (error) {
      console.warn('Logout error:', error);
    } finally {
      // Always clear local state regardless of server response
      clearTokens();
      localStorage.removeItem('cachedStudentProfile');
      setStudent(null);
      setIsAuthenticated(false);
      setError(null);
      
      // Clear all React Query cache to prevent stale requests
      queryClient.clear();
      
      console.log('User logged out successfully');
      
      // Force navigation to login page with full reload to avoid any routing conflicts
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        student,
        isAuthenticated,
        loading,
        error,
        login,
        loginWithGoogle,
        setAuthFromTokens,
        logout,
        setStudent,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
