import { QueryClient, QueryFunction } from "@tanstack/react-query";
import { API_CONFIG } from "@/config/api"; // <--- Crucial: Import your API_CONFIG
import { getAccessToken, authenticatedFetch } from "@/lib/auth"; // Import JWT utilities

// Helper function to throw an error if the response is not OK
async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    // Attempt to parse the error body if available, otherwise use statusText
    const errorBody = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${errorBody}`);
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