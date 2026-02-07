import React, { useEffect, useCallback, useState } from "react";
import { Switch, Route, useLocation } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { NotFound, Home, Test, Results, TestHistory, Topics, LandingDashboard, ScheduledTests, Chatbot, ForgotPassword, ResetPassword, LoginPage, RegisterPage, GoogleAuthCallback, GoogleCallback, ErrorPage, StudentProfile, PaymentPage, InstitutionTesterPage, InstitutionRegisterPage, InstitutionAdminDashboard, OfflineResultsUpload, AnswerKeyUpload, JSONQuestionUpload, ThankYou, GetNumberPage } from "@/pages";
import LoadingResultsPage from "@/pages/LoadingResultsPage";
import { ErrorBoundary } from "@/components/error-boundary";
import { getPostTestHidden } from '@/lib/postTestHidden';
import AppTourOverlay from "@/components/AppTourOverlay";
import { completeTour } from "@/config/api";

// Simple wrapper to prevent access to routes when post-test hidden flag is set
function protect(Component: any) {
  return function ProtectedWrapper(props: any) {
    const [, setLoc] = useLocation();
    useEffect(() => {
      if (getPostTestHidden()) {
        // redirect to home
        setLoc('/');
      }
    }, [setLoc]);

    if (getPostTestHidden()) return null;
    return <Component {...props} />;
  };
}

// Wrapper to check if user has phone number before accessing dashboard
function requirePhoneNumber(Component: any) {
  return function PhoneNumberProtectedWrapper(props: any) {
    const { student, isAuthenticated, loading } = useAuth();
    const [, navigate] = useLocation();

    useEffect(() => {
      if (!loading) {
        if (!isAuthenticated) {
          navigate("/login");
        } else if (!student?.phoneNumber) {
          navigate("/get-number");
        }
      }
    }, [loading, isAuthenticated, student, navigate]);

    if (loading) return null;
    if (!isAuthenticated || !student?.phoneNumber) return null;

    return <Component {...props} />;
  };
}

// Wrapper to blur a component when post-test hidden flag is set.
// Uses a full-screen fixed overlay with `backdrop-filter` so elements
// that are positioned above the overlay (like the sidebar/header with
// higher z-index) remain visible and unblurred.
function blurIfPostTest(Component: any) {
  return function BlurWrapper(props: any) {
    const hidden = getPostTestHidden();
    return (
      <div style={{ position: 'relative' }}>
        {/* Render component normally (no parent filter) */}
        <Component {...props} />

        {/* If hidden, place a full-viewport overlay that blurs everything behind it
            while allowing header/sidebar (which have higher z-index) to remain on top */}
        {hidden && (
          <div
            aria-hidden
            style={{
              position: 'fixed',
              inset: 0,
              // Place overlay below sidebar (sidebar z-40) and header (z-50)
              zIndex: 30,
              // Slight translucent white + backdrop blur for modern effect
              backgroundColor: 'rgba(255,255,255,0.5)',
              backdropFilter: 'blur(6px) saturate(120%)',
              WebkitBackdropFilter: 'blur(6px) saturate(120%)',
              // Block clicks to underlying content
              pointerEvents: 'auto',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 16,
              textAlign: 'center',
            }}
          >
          </div>
        )}
      </div>
    );
  };
}

