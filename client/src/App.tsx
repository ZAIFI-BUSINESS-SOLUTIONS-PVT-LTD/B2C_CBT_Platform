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
import Topics from "@/pages/topics";
import Dashboard from "@/pages/dashboard";
import LandingDashboard from "@/pages/landing-dashboard";

/**
 * Application Router Component
 * Defines all available routes and their corresponding page components
 */
function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />                           {/* Home page with topic selection */}
      <Route path="/topics" component={Topics} />                  {/* Topics overview page */}
      <Route path="/dashboard" component={Dashboard} />            {/* Student performance dashboard */}
      <Route path="/landing-dashboard" component={LandingDashboard} />  {/* Comprehensive landing dashboard */}
      <Route path="/test/:sessionId" component={Test} />           {/* Test taking interface */}
      <Route path="/results/:sessionId" component={Results} />     {/* Test results and analytics */}
      <Route component={NotFound} />                               {/* 404 page for undefined routes */}
    </Switch>
  );
}

/**
 * Root Application Component
 * Provides global context providers and renders the router
 */
function App() {
  return (
    <QueryClientProvider client={queryClient}>  {/* React Query for server state management */}
      <AuthProvider>                             {/* Authentication context provider */}
        <TooltipProvider>                        {/* Tooltip context for UI components */}
          <Toaster />                            {/* Toast notification system */}
          <Router />                             {/* Application routing */}
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
