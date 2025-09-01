import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { StudentProfile, LoginCredentials, LoginResponse } from "@/types/api";
import { 
  loginWithJWT, 
  getCurrentStudent, 
  getAccessToken, 
  setTokens, 
  clearTokens,
  type JWTLoginResponse,
  API_BASE_URL
} from "@/lib/auth";

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

  // Check for existing authentication on mount
  useEffect(() => {
    const checkAuthStatus = async () => {
      const token = getAccessToken();
      if (token) {
        try {
          const studentData = await getCurrentStudent();
          setStudent(studentData);
          setIsAuthenticated(true);
        } catch (error) {
          console.error("Failed to verify existing authentication:", error);
          clearTokens();
        }
      }
      setLoading(false);
    };

    checkAuthStatus();
  }, []);

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
      console.log("AuthContext: Authentication state updated with JWT");
      
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
      console.log("AuthContext: Google authentication state updated");
      
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
      setStudent(null);
      setIsAuthenticated(false);
      setError(null);
      
      // Clear all React Query cache to prevent stale requests
      queryClient.clear();
      
      console.log('User logged out successfully');
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
