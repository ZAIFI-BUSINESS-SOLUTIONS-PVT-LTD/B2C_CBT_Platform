// JWT Authentication utilities
import { StudentProfile } from "@/types/api";

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface JWTLoginResponse {
  access: string;
  refresh: string;
  student: StudentProfile;
}

// Token storage utilities
export const getAccessToken = (): string | null => {
  return localStorage.getItem('accessToken');
};

export const getRefreshToken = (): string | null => {
  return localStorage.getItem('refreshToken');
};

export const setTokens = (tokens: TokenPair): void => {
  localStorage.setItem('accessToken', tokens.access);
  localStorage.setItem('refreshToken', tokens.refresh);
};

export const clearTokens = (): void => {
  localStorage.removeItem('accessToken');
  localStorage.removeItem('refreshToken');
};

// Refresh token utility
export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    return null;
  }

  try {
    const response = await fetch('http://127.0.0.1:8000/api/auth/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('accessToken', data.access);
      return data.access;
    } else {
      clearTokens();
      return null;
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
    clearTokens();
    return null;
  }
};

// Authenticated fetch wrapper
export const authenticatedFetch = async (
  url: string,
  options: RequestInit = {}
): Promise<Response> => {
  let accessToken = getAccessToken();

  // If no token, throw error
  if (!accessToken) {
    console.error('❌ No access token available for request:', url);
    throw new Error('No access token available');
  }

  console.log('🔄 Making authenticated request to:', url);
  console.log('🔑 Using token (first 30 chars):', accessToken.substring(0, 30) + '...');

  // Add authorization header
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };

  // Make the request
  let response = await fetch(url, {
    ...options,
    headers,
  });

  console.log('📡 Response status:', response.status, response.statusText);

  // If unauthorized, try to refresh token
  if (response.status === 401) {
    console.warn('🔄 401 received, attempting token refresh...');
    const newToken = await refreshAccessToken();
    if (newToken) {
      console.log('✅ Token refreshed successfully, retrying request...');
      // Retry with new token
      const newHeaders = {
        ...options.headers,
        'Authorization': `Bearer ${newToken}`,
        'Content-Type': 'application/json',
      };

      response = await fetch(url, {
        ...options,
        headers: newHeaders,
      });
      
      console.log('📡 Retry response status:', response.status, response.statusText);
    } else {
      console.error('❌ Token refresh failed, authentication failed');
      throw new Error('Authentication failed');
    }
  }

  return response;
};

// Login function - using email and password as per updated LoginCredentials type
export const loginWithJWT = async (email: string, password: string): Promise<JWTLoginResponse> => {
  const response = await fetch('http://127.0.0.1:8000/api/auth/login/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Login failed');
  }

  return response.json();
};

// Get current student profile
export const getCurrentStudent = async (): Promise<StudentProfile> => {
  const response = await authenticatedFetch('http://127.0.0.1:8000/api/students/me/');
  
  if (!response.ok) {
    throw new Error('Failed to get student profile');
  }

  return response.json();
};
