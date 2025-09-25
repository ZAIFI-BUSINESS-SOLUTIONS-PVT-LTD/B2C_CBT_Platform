import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider } from "@/contexts/AuthContext";
import { NotFound, Home, Test, Results, TestHistory, Topics, LandingDashboard, ScheduledTests, Chatbot, ForgotPassword, ResetPassword, LoginPage, RegisterPage, GoogleAuthCallback, GoogleCallback, ErrorPage, StudentProfile, PaymentPage, } from "@/pages";
import { ErrorBoundary } from "@/components/error-boundary";

function ErrorPageRoute() {
  return <ErrorPage />;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />                           {/* Home page with topic selection */}
      <Route path="/login" component={LoginPage} />
      <Route path="/register" component={RegisterPage} />
      <Route path="/forgot-password" component={ForgotPassword} />
      <Route path="/reset-password" component={ResetPassword} />
      <Route path="/topics" component={Topics} />                  {/* Topics overview page */}
      <Route path="/profile" component={StudentProfile} />        {/* Student profile page */}
      <Route path="/scheduled-tests" component={ScheduledTests} /> {/* Platform tests page */}
      <Route path="/dashboard" component={LandingDashboard} />  {/* Comprehensive landing dashboard */}
      <Route path="/chatbot" component={Chatbot} />               {/* AI Chatbot tutor page */}
      <Route path="/auth/callback" component={GoogleAuthCallback} /> {/* Google OAuth callback */}
      <Route path="/auth/google/callback" component={GoogleCallback} /> {/* Google OAuth popup callback */}
      <Route path="/test/:sessionId" component={Test} />           {/* Test taking interface */}
      <Route path="/results/:sessionId" component={Results} />     {/* Test results and analytics */}
      <Route path="/test-history" component={TestHistory} />
      <Route path="/error" component={ErrorPageRoute} />               {/* Error page for critical errors */}
      <Route path="/payment" component={PaymentPage} />            {/* Payment processing page */}
      <Route component={NotFound} />                               {/* 404 page for undefined routes */}
    </Switch>
  );
}


function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ErrorBoundary>
          <TooltipProvider>
            <Toaster />
            {/* floating chatbot removed */}
            <Router />
          </TooltipProvider>
        </ErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
