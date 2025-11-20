import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { API_CONFIG } from "@/config/api"; // <--- Crucial: Import your API_CONFIG
import { getAccessToken, authenticatedFetch } from "@/lib/auth"; // Import JWT utilities

// Enhanced error class to handle standardized backend error format
export class APIError extends Error {
  public code: string;
  public status: number;
  public timestamp?: string;
  public details?: any;

  constructor(
    code: string,
    message: string,
    status: number,
    timestamp?: string,
    details?: any
  ) {
    super(message);
    this.name = 'APIError';
    this.code = code;
    this.status = status;
    this.timestamp = timestamp;
    this.details = details;
  }

  // Helper method to check if error is of a specific type
  public isType(code: string): boolean {
    return this.code === code;
  }

  // Helper method to check if error is authentication related
  public isAuthError(): boolean {
    return this.code.startsWith('AUTH_');
  }

  // Helper method to check if error is validation related
  public isValidationError(): boolean {
    return this.code === 'INVALID_INPUT' || this.code === 'MISSING_REQUIRED_FIELD';
  }
}

// Helper to read cookie by name (used for CSRF token)
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;
  const match = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[2]) : null;
}

// Enhanced error handler that parses standardized backend error format
async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    try {
      // Try to parse JSON error response
      const errorData = await res.json();

      // Check if response follows our standardized error format
      if (errorData.error && errorData.error.code && errorData.error.message) {
        throw new APIError(
          errorData.error.code,
          errorData.error.message,
          res.status,
          errorData.error.timestamp,
          errorData.error.details
        );
      }

      // Handle legacy error formats
      if (errorData.detail) {
        throw new APIError(
          'UNKNOWN_ERROR',
          errorData.detail,
          res.status
        );
      }

      // Handle serializer-style field errors (e.g., { "email": ["..."] })
      if (typeof errorData === 'object' && errorData !== null && !errorData.error) {
        const maybeFieldErrors = Object.values(errorData).every(
          (v) => Array.isArray(v) || typeof v === 'string'
        );
        if (maybeFieldErrors && Object.keys(errorData).length > 0) {
          const firstField = Object.entries(errorData)[0];
          const field = firstField[0];
          const val = firstField[1];
          const message = Array.isArray(val) ? val.join(', ') : String(val);
          throw new APIError(
            'INVALID_INPUT',
            `${field}: ${message}`,
            res.status,
            undefined,
            { validation_errors: errorData }
          );
        }
      }

      // Generic error for unrecognized format
      throw new APIError(
        'UNKNOWN_ERROR',
        errorData.message || 'An error occurred',
        res.status
      );
    } catch (parseError) {
      // If JSON parsing fails, fall back to text
      if (parseError instanceof APIError) {
        throw parseError;
      }

      const errorText = await res.text().catch(() => res.statusText);
      throw new APIError(
        'UNKNOWN_ERROR',
        errorText || `HTTP ${res.status}`,
        res.status
      );
    }
  }
}

/**
* A general-purpose API request helper.
* This function is used by mutations (POST, PUT, DELETE) where you explicitly
* call `apiRequest` with the endpoint and data.
*
* @param endpoint The API endpoint (e.g., "/api/test-answers", "/api/test-sessions/123/submit")
* @param method The HTTP method (e.g., "POST", "PUT", "DELETE")
* @param data Optional: The request body data
* @returns The JSON response from the API, or null for DELETE requests
*/
export async function apiRequest(
  endpoint: string, // This is the relative endpoint, not the full URL
  method: string,
  data?: unknown | undefined,
): Promise<any> { // Consider making this return type more specific if possible
  // Construct the full URL by prepending the BASE_URL
  const fullUrl = `${API_CONFIG.BASE_URL}${endpoint}`;

  // Check if we have an access token for authenticated requests
  const accessToken = getAccessToken();

  const headers: Record<string, string> = {};
  if (data) {
    headers["Content-Type"] = "application/json";
  }
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`;
  }

  try {
    // For authenticated requests, use the authenticatedFetch utility
    if (accessToken) {
      const res = await authenticatedFetch(fullUrl, {
        method,
        headers: data ? { "Content-Type": "application/json" } : {},
        body: data ? JSON.stringify(data) : undefined,
      });
      await throwIfResNotOk(res);
      return method === "DELETE" ? null : await res.json();
    } else {
      // For non-authenticated requests (like login), use regular fetch
      // Ensure CSRF token is provided for unsafe methods when using session-based auth
      // (Django will reject POST/PUT/DELETE without X-CSRFToken when using SessionAuthentication)
      if (!headers['X-CSRFToken'] && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
        const csrf = getCookie('csrftoken') || getCookie('csrf');
        if (csrf) headers['X-CSRFToken'] = csrf;
      }
      const res = await fetch(fullUrl, {
        method,
        headers,
        body: data ? JSON.stringify(data) : undefined,
        credentials: "include", // Include cookies for session-based fallback
      });
      await throwIfResNotOk(res);
      return method === "DELETE" ? null : await res.json();
    }
  } catch (error) {
    console.error(`API Request failed: ${method} ${fullUrl}`, error);

    // Log additional context for APIError instances
    if (error instanceof APIError) {
      console.error(`Error Code: ${error.code}, Status: ${error.status}`);
      if (error.details) {
        console.error('Error Details:', error.details);
      }
    }

    throw error;
  }
}

type UnauthorizedBehavior = "returnNull" | "throw";

/**
* React Query's default queryFn.
* This function is used by `useQuery` hooks where a custom `queryFn` is not provided.
* It takes the `queryKey[0]` (which is expected to be the API endpoint string)
* and constructs the full URL using BASE_URL.
*
* @param options.on401 Behavior when a 401 Unauthorized status is received.
* @returns A QueryFunction that fetches data.
*/
export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
    async ({ queryKey }) => {
      // queryKey[0] is expected to be the endpoint string (e.g., "/api/topics")
      const endpoint = queryKey[0] as string;
      // Construct the full URL for use by the default query function
      const fullUrl = `${API_CONFIG.BASE_URL}${endpoint}`;

      // Check if we have an access token for authenticated requests
      const accessToken = getAccessToken();

      try {
        let res: Response;

        if (accessToken) {
          // Use authenticated fetch for requests with JWT token
          res = await authenticatedFetch(fullUrl, {
            method: 'GET',
          });
        } else {
          // Use regular fetch for non-authenticated requests
          res = await fetch(fullUrl, {
            credentials: "include",
          });
        }

        if (unauthorizedBehavior === "returnNull" && res.status === 401) {
          return null;
        }

        await throwIfResNotOk(res);
        return await res.json();
      } catch (error) {
        console.error(`Query failed: GET ${fullUrl}`, error);

        // Log additional context for APIError instances
        if (error instanceof APIError) {
          console.error(`Error Code: ${error.code}, Status: ${error.status}`);
        }

        if (unauthorizedBehavior === "returnNull" && error instanceof APIError && error.status === 401) {
          return null;
        }
        if (unauthorizedBehavior === "returnNull" && error instanceof Error && error.message.includes('401')) {
          return null;
        }
        throw error;
      }
    };

// Initialize the React Query client with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }), // All useQuery calls will use this unless overridden
      refetchInterval: false,
      refetchOnWindowFocus: false,
      staleTime: Infinity, // Data is considered fresh indefinitely unless explicitly invalidated
      retry: false, // Do not retry failed queries by default
    },
    mutations: {
      retry: false, // Do not retry failed mutations by default
    },
  },
});