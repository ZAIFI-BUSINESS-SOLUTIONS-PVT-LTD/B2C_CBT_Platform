// API Configuration for NEET Practice Platform
export const API_CONFIG = {
  // Use environment-based URLs for proper dev/production switching
  BASE_URL: import.meta.env.DEV 
    ? 'http://localhost:8000' 
    : 'https://cbtapi.inzighted.com',
  
  // API endpoints
  ENDPOINTS: {
    // Standard DRF endpoints with trailing slashes (Django default)
    TOPICS: '/api/topics/',
    QUESTIONS: '/api/questions/',
    TEST_ANSWERS: '/api/test-answers/', // For individual answer submission (POST)

    // Test Sessions endpoints:
    TEST_SESSIONS: '/api/test-sessions/', // For POST to create a session, GET to list all sessions
    // For fetching a specific test session (GET /api/test-sessions/:id)
    TEST_SESSION_DETAIL: (id: number) => `/api/test-sessions/${id}/`,
    // For submitting a test session (POST /api/test-sessions/:id/submit)
    TEST_SESSION_SUBMIT: (id: number) => `/api/test-sessions/${id}/submit/`,
    // For retrieving test results (GET /api/test-sessions/:id/results)
    TEST_SESSION_RESULTS: (id: number) => `/api/test-sessions/${id}/results/`,

    // Student Profile endpoints:
    STUDENT_PROFILE: '/api/student-profile/', // For general list/create (if applicable)
    // For fetching a student profile by email (GET /api/student-profile/email/:email)
    STUDENT_PROFILE_BY_EMAIL: (email: string) => `/api/student-profile/email/${encodeURIComponent(email)}/`, // Use encodeURIComponent for email

    // Add other custom endpoints here if you have them, e.g.:
    DASHBOARD_ANALYTICS: '/api/dashboard/analytics/',
    DASHBOARD_COMPREHENSIVE_ANALYTICS: '/api/dashboard/comprehensive-analytics/',
  },
};

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string, id?: number | string) => {
  const baseUrl = API_CONFIG.BASE_URL + endpoint;
  return id ? `${baseUrl}${id}/` : baseUrl;
};

// --- API Utility Functions for Auth and Test Session Creation ---
import { LoginCredentials, LoginResponse, CreateTestSessionRequest, CreateTestSessionResponse } from "@/types/api";
import { apiRequest } from "@/lib/queryClient";

/**
 * Login a student using studentId and password
 * @param credentials LoginCredentials
 * @returns LoginResponse
 */
export async function loginStudent(credentials: LoginCredentials): Promise<LoginResponse> {
  // Use the correct backend endpoint for login
  return await apiRequest("/api/test/login/", "POST", credentials);
}

/**
 * Create a new test session for a student
 * @param data CreateTestSessionRequest
 * @returns CreateTestSessionResponse
 */
export async function createTestSession(data: CreateTestSessionRequest): Promise<CreateTestSessionResponse> {
  // Assumes backend endpoint: /api/test-sessions/ (POST)
  return await apiRequest(API_CONFIG.ENDPOINTS.TEST_SESSIONS, "POST", data);
}