// Barrel file to re-export all page components from a single entry
// This lets other files import pages from '@/pages' instead of many paths.

// Use a responsive wrapper that selects mobile or desktop implementation
export { default as Home } from "./responsive/home-responsive";
export { default as LoginPage } from "./login-register/login";
export { default as RegisterPage } from "./login-register/register";
export { default as ForgotPassword } from "./login-register/forgot-password";
export { default as ResetPassword } from "./login-register/reset-password";
export { default as Topics } from "./responsive/topics-responsive";
export { StudentProfile } from "./profile";
export { default as ScheduledTests } from "./scheduled-tests";
export { default as LandingDashboard } from "./responsive/dashboard-responsive";
export { default as Chatbot } from "./responsive/chatbot-responsive";
export { default as GoogleAuthCallback } from "./login-register/google-auth-callback";
export { default as GoogleCallback } from "./login-register/GoogleCallback";
export { default as Test } from "./test";
export { default as Results } from "./results";
export { default as TestHistory } from "../components/test-history";
export { default as ThankYou } from "./thank-you";
export { default as NotFound } from "./not-found";
export { default as ErrorPage } from "./error-page";
export { default as PaymentPage } from "./payment-page";
export { default as InstitutionTesterPage } from "./institution-tester";
export { default as InstitutionRegisterPage } from "./institution-register";
export { default as InstitutionAdminDashboard } from "./institution-admin-dashboard";
export { default as OfflineResultsUpload } from "./offline-results-upload";
export { default as AnswerKeyUpload } from "./answer-key-upload";
export { default as JSONQuestionUpload } from "./json-question-upload";
export { default as GetNumberPage } from "./get-number";
