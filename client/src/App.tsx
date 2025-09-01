/**
 * Main Application Component for NEET Practice Platform
 * 
 * This is the root component that sets up the application structure including:
 * - React Query for server state management
 * - Wouter for client-side routing
 * - Toast notifications for user feedback
 * - Tooltip support for enhanced UX
 */

import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";
import Test from "@/pages/test";
import Results from "@/pages/results";
import TestHistory from "@/pages/test-history";
import Topics from "@/pages/topics";
import LandingDashboard from "@/pages/landing-dashboard";
import Chatbot from "@/pages/chatbot";
import ForgotPassword from "@/pages/forgot-password";
import ResetPassword from "@/pages/reset-password";
import GoogleAuthCallback from "@/pages/google-auth-callback";
import GoogleCallback from "@/pages/GoogleCallback";
import { FloatingChatbot } from "@/components/floating-chatbot";
import { useLocation } from "wouter";
/**
 * Application Router Component
 * Defines all available routes and their corresponding page components
 */
function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />                           {/* Home page with topic selection */}
  <Route path="/login" component={Home} />
  <Route path="/forgot-password" component={ForgotPassword} />
  <Route path="/reset-password" component={ResetPassword} />
      <Route path="/topics" component={Topics} />                  {/* Topics overview page */}
      <Route path="/dashboard" component={LandingDashboard} />  {/* Comprehensive landing dashboard */}
      <Route path="/chatbot" component={Chatbot} />               {/* AI Chatbot tutor page */}
      <Route path="/auth/callback" component={GoogleAuthCallback} /> {/* Google OAuth callback */}
      <Route path="/auth/google/callback" component={GoogleCallback} /> {/* Google OAuth popup callback */}
      <Route path="/test/:sessionId" component={Test} />           {/* Test taking interface */}
      <Route path="/results/:sessionId" component={Results} />     {/* Test results and analytics */}
  <Route path="/test-history" component={TestHistory} />
      <Route component={NotFound} />                               {/* 404 page for undefined routes */}
    </Switch>
  );
}

/**
 * Root Application Component
 * Provides global context providers and renders the router
 */

function App() {
  const [location] = useLocation();
  // Hide chatbot on any /test route
  const isTestPage = location.startsWith("/test");
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          {!isTestPage && <FloatingChatbot />}
          <Router />
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
