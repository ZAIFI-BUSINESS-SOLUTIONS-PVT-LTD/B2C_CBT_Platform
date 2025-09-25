// Barrel file to re-export all page components from a single entry
// This lets other files import pages from '@/pages' instead of many paths.

// Use a responsive wrapper that selects mobile or desktop implementation
export { default as Home } from "./responsive/home-responsive";
export { default as LoginPage } from "./login";
export { default as RegisterPage } from "./register";
export { default as ForgotPassword } from "./forgot-password";
export { default as ResetPassword } from "./reset-password";
export { default as Topics } from "./responsive/topics-responsive";
export { StudentProfile } from "./profile";
export { default as ScheduledTests } from "./scheduled-tests";
export { default as LandingDashboard } from "./responsive/dashboard-responsive";
export { default as Chatbot } from "./responsive/chatbot-responsive";
export { default as GoogleAuthCallback } from "./google-auth-callback";
export { default as GoogleCallback } from "./GoogleCallback";
export { default as Test } from "./test";
export { default as Results } from "./results";
export { default as TestHistory } from "../components/test-history";
export { default as NotFound } from "./not-found";
export { default as ErrorPage } from "./error-page";
export { default as PaymentPage } from "./payment-page";
