// API Configuration for NEET Practice Platform
export const API_CONFIG = {
  // Use environment-based URLs for proper dev/production switching
  BASE_URL: import.meta.env.DEV
    ? 'http://localhost:8000'
    : 'https://testapi.inzighted.com',

  // API endpoints
  ENDPOINTS: {
    // Standard DRF endpoints with trailing slashes (Django default)
    TOPICS: '/api/topics/',
    TOPIC_QUESTION_COUNTS: '/api/topics/question-counts/',
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
    DASHBOARD_PLATFORM_TEST_ANALYTICS: '/api/dashboard/platform-test-analytics/',

    // Time tracking endpoint
    TEST_SESSION_LOG_TIME: '/api/time-tracking/log_time/',

    // Chatbot endpoints
    CHAT_SESSIONS: '/api/chat-sessions/',
    CHAT_SESSION_DETAIL: (sessionId: string) => `/api/chat-sessions/${sessionId}/`,
    CHAT_SESSION_MESSAGES: (sessionId: string) => `/api/chat-sessions/${sessionId}/messages/`,
    CHAT_SESSION_SEND_MESSAGE: (sessionId: string) => `/api/chat-sessions/${sessionId}/send-message/`,
    CHAT_QUICK: '/api/chatbot/quick-chat/',
    CHAT_STATISTICS: '/api/chatbot/statistics/',
    
    // Chat Memory endpoints
    CHAT_MEMORY: '/api/chat-memory/',
    CHAT_MEMORY_DETAIL: (memoryId: string) => `/api/chat-memory/${memoryId}/`,
    CHAT_MEMORY_TRIGGER_SUMMARIZATION: '/api/chat-memory/trigger-summarization/',

    // Platform Tests endpoints
    PLATFORM_TESTS_AVAILABLE: '/api/platform-tests/available/',
    PLATFORM_TEST_DETAIL: (testId: number) => `/api/platform-tests/${testId}/`,
    PLATFORM_TEST_START: (testId: number) => `/api/platform-tests/${testId}/start/`,

    // Password reset endpoints
    AUTH_FORGOT_PASSWORD: '/api/auth/forgot-password/',
    AUTH_VERIFY_RESET: '/api/auth/verify-reset-token/',
    AUTH_RESET_PASSWORD: '/api/auth/reset-password/',

    // Mobile OTP authentication endpoints
    AUTH_SEND_OTP: '/api/auth/send-otp/',
    AUTH_VERIFY_OTP: '/api/auth/verify-otp/',

    // Payment endpoints
    PAYMENTS_CREATE_ORDER: '/api/payments/create-order/',
    PAYMENTS_VERIFY_PAYMENT: '/api/payments/verify-payment/',
    PAYMENTS_SUBSCRIPTION_STATUS: '/api/payments/subscription-status/',
  },
};

// Helper function to build full API URLs
export const buildApiUrl = (endpoint: string, id?: number | string) => {
  const baseUrl = API_CONFIG.BASE_URL + endpoint;
  return id ? `${baseUrl}${id}/` : baseUrl;
};

// --- API Utility Functions for Auth and Test Session Creation ---
import { LoginCredentials, LoginResponse, CreateTestSessionRequest, CreateTestSessionResponse, AvailablePlatformTestsResponse, StartPlatformTestRequest, StartPlatformTestResponse, PlatformTest } from "@/types/api";
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

/**
 * Get all available platform tests (scheduled and open)
 * @returns AvailablePlatformTestsResponse
 */
export async function getAvailablePlatformTests(): Promise<AvailablePlatformTestsResponse> {
  return await apiRequest(API_CONFIG.ENDPOINTS.PLATFORM_TESTS_AVAILABLE, "GET");
}

/**
 * Get details of a specific platform test
 * @param testId Platform test ID
 * @returns PlatformTest
 */
export async function getPlatformTestDetails(testId: number): Promise<PlatformTest> {
  return await apiRequest(API_CONFIG.ENDPOINTS.PLATFORM_TEST_DETAIL(testId), "GET");
}

/**
 * Start a platform test (create a test session for platform test)
 * @param data StartPlatformTestRequest
 * @returns StartPlatformTestResponse
 */
export async function startPlatformTest(data: StartPlatformTestRequest): Promise<StartPlatformTestResponse> {
  return await apiRequest(API_CONFIG.ENDPOINTS.PLATFORM_TEST_START(data.testId), "POST", data);
}

// --- Payment API Functions ---

/**
 * Create a Razorpay order for the specified plan
 * @param plan 'basic' | 'pro'
 * @returns Order creation response with order_id, amount, currency, key_id, local_order_id
 */
export async function createOrder(plan: 'basic' | 'pro') {
  return await apiRequest(API_CONFIG.ENDPOINTS.PAYMENTS_CREATE_ORDER, "POST", { plan });
}

/**
 * Verify payment after Razorpay checkout completion
 * @param payload Payment verification data from Razorpay
 * @returns Payment verification response
 */
export async function verifyPayment(payload: {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  local_order_id: number;
}) {
  return await apiRequest(API_CONFIG.ENDPOINTS.PAYMENTS_VERIFY_PAYMENT, "POST", payload);
}

/**
 * Get current subscription status for the authenticated student
 * @returns Subscription status with plan, expiry, and availability
 */
export async function getSubscriptionStatus() {
  return await apiRequest(API_CONFIG.ENDPOINTS.PAYMENTS_SUBSCRIPTION_STATUS, "GET");
}

// --- Chat Session API Functions ---

/**
 * Delete a chat session by setting it as inactive
 * @param sessionId Chat session ID to delete
 * @returns Delete confirmation response
 */
export async function deleteChatSession(sessionId: string) {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_SESSION_DETAIL(sessionId), "DELETE");
}

// --- Chat Memory API Functions ---

/**
 * Get all chat memories for the authenticated student
 * @returns List of chat memories
 */
export async function getChatMemories() {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_MEMORY, "GET");
}

/**
 * Create a new chat memory
 * @param memoryData Memory data object
 * @returns Created memory response
 */
export async function createChatMemory(memoryData: {
  memory_type?: 'long_term' | 'short_term';
  content: any;
  source_session_id?: string;
  key_tags?: string[];
  confidence_score?: number;
}) {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_MEMORY, "POST", memoryData);
}

/**
 * Update an existing chat memory
 * @param memoryId Memory ID to update
 * @param memoryData Updated memory data
 * @returns Updated memory response
 */
export async function updateChatMemory(memoryId: string, memoryData: any) {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_MEMORY_DETAIL(memoryId), "PATCH", memoryData);
}

/**
 * Delete a chat memory
 * @param memoryId Memory ID to delete
 * @returns Delete confirmation response
 */
export async function deleteChatMemory(memoryId: string) {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_MEMORY_DETAIL(memoryId), "DELETE");
}

/**
 * Manually trigger memory summarization for a session
 * @param sessionId Chat session ID to summarize
 * @returns Task response with task_id
 */
export async function triggerMemorySummarization(sessionId: string) {
  return await apiRequest(API_CONFIG.ENDPOINTS.CHAT_MEMORY_TRIGGER_SUMMARIZATION, "POST", { session_id: sessionId });
}
