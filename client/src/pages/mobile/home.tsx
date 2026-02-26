/**
 * Home Page Component
 *
 * This file contains the main dashboard page for the B2C CBT Platform.
 * It displays user insights, analytics, and provides navigation to tes  // Accordion state for collapsible cards
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set(['study-plan']));Features:
 * - User authentication check
 * - Dashboard analytics and insights
 * - Tabbed interface for different insight categories
 * - Mobile-friendly swipe navigation
 * - AI-powered study recommendations
 */

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, useRef, useCallback, useMemo } from "react";
import { useAuth } from '@/contexts/AuthContext';
import { useLocation } from "wouter";
import Logo from "@/assets/images/logo.svg";
import MiniChatbot from '@/components/mini-chatbot';
import { ArrowRight, History, NotebookPen, Trophy, AlertTriangle, Lock, GraduationCap, Timer, HelpCircle, FileText, ChevronRight, ClipboardList, Bookmark } from "lucide-react";
import MobileDock from "@/components/mobile-dock";
import { AnalyticsData } from "@/components/insight-card";
import NeetCountdown from '@/components/coundown';
import Share from '@/components/share';
import Stat from '@/components/ui/stat-mobile';

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Formats a date string into a human-readable relative time string
 * @param dateString - ISO date string or null
 * @returns Relative time string (e.g., "2 hours ago", "just now")
 */
const formatRelativeTime = (dateString: string | null): string => {
  if (!dateString) return 'just now';

  try {
    const date = new Date(dateString);

    // Check if date is valid
    if (isNaN(date.getTime())) return 'just now';

    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    // Handle future dates (shouldn't happen but just in case)
    if (diffInSeconds < 0) return 'just now';

    if (diffInSeconds < 60) return 'just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minute${Math.floor(diffInSeconds / 60) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hour${Math.floor(diffInSeconds / 3600) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)} day${Math.floor(diffInSeconds / 86400) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 2592000) return `${Math.floor(diffInSeconds / 604800)} week${Math.floor(diffInSeconds / 604800) === 1 ? '' : 's'} ago`;
    if (diffInSeconds < 31536000) return `${Math.floor(diffInSeconds / 2592000)} month${Math.floor(diffInSeconds / 2592000) === 1 ? '' : 's'} ago`;
    return `${Math.floor(diffInSeconds / 31536000)} year${Math.floor(diffInSeconds / 31536000) === 1 ? '' : 's'} ago`;
  } catch (error) {
    console.warn('Error parsing date for relative time:', dateString, error);
    return 'just now';
  }
};

/**
 * Test function to verify the formatRelativeTime function works correctly
 * Logs various test cases to the console
 */
const testRelativeTime = () => {
  const now = new Date();
  console.log('Testing formatRelativeTime function:');
  console.log('Just now:', formatRelativeTime(now.toISOString()));
  console.log('5 minutes ago:', formatRelativeTime(new Date(now.getTime() - 5 * 60 * 1000).toISOString()));
  console.log('2 hours ago:', formatRelativeTime(new Date(now.getTime() - 2 * 60 * 60 * 1000).toISOString()));
  console.log('1 day ago:', formatRelativeTime(new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString()));
  console.log('Invalid date:', formatRelativeTime('invalid-date'));
  console.log('Null:', formatRelativeTime(null));
};

// =============================================================================
// STYLING CONFIGURATIONS
// =============================================================================

// Centralized insight card styling configuration
// To change all insight cards at once, modify the styles below:
// - container: Main card container styles (padding, border, etc.)
// - text: Base text styling
// - variants: Color schemes for different card types
const INSIGHT_CARD_STYLES = {
  // Main card container styles
  container: "p-3 rounded-xl",
  text: "text-sm",

  // Color variants for different insight types
  variants: {
    blue: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-blue-600",
      accentBg: "bg-blue-50"
    },
    indigo: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-indigo-600",
      accentBg: "bg-indigo-50"
    },
    green: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-green-600",
      accentBg: "bg-green-50"
    },
    red: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-red-600",
      accentBg: "bg-red-50"
    },
    gray: {
      container: "bg-gray-200",
      text: "text-gray-700",
      accent: "text-gray-600",
      accentBg: "bg-gray-50"
    }
  }
};

// =============================================================================
// REUSABLE COMPONENTS
// =============================================================================

/**
 * Reusable InsightCard component for displaying insights with consistent styling
 */
interface InsightCardProps {
  children: React.ReactNode;
  variant: keyof typeof INSIGHT_CARD_STYLES.variants;
  className?: string;
}