function ErrorPageRoute() {
  return <ErrorPage />;
}

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />                           {/* Home page with topic selection */}
      <Route path="/login" component={LoginPage} />
      <Route path="/register" component={RegisterPage} />
      <Route path="/institution-register" component={InstitutionRegisterPage} />
      <Route path="/institution-admin/dashboard" component={InstitutionAdminDashboard} />
      <Route path="/institution-admin-dashboard" component={InstitutionAdminDashboard} />
      <Route path="/offline-results-upload" component={OfflineResultsUpload} />
      <Route path="/answer-key-upload" component={AnswerKeyUpload} />
      <Route path="/json-question-upload" component={JSONQuestionUpload} />
      <Route path="/get-number" component={GetNumberPage} />
      <Route path="/forgot-password" component={ForgotPassword} />
      <Route path="/reset-password" component={ResetPassword} />
      <Route path="/topics" component={Topics} />                  {/* Topics overview page */}
      <Route path="/profile" component={requirePhoneNumber(StudentProfile)} />        {/* Student profile page */}
      <Route path="/scheduled-tests" component={requirePhoneNumber(ScheduledTests)} /> {/* Platform tests page */}
      <Route path="/institution-tests" component={InstitutionTesterPage} /> {/* Institution tests page */}
      <Route path="/dashboard" component={requirePhoneNumber(LandingDashboard)} />  {/* Comprehensive landing dashboard */}
      <Route path="/loading-results/:sessionId" component={requirePhoneNumber(LoadingResultsPage)} /> {/* Loading results with video */}
      <Route path="/chatbot" component={requirePhoneNumber(Chatbot)} />               {/* AI Chatbot tutor page */}
      <Route path="/auth/callback" component={GoogleAuthCallback} /> {/* Google OAuth callback */}
      <Route path="/auth/google/callback" component={GoogleCallback} /> {/* Google OAuth popup callback */}
      <Route path="/test/:sessionId" component={Test} />           {/* Test taking interface */}
      <Route path="/results/:sessionId" component={Results} />     {/* Test results and analytics */}
      <Route path="/test-history" component={TestHistory} />
      <Route path="/thank-you" component={ThankYou} />
      <Route path="/error" component={ErrorPageRoute} />               {/* Error page for critical errors */}
      <Route path="/payment" component={PaymentPage} />            {/* Payment processing page */}
      <Route component={NotFound} />                               {/* 404 page for undefined routes */}
    </Switch>
  );
}


/** Per-user localStorage prefix so the guard is scoped to each student. */
const TOUR_DONE_PREFIX = 'neet_tour_completed_';

/** Routes where the mobile dock exists and the tour can safely start. */
const TOUR_START_ROUTES = ['/', '/dashboard', '/topics'];

/**
 * TourWrapper — shows the onboarding overlay on first login.
 * Renders inside AuthProvider so it has access to `useAuth()`.
 *
 * Guards (belt-and-suspenders):
 *   1. Backend: is_first_login on StudentProfile (source of truth)
 *   2. localStorage: TOUR_DONE_PREFIX + studentId (per-user client-side check)
 *   3. Route check: tour only *starts* on pages that have the mobile dock;
 *      once running it stays visible as the user navigates (Step 2 → /topics etc.)
 */
function TourWrapper() {
  const { student, isAuthenticated, setStudent } = useAuth();
  const [showTour, setShowTour] = useState(false);
  const [location] = useLocation();

  useEffect(() => {
    // Once tour is already showing, don't re-evaluate (the tour itself handles navigation)
    if (showTour) return;

    if (!isAuthenticated || !student?.studentId) return;

    // CRITICAL: Only start tour AFTER phone number is set (phone form must be completed first)
    if (!student?.phoneNumber) return;

    // Only START the tour on pages with the mobile dock
    if (!TOUR_START_ROUTES.includes(location)) return;

    const localDone = localStorage.getItem(TOUR_DONE_PREFIX + student.studentId) === 'true';
    if (student.isFirstLogin === true && !localDone) {
      setShowTour(true);
    }
  }, [isAuthenticated, student?.isFirstLogin, student?.studentId, student?.phoneNumber, location, showTour]);

  const handleTourComplete = useCallback(async () => {
    // 1. Per-user localStorage guard — prevents re-show even if API is slow/fails
    if (student?.studentId) {
      localStorage.setItem(TOUR_DONE_PREFIX + student.studentId, 'true');
    }

    // 2. Persist to backend (source of truth)
    try {
      await completeTour();
    } catch (err) {
      console.error('Failed to persist tour completion to server:', err);
    }

    // 3. Update local React state so overlay hides immediately
    if (student) {
      setStudent({ ...student, isFirstLogin: false });
    }
    setShowTour(false);
  }, [student, setStudent]);

  if (!showTour) return null;

  return <AppTourOverlay onTourComplete={handleTourComplete} />;
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
            {/* First-login onboarding tour overlay */}
            <TourWrapper />
          </TooltipProvider>
        </ErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