const InsightCard: React.FC<InsightCardProps> = ({ children, variant, className = "" }) => {
  const styles = INSIGHT_CARD_STYLES.variants[variant];
  return (
    <div className={`${INSIGHT_CARD_STYLES.container} ${styles.container} ${className}`}>
      <div className={`${INSIGHT_CARD_STYLES.text} ${styles.text}`}>
        {children}
      </div>
    </div>
  );
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/**
 * Home page component that renders the dashboard-focused landing page
 * @returns JSX element containing the main dashboard interface
 */
export default function Home() {
  // =============================================================================
  // HOOKS AND STATE MANAGEMENT
  // =============================================================================

  // Authentication and navigation hooks
  const { isAuthenticated, loading, student } = useAuth();
  const [, navigate] = useLocation();
  const queryClient = useQueryClient();

  // Check if user is institution student
  const hasInstitution = !!student?.institution;

  // Debug: Log institution status
  useEffect(() => {
    console.log('🏫 Institution check:', {
      student,
      hasInstitution,
      institutionData: student?.institution
    });
  }, [student, hasInstitution]);

  // Tab state for horizontal swipable tabs
  const [activeTab, setActiveTab] = useState(0);

  // Touch/swipe navigation state for mobile
  const [touchStart, setTouchStart] = useState<{ x: number; y: number } | null>(null);
  const [touchEnd, setTouchEnd] = useState<{ x: number; y: number } | null>(null);
  const [isSwiping, setIsSwiping] = useState(false);

  // Ref for touch container to attach native event listeners
  const touchContainerRef = useRef<HTMLDivElement>(null);

  // Ref for the tab navigation container
  const tabNavRef = useRef<HTMLElement>(null);

  // =============================================================================
  // UTILITY FUNCTIONS
  // =============================================================================

  // Tab navigation functions
  const nextTab = useCallback(() => {
    setActiveTab(prev => (prev + 1) % 4);
  }, []);

  const prevTab = useCallback(() => {
    setActiveTab(prev => (prev - 1 + 4) % 4);
  }, []);

  // Touch event handlers for swipe navigation
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart({
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    });
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    setTouchEnd({
      x: e.targetTouches[0].clientX,
      y: e.targetTouches[0].clientY
    });
  }, []);

  const handleTouchEnd = useCallback(() => {
    if (!touchStart || !touchEnd) return;

    const distanceX = touchStart.x - touchEnd.x;
    const distanceY = touchStart.y - touchEnd.y;
    const isLeftSwipe = distanceX > 50;
    const isRightSwipe = distanceX < -50;
    const isVerticalSwipe = Math.abs(distanceY) > Math.abs(distanceX);

    // Only handle horizontal swipes
    if (!isVerticalSwipe) {
      if (isLeftSwipe) {
        nextTab();
      } else if (isRightSwipe) {
        prevTab();
      }
    }
  }, [touchStart, touchEnd, nextTab, prevTab]);

  // =============================================================================
  // DATA FETCHING
  // =============================================================================

  // Dashboard and analytics queries (only when authenticated)
  const { data: analytics } = useQuery<AnalyticsData>({
    queryKey: ['/api/dashboard/comprehensive-analytics/'],
    // match landing-dashboard behavior: refresh periodically and only run when auth state settled
    refetchInterval: 30000,
    enabled: isAuthenticated && !loading, // Only run when authenticated and auth finished loading
  });

  // `insights` endpoint removed from backend; no client request here anymore.

  // =============================================================================
  // SIDE EFFECTS
  // =============================================================================

  // Scroll active tab into view when tab changes
  useEffect(() => {
    if (tabNavRef.current) {
      const activeTabButton = tabNavRef.current.querySelector(`[data-tab-id="${activeTab}"]`) as HTMLElement;
      if (activeTabButton) {
        activeTabButton.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest',
          inline: 'center'
        });
      }
    }
  }, [activeTab]);

  // Run quick debug tests on mount
  useEffect(() => {
    testRelativeTime();
  }, []);

  // =============================================================================
  // EARLY RETURNS AND COMPUTED VALUES
  // =============================================================================

  // Show login form if not authenticated
  // Redirect to login page if not authenticated
  if (!isAuthenticated) {
    // While auth is loading, keep the placeholder minimal
    if (loading) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-indigo-50">
          <div className="text-center text-sm text-gray-600">Checking authentication...</div>
        </div>
      );
    }

    // Navigate to login for unauthenticated users
    navigate('/login');
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-indigo-50 to-indigo-50">
        <div className="text-center text-sm text-gray-600">Redirecting to login...</div>
      </div>
    );
  }

  // Check if user has previous test data
  const hasData = analytics && analytics.totalTests > 0;

  // =============================================================================
  // MAIN RENDER
  // =============================================================================

  return (
    <div className="min-h-screen bg-white">
      {/* ============================================================================= */}
      {/* INLINE STYLES - MOVED TO index.css FOR BETTER ORGANIZATION */}
      {/* Styles for hide-scrollbar, tab-content, insights-container, and tab-content-container */}
      {/* are now located in client/src/index.css under HOME PAGE COMPONENT STYLES */}
      {/* ============================================================================= */}

      {/* ============================================================================= */}
      {/* HEADER SECTION */}
      {/* ============================================================================= */}
      <header className="w-full bg-white border-b sticky top-0 z-50">
        <div className="w-full mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <img src={Logo} alt="InzightEd" className="h-6 w-auto" />
              {/* Debug indicator */}
              {hasInstitution && (
                <span className="text-xs bg-red-500 text-white px-2 py-1 rounded">INSTITUTION</span>
              )}
            </div>
            {/* Right side with profile */}
            <div className="flex items-center space-x-2">
              {/* crown button removed — moved to topics/test page */}
            </div>
          </div>
        </div>
      </header>

      {/* ============================================================================= */}
      {/* MAIN CONTENT AREA */}
      {/* ============================================================================= */}
      <div className="w-full bg-gray-100 relative">
        {/* Blur overlay for institution students */}
        {hasInstitution && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-white/60 backdrop-blur-sm min-h-screen">
            <div className="bg-white p-8 rounded-2xl shadow-2xl border-2 border-gray-300 max-w-md mx-4">
              <div className="flex flex-col items-center gap-4 text-center">
                <div className="bg-gray-100 p-4 rounded-full">
                  <Lock className="h-16 w-16 text-gray-500" />
                </div>
                <div>
                  <h3 className="font-bold text-xl text-gray-900 mb-2"></h3>
                  <p className="text-base text-gray-600 leading-relaxed">This feature is not available for institution-enrolled students. Please access your institution-specific tests and resources.</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Content wrapper with conditional blur */}
        <div className={hasInstitution ? 'blur-lg pointer-events-none select-none' : ''} aria-hidden={hasInstitution}>

          {/* ============================================================================= */}
          {/* STATS SECTION - Mini Dashboard at the top */}
          {/* ============================================================================= */}
          <div className="w-full px-3 py-2 bg-gradient-to-br from-slate-100 to-white">
            <div className="w-full overflow-x-auto hide-scrollbar">
              <div className="flex gap-3 snap-x snap-mandatory items-center">
                {/* Accuracy Card */}
                <div className="flex-shrink-0 snap-center p-1">
                  <Stat
                    icon={<GraduationCap className="w-5 h-5 text-green-600" />}
                    iconBgClass="bg-green-50 border border-green-100"
                    label="Your Average Score"
                    value={analytics ? `${Math.round(analytics.overallAccuracy ?? 0)}%` : '0%'}
                    info="Percentage score across all tests taken"
                    className="p-2"
                  />
                </div>

                {/* Avg. Speed Card */}
                <div className="flex-shrink-0 snap-center p-1">
                  <Stat
                    icon={<Timer className="w-5 h-5 text-orange-600" />}
                    iconBgClass="bg-orange-50 border border-orange-100"
                    label="Avg. Speed /Question"
                    value={analytics ? `${Math.round(analytics.averageTimePerQuestion ?? 0)} sec.` : '0 sec.'}
                    info="Average time spent per question"
                    className="p-2"
                  />
                </div>

                {/* Questions Card */}
                <div className="flex-shrink-0 snap-center p-1">
                  <Stat
                    icon={<HelpCircle className="w-5 h-5 text-blue-600" />}
                    iconBgClass="bg-blue-50 border border-blue-100"
                    label="Questions attended"
                    value={analytics ? `${analytics.uniqueQuestionsAttempted ?? 0}` : '0'}
                    info="Total number of questions attempted"
                    className="p-2"
                  />
                </div>

                {/* Tests Attended Card */}
                <div className="flex-shrink-0 snap-center p-1">
                  <Stat
                    icon={<FileText className="w-5 h-5 text-purple-600" />}
                    iconBgClass="bg-purple-50 border border-purple-100"
                    label="Tests attended"
                    value={analytics ? `${analytics.totalTests ?? 0}` : '0'}
                    info="Total number of tests completed"
                    className="p-2"
                  />
                </div>
              </div>
            </div>
          </div>




          {/* ============================================================================= */}
          {/* BODY CONTAINER - Main content area below insights */}
          {/* ============================================================================= */}
          <div className="pb-20 bg-white rounded-t-3xl w-full shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1),0_10px_15px_-3px_rgba(0,0,0,0.1),0_4px_6px_-2px_rgba(0,0,0,0.05)]">

            {/* ============================================================================= */}
            {/* INSIGHTS SECTION - Show tabs always; if no tests, show friendly fallback cards */}
            {/* ============================================================================= */}
            <>
              {/* Focus/Steady tabs removed (backend insights flow deprecated) */}
              <div className="px-4 pt-4"></div>

              {/* Tab Content Card */}
              <div className="select-none insights-container relative bg-white">
                <div
                  ref={touchContainerRef}
                  onTouchStart={handleTouchStart}
                  onTouchMove={handleTouchMove}
                  onTouchEnd={handleTouchEnd}
                  className="overflow-hidden"
                >
                  {/* Tab Content */}
                  <div className="p-4 min-h-[120px]">
                    {/* If user has no tests, show a clear fallback CTA card for all tabs */}
                    {!hasData ? (
                      <div className="space-y-3">
                        <InsightCard variant={activeTab === 0 ? 'red' : activeTab === 1 ? 'blue' : 'green'}>
                          <div className="flex flex-col  justify-center items-center gap-3">
                            <div>

                              <Lock className="h-16 w-16 text-gray-400" />

                            </div>
                            <div className="text-center">
                              <p className="font-semibold">Get personalized insights</p>
                              <p className="text-xs text-gray-600">Take your first practice test to unlock AI-powered Focus Zone and Steady Zone analysis.</p>
                            </div>
                            <div className="flex">
                              <Button
                                variant="default"
                                size="lg"
                                onClick={() => navigate('/topics')}
                                className="w-full rounded-lg font-bold"
                                aria-label="Take a Test"
                              >
                                Take Unlimited Mock Tests
                              </Button>
                            </div>
                          </div>
                        </InsightCard>
                      </div>
                    ) : (
                      // Existing content when user has data
                      <>
                        
                              <></>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* ============================================================================= */}
              {/* VIEW MORE AI TIPS SECTION */}
              {/* ============================================================================= */}
              <div className="px-4 pb-6">
                <Button
                  variant="default"
                  size="lg"
                  onClick={() => navigate('/dashboard')}
                  className="w-full px-4 bg-gradient-to-b from-gray-600 to-gray-800 text-white rounded-xl font-semibold flex"
                  aria-label="View more AI generated tips"
                >
                  Results and more AI generated tips
                  <ChevronRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </>
            {/* Visual separator */}
            <div className="px-4 pb-4">
              <div className="h-px bg-gradient-to-r from-transparent via-gray-100 to-transparent"></div>
            </div>

            {/* ============================================================================= */}
            {/* TEST SECTION */}
            {/* ============================================================================= */}
            <div className="px-4 pb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Take your tests to grow</h2>
              <div className="space-y-3">
                <Card
                  onClick={() => navigate('/topics')}
                  className="rounded-2xl border-2 border-blue-200"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">

                      {/* LEFT SIDE */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1 group">
                          <h3 className="text-lg font-semibold text-blue-900">
                            Select your test
                          </h3>

                          {/* Micro-interaction arrow */}
                          <ChevronRight className="w-4 h-4 text-gray-700 transition-transform duration-200 group-hover:translate-x-0.5" />
                        </div>

                        <p className="text-sm text-gray-600">
                          Scheduled Tests • Quick Tests • Build Your Own Tests and more
                        </p>
                      </div>

                      {/* RIGHT-SIDE ICON */}
                      <div className="ml-3">
                        <div className="p-2 rounded-xl bg-blue-50 border border-blue-100">
                          <ClipboardList className="w-6 h-6 text-blue-600" />
                        </div>
                      </div>

                    </div>
                  </CardContent>
                </Card>

                {/* NEW: Bookmarked Questions Card */}
                <Card
                  onClick={() => navigate('/bookmarks')}
                  className="rounded-2xl border-2 border-amber-200"
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">

                      {/* LEFT SIDE */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-2 mb-1 group">
                          <h3 className="text-lg font-semibold text-amber-900">
                            Bookmarked Questions
                          </h3>

                          {/* Micro-interaction arrow */}
                          <ChevronRight className="w-4 h-4 text-gray-700 transition-transform duration-200 group-hover:translate-x-0.5" />
                        </div>

                        <p className="text-sm text-gray-600">
                          Review questions you bookmarked during tests
                        </p>
                      </div>

                      {/* RIGHT-SIDE ICON */}
                      <div className="ml-3">
                        <div className="p-2 rounded-xl bg-amber-50 border border-amber-100">
                          <Bookmark className="w-6 h-6 text-amber-600" />
                        </div>
                      </div>

                    </div>
                  </CardContent>
                </Card>

              </div>
            </div>

            {/* Visual separator */}
            <div className="px-4 pb-6">
              <div className="h-px bg-gradient-to-r from-transparent via-gray-200 to-transparent"></div>
            </div>

            {/* ============================================================================= */}
            {/* AI TUTOR CHAT SECTION */}
            {/* ============================================================================= */}
            <div className="px-4 pb-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Learn how to improve with your own assisstant</h2>
              <MiniChatbot className="max-w-full" />
            </div>
          </div>
        </div>
        {/* End content wrapper */}
      </div>

      {/* ============================================================================= */}
      {/* MOBILE DOCK */}
      {/* ============================================================================= */}
      <MobileDock />
    </div>
  );
}






